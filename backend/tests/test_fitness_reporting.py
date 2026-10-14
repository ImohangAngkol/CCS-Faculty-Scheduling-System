"""Phase 3F observations and exports; all GA artifacts use isolated fixtures."""
import copy
import csv
import importlib
import io
import json
import random
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from services import fitness_reporting_service as reports, ga_history_service as history, ga_service
from tests.test_ga_safe_stop import isolated, bounded_run, small_population
from tests.test_ga_generation_history import archived, execute
from services.ga_control_service import RunControl

router = importlib.import_module("routers.genetic_algorithm")


def context():
    return {"version": 1, "preference_scoring_version": 2, "input_fingerprint": "original", "scorer_sha256": reports.scorer_hash(),
            "settings": {"underload_penalty": 25}, "preferences": {},
            "faculty": [{"faculty": "Faculty 1", "code": "1", "required_teaching_load": 19,
                         "admin_load": 3, "research_load": 1, "extension_load": 1, "overload_warning_threshold": 30}]}


def assignment(code="CCC121", units=15):
    return {"subject": code, "section": "3A", "faculty": "1", "teaching_units": units,
            "external": False, "display_name": "Faculty 1",
            "lecture": [["monday", 540, 570], ["monday", 570, 600], ["monday", 600, 630], ["monday", 630, 660]], "laboratory": []}


@pytest.mark.parametrize("faculty_code", [1, 1.0, "1.0"])
def test_workload_release_target_and_recorded_components_reconcile(faculty_code):
    breakdown = {key: 0 for key in reports.CATALOG}
    breakdown["teaching_load_balance"] = 75
    record = {"Faculty_Code": faculty_code, "Teaching_Load": 15, "Total_Penalty": 75,
              **{field: breakdown[key] for key, field in reports.PENALTY_FIELDS.items()}}
    report = reports.build_report({"kind": "fixture"}, 75, breakdown, [], context(), [assignment()], {"faculty": [record]})
    member = report["faculty"][0]
    assert len(report["faculty"]) == 1
    assert member["required_teaching_load"] == 24 - 3 - 1 - 1 == 19
    assert member["difference"] == -4 and member["fulfillment_percent"] == pytest.approx(15 / 19 * 100)
    assert member["underload_steps"] == 3 and member["workload_penalty"] == 75
    assert report["recorded_component_sum"] == report["overall_penalty"] == 75


@pytest.mark.parametrize("target,actual,expected,fulfillment", [(0, 0, "on_target", None), (19, 19, "on_target", 100), (19, 31, "overload", 31 / 19 * 100), (19, 0, "underload", 0)])
def test_zero_target_unassigned_and_overload(target, actual, expected, fulfillment):
    captured = context(); captured["faculty"][0]["required_teaching_load"] = target
    report = reports.build_report({}, 0, None, [], captured, [assignment(units=actual)] if actual else [])
    row = report["faculty"][0]
    assert row["workload_status"] == expected and row["fulfillment_percent"] == fulfillment
    assert row["heavy_overload"] == (actual > 30)
    assert row["workload_penalty"] is None  # No invented numerical contribution.


def test_exact_raw_start_membership_keeps_independent_matching_but_respects_toggles():
    pref = {"use_day_preference": False, "use_time_preference": False, "day_importance": 5, "time_importance": 3,
            "preferred_schedule_blocks": [{"kind": "subject", "subject_code": "CCC121", "component": "lecture", "day": "Tuesday", "start_time": "09:30"}]}
    indicators = {row["key"]: row for row in reports.preference_indicators([assignment()], pref, {})}
    assert indicators["day_preference"]["status"] == "disabled"
    assert indicators["time_preference"]["status"] == "disabled"
    assert not indicators["time_preference"]["affects_fitness"] and indicators["time_preference"]["penalty"] is None


def test_general_preferences_do_not_gain_influence_from_another_subject_exact_block():
    a, b = assignment(), assignment("ITD104")
    pref = {"use_day_preference": False, "use_time_preference": False, "preferred_days": ["Tuesday"],
            "preferred_start_time": "13:00", "preferred_end_time": "14:00", "time_importance": 3, "day_importance": 4,
            "preferred_schedule_blocks": [{"kind": "subject", "subject_code": "CCC121", "component": "lecture", "day": "Monday", "start_time": "09:30"}]}
    result = {row["key"]: row for row in reports.preference_indicators([a, b], pref, {})}
    assert result["day_preference"]["total"] == result["time_preference"]["total"] == 1


def test_ranked_subjects_partial_satisfaction_and_zero_importance():
    pref = {"use_subject_preference": True, "subject_importance": 0, "preferred_subjects": ["ITD104", "CCC121"]}
    row = reports.preference_indicators([assignment()], pref, {})[0]
    assert row["status"] == "partially_satisfied" and row["satisfaction_percent"] == 50
    assert not row["affects_fitness"] and row["penalty"] is None
    pref["use_subject_preference"] = False
    assert reports.preference_indicators([assignment()], pref, {})[0]["status"] == "disabled"


@pytest.mark.parametrize("style,expected", [("Compact", "unmet"), ("Scattered", "satisfied")])
def test_gap_and_lecture_lab_indicators(style, expected):
    a = assignment(); a["laboratory"] = [["monday", 720, 900]]
    pref = {"use_gap_preference": True, "gap_preference": style, "gap_importance": 4,
            "use_lecture_lab_preference": True, "lecture_lab_preference": "Different Day", "lecture_lab_importance": 5}
    rows = {row["key"]: row for row in reports.preference_indicators([a], pref, {})}
    assert rows["schedule_style"]["status"] == expected and rows["schedule_style"]["idle_minutes"] == 60
    assert rows["lecture_lab_preference"]["status"] == "unmet"


def test_external_instructor_is_separate_and_not_scored():
    external = assignment(); external.update(faculty="external:eddie-bouy-palad", external=True, display_name="Atty. Eddie Bouy Palad")
    result = reports.build_report({}, 0, None, [], context(), [external])
    assert len(result["faculty"]) == 1 and result["faculty"][0]["teaching_units"] == 0
    assert result["external_instructors"][0]["name"] == "Atty. Eddie Bouy Palad"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "100"])
def test_invalid_observations_are_rejected(bad):
    with pytest.raises(history.HistoryError): reports.build_report({}, bad, None, [])


def test_inconsistent_components_hard_overload_and_intervals_are_rejected():
    with pytest.raises(history.HistoryError): reports.build_report({}, 100, {key: 0 for key in reports.CATALOG}, [])
    with pytest.raises(history.HistoryError): reports.build_report({}, 0, None, [], context(), [assignment(units=41)])
    with pytest.raises(history.HistoryError): reports.validate_assignments([assignment()], {"schedule": []})


def test_legacy_context_is_not_filled_from_current_preferences(monkeypatch):
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", lambda *a, **k: pytest.fail("Reporting cannot score"))
    workload = [{"faculty": "Faculty 1", "teaching_units": 15, "required_teaching_load": 19, "preparations": 2}]
    report = reports.build_report({}, 75, None, workload)
    row = report["faculty"][0]
    assert row["required_teaching_load"] == 19 and row["admin_load"] is None
    assert row["preferences"] is None and all(component["penalty"] is None for component in report["components"])


def test_changed_engine_does_not_reinterpret_captured_preferences():
    captured = context(); captured["engine_fingerprint"] = "different-historical-engine"
    result = reports.build_report({}, 75, None, [], captured, [assignment()])
    assert result["faculty"][0]["preferences"] is None
    assert result["faculty"][0]["underload_steps"] is None
    assert "Captured engine differs" in result["faculty"][0]["unavailable_reason"]


def test_legacy_policy_report_retains_original_disabled_flag_interpretation():
    captured = context()
    captured["preference_scoring_version"] = 1
    captured["scorer_sha256"] = reports.scorer_hash(1)
    captured["engine_fingerprint"] = history.checkpoints.engine_fingerprint(1)
    captured["preferences"] = {"1": {"use_day_preference": False, "use_time_preference": False,
        "day_importance": 4, "time_importance": 3,
        "preferred_schedule_blocks": [{"kind": "subject", "subject_code": "CCC121", "component": "Lecture", "day": "Tuesday", "start_time": "13:00"}]}}
    report = reports.build_report({}, 50, None, [], captured, [assignment()])
    rows = {row["key"]: row for row in report["faculty"][0]["preferences"]}
    assert rows["day_preference"]["affects_fitness"] and rows["time_preference"]["affects_fitness"]
    assert "Legacy policy 1" in report["definitions"]["preference_scoring_policy"]
    assert report["overall_penalty"] == 50 and all(row["penalty"] is None for row in report["components"])


def test_unverified_future_source_preserves_observations_without_reinterpretation(monkeypatch):
    captured = context()
    def changed(*args):
        raise ValueError("Unsupported future source release")
    monkeypatch.setattr(reports, "scorer_hash", changed)
    report = reports.build_report({}, 75, None, [], captured, [assignment()])
    assert report["overall_penalty"] == 75 and report["faculty"][0]["teaching_units"] == 15
    assert report["faculty"][0]["preferences"] is None


def test_export_definitions_provenance_missing_values_and_formula_injection():
    result = reports.build_report({"run_id": "=HYPERLINK(\"evil\")", "generation": 1, "candidate": "best_ever", "timestamp": "captured"}, 75, None,
                                  [{"faculty": "@SUM(1)", "teaching_units": 15, "required_teaching_load": 19}])
    csv_rows = list(csv.DictReader(io.StringIO(reports.export_csv(result, "workload"))))
    assert csv_rows[0]["run_id"].startswith("'=") and csv_rows[0]["faculty"].startswith("'@")
    assert csv_rows[0]["workload_penalty"] == "" and csv_rows[0]["generation"] == "1"
    assert "24" in csv_rows[0]["definition"] and "Actual" in csv_rows[0]["definition"]
    assert json.loads(history.checkpoints.canonical(result))["overall_penalty"] == 75


def test_historical_reports_exports_and_comparisons_are_readonly(archived, monkeypatch):
    paths = list(history.directory(archived).glob("*.json")); before = {p: p.read_bytes() for p in paths}
    rng = random.getstate()
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", lambda *a, **k: pytest.fail("No historical re-evaluation"))
    # Inputs may change; observations must remain under their original captured context.
    monkeypatch.setattr(history, "input_fingerprint", lambda: "current-preferences-have-changed")
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=4) as pool:
        base = f"/api/ga/runs/{archived}"
        responses = list(pool.map(lambda _: client.get(base + "/generations/1/fitness-analysis?candidate=best_ever"), range(8)))
        assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
        data = responses[0].json()
        assert data["breakdown_available"] and data["recorded_component_sum"] == data["overall_penalty"]
        assert all(row["admin_load"] is not None for row in data["faculty"])
        assert sum(row["total_penalty"] for row in data["faculty"] if row["total_penalty"] is not None) == data["overall_penalty"]
        assert any(row["preferences"] for row in data["faculty"])
        comparison = client.get(base + "/fitness-comparison?left=0&right=1").json()
        assert comparison["source"]["run_id"] == archived
        same_candidate = history.get_generation(archived, 0)["generation_best"]["chromosome_id"] == history.get_generation(archived, 1)["generation_best"]["chromosome_id"]
        if same_candidate:
            assert all(row["reduction"] == 0 for row in comparison["component_changes"])
        else:
            assert all(row["reduction"] is None for row in comparison["component_changes"])
        for section in ("fitness", "workload"):
            for format in ("json", "csv"):
                response = client.get(base + f"/generations/1/fitness-analysis/export?candidate=best_ever&section={section}&format={format}")
                assert response.status_code == 200, response.text
                assert archived in response.headers["content-disposition"]
                if format == "json": assert response.json()["source"]["generation"] == 1
        assert client.get(base + "/generations/999/fitness-analysis").status_code == 404
        assert client.get(base + "/generations/1/fitness-analysis?candidate=invalid").status_code == 422
    assert random.getstate() == rng and all(p.read_bytes() == before[p] for p in paths)


def test_legacy_snapshot_reports_do_not_backfill_or_rewrite(archived):
    path = history.directory(archived) / "generation-000000.json"
    data = history.read_document(path)
    data.pop("reporting_context")
    for kind in ("generation_best", "best_ever"): data[kind].pop("reporting_assignments")
    history.write_document(path, data)
    # Remove final sidecar only in this isolated fixture to represent a legacy boundary.
    for extra in history.directory(archived).glob("analysis-*.json"): extra.unlink()
    before = path.read_bytes()
    result = reports.generation_report(archived, 0)
    assert not result["breakdown_available"] and all(row["preferences"] is None for row in result["faculty"])
    assert path.read_bytes() == before
    comparison = reports.comparison_report(archived, 0, 1)
    assert all(row["reduction"] is None for row in comparison["component_changes"])


def test_latest_result_uses_its_recorded_analysis_and_does_not_score(isolated, monkeypatch):
    result = ga_service.run_genetic_algorithm(3, 1, 0, progress_callback=lambda *a: None)
    router.LATEST_RESULT_FILE.write_text(json.dumps(result), encoding="utf-8")
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", lambda *a, **k: pytest.fail("Latest report cannot score"))
    with TestClient(app) as client:
        response = client.get("/api/ga/fitness-analysis/latest")
        assert response.status_code == 200, response.text
        assert response.json()["overall_penalty"] == result["best_fitness"]
        assert all(row["required_teaching_load"] is None for row in response.json()["faculty"])
        assert client.get("/api/ga/fitness-analysis/latest/export?format=json&section=workload").status_code == 200


def test_legacy_latest_reuses_recorded_faculty_analysis_without_recomputing(archived, monkeypatch):
    snapshot_path = history.directory(archived) / "generation-000001.json"
    snapshot = history.read_document(snapshot_path)
    identity = snapshot["best_ever"]["chromosome_id"]
    sidecar_path = history.directory(archived) / f"analysis-{identity}.json"
    sidecar = history.read_document(sidecar_path)
    latest = {"run_id": archived, "best_fitness": sidecar["fitness"], "fitness_breakdown": sidecar["fitness_breakdown"],
              "faculty_analysis": sidecar["faculty_analysis"], "schedule": snapshot["best_ever"]["payload"]["schedule"]}
    router.LATEST_RESULT_FILE.write_text(json.dumps(latest), encoding="utf-8")
    for key in ("faculty_analysis", "reporting_context", "reporting_assignments"): sidecar.pop(key, None)
    history.write_document(sidecar_path, sidecar)
    snapshot.pop("reporting_context")
    for kind in ("generation_best", "best_ever"): snapshot[kind].pop("reporting_assignments")
    history.write_document(snapshot_path, snapshot)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", lambda *a, **k: pytest.fail("Cannot re-evaluate legacy result"))
    result = reports.latest_report()
    assert any(row["preferences"] is not None for row in result["faculty"])
    assert sum(row["total_penalty"] for row in result["faculty"] if row["total_penalty"] is not None) == result["overall_penalty"]
    assert all(row["admin_load"] is None for row in result["faculty"])
    assert result["external_instructors"][0]["name"] == "Atty. Eddie Bouy Palad"
