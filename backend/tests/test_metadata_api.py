"""Identity and metadata contracts, without executing a GA or writing inputs."""

import copy
import json
import random
from uuid import UUID

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app
from genetic_algorithm.models.Section import Section
from genetic_algorithm.models.Subject import Subject
from genetic_algorithm.utils import Functions as scheduling
from services.identity_service import (
    IDENTITY_FILE,
    build_legacy_faculty_codes,
    load_faculty_identities,
    parse_faculty_identities,
    resolve_faculty_identity,
)
from services.metadata_service import component_metadata


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def available(client):
    response = client.get("/api/subjects/available")
    assert response.status_code == 200
    return response.json()["data"]


def by_code(subjects, code):
    return next(subject for subject in subjects if subject["subject_code"] == code)


def test_source_and_registry_order_do_not_assign_faculty_codes():
    identities = load_faculty_identities()
    source_names = scheduling.df_preferences["Faculty"].tolist()
    original = build_legacy_faculty_codes(source_names, identities)
    reordered = build_legacy_faculty_codes(reversed(source_names), reversed(identities))
    assert reordered == original
    assert original == {identity.name: identity.faculty_code for identity in identities}
    # Removing a source record must not renumber the remaining faculty.
    subset = build_legacy_faculty_codes(["TINAM-ISAN", "BOKINGKITO", "BALAGA"])
    assert subset == {"TINAM-ISAN": 10, "BOKINGKITO": 1, "BALAGA": 0}
    for faculty in scheduling.list_faculty:
        identity = resolve_faculty_identity(faculty.code)
        assert faculty.stable_id == identity.faculty_id
        assert faculty.display_code == identity.display_code


def test_unregistered_faculty_cannot_silently_shift_existing_ids():
    with pytest.raises(ValueError, match="Register an unused legacy code"):
        build_legacy_faculty_codes(["NEW FACULTY", "BALAGA"])


@pytest.mark.parametrize("field", ["faculty_id", "faculty_code", "display_code", "name"])
def test_duplicate_identity_registry_entries_are_rejected(field):
    payload = json.loads(IDENTITY_FILE.read_text(encoding="utf-8"))
    payload["faculty"][1][field] = payload["faculty"][0][field]
    with pytest.raises(ValueError, match="Duplicate"):
        parse_faculty_identities(payload)


def test_name_alias_keeps_registered_identity_after_display_name_change():
    payload = json.loads(IDENTITY_FILE.read_text(encoding="utf-8"))
    original_id = payload["faculty"][0]["faculty_id"]
    payload["faculty"][0].update(name="Updated faculty name", aliases=["BALAGA"])
    identities = parse_faculty_identities(payload)
    assert identities[0].faculty_id == original_id
    assert build_legacy_faculty_codes(["BALAGA", "Updated faculty name"], identities) == {
        "BALAGA": 0, "UPDATED FACULTY NAME": 0,
    }


@pytest.mark.parametrize("legacy_code", range(11))
def test_legacy_and_stable_faculty_routes_resolve_the_same_record(client, legacy_code):
    legacy = client.get(f"/api/faculty/{legacy_code}")
    assert legacy.status_code == 200
    faculty = legacy.json()["data"]
    assert faculty["faculty_code"] == legacy_code
    assert faculty["display_code"] == f"Faculty {legacy_code}"
    assert str(UUID(faculty["faculty_id"])) == faculty["faculty_id"]
    stable = client.get(f"/api/faculty/{faculty['faculty_id']}")
    assert stable.json() == legacy.json()
    assert faculty["required_teaching_load"] == max(
        0, 24 - faculty["admin_load"] - faculty["research_load"] - faculty["extension_load"],
    )
    assert faculty["absolute_max_teaching_load"] == 40


@pytest.mark.parametrize("reference", ["999", "unknown", "external:eddie-bouy-palad"])
def test_unknown_and_external_faculty_references_are_not_normal_faculty(client, reference):
    assert client.get(f"/api/faculty/{reference}").status_code == 404
    assert client.get(f"/api/faculty/{reference}/eligible-subjects").status_code == 404


def test_course_offering_and_section_identities_are_distinct_and_order_independent(client, monkeypatch):
    subjects = available(client)
    course = by_code(subjects, "CCC100")
    assert {offering["section"] for offering in course["offerings"]} == {"1A", "1B"}
    assert len({offering["offering_id"] for offering in course["offerings"]}) == 2
    assert {offering["course_id"] for offering in course["offerings"]} == {course["course_id"]}
    sections = {}
    ids = set()
    for item in subjects:
        assert str(UUID(item["course_id"])) == item["course_id"]
        for offering in item["offerings"]:
            assert offering["offering_id"] not in ids
            ids.add(offering["offering_id"])
            assert offering["offering_key"] == f"{item['subject_code']}::{offering['section']}"
            assert sections.setdefault(offering["section"], offering["section_id"]) == offering["section_id"]
    monkeypatch.setattr(scheduling, "list_subjects", list(reversed(scheduling.list_subjects)))
    assert available(client) == subjects


def test_zero_hour_components_are_not_exposed(client, monkeypatch):
    lecture_only = by_code(available(client), "ITE184")
    assert lecture_only["laboratory_hours"] == 0
    assert [component["type"] for component in lecture_only["components"]] == ["Lecture"]
    lab_only = Subject("TEST100", "Lab only", 1, 0, 3, Section("1A"), 1)
    monkeypatch.setattr(scheduling, "list_subjects", [lab_only])
    metadata = available(client)[0]
    assert [component["type"] for component in metadata["components"]] == ["Laboratory"]
    assert metadata["category"] == "OTHER"
    assert metadata["prefix"] == "TEST"


def test_two_hour_lecture_and_continuous_three_hour_lab_metadata(client):
    subject = by_code(available(client), "CCC100")
    lecture, laboratory = subject["components"]
    assert lecture["weekly_hours"] == 2
    assert lecture["duration_minutes"] == 120
    assert lecture["meetings_per_week"] == 1
    assert laboratory["weekly_hours"] == 3
    assert laboratory["duration_minutes"] == 180
    assert laboratory["meetings_per_week"] == 1
    assert laboratory["continuous"] is True
    assert laboratory["fixed_duration"] is True
    assert all(offering["components"] == subject["components"] for offering in subject["offerings"])


def test_three_hour_lectures_expose_both_supported_patterns(client):
    lecture = by_code(available(client), "ITE131")["components"][0]
    assert lecture["duration_minutes"] is None
    assert lecture["meetings_per_week"] is None
    assert lecture["fixed_duration"] is True
    patterns = lecture["meeting_patterns"]
    assert {(pattern["meetings_per_week"], pattern["duration_minutes"]) for pattern in patterns} == {
        (1, 180), (2, 90),
    }
    assert patterns[1]["day_combinations"] == [["M", "TH"], ["T", "F"], ["W", "S"]]


@pytest.mark.parametrize("kind,hours", [("Lecture", 4), ("Laboratory", 1)])
def test_unsupported_patterns_are_explicit_without_guessed_durations(kind, hours):
    component = component_metadata(kind, hours)
    assert component.metadata_status == "unsupported"
    assert component.weekly_hours == hours
    assert component.meeting_patterns == []
    assert component.duration_minutes is None
    assert component.meetings_per_week is None
    assert component.fixed_duration is False


def test_faculty_eligibility_matches_authoritative_csv_for_every_normal_faculty(client):
    offered = {subject["subject_code"] for subject in available(client)}
    for identity in load_faculty_identities():
        rows = scheduling.df_faculty_subject_eligibility
        expected = set(rows.loc[
            (rows["faculty_code"] == identity.faculty_code)
            & (rows["eligibility_status"].str.lower() == "eligible"), "course_no",
        ]) & offered
        response = client.get(f"/api/faculty/{identity.faculty_id}/eligible-subjects")
        assert response.status_code == 200
        subjects = response.json()["data"]
        assert {subject["subject_code"] for subject in subjects} == expected
        for subject in subjects:
            assert subject["eligibility"]["explicitly_eligible"] is True
            assert subject["eligibility"]["authority"] == "faculty_subject_eligibility.csv"
            assert subject["eligibility"]["records"][0]["basis"]
            assert subject["eligibility"]["records"][0]["source"]
            assert any(offering["can_be_assigned"] for offering in subject["offerings"])


def test_domain_and_prefix_do_not_grant_eligibility(client, monkeypatch):
    faculty = copy.deepcopy(scheduling.list_faculty)
    selected = next(item for item in faculty if item.code == 3)
    selected.specializations = ["Data Science", "Networking", "Databases"]
    monkeypatch.setattr(scheduling, "list_faculty", faculty)
    response = client.get("/api/faculty/3/eligible-subjects?eligible_only=false")
    assert response.status_code == 200
    payload = response.json()
    assert payload["faculty"]["specializations"] == selected.specializations
    assert by_code(payload["data"], "CCC121")["eligibility"]["explicitly_eligible"] is True
    for code in ["CCC100", "ITD105", "ITN101"]:
        subject = by_code(payload["data"], code)
        assert subject["eligibility"]["explicitly_eligible"] is False
        assert all(offering["can_be_assigned"] is False for offering in subject["offerings"])


def test_ccc_can_be_explicitly_eligible_for_different_specializations(client):
    responses = [client.get(f"/api/faculty/{code}/eligible-subjects").json() for code in [3, 4]]
    assert responses[0]["faculty"]["specializations"] != responses[1]["faculty"]["specializations"]
    for payload in responses:
        assert by_code(payload["data"], "CCC121")["eligibility"]["explicitly_eligible"] is True


def test_palad_is_friendly_metadata_with_locked_offerings_not_normal_faculty(client):
    faculty = client.get("/api/faculty/").json()["data"]
    assert len(faculty) == 11
    assert all(item["instructor_type"] == "optimization_faculty" for item in faculty)
    assert not any("Palad" in item["name"] for item in faculty)
    subjects = available(client)
    external = by_code(subjects, "ITE184")
    assert external["preassignment_status"] == "all"
    assert {offering["section"] for offering in external["offerings"]} == {"4A", "4B"}
    for offering in external["offerings"]:
        instructor = offering["preassigned_instructor"]
        assert instructor["display_name"] == "Atty. Eddie Bouy Palad"
        assert instructor["instructor_type"] == "preassigned_external"
        assert instructor["locked_room"] == "ICT3A"
        assert str(UUID(instructor["instructor_id"])) == instructor["instructor_id"]
        assert client.get(f"/api/faculty/{instructor['instructor_id']}").status_code == 404
    assert "external:eddie-bouy-palad" not in json.dumps(subjects)


def test_preassignment_blocks_normal_assignment_even_with_explicit_course_permission(client, monkeypatch):
    faculty = copy.deepcopy(scheduling.list_faculty)
    next(item for item in faculty if item.code == 3).eligible_subjects.add("ITE184")
    monkeypatch.setattr(scheduling, "list_faculty", faculty)
    rows = pd.concat([scheduling.df_faculty_subject_eligibility, pd.DataFrame([{
        "faculty_code": 3, "course_no": "ITE184", "eligibility_status": "Eligible",
        "eligibility_basis": "Test permission", "source": "Test fixture",
    }])], ignore_index=True)
    monkeypatch.setattr(scheduling, "df_faculty_subject_eligibility", rows)
    all_subjects = client.get("/api/faculty/3/eligible-subjects?eligible_only=false").json()["data"]
    locked = by_code(all_subjects, "ITE184")
    assert locked["eligibility"]["explicitly_eligible"] is True
    assert all(offering["can_be_assigned"] is False for offering in locked["offerings"])
    selectable = client.get("/api/faculty/3/eligible-subjects").json()["data"]
    assert "ITE184" not in {subject["subject_code"] for subject in selectable}


def test_metadata_reads_do_not_mutate_scheduling_resources_or_ga_random_state(client):
    before_rng = random.getstate()
    resources = [*scheduling.list_faculty, *scheduling.lst_rooms, *scheduling.lst_sections]
    blocks = [
        block for resource in resources
        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        for block in getattr(resource, f"time_blocks_{day}")
    ]
    # Preserve references when other GA tests have already populated calendars.
    before_blocks = [dict(vars(block)) for block in blocks]
    before_profiles = [(faculty.current_teaching_load, set(faculty.eligible_subjects))
                       for faculty in scheduling.list_faculty]
    before_schedule = copy.deepcopy([
        scheduling.get_subject_schedule_entries(subject) for subject in scheduling.list_subjects
    ])
    client.get("/api/faculty/")
    client.get("/api/subjects/available")
    client.get("/api/faculty/3/eligible-subjects")
    assert random.getstate() == before_rng
    assert before_blocks == [vars(block) for block in blocks]
    assert before_profiles == [(faculty.current_teaching_load, faculty.eligible_subjects)
                               for faculty in scheduling.list_faculty]
    assert before_schedule == [
        scheduling.get_subject_schedule_entries(subject) for subject in scheduling.list_subjects
    ]
