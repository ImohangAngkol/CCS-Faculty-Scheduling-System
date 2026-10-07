"""Preference-write contract checks; all writes use isolated temporary JSON."""
import copy

import pytest
from fastapi.testclient import TestClient

from main import app
from routers import preferences


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(preferences, "PREFERENCE_FILE", tmp_path / "preferences.json")
    with TestClient(app) as test_client:
        yield test_client


def example(client, meetings=1, component="Lecture"):
    for faculty in client.get("/api/faculty/").json()["data"]:
        subjects = client.get(f"/api/faculty/{faculty['faculty_id']}/eligible-subjects").json()["data"]
        for subject in subjects:
            for part in subject["components"]:
                for pattern in part["meeting_patterns"]:
                    if part["type"] != component or pattern["meetings_per_week"] != meetings:
                        continue
                    end = 480 + pattern["duration_minutes"]
                    payload = {
                        "preferred_subjects": [subject["subject_code"]],
                        "preferred_schedule_blocks": [
                            {"id": f"meeting-{index}", "kind": "subject", "day": day,
                             "start_time": "08:00", "end_time": f"{end // 60:02}:{end % 60:02}",
                             "subject_code": subject["subject_code"], "component": component}
                            for index, day in enumerate(pattern["day_combinations"][0])
                        ],
                        "day_importance": 0, "time_importance": 0,
                    }
                    return faculty["faculty_code"], payload
    pytest.fail("Dataset must provide an eligible supported example")


@pytest.mark.parametrize("meetings,component", [(1, "Lecture"), (2, "Lecture"), (1, "Laboratory")])
def test_complete_real_patterns_round_trip_and_can_move(client, meetings, component):
    code, payload = example(client, meetings, component)
    response = client.put(f"/preferences/{code}", json=payload)
    assert response.status_code == 200, response.text
    assert client.get(f"/preferences/{code}").json() == response.json()
    assert response.json()["day_importance"] == 0
    assert response.json()["time_importance"] == 0
    moved = copy.deepcopy(payload)
    block = moved["preferred_schedule_blocks"][0]
    block["start_time"] = "09:00"
    end_hour, end_minute = map(int, block["end_time"].split(":"))
    block["end_time"] = f"{end_hour + 1:02}:{end_minute:02}"
    assert client.put(f"/preferences/{code}", json=moved).status_code == 200


@pytest.mark.parametrize("invalid_end", ["09:00", "12:30", "14:00", "08:00", "07:00", "25:00", "bad"])
def test_lab_cannot_be_stretched_or_shortened(client, invalid_end):
    code, payload = example(client, component="Laboratory")
    payload["preferred_schedule_blocks"][0]["end_time"] = invalid_end
    assert client.put(f"/preferences/{code}", json=payload).status_code == 422
    assert not preferences.PREFERENCE_FILE.exists()


def test_lecture_cannot_be_stretched(client):
    code, payload = example(client)
    payload["preferred_schedule_blocks"][0]["end_time"] = "14:00"
    assert client.put(f"/preferences/{code}", json=payload).status_code == 422


def test_partial_or_duplicate_two_meeting_patterns_are_rejected(client):
    code, payload = example(client, meetings=2)
    incomplete = copy.deepcopy(payload)
    incomplete["preferred_schedule_blocks"].pop()
    assert client.put(f"/preferences/{code}", json=incomplete).status_code == 422
    payload["preferred_schedule_blocks"][1]["day"] = payload["preferred_schedule_blocks"][0]["day"]
    assert client.put(f"/preferences/{code}", json=payload).status_code == 422


def test_invalid_write_preserves_previous_saved_record(client):
    code, payload = example(client)
    assert client.put(f"/preferences/{code}", json=payload).status_code == 200
    before = preferences.PREFERENCE_FILE.read_bytes()
    payload["preferred_subjects"] = ["ITE184"]
    assert client.put(f"/preferences/{code}", json=payload).status_code == 422
    assert preferences.PREFERENCE_FILE.read_bytes() == before


def test_specialization_does_not_grant_eligibility(client):
    # Faculty 1 has only two explicit offered permissions; CCC courses remain denied.
    assert client.put("/preferences/1", json={"preferred_subjects": ["CCC100"]}).status_code == 422
    assert client.put("/preferences/99", json={}).status_code == 422


def test_missing_component_is_rejected(client):
    faculty = client.get("/api/faculty/").json()["data"]
    for row in faculty:
        subjects = client.get(f"/api/faculty/{row['faculty_code']}/eligible-subjects").json()["data"]
        for subject in subjects:
            if subject["laboratory_hours"] != 0:
                continue
            payload = {"preferred_subjects": [subject["subject_code"]], "preferred_schedule_blocks": [
                {"id": "fake-lab", "kind": "subject", "day": "M", "start_time": "08:00", "end_time": "11:00", "subject_code": subject["subject_code"], "component": "Laboratory"}
            ]}
            assert client.put(f"/preferences/{row['faculty_code']}", json=payload).status_code == 422
            return
    pytest.fail("Expected at least one lecture-only eligible subject")


@pytest.mark.parametrize("kind", ["rank", "id", "day", "component", "unranked", "general-tags", "summary"])
def test_invalid_shape_is_rejected(client, kind):
    code, payload = example(client)
    block = payload["preferred_schedule_blocks"][0]
    if kind == "rank": payload["preferred_subjects"] *= 2
    elif kind == "id": payload["preferred_schedule_blocks"].append(copy.deepcopy(block))
    elif kind == "day": block["day"] = "SUN"
    elif kind == "component": block["component"] = None
    elif kind == "unranked": payload["preferred_subjects"] = []
    elif kind == "general-tags": block["kind"] = "general"
    elif kind == "summary": payload["preferred_start_time"] = "08:00"
    assert client.put(f"/preferences/{code}", json=payload).status_code == 422


def test_general_periods_and_legacy_weight_are_preserved(client):
    payload = {"preferred_schedule_blocks": [{"id": "general", "kind": "general", "day": "T", "start_time": "13:00", "end_time": "16:00"}],
               "preferred_days": ["T"], "preferred_start_time": "13:00", "preferred_end_time": "16:00",
               "gap_preference": "Scattered", "gap_importance": 0, "faculty_priority": 4}
    response = client.put("/preferences/0", json=payload)
    assert response.status_code == 200
    assert response.json()["gap_importance"] == 0
    assert response.json()["faculty_priority"] == 4


def test_old_invalid_data_remains_readable_without_rewriting(client):
    preferences.PREFERENCE_FILE.write_text('[{"faculty_code": 0, "preferred_subjects": ["ITE184"]}]')
    before = preferences.PREFERENCE_FILE.read_bytes()
    assert client.get("/preferences/0").json()["preferred_subjects"] == ["ITE184"]
    assert preferences.PREFERENCE_FILE.read_bytes() == before
