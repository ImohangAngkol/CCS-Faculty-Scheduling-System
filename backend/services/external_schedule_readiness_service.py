"""Central D7 readiness policy and fresh detached validation, never confirmation."""
import base64
from datetime import date, datetime, timezone
import hashlib
import hmac
import json
import re

from schemas.external_schedule import ExternalRow, ReviewRequest
from schemas.external_readiness import ReadinessAssessment, ReadinessFinding, ReadinessHandoff
from services import external_schedule_service as intake, external_schedule_review_service as review
from services import external_schedule_preview_lifecycle as lifecycle
from services import external_schedule_verification_service as authority
from services.evidence_sanitization import sanitize

POLICY_VERSION = "d7.1"
SUPPORTED_TIMEZONE = "Asia/Manila"
MAX_DATE_SPAN_DAYS = 370
IGNORED_PROTOTYPE_FINDINGS = {"TERM_UNKNOWN", "TERM_UNVERIFIED", "SUBJECT_NOT_IN_CATALOG", "EXPLICIT_RESOURCE_MAPPING"}


def fingerprint(value):
    return hashlib.sha256(review._json(value)).hexdigest()


def _safe(value):
    if isinstance(value, dict):
        for child in value.values(): _safe(child)
    elif isinstance(value, list):
        for child in value: _safe(child)
    elif isinstance(value, str) and (len(value) > 1000 or intake._unsafe_text(value) or sanitize(value) != value):
        intake.fail("UNSAFE_COMPLETION_METADATA", "Completion contains unsafe or oversized text. No assessment was accepted.")


def evaluate(payload):
    """Pure policy output; caller enforces session/revision and issues the receipt."""
    metadata = payload.metadata
    _safe(metadata.model_dump())
    original = review.project(payload)
    source_fingerprint = fingerprint(original.model_dump())
    findings = []
    def add(code, field, explanation, action, row=None, warning=False, related=()):
        if len(findings) >= intake.MAX_ISSUES: intake.fail("TOO_MANY_READINESS_FINDINGS", "Split the preview to review all findings safely.")
        findings.append(ReadinessFinding(code=code, severity="warning" if warning else "blocker", field=field,
            source_row=row, related_rows=list(related), explanation=explanation, action=action))
    for field in ("supplier", "source_reference", "evidence_reference", "academic_year", "term", "effective_start", "effective_end", "timezone"):
        if not getattr(metadata, field).strip():
            add("MISSING_"+field.upper(), field, "Required completion metadata is missing.", "Supply sourced "+field.replace('_',' ')+"; it remains an administrator claim until verified.")
    if not metadata.source_revision:
        add("SOURCE_REVISION_UNAVAILABLE", "source_revision", "No source revision/version was supplied.", "Obtain a revision reference where available.", warning=True)
    year = re.fullmatch(r"(\d{4})-(\d{4})", metadata.academic_year)
    if metadata.academic_year and (not year or int(year[2]) != int(year[1])+1):
        add("INVALID_ACADEMIC_YEAR", "academic_year", "Use an explicit consecutive YYYY-YYYY academic year.", "Verify the academic-year label with the supplier.")
    start = end = None
    try:
        start, end = date.fromisoformat(metadata.effective_start), date.fromisoformat(metadata.effective_end)
        if start.isoformat() != metadata.effective_start or end.isoformat() != metadata.effective_end or end < start or (end-start).days > MAX_DATE_SPAN_DAYS:
            raise ValueError()
        if year and (start.year < int(year[1]) or end.year > int(year[2])): raise ValueError()
    except ValueError:
        add("INVALID_EFFECTIVE_DATES", "effective_start/effective_end", "An ordered ISO date window within the academic year and 370-day prototype bound is required.", "Supply verified effective dates; do not infer them from filenames.")
        start = end = None
    if metadata.timezone and metadata.timezone != SUPPORTED_TIMEZONE:
        add("UNSUPPORTED_TIMEZONE", "timezone", "Only explicit Asia/Manila local weekly patterns are supported.", "Obtain a supported timezone statement; no conversion was inferred.")
    if metadata.recurrence != "weekly":
        add("RECURRENCE_UNRESOLVED", "recurrence", "Weekly applicability is unknown or unsupported.", "Clarify the weekly recurrence with evidence.")
    if metadata.exceptions != "none_reported" or metadata.exception_notes.strip():
        add("CALENDAR_EXCEPTIONS_UNRESOLVED", "exceptions", "Exceptions are unknown, listed or unsupported; this prototype cannot validate date-specific exceptions.", "Resolve exception applicability through an authorized source; listed exceptions remain blocked.")
    rows_by_line = {r.source_row:r for r in metadata.rows}
    lines = {r.source_row for r in original.rows}
    if len(rows_by_line) != len(metadata.rows) or set(rows_by_line)-lines:
        intake.fail("INVALID_COMPLETION_ROWS", "Completion rows must refer once to original source-row references.")
    candidate_rows, candidate_maps = [], []
    for item in original.rows:
        line = item.source_row; completed = rows_by_line.get(line)
        values = item.original.model_dump()
        for field, value in (("supplier",metadata.supplier),("source_reference",metadata.source_reference),("academic_term",metadata.term)):
            if value:
                if values[field] and intake.key(values[field]) != intake.key(value) and original.legacy is None:
                    add("SOURCE_METADATA_CONTRADICTION", field, "Completion contradicts a nonblank original source field.", "Resolve the source discrepancy; the original field has not been overwritten.", line)
                values[field] = value
        if not completed:
            add("ROW_COMPLETION_MISSING", "row", "Meeting metadata has not been completed.", "Complete component, sharing and resource applicability for this source row.", line)
        else:
            if completed.title:
                values["title"] = completed.title
                if completed.title != item.original.title:
                    add("ADMINISTRATOR_TITLE_COMPLETION", "title", "Title is an administrator proposal, separate from the original source.", "Verify the title evidence before subsequent confirmation review.", line, warning=True)
            if not completed.evidence_reference:
                add("ROW_EVIDENCE_MISSING", "evidence_reference", "Meeting completion has no supporting evidence reference.", "Supply a source clarification reference; a typed reference alone is not verification.", line)
            if completed.component == "unknown":
                add("COMPONENT_UNRESOLVED", "component", "Meeting/component type is unknown.", "Identify the lecture, laboratory or external-meeting component.", line)
            if completed.section_ids:
                if len(set(completed.section_ids)) != len(completed.section_ids):
                    add("INCONSISTENT_SECTION_MAPPING", "sections", "Repeated selected section identities.", "Select each recognized affected section once.", line)
                values["sections"] = completed.section_ids
                for mapping in payload.mappings:
                    if mapping.source_row == line and any(slot.target_id not in completed.section_ids for slot in mapping.sections):
                        add("INCONSISTENT_SECTION_MAPPING", "sections", "D4 selections contradict completed section identities.", "Reconcile or clear the conflicting D4 mapping explicitly.", line)
            count = len(values["sections"])
            if completed.shared == "unknown" or completed.shared == "single_section" and count != 1 or completed.shared == "shared" and count < 2:
                add("SHARING_UNRESOLVED", "sections", "Single/shared commitment applicability is unresolved or inconsistent with selected sections.", "Clarify all affected CCS sections and the sharing declaration.", line)
            proposal = completed.proposed_meeting
            if proposal is not None:
                if not proposal.reason.strip() or not proposal.evidence_reference.strip():
                    add("CORRECTION_EVIDENCE_MISSING", "proposed_meeting", "A meeting correction requires an explicit reason and evidence reference.", "Obtain source clarification; unsupported corrections cannot be silently accepted.", line)
                values.update(days=proposal.days, start=proposal.start, end=proposal.end)
                add("PROPOSED_MEETING_CORRECTION", "proposed_meeting", "Candidate day/time differs by explicit administrator proposal; original source remains intact.", "Review the original and proposal with its evidence.", line, warning=True)
        candidate_rows.append(ExternalRow(**values))
        for mapping in payload.mappings:
            if mapping.source_row == line:
                candidate_maps.append(mapping.model_copy(update={"sections": []}) if completed and completed.section_ids else mapping)
    candidate = intake.validate(candidate_rows, original.source_kind, original.source_name,
                                source_rows=[r.source_row for r in original.rows])
    effective = review.project(ReviewRequest(review_token=candidate.review_token, mappings=candidate_maps))
    if effective.reference_digest != original.reference_digest:
        intake.fail("PREVIEW_REFERENCES_CHANGED", "Reference data changed during assessment. Reimport and assess again.", 409)
    effective.source_sha256 = original.source_sha256
    for item in effective.rows:
        line = item.source_row; completed = rows_by_line.get(line)
        if not item.sections or any(r.state != "resolved" for r in item.sections):
            add("SECTION_UNRESOLVED", "sections", "Every affected section requires a recognized identity.", "Explicitly reconcile sections; no UUID is generated from a name or year.", line)
        for field in ("room", "instructor"):
            applicability = getattr(completed,field+"_applicability", "unknown")
            resource = getattr(item,field)
            if applicability == "unknown":
                add("RESOURCE_APPLICABILITY_UNKNOWN", field, "Missing resource data does not establish non-applicability.", "Declare applicability and provide source evidence or a recognized identity.", line)
            elif applicability == "applicable" and resource.state != "resolved":
                add("APPLICABLE_RESOURCE_UNRESOLVED", field, "Applicable resource is unknown or ambiguous.", "Map a recognized resource using D4 reconciliation.", line)
            elif applicability == "not_applicable" and (resource.original.strip() or resource.id):
                add("RESOURCE_APPLICABILITY_CONTRADICTION", field, "Not-applicable declaration contradicts a supplied or mapped resource.", "Resolve the declaration against source and selected mappings.", line)
        for issue in item.discrepancies:
            if issue.code in IGNORED_PROTOTYPE_FINDINGS:
                if issue.code == "SUBJECT_NOT_IN_CATALOG":
                    add(issue.code,issue.field,"External subject is outside the prototype catalog.","Verify its code/title through source evidence.",line,warning=True)
                continue
            field = "instructor" if issue.field == "instructor" else "room" if issue.field == "room" else None
            if field and issue.code.startswith("MISSING_OPTIONAL_") and completed and getattr(completed,field+"_applicability") == "not_applicable": continue
            add(issue.code,issue.field,issue.message,"Resolve this discrepancy before institutional confirmation review.",line,related=issue.related_rows)
        if not item.calendar_supported:
            add("MEETING_NOT_SUPPORTED", "days/start/end", "Candidate meeting cannot be represented by the weekly review.", "Resolve invalid or ambiguous day/time information.", line)
        if start is not None and end is not None and item.calendar_supported:
            weekdays = {"M":0,"T":1,"W":2,"TH":3,"F":4,"S":5}
            span = min((end-start).days+1,7)
            occurring = {(start.weekday()+i)%7 for i in range(span)}
            if not any(weekdays[d] in occurring for d in item.original.days):
                add("NO_MEETING_IN_DATE_WINDOW", "effective_dates", "The date window contains none of the declared weekly meeting days.", "Clarify date applicability.", line)
    binding = fingerprint({"policy":POLICY_VERSION,"original":original.model_dump(),"effective":effective.model_dump(),"metadata":metadata.model_dump()})
    material_fields = ('subject_code', 'title', 'sections', 'days', 'start', 'end', 'room', 'instructor')
    changed_rows = frozenset(a.source_row for a,b in zip(original.rows,effective.rows) if
        any(getattr(a.original,key) != getattr(b.original,key) for key in material_fields)
        or [r.id for r in a.sections] != [r.id for r in b.sections] or a.room.id != b.room.id or a.instructor.id != b.instructor.id)
    trust = authority.evaluate_trust(authority.EvidenceContext(input_fingerprint=binding, source_fingerprint=source_fingerprint,
        preview_fingerprint=hashlib.sha256(payload.review_token.encode()).hexdigest(), supplier=metadata.supplier,
        source_revision=metadata.source_revision, academic_year=metadata.academic_year, term=metadata.term,
        subjects={r.source_row:r.original.subject_code for r in effective.rows}, changed_rows=changed_rows))
    valid_verification = trust.outcome == 'VERIFIED'
    if not valid_verification:
        add("AUTHORITATIVE_VERIFICATION_REQUIRED", "verification", "No trusted institutional policy/evidence covers this exact source, metadata, mappings and recurrence. Administrator text cannot grant verified status.", "Obtain an authorized verification policy/provider. This deployment has none; readiness remains blocked.")
    for finding in trust.findings:
        add('D8_'+finding.code, 'evidence_trust', finding.explanation, finding.action, finding.source_row)
    blockers = sum(f.severity=="blocker" for f in findings)
    result = ReadinessAssessment(status="BLOCKED" if blockers else "READY", metadata=metadata,
        verification_status="verified_for_readiness" if valid_verification else "unavailable" if trust.outcome == 'PROVIDER_UNAVAILABLE' else "requires_verification",
        verification_reference=trust.evidence_id if valid_verification else None,
        authority_policy_version=trust.policy_revision if valid_verification else None,
        source_fingerprint=source_fingerprint, input_fingerprint=binding, reference_digest=original.reference_digest,
        assessment_fingerprint="", blocker_count=blockers, warning_count=len(findings)-blockers, findings=findings,
        effective_review=effective, original_row_count=len(original.rows), assessed_at="", expires_at="", evidence_trust=trust)
    # Time/receipt never make equivalent content acquire a different identity.
    result.assessment_fingerprint = "d7-"+fingerprint(result.model_dump(exclude={"assessment_fingerprint","assessed_at","expires_at","assessment_receipt"}))
    return original, result


def _receipt(value):
    raw = review._json(value)
    return base64.urlsafe_b64encode(raw).decode()+"."+hmac.new(review._PROCESS_KEY,raw,hashlib.sha256).hexdigest()


def assess(payload, owner):
    head = lifecycle.current(payload.review_token, owner)
    _, result = evaluate(payload)
    lifecycle.record(payload.review_token, owner, head["revision"], result.assessment_fingerprint)
    result.assessed_at = datetime.now(timezone.utc).isoformat()
    result.expires_at = _expires(result, head['expires'])
    result.assessment_receipt = _receipt({"kind":"d7-assessment","owner":owner,"revision":head["revision"],"fingerprint":result.assessment_fingerprint,
                                         "source":head["source"],"expires":head["expires"]})
    return result


def prepare_handoff(payload, owner):
    lifecycle.current(payload.review_token,owner)
    try:
        encoded, signature = payload.assessment_receipt.split('.')
        raw = base64.b64decode(encoded,altchars=b'-_',validate=True)
        if not hmac.compare_digest(signature,hmac.new(review._PROCESS_KEY,raw,hashlib.sha256).hexdigest()): raise ValueError()
        receipt = json.loads(raw)
        if (set(receipt) != {'kind','owner','revision','fingerprint','source','expires'} or receipt['kind'] != 'd7-assessment'
                or receipt['owner'] != owner or type(receipt['revision']) is not int
                or not re.fullmatch(r'd7-[a-f0-9]{64}',receipt['fingerprint'])
                or not re.fullmatch(r'[a-f0-9]{64}',receipt['source']) or type(receipt['expires']) not in {int,float}): raise ValueError()
    except (ValueError,KeyError,TypeError):
        intake.fail("READINESS_RECEIPT_INVALID", "Assess this preview again in the current session.",409)
    head = lifecycle.require_assessment(payload.review_token,owner,receipt['revision'],receipt['fingerprint'])
    if receipt.get('source') != head['source'] or receipt.get('expires') != head['expires']:
        intake.fail("READINESS_STALE", "Assessment source or lifetime changed. Assess again.",409)
    original, result = evaluate(payload)
    if result.assessment_fingerprint != receipt['fingerprint']:
        intake.fail("READINESS_STALE", "Source, metadata, mappings or verification changed. Assess again.",409)
    lifecycle.require_assessment(payload.review_token,owner,receipt['revision'],receipt['fingerprint'])
    result.assessed_at = datetime.now(timezone.utc).isoformat()
    result.expires_at = _expires(result, head['expires'])
    return ReadinessHandoff(preview_id="d5-"+fingerprint({"review":original.model_dump(),"readiness":result.model_dump()}),
        revalidated_at=datetime.now(timezone.utc),review=original,readiness=result)


def _expires(result, session_expiry):
    expiry = datetime.fromtimestamp(session_expiry,timezone.utc)
    if result.evidence_trust and result.evidence_trust.valid_until:
        expiry = min(expiry, authority.instant(result.evidence_trust.valid_until))
    return expiry.isoformat()
