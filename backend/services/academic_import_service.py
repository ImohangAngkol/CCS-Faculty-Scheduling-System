"""Deterministic identity-only dry run. Explicit bytes in; sanitized plan out.

No filesystem reads/writes, env loading, database access, import apply or GA imports.
Inputs are normalized identity documents, NOT institutional CSV import adapters.
"""
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from schemas.academic import (IdentityRecord, ImportPlan, PlanItem, SourceReference)
from services.academic_metadata_adapter import scoped_course_id, scoped_offering_id, scoped_section_id

RECORD = TypeAdapter(IdentityRecord)
DEFERRED_KINDS = frozenset({"eligibility", "domain", "workload", "capacity", "enrollment",
                            "qualification", "preference", "component", "room", "preassignment"})


def natural_keys(row):
    """Every unique identity boundary, not only the primary UUID."""
    if row.kind == "scope": return ((row.scope_key,),)
    if row.kind == "year": return ((row.scope_id, row.year_key),)
    if row.kind == "term": return ((row.scope_id, row.term_key), (row.identity_scope,))
    if row.kind == "faculty_code": return ((row.legacy_code,),)
    if row.kind == "course": return ((row.scope_id, row.identity_code),)
    if row.kind == "section": return ((row.term_id, row.identity_code),)
    return ((row.term_id, row.identity_key), (row.term_id, row.course_id, row.section_id))


def _strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _identity_issue(row, index, faculty_registry):
    """Validate relationships and frozen ID formulas without loading any registry."""
    if row.kind == "faculty_code":
        if row.id not in faculty_registry: return "UNKNOWN_FACULTY_UUID"
        return "FACULTY_CODE_MISMATCH" if row.legacy_code != faculty_registry[row.id] else None
    if row.kind == "scope":
        return "NONCANONICAL_KEY" if row.scope_key != row.scope_key.strip() else None
    scope = index.get(("scope", row.scope_id))
    if scope is None: return "MISSING_SCOPE"
    if row.kind == "year":
        return "NONCANONICAL_KEY" if row.year_key != row.year_key.strip() else None
    if row.kind == "term":
        if row.term_key != row.term_key.strip() or row.identity_scope != row.identity_scope.strip(): return "NONCANONICAL_KEY"
        if row.year_id is not None:
            year = index.get(("year", row.year_id))
            if year is None: return "MISSING_YEAR"
            if year.scope_id != row.scope_id: return "CROSS_SCOPE_YEAR"
        return None
    if row.kind in {"course", "section"}:
        if row.identity_code != row.identity_code.strip().upper(): return "NONCANONICAL_KEY"
    if row.kind == "course":
        return "COURSE_UUID_MISMATCH" if row.id != scoped_course_id(scope.scope_key, row.identity_code) else None
    term = index.get(("term", row.term_id))
    if term is None: return "MISSING_TERM"
    if term.scope_id != row.scope_id: return "CROSS_SCOPE_TERM"
    if row.kind == "section":
        return "SECTION_UUID_MISMATCH" if row.id != scoped_section_id(term.identity_scope, row.identity_code) else None
    course, section = index.get(("course", row.course_id)), index.get(("section", row.section_id))
    if course is None or section is None: return "MISSING_OFFERING_PARENT"
    if course.scope_id != row.scope_id or section.scope_id != row.scope_id or section.term_id != row.term_id: return "CROSS_SCOPE_OR_TERM_OFFERING"
    if row.identity_key != f"{course.identity_code}::{section.identity_code}": return "OFFERING_KEY_MISMATCH"
    if row.id != scoped_offering_id(term.identity_scope, course.identity_code, section.identity_code): return "OFFERING_UUID_MISMATCH"
    return None


def plan_import(sources: Mapping[str, bytes], *, existing: tuple = (),
                faculty_registry: Mapping[UUID, int] | None = None) -> ImportPlan:
    """Never applies a plan. 'matching' covers identity fields only, not full rows.

    Source format: {schema_version: 1, records: [typed identity records or deferred
    kind descriptors]}. Unknown fields on supported identities fail closed.
    Caller explicitly supplies authoritative UUID/code pairs and optional existing
    identities. The planner never opens the institutional identity registry itself.
    """
    references, items, candidates = [], [], []
    faculty_registry = dict(faculty_registry or {})
    if (any(not isinstance(key, UUID) or type(code) is not int or not 0 <= code <= 2147483647
            for key, code in faculty_registry.items())
            or len(set(faculty_registry.values())) != len(faculty_registry)):
        raise ValueError("Invalid or ambiguous supplied faculty registry; details withheld.")
    existing = tuple(RECORD.validate_python(row) for row in existing)
    existing_index = {(row.kind, row.id): row for row in existing}
    if len(existing_index) != len(existing): raise ValueError("Existing projection has duplicate IDs.")
    existing_keys = defaultdict(dict)
    for row in existing:
        for position, key in enumerate(natural_keys(row)):
            bucket = existing_keys[(row.kind, position)]
            if key in bucket: raise ValueError("Existing projection has duplicate natural keys.")
            bucket[key] = row
    def issue(source, ordinal, classification, code, kind=None):
        items.append(PlanItem(classification=classification, code=code, source_key=source,
                              row_ordinal=ordinal, record_kind=kind))
    for source, raw in sorted(sources.items()):
        references.append(SourceReference(source_key=source, sha256=hashlib.sha256(raw).hexdigest()))
        try:
            payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_pairs,
                                 parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if (not isinstance(payload, dict) or set(payload) != {"schema_version", "records"}
                    or type(payload["schema_version"]) is not int or payload["schema_version"] != 1
                    or not isinstance(payload["records"], list)):
                raise ValueError()
        except (ValueError, UnicodeError):
            issue(source, 0, "unresolved", "INVALID_SOURCE_DOCUMENT")
            continue
        for ordinal, raw_row in enumerate(payload["records"], 1):
            kind = raw_row.get("kind") if isinstance(raw_row, dict) else None
            if isinstance(kind, str) and kind in DEFERRED_KINDS:
                # Preserve source bytes outside the report; do not serialize sensitive payloads.
                issue(source, ordinal, "deferred", "OUTSIDE_IDENTITY_FOUNDATION", kind)
                continue
            try:
                row = RECORD.validate_python(raw_row)
            except (ValidationError, ValueError, TypeError):
                issue(source, ordinal, "unresolved", "INVALID_IDENTITY_RECORD")
                continue
            candidates.append((source, ordinal, row))
    # Detect all competing candidates before resolving parents; source order cannot win.
    counts = Counter((row.kind, row.id) for _, _, row in candidates)
    key_counts = Counter((row.kind, pos, key) for _, _, row in candidates
                         for pos, key in enumerate(natural_keys(row)))
    accepted, conflicts = {}, {}
    for source, ordinal, row in candidates:
        pk = row.kind, row.id
        conflict = (counts[pk] > 1 or any(key_counts[(row.kind, pos, key)] > 1
                    for pos, key in enumerate(natural_keys(row))))
        prior = existing_index.get(pk)
        if prior is not None and prior != row: conflict = True
        for pos, key in enumerate(natural_keys(row)):
            other = existing_keys[(row.kind, pos)].get(key)
            if other is not None and other.id != row.id: conflict = True
        if conflict:
            conflicts[pk] = True
            issue(source, ordinal, "conflicting", "IDENTITY_COLLISION", row.kind)
        else:
            accepted[pk] = row
    index = {**existing_index, **accepted}
    # Parent validation reaches a fixed point; invalid ancestors cannot support descendants.
    invalid = {}
    while True:
        found = {}
        for pk, row in accepted.items():
            if pk not in invalid:
                problem = _identity_issue(row, index, faculty_registry)
                if problem: found[pk] = problem
        if not found: break
        invalid.update(found)
        for pk in found: index.pop(pk, None)
    for source, ordinal, row in candidates:
        pk = row.kind, row.id
        if pk in conflicts: continue
        if pk in invalid:
            issue(source, ordinal, "unresolved", invalid[pk], row.kind)
        else:
            matching = pk in existing_index
            issue(source, ordinal, "matching" if matching else "new",
                  "IDENTITY_MATCH" if matching else "NEW_IDENTITY_ONLY", row.kind)
    items.sort(key=lambda item: (item.source_key, item.row_ordinal, item.code))
    return ImportPlan(sources=tuple(references), items=tuple(items))
