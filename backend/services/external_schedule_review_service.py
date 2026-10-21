"""Read-only reconciliation of signed transient previews. No file/DB/cache writes."""
import base64
import hashlib
import hmac
import json
import secrets

from schemas.external_schedule import ExternalRow, ReviewProjection, ReviewMeeting, ResourceResolution, Discrepancy
from services import external_schedule_service as intake

# Only a process key is retained; source batches exist in caller-held receipts,
# not in server storage. Restarts invalidate receipts. This is not authentication.
_PROCESS_KEY = secrets.token_bytes(32)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def reference_digest(ctx):
    canonical = {name: sorted(values, key=lambda value: _json(value)) for name, values in ctx.items()}
    return hashlib.sha256(_json(canonical)).hexdigest()


def sign_preview(result, ctx):
    source = {"version": 1, "reference_digest": reference_digest(ctx),
              "source_kind": result.source_kind, "source_name": result.source_name,
              "source_sha256": result.source_sha256, "source_parser_version": result.parser_version,
              "rows": [{"source_row": row.source_row, "original": row.input.model_dump()} for row in result.rows]}
    raw = _json(source)
    token = base64.urlsafe_b64encode(raw).decode() + "." + hmac.new(_PROCESS_KEY, raw, hashlib.sha256).hexdigest()
    if len(token) > 1600000:
        intake.fail("REVIEW_SNAPSHOT_TOO_LARGE", "This batch is too large for transient reconciliation. Split the preview.")
    return token


def _source(token):
    try:
        encoded, signature = token.split(".")
        raw = base64.b64decode(encoded, altchars=b"-_", validate=True)
        expected = hmac.new(_PROCESS_KEY, raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        source = json.loads(raw)
        if source["version"] != 1 or source["source_parser_version"] != "d3.1":
            raise ValueError()
        return source
    except (ValueError, KeyError, TypeError, UnicodeError):
        intake.fail("PREVIEW_RECEIPT_INVALID", "The preview receipt is invalid or belongs to an earlier backend process. Preview the source again.", 409)


def resolve(value, choices, field, selected=None):
    """Only select existing IDs; ambiguous labels never choose a first record."""
    if selected is not None:
        candidates = [r for r in choices if r["id"] == selected]
        if len(candidates) != 1:
            intake.fail("INVALID_RESOURCE_MAPPING", "A selected resource ID is unavailable or ambiguous. No mappings were applied.")
        return ResourceResolution(original=value, id=selected, label=candidates[0]["label"], state="resolved", method="explicit")
    if not value.strip():
        return ResourceResolution(original=value, id=None, label=None,
                                  state="unresolved" if field == "sections" else "missing_optional")
    if not choices:
        return ResourceResolution(original=value, id=None, label=None, state="unsupported")
    normalized = intake.key(value)
    # Section codes and room natural keys are authoritative lookup keys already.
    # Instructor display names are suggestions only, requiring explicit selection.
    recognized = [r for r in choices if normalized == intake.key(r["id"])
                  or field == "sections" and normalized == intake.key(r["label"])
                  or field == "instructor" and r.get("alias") and normalized == intake.key(r["alias"])]
    candidates = recognized or [r for r in choices if normalized == intake.key(r["label"])]
    ids = sorted({r["id"] for r in candidates})
    if len(ids) > 1 or len(candidates) > 1:
        return ResourceResolution(original=value, id=None, label=None, state="ambiguous", candidate_ids=ids)
    if recognized:
        item = recognized[0]
        return ResourceResolution(original=value, id=item["id"], label=item["label"], state="resolved", method="recognized")
    return ResourceResolution(original=value, id=None, label=None, state="unresolved", candidate_ids=ids)


def project(payload):
    source = _source(payload.review_token)
    ctx = intake.safe_context()
    if source["reference_digest"] != reference_digest(ctx):
        intake.fail("PREVIEW_REFERENCES_CHANGED", "Recognized resources or legacy input references changed. Reload metadata and preview the source again.", 409)
    originals = [ExternalRow(**row["original"]) for row in source["rows"]]
    lines = [row["source_row"] for row in source["rows"]]
    mappings = {}
    for mapping in payload.mappings:
        if mapping.source_row not in lines or mapping.source_row in mappings:
            intake.fail("INVALID_ROW_MAPPING", "Mappings must refer once to an original source row.")
        mappings[mapping.source_row] = mapping
    # Reuse all existing format/domain checks, replacing only resource-dependent
    # findings so original labels cannot override explicit canonical identities.
    base = intake.validate(originals, source["source_kind"], source["source_name"], source_rows=lines, _context=ctx, _sign=False)
    replaced = {"DUPLICATE_SECTION", "DUPLICATE_ENTRY", "SECTION_OVERLAP", "ROOM_OVERLAP", "INSTRUCTOR_OVERLAP",
                "EXISTING_FIXED_SECTION_OVERLAP"}
    output = []
    count = 0

    def issue(row, code, severity, field, message, related=()):
        nonlocal count
        count += 1
        if count > intake.MAX_ISSUES:
            intake.fail("TOO_MANY_DISCREPANCIES", "This batch has too many reconciliation findings. Split the preview.")
        row.discrepancies.append(Discrepancy(code=code, severity=severity, field=field, message=message, related_rows=list(related)))

    for original in base.rows:
        mapping = mappings.get(original.source_row)
        selected = {}
        if mapping:
            for slot in mapping.sections:
                if slot.reference_index >= len(original.input.sections) or slot.reference_index in selected:
                    intake.fail("INVALID_SECTION_MAPPING", "Each mapping must identify one existing source section reference.")
                selected[slot.reference_index] = slot.target_id
        row = ReviewMeeting(source_row=original.source_row, original=original.input, status=original.status,
                            sections=[resolve(value, ctx["sections"], "sections", selected.get(index)) for index,value in enumerate(original.input.sections)],
                            room=resolve(original.input.room, ctx["rooms"], "room", mapping.room_id if mapping else None),
                            instructor=resolve(original.input.instructor, ctx["instructors"], "instructor", mapping.instructor_id if mapping else None),
                            discrepancies=[d for d in original.discrepancies if d.code not in replaced and not d.code.startswith("UNRESOLVED_")],
                            calendar_supported=False)
        output.append(row)
        count += len(row.discrepancies)
        start, end = intake._minutes(row.original.start), intake._minutes(row.original.end)
        row.calendar_supported = (start is not None and end is not None and start < end
                                  and bool(row.original.days) and len(set(row.original.days)) == len(row.original.days)
                                  and all(day in intake.DAYS for day in row.original.days))
        resources = [("sections", r) for r in row.sections] + [("room", row.room), ("instructor", row.instructor)]
        for field, resource in resources:
            if resource.state != "resolved":
                issue(row, resource.state.upper() + "_" + field.upper().rstrip("S"), "review", field,
                      "Resource state: " + resource.state + ". No identity was inferred; coverage is incomplete or the optional resource is absent.")
            elif resource.method == "explicit":
                issue(row, "EXPLICIT_RESOURCE_MAPPING", "review", field, "Administrator selected an existing resource for this preview only. The source text is preserved.")
        section_ids = [r.id for r in row.sections if r.id is not None]
        if len(section_ids) != len(set(section_ids)):
            issue(row, "DUPLICATE_SECTION", "error", "sections", "Source references map to the same recognized section more than once.")
        if row.calendar_supported:
            for fixed in ctx["fixed"]:
                match = resolve(fixed["section"], ctx["sections"], "sections")
                a,b = intake._minutes(fixed["start"]),intake._minutes(fixed["end"])
                if match.id in section_ids and fixed["day"] in row.original.days and a is not None and b is not None and start < b and a < end:
                    issue(row, "EXISTING_FIXED_SECTION_OVERLAP", "review", "sections",
                          "Mapped section may overlap a loaded legacy fixed interval. Academic dates remain unverified; no availability was changed.")
    duplicates = {}
    for row in output:
        # Include original unresolved text so unknown resources cannot be equated
        # by an invented ID. Known resources compare canonical IDs only.
        resource_key = lambda r: ("id",r.id) if r.id else ("source", intake.key(r.original))
        duplicate = (intake.key(row.original.supplier), intake.key(row.original.subject_code),
                     tuple(sorted(resource_key(r) for r in row.sections)), tuple(sorted(row.original.days)),
                     row.original.start,row.original.end,resource_key(row.room),resource_key(row.instructor),intake.key(row.original.academic_term))
        if duplicate in duplicates:
            other = duplicates[duplicate]
            issue(row,"DUPLICATE_ENTRY","error","row","Duplicate meeting in the reconciled preview.",[other.source_row])
            issue(other,"DUPLICATE_ENTRY","error","row","Duplicate meeting in the reconciled preview.",[row.source_row])
        else:
            duplicates[duplicate] = row
    for index,row in enumerate(output):
        if not row.calendar_supported:
            continue
        start,end = intake._minutes(row.original.start),intake._minutes(row.original.end)
        for other in output[:index]:
            if not other.calendar_supported or not set(row.original.days) & set(other.original.days):
                continue
            a,b = intake._minutes(other.original.start),intake._minutes(other.original.end)
            if not (start < b and a < end):
                continue
            clashes = []
            if {r.id for r in row.sections if r.id} & {r.id for r in other.sections if r.id}:
                clashes.append(("SECTION_OVERLAP","sections"))
            elif {intake.key(r.original) for r in row.sections if not r.id} & {intake.key(r.original) for r in other.sections if not r.id}:
                clashes.append(("POSSIBLE_UNRESOLVED_SECTION_OVERLAP","sections"))
            for field in ("room","instructor"):
                left,right = getattr(row,field),getattr(other,field)
                if left.id is not None and left.id == right.id:
                    clashes.append((field.upper()+"_OVERLAP",field))
            for code,field in clashes:
                severity = "review" if code.startswith("POSSIBLE_") else "error"
                message = "Potential same-week resource overlap; dates remain unverified."
                issue(row,code,severity,field,message,[other.source_row]);issue(other,code,severity,field,message,[row.source_row])
    for row in output:
        row.status = "invalid" if any(d.severity=="error" for d in row.discrepancies) else "needs_review" if row.discrepancies else row.original.status
    return ReviewProjection(source_kind=source["source_kind"],source_name=source["source_name"],
                            source_sha256=source["source_sha256"],reference_digest=source["reference_digest"],rows=output)
