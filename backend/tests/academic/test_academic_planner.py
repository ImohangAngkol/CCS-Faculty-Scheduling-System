"""Synthetic bytes only; no registry or institutional CSV loads."""
import hashlib
import json
import random
from uuid import UUID

import pytest

from schemas.academic import IdentityProjection
from services.academic_import_service import plan_import
from services.academic_metadata_adapter import (compare_projections, scoped_course_id,
                                              scoped_offering_id, scoped_section_id)
from services.identity_service import (CATALOG_SCOPE, OFFERING_SCOPE, course_identity,
                                      offering_identity, section_identity)


def uid(n): return UUID(int=n)


def records():
    scope, term, faculty = str(uid(1)), str(uid(2)), str(uid(7))
    course = str(scoped_course_id(CATALOG_SCOPE, "SYN101"))
    section = str(scoped_section_id(OFFERING_SCOPE, "1A"))
    offering = str(scoped_offering_id(OFFERING_SCOPE, "SYN101", "1A"))
    return [
        dict(kind="scope", id=scope, scope_key=CATALOG_SCOPE),
        dict(kind="term", id=term, scope_id=scope, term_key="legacy", identity_scope=OFFERING_SCOPE),
        dict(kind="faculty_code", id=faculty, legacy_code=17),
        dict(kind="course", id=course, scope_id=scope, identity_code="SYN101"),
        dict(kind="section", id=section, scope_id=scope, term_id=term, identity_code="1A"),
        dict(kind="offering", id=offering, scope_id=scope, term_id=term, course_id=course, section_id=section, identity_key="SYN101::1A"),
    ]


def source(rows):
    return json.dumps(dict(schema_version=1, records=rows), sort_keys=True).encode()


def run(rows, **kwargs):
    return plan_import({"synthetic.json": source(rows)}, faculty_registry={uid(7): 17}, **kwargs)


def test_preserves_legacy_uuid_formulas_and_does_not_consume_rng():
    state = random.getstate()
    assert str(scoped_course_id(CATALOG_SCOPE, " syn101 ")) == course_identity("SYN101")
    assert str(scoped_section_id(OFFERING_SCOPE, " 1a ")) == section_identity("1A")
    assert str(scoped_offering_id(OFFERING_SCOPE, "syn101", "1a")) == offering_identity("SYN101", "1A")
    assert scoped_section_id("synthetic:new-term", "1A") != scoped_section_id(OFFERING_SCOPE, "1A")
    assert scoped_offering_id("synthetic:new-term", "SYN101", "1A") != scoped_offering_id(OFFERING_SCOPE, "SYN101", "1A")
    assert random.getstate() == state


def test_new_matching_deterministic_and_hashes():
    rows = records()
    result = run(rows)
    assert result.counts == dict(new=6, matching=0, conflicting=0, unresolved=0, deferred=0)
    assert result == run(rows)
    assert result.sources[0].sha256 == hashlib.sha256(source(rows)).hexdigest()
    assert run(rows, existing=tuple(rows)).counts["matching"] == 6
    assert run(list(reversed(rows))).counts == result.counts
    assert not result.apply_available


def test_source_mapping_order_cannot_select_a_winner():
    a, b = records()[0], {**records()[0], "scope_key": "other"}
    sources = {"b.json": source([b]), "a.json": source([a])}
    one = plan_import(sources)
    two = plan_import(dict(reversed(list(sources.items()))))
    assert one == two and one.counts["conflicting"] == 2


@pytest.mark.parametrize("kind_index,field,value", [
    (2, "legacy_code", 18), (3, "identity_code", "SYN102"),
    (1, "identity_scope", "other"), (5, "section_id", str(uid(99))),
])
def test_changed_existing_identity_is_conflict(kind_index, field, value):
    rows = records()
    changed = [{**row} for row in rows]
    changed[kind_index][field] = value
    assert run(changed, existing=tuple(rows)).counts["conflicting"] >= 1


def test_numeric_code_cannot_be_assigned_to_another_uuid():
    old = records()[2]
    new = {**old, "id": str(uid(8))}
    result = plan_import({"synthetic.json": source([new])}, existing=(old,), faculty_registry={uid(8): 17})
    assert result.items[0].classification == "conflicting"


@pytest.mark.parametrize("change,expected", [
    ((3, "id", str(uid(99))), "COURSE_UUID_MISMATCH"),
    ((4, "term_id", str(uid(99))), "MISSING_TERM"),
    ((5, "identity_key", "SYN101::2A"), "OFFERING_KEY_MISMATCH"),
    ((2, "id", str(uid(99))), "UNKNOWN_FACULTY_UUID"),
    ((3, "identity_code", " syn101 "), "NONCANONICAL_KEY"),
])
def test_unresolved_parent_uuid_or_key(change, expected):
    rows = records()
    index, field, value = change
    rows[index][field] = value
    assert expected in {item.code for item in run(rows).items}


def test_invalid_ancestor_is_not_used_to_validate_descendants():
    rows = records()
    rows[0]["scope_key"] = " noncanonical "
    result = run(rows)
    assert result.counts["unresolved"] == 5
    assert result.counts["new"] == 1  # explicit global faculty-code bridge


def test_orphan_descriptors_deferred_and_not_promoted_to_offerings():
    rows = records()[:1] + [dict(kind="course", id=str(scoped_course_id(CATALOG_SCOPE, "UNOFF101")), scope_id=str(uid(1)), identity_code="UNOFF101")]
    rows += [dict(kind="eligibility", private_name="PRIVATE-SENTINEL", faculty_code=999, course_code="UNOFF101"), dict(kind="domain", course_code="UNOFF101")]
    result = run(rows)
    assert result.counts["new"] == 2 and result.counts["deferred"] == 2
    assert all(item.record_kind != "offering" for item in result.items)
    assert "PRIVATE-SENTINEL" not in result.model_dump_json()


@pytest.mark.parametrize("raw", [b"{", b'{"schema_version":1,"schema_version":1,"records":[]}',
                                     b'{"schema_version":true,"records":[]}', b'{"schema_version":1,"records":NaN}'])
def test_invalid_source_is_sanitized(raw):
    result = plan_import({"synthetic.json": raw})
    assert result.items[0].code == "INVALID_SOURCE_DOCUMENT"


@pytest.mark.parametrize("field,value", [("legacy_code", True), ("legacy_code", "17"), ("legacy_code", -1), ("legacy_code", 2147483648), ("password", "PRIVATE-SENTINEL")])
def test_invalid_fields_never_enter_plan_payload(field, value):
    row = {**records()[2], field: value}
    result = run([row])
    assert result.items[0].code == "INVALID_IDENTITY_RECORD"
    assert "PRIVATE-SENTINEL" not in result.model_dump_json()


def test_shadow_detects_missing_changed_and_unexpected():
    rows = records()
    expected = IdentityProjection(scope_id=uid(1), term_id=uid(2), records=rows)
    actual_rows = rows[1:] + [dict(kind="faculty_code", id=str(uid(8)), legacy_code=18)]
    actual_rows[1] = {**actual_rows[1], "legacy_code": 19}
    actual = IdentityProjection(scope_id=uid(1), term_id=uid(2), records=actual_rows)
    result = compare_projections(expected, actual)
    assert not result.equal and len(result.missing) == len(result.changed) == len(result.unexpected) == 1
    assert "GA_input_equivalence" in result.unsupported_fields
    with pytest.raises(ValueError, match="mismatch"):
        compare_projections(expected, actual.model_copy(update={"term_id": uid(99)}))


def test_duplicate_projection_does_not_hide_identity():
    rows = records()
    p = IdentityProjection(scope_id=uid(1), term_id=uid(2), records=rows + [rows[0]])
    with pytest.raises(ValueError, match="Duplicate"): compare_projections(p, p)


def test_empty_database_cannot_renumber_known_faculty():
    result = run([{**records()[2], "legacy_code": 18}])
    assert result.items[0].code == "FACULTY_CODE_MISMATCH"


def test_registry_code_collisions_rejected_before_planning():
    with pytest.raises(ValueError, match="ambiguous"):
        plan_import({}, faculty_registry={uid(7): 17, uid(8): 17})


def test_imports_have_not_loaded_ga_or_application():
    import sys
    assert "genetic_algorithm.utils.Functions" not in sys.modules
    assert "main" not in sys.modules
