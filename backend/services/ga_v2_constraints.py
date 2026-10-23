"""Immutable D10 constraints and a fresh, locked D8/D9 authority boundary.

No deployment provider is configured here. No engine, connection or schema is
created at import. Clients cannot supply catalogs, mappings or authority flags.
"""
from contextlib import contextmanager
from datetime import date
import copy
import re
import threading
from typing import Literal
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text

from confirmation_models import ExternalRecord, ExternalRevision, ConfirmationEvent
from schemas.external_readiness import CompletionMetadata
from schemas.external_schedule import ReviewProjection
from services import external_confirmation_service as ledger
from services import external_schedule_verification_service as evidence
from services import confirmation_authority_service as confirmer
from services.external_schedule_readiness_service import fingerprint, POLICY_VERSION

DAYS = dict(zip(("M", "T", "W", "TH", "F", "S"),
                ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday")))


class ConstraintError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def reject(code, message):
    raise ConstraintError(code, message)


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Catalog(Frozen):
    """Institution-supplied term/runtime mapping, never inferred from labels."""
    academic_year: str
    term: str
    effective_start: str
    effective_end: str
    revision: str
    input_fingerprint: str
    template_digest: str
    sections: tuple[tuple[str, str], ...]  # authoritative ID -> exact runtime code
    faculty: tuple[tuple[str, str], ...]
    rooms: tuple[tuple[str, str], ...]


class Head(Frozen):
    record_id: str
    revision_id: str
    event_id: str
    version: int
    content_digest: str
    evidence_digest: str
    source_sha256: str
    source_hash_kind: Literal["original_file", "canonical_manual_content"] = "original_file"


class Commitment(Frozen):
    record_id: str
    revision_id: str
    source_row: int
    source_sha256: str
    source_hash_kind: Literal["original_file", "canonical_manual_content"] = "original_file"
    subject: str
    day: str
    start: int
    end: int
    sections: tuple[str, ...]
    faculty: str | None
    room: str | None


class Snapshot(Frozen):
    version: Literal["gec-constraints-v2.1"] = "gec-constraints-v2.1"
    catalog: Catalog
    heads: tuple[Head, ...]
    commitments: tuple[Commitment, ...]

    @property
    def digest(self):
        return ledger.digest(self.model_dump(mode="json"))


def minutes(value):
    if not re.fullmatch(r"\d{1,2}:\d{2}", value):
        reject("INVALID_TIME", "An explicit local hour and minute is required.")
    hour, minute = map(int, value.split(":"))
    if hour > 23 or minute > 59:
        reject("INVALID_TIME", "Meeting time is outside the local day.")
    return hour*60+minute


def overlap(a, b, c, d):
    return a < d and c < b


def calendar(resource, day):
    return getattr(resource, "time_blocks_"+DAYS[day])


def template_fingerprint(templates):
    from services.ga_checkpoint_service import encode_graph
    graph=encode_graph(templates)
    for node in graph["nodes"]:
        if node["kind"]=="set":
            node["items"].sort(key=ledger.canonical)
    return ledger.digest(graph)


def validate_catalog(catalog, templates):
    from services.ga_progress_service import input_fingerprint
    if not catalog.revision or catalog.input_fingerprint != input_fingerprint():
        reject("CATALOG_INPUT_CHANGED", "The authoritative term catalog does not bind current scheduling inputs.")
    if catalog.template_digest != template_fingerprint(templates):
        reject("CATALOG_INPUT_CHANGED", "The authoritative term catalog does not bind these runtime templates.")
    year = re.fullmatch(r"(\d{4})-(\d{4})", catalog.academic_year)
    try:
        first, last = date.fromisoformat(catalog.effective_start), date.fromisoformat(catalog.effective_end)
        valid = year and int(year[2]) == int(year[1])+1 and int(year[1]) <= first.year <= last.year <= int(year[2]) and first <= last and (last-first).days<=370
    except ValueError:
        valid = False
    if not valid or not catalog.term.strip():
        reject("TERM_UNSUPPORTED", "A sourced year, term and ordered calendar window are required.")
    expected = ({str(s.section.code) for s in templates[0]}, {str(f.code) for f in templates[1]},
                {str(r.name) for r in templates[2]})
    for mapping, required in zip((catalog.sections, catalog.faculty, catalog.rooms), expected):
        if (len(dict(mapping)) != len(mapping) or len({v for _, v in mapping}) != len(mapping)
                or not required <= {v for _, v in mapping} or any(not k or not v for k, v in mapping)):
            reject("RESOURCE_MAPPING_REQUIRED", "Explicit, unambiguous authoritative runtime mappings are required.")


def validate_snapshot(snapshot, templates):
    catalog = snapshot.catalog
    validate_catalog(catalog, templates)
    sections = {str(s.section.code): s.section for s in templates[0]}
    resources = {"section": sections, "faculty": {str(f.code): f for f in templates[1]},
                 "room": {str(r.name): r for r in templates[2]}}
    maps = {"section": dict(catalog.sections), "faculty": dict(catalog.faculty), "room": dict(catalog.rooms)}
    seen, occupied = set(), []
    if not snapshot.heads or not snapshot.commitments:
        reject("NO_CONFIRMED_CONSTRAINTS", "No complete confirmed commitment set is available for this term.")
    heads = {(h.record_id,h.revision_id):h for h in snapshot.heads}
    if len(heads)!=len(snapshot.heads):
        reject("INVALID_PROVENANCE", "Repeated current revision identities are unsupported.")
    first,last = date.fromisoformat(catalog.effective_start),date.fromisoformat(catalog.effective_end)
    occurring={(first.weekday()+i)%7 for i in range(min(7,(last-first).days+1))}
    for item in snapshot.commitments:
        head=heads.get((item.record_id,item.revision_id))
        if head is None or item.source_sha256!=head.source_sha256 or item.source_hash_kind!=head.source_hash_kind or not re.fullmatch(r"[a-f0-9]{64}",item.source_sha256):
            reject("INVALID_PROVENANCE", "A fixed row does not bind its confirmed head and source hash.")
        if item.day not in DAYS or not 450 <= item.start < item.end <= 1320 or item.start % 30 or item.end % 30:
            reject("INVALID_COMMITMENT", "Fixed meetings must use supported days and the 30-minute calendar within 07:30-22:00.")
        if list(DAYS).index(item.day) not in occurring:
            reject("CALENDAR_CONTAINMENT", "The sourced date window contains none of this meeting's weekly day.")
        if item.source_row <= 0 or not item.sections or len(set(item.sections)) != len(item.sections):
            reject("INVALID_PROVENANCE", "Each commitment requires an original source row and distinct authoritative sections.")
        duplicate = (item.subject, item.day, item.start, item.end, tuple(sorted(item.sections)), item.faculty, item.room)
        if duplicate in seen:
            reject("DUPLICATE_COMMITMENT", "The confirmed set contains duplicate fixed commitments; nothing was omitted.")
        seen.add(duplicate)
        for kind, ids in (("section", item.sections), ("faculty", (item.faculty,) if item.faculty else ()),
                          ("room", (item.room,) if item.room else ())):
            for stable_id in ids:
                code = maps[kind].get(stable_id)
                resource = resources[kind].get(code)
                if resource is None:
                    reject("RESOURCE_MAPPING_REQUIRED", "A confirmed applicable resource has no exact runtime identity.")
                blocks = calendar(resource, item.day)
                actual = {(minutes(b.start_time), minutes(b.end_time)) for b in blocks}
                if not {(n, n+30) for n in range(item.start, item.end, 30)} <= actual:
                    reject("CALENDAR_CONTAINMENT", "A fixed resource is outside the authoritative runtime calendar.")
                if any(day == item.day and other_kind == kind and other_id == stable_id and overlap(item.start,item.end,start,end)
                       for day, other_kind, other_id, start, end in occupied):
                    reject("FIXED_RESOURCE_CONFLICT", "Confirmed commitments overlap on an authoritative resource.")
                occupied.append((item.day, kind, stable_id, item.start, item.end))
                if kind == "section" and any(getattr(b,"fixed_schedule",False) and overlap(item.start,item.end,minutes(b.start_time),minutes(b.end_time)) for b in blocks):
                    reject("EXISTING_FIXED_SECTION_CONFLICT", "A confirmed commitment overlaps an existing fixed section input; reconcile provenance first.")


def reduced_templates(snapshot, templates):
    """Remove fixed faculty/room slots; reset cannot recreate removed slots.

    Sections retain the original fixed-calendar contract. No subject is added.
    """
    validate_snapshot(snapshot, templates)
    subjects, faculty, rooms = copy.deepcopy(templates)
    mappings = {"section": dict(snapshot.catalog.sections), "faculty": dict(snapshot.catalog.faculty), "room": dict(snapshot.catalog.rooms)}
    for item in snapshot.commitments:
        for kind, group, attr in (("faculty", faculty, "code"), ("room", rooms, "name")):
            identity = getattr(item, kind)
            if identity is not None:
                resource = next(r for r in group if str(getattr(r,attr)) == mappings[kind][identity])
                setattr(resource, "time_blocks_"+DAYS[item.day], [b for b in calendar(resource,item.day)
                    if not overlap(item.start,item.end,minutes(b.start_time),minutes(b.end_time))])
        # Distinct section objects with the same identity must all be reserved.
        for subject in subjects:
            if str(subject.section.code) in {mappings["section"][i] for i in item.sections}:
                for block in calendar(subject.section,item.day):
                    if overlap(item.start,item.end,minutes(block.start_time),minutes(block.end_time)):
                        block.is_available = False
                        block.fixed_schedule = True
                        block.fixed_course = "D10:"+item.record_id+":"+str(item.source_row)
    return subjects, faculty, rooms


def external_conflict(candidate, snapshot):
    maps = {"section": dict(snapshot.catalog.sections), "faculty": dict(snapshot.catalog.faculty), "room": dict(snapshot.catalog.rooms)}
    for subject in candidate:
        for component in ("lecture", "laboratory"):
            room = getattr(subject, component+"_room", None)
            codes = {"section": str(subject.section.code), "faculty": str(getattr(subject.assigned_faculty,"code",None)),
                     "room": str(getattr(room,"name",None))}
            for day, block in getattr(subject,component+"_time_blocks"):
                for fixed in snapshot.commitments:
                    if day == fixed.day and overlap(minutes(block.start_time),minutes(block.end_time),fixed.start,fixed.end):
                        for kind, ids in (("section", fixed.sections), ("faculty", (fixed.faculty,) if fixed.faculty else ()), ("room", (fixed.room,) if fixed.room else ())):
                            if codes[kind] in {maps[kind][i] for i in ids}:
                                return "EXTERNAL_"+kind.upper()+"_CONFLICT"
    return None


def _read_snapshot(db, catalog, templates):
    records = db.scalars(select(ExternalRecord).where(ExternalRecord.academic_year==catalog.academic_year,
        ExternalRecord.term==catalog.term).order_by(ExternalRecord.id).limit(1001)).all()
    if len(records)>1000:
        reject("CONSTRAINT_SET_LIMIT", "The entire applicable ledger exceeds the supported bound; no partial set was used.")
    heads, commitments = [], []
    for record in records:
        # Reuse D9's full chain/digest checks, not the paginated display list.
        history=ledger.history(db, record.id)
        previous=None
        for decision in history["events"]:
            from uuid import UUID
            decided=db.get(ExternalRevision,UUID(decision["revision_id"]))
            if decided is None or decided.record_id!=record.id:
                reject("LEDGER_INTEGRITY", "A decision revision belongs to a different record.")
            if ((decision["action"]=="CONFIRM" and (str(decided.base_event_id) if decided.base_event_id else None)!=decision["previous_event_id"])
                    or (decision["action"]=="REVOKE" and (previous is None or previous["action"]!="CONFIRM" or previous["revision_id"]!=decision["revision_id"]))):
                reject("LEDGER_INTEGRITY", "A confirmation/revocation does not follow its declared revision base.")
            previous=decision
        event = db.get(ConfirmationEvent, record.head_event_id) if record.head_event_id else None
        if event is None or event.action != "CONFIRM":
            reject("CONFIRMATION_NOT_CURRENT", "Every applicable ledger record must have a current confirmed head.")
        revision, content = ledger.checked_revision(db, event.revision_id)
        if revision.record_id != record.id or event.record_id != record.id or event.sequence != record.version:
            reject("LEDGER_INTEGRITY", "Current record, event and revision identities disagree.")
        historical = ledger.checked_evidence(event.evidence_json, event.evidence_digest)
        if set(content) != {"version","review","metadata","candidate"} or content["version"]!="d9.1":
            reject("DURABLE_CONTENT_UNSUPPORTED", "The durable revision has an unsupported content contract.")
        original, candidate = (ReviewProjection.model_validate(content[k]) for k in ("review","candidate"))
        meta = CompletionMetadata.model_validate(content["metadata"])
        if original.model_dump()!=content["review"] or candidate.model_dump()!=content["candidate"] or meta.model_dump()!=content["metadata"]:
            reject("DURABLE_CONTENT_UNSUPPORTED", "Durable revision contains unrecognized or normalized-away fields.")
        if (record.academic_year,record.term,record.supplier)!=(meta.academic_year,meta.term,meta.supplier):
            reject("TERM_MISMATCH", "The durable record and revision term/supplier differ.")
        if (meta.timezone!="Asia/Manila" or meta.recurrence!="weekly" or meta.exceptions!="none_reported" or meta.exception_notes
                or meta.effective_start!=catalog.effective_start or meta.effective_end!=catalog.effective_end):
            reject("CALENDAR_APPLICABILITY_UNSUPPORTED", "Weekly constraints must cover the exact sourced runtime term window without unresolved exceptions.")
        if (candidate.source_sha256!=original.source_sha256
                or {r.source_row for r in original.rows}!={r.source_row for r in candidate.rows}
                or len(candidate.rows)!=len(original.rows)):
            reject("PROVENANCE_MISMATCH", "Original and effective source-row provenance differ.")
        if original.source_sha256 is None:
            if original.source_kind!="manual":
                reject("PROVENANCE_MISMATCH", "Imported files require their original source byte hash.")
            source_hash=ledger.digest(original.model_dump())
            source_hash_kind="canonical_manual_content"
        else:
            source_hash=original.source_sha256
            source_hash_kind="original_file"
        binding = fingerprint({"policy":POLICY_VERSION,"original":original.model_dump(),"effective":candidate.model_dump(),"metadata":meta.model_dump()})
        # New durable scope contract: a digest of canonical content, never a
        # recovered/expired session receipt or its historical VERIFIED label.
        original_rows={r.source_row:r for r in original.rows}
        fields=("subject_code","title","sections","days","start","end","room","instructor")
        changed=frozenset(row.source_row for row in candidate.rows if
            any(getattr(original_rows[row.source_row].original,key)!=getattr(row.original,key) for key in fields)
            or [r.id for r in original_rows[row.source_row].sections]!=[r.id for r in row.sections]
            or original_rows[row.source_row].room.id!=row.room.id or original_rows[row.source_row].instructor.id!=row.instructor.id)
        context = evidence.EvidenceContext(binding, fingerprint(original.model_dump()),
            ledger.digest({"contract":"d10-durable.1","revision":str(revision.id),"content":revision.content_digest}),
            meta.supplier,meta.source_revision,meta.academic_year,meta.term,
            {r.source_row:r.original.subject_code for r in candidate.rows},changed)
        trust = evidence.evaluate_trust(context)
        if trust.outcome!="VERIFIED":
            reject("EVIDENCE_NOT_CURRENT", "Fresh institutional evidence and issuer verification are unavailable or invalid.")
        if any(historical.get(k)!=getattr(trust,k) for k in ("evidence_id","evidence_revision","verified_issuer","policy_digest")):
            reject("EVIDENCE_IDENTITY_CHANGED", "The current evidence identity/policy differs from the confirmed decision.")
        authority = confirmer.require_authority(confirmer.ConfirmationContext(str(event.actor_id),"CONFIRM",str(event.id),str(record.id),
            str(revision.id),event.sequence-1,record.academic_year,record.term,record.supplier,revision.content_digest,event.evidence_digest))
        if authority is None or (authority.policy_reference,authority.policy_digest)!=(event.policy_reference,event.policy_digest):
            reject("CONFIRMATION_AUTHORITY_UNAVAILABLE", "The independent original confirmer's current mandate is not established.")
        heads.append(Head(record_id=str(record.id),revision_id=str(revision.id),event_id=str(event.id),version=record.version,
            content_digest=revision.content_digest,evidence_digest=event.evidence_digest,source_sha256=source_hash,source_hash_kind=source_hash_kind))
        completion = {r.source_row:r for r in meta.rows}
        if len(completion)!=len(meta.rows) or set(completion)!={r.source_row for r in candidate.rows}:
            reject("ROW_COMPLETION_MISMATCH", "Every original row requires exact durable completion metadata.")
        for row in candidate.rows:
            details = completion[row.source_row]
            if not row.calendar_supported or row.status=="invalid" or not row.sections or any(r.state!="resolved" or not r.id for r in row.sections):
                reject("UNRESOLVED_COMMITMENT", "A confirmed row has unsupported time or unresolved section identities.")
            if not details.evidence_reference or details.component=="unknown" or details.shared=="unknown":
                reject("UNRESOLVED_COMMITMENT", "Component, sharing and sourced completion must be explicit.")
            if ((details.shared=="single_section" and len(row.sections)!=1) or (details.shared=="shared" and len(row.sections)<2)
                    or (details.section_ids and set(details.section_ids)!={r.id for r in row.sections})):
                reject("RESOURCE_MAPPING_REQUIRED", "Durable sharing and explicit section selections disagree.")
            optional = {}
            for field in ("room","instructor"):
                resource = getattr(row,field); applicability = getattr(details,field+"_applicability")
                if applicability=="applicable" and resource.state=="resolved" and resource.id:
                    optional[field]=resource.id
                elif applicability=="not_applicable" and not resource.id and not resource.original:
                    optional[field]=None
                else:
                    reject("RESOURCE_MAPPING_REQUIRED", "An applicable or ambiguous resource is unresolved; missing is not non-applicable.")
            if len(set(row.original.days))!=len(row.original.days) or not row.original.days:
                reject("INVALID_COMMITMENT", "Meeting days must be explicit and distinct.")
            for day in row.original.days:
                commitments.append(Commitment(record_id=str(record.id),revision_id=str(revision.id),source_row=row.source_row,
                    source_sha256=source_hash,source_hash_kind=source_hash_kind,subject=row.original.subject_code,day=day,start=minutes(row.original.start),
                    end=minutes(row.original.end),sections=tuple(r.id for r in row.sections),faculty=optional["instructor"],room=optional["room"]))
    snapshot = Snapshot(catalog=catalog, heads=tuple(heads), commitments=tuple(commitments))
    validate_snapshot(snapshot, templates)
    return snapshot


class LedgerAuthority:
    """Server-owned adapter. Lock lifetime includes the guarded atomic write.

    SQLite is for owned fictional tests. PostgreSQL locking is implemented but
    remains unexecuted/unaccepted. No provider is installed in production.
    """
    def __init__(self, session_factory, catalog, templates):
        self.session_factory, self.catalog, self.templates = session_factory, catalog, templates
        self._active=threading.local()

    def recheck(self, expected):
        db=getattr(self._active,"db",None)
        if db is None:
            reject("CONSTRAINT_AUTHORITY_UNAVAILABLE", "A locked confirmation transaction is required before publication.")
        current=_read_snapshot(db,self.catalog,self.templates)
        if current.digest!=expected.digest:
            reject("CONSTRAINT_SET_CHANGED", "The pinned confirmation set changed before atomic publication.")

    @contextmanager
    def pinned(self, expected=None):
        try:
            with self.session_factory() as db:
                dialect = db.get_bind().dialect.name
                if dialect=="sqlite":
                    db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                elif dialect=="postgresql":
                    db.execute(text("SET LOCAL lock_timeout = '2s'"))
                    db.execute(text("SET LOCAL statement_timeout = '10s'"))
                    db.execute(text("LOCK TABLE public.gec_records, public.gec_revisions, public.gec_events IN SHARE MODE"))
                else:
                    reject("LEDGER_DIALECT_UNSUPPORTED", "No coherent confirmation read is implemented for this database.")
                try:
                    current = _read_snapshot(db, self.catalog, self.templates)
                    if expected is not None and current.digest!=expected.digest:
                        reject("CONSTRAINT_SET_CHANGED", "The complete confirmed revision set or term catalog changed; restart against a fresh snapshot.")
                    self._active.db=db
                    yield current
                finally:
                    self._active.db=None
                    db.rollback()  # SELECTs/locks only; never ledger writes.
        except ConstraintError:
            raise
        except Exception:
            reject("CONSTRAINT_AUTHORITY_UNAVAILABLE", "The confirmation set or institutional authority could not be verified safely.")
