"""Small real-model Phase 3E regressions; never touch institutional artifacts."""
import copy
import importlib
import json
import pickle
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from services import ga_service, ga_history_service as history, ga_checkpoint_service as checkpoints
from services.ga_control_service import RunControl, RunRegistry
from tests.test_ga_safe_stop import isolated, bounded_run, small_population
from tests.test_ga_pause_resume import wait_finished

router = importlib.import_module("routers.genetic_algorithm")


def execute(control, callback=None, resume=None, generations=2):
    with history.capture_history(control, router._templates(), resume) as recorder:
        result = ga_service.run_genetic_algorithm(3, generations, 1, run_control=control,
            progress_callback=callback or control.capture_progress, resume_state=resume)
        if isinstance(result, dict):
            recorder.record_result(result)
        return result


def test_every_boundary_rng_scores_equivalence_and_analysis(isolated, monkeypatch):
    calls = []
    population_module = importlib.import_module("genetic_algorithm.operators.CreatePopulation")
    def counted(*args, **kwargs):
        calls.append(1)
        return faculty_preference_fitness(*args, **kwargs)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", counted)
    monkeypatch.setattr(population_module, "faculty_preference_fitness", counted)
    rng = random.getstate()
    profile_before = sys.getprofile()
    total_calls = [0]
    def profile(frame, event, arg):
        if (event == "call" and frame.f_code.co_name == "faculty_preference_fitness"
                and frame.f_code.co_filename.endswith("FitnessFunction.py")):
            total_calls[0] += 1
    sys.setprofile(profile)
    try:
        random.seed(163)
        plain = ga_service.run_genetic_algorithm(3, 2, 1, progress_callback=lambda *a: None)
        expected_rng, expected_count = random.getstate(), len(calls)
        expected_total = total_calls[0]
        total_calls[0] = 0
        calls.clear()
        control = RunControl(); control.start()
        random.seed(163)
        observed = execute(control)
        assert random.getstate() == expected_rng and len(calls) == expected_count
        assert total_calls[0] == expected_total  # Includes tournament and per-faculty final analysis calls.
        for key in ("schedule", "history", "fitness_breakdown", "faculty_analysis", "best_fitness"):
            assert plain[key] == observed[key]
        index = history.manifest(control.run_id)
        assert index["errors"] == []
        assert [row["generation"] for row in index["generations"]] == [0, 1, 2]
        penalties = [row["metrics"]["best_ever_fitness"] for row in index["generations"]]
        assert penalties == sorted(penalties, reverse=True)
        for generation in range(3):
            data = history.get_generation(control.run_id, generation)
            assert data["generation_best"]["payload"]["best_fitness"] == data["metrics"]["generation_best_fitness"]
            assert data["best_ever"]["payload"]["best_fitness"] == data["metrics"]["best_ever_fitness"]
            assert data["validation"]["status"] == "passed"
            assert data["capture_elapsed_ms"] >= 0
        analysis = history.analysis(control.run_id, 2, "best_ever")
        assert analysis["fitness_breakdown"] == observed["fitness_breakdown"]
        targets = {f"Faculty {member.code}": max(0, 24 - member.admin_load - member.research_load - member.extension_load)
                   for member in isolated[2]}
        assert all(row["required_teaching_load"] == targets[row["faculty"]] for row in analysis["workload"])
        print("HISTORY_MEASUREMENT", json.dumps(index["generations"]))
        print("FITNESS_CALL_EQUIVALENCE", expected_total, total_calls[0])
    finally:
        sys.setprofile(profile_before)
        random.setstate(rng)


def test_paused_resume_restart_readonly_apis_exports_and_no_rewrite(isolated, monkeypatch):
    original = RunControl.capture_progress
    def pause(self, kind, metrics):
        original(self, kind, metrics)
        if metrics["generation"] == 1:
            self.request_pause()
    monkeypatch.setattr(RunControl, "capture_progress", pause)
    with TestClient(app) as client:
        response = client.post("/api/ga/run", params={"population_size": 3, "generations": 2, "fresh_chromosomes": 1})
        assert response.status_code == 200, response.text
        run_id = response.json()["run"]["run_id"]
        recorded = history.directory(run_id) / "generation-000001.json"
        previous = recorded.read_bytes()
        # New process registry, same durable files; inspection does not claim admission.
        monkeypatch.setattr(router, "_run_registry", RunRegistry())
        listing = client.get("/api/ga/runs").json()
        assert listing["items"][0]["state"] == "PAUSED"
        page = client.get(f"/api/ga/runs/{run_id}/generations?offset=1&limit=1").json()
        assert page["total"] == 2 and page["items"][0]["generation"] == 1
        assert client.get(f"/api/ga/runs/{run_id}/checkpoint-status").json()["resumable"]
        assert client.post(f"/api/ga/runs/{run_id}/resume").status_code == 200
        assert client.post(f"/api/ga/runs/{run_id}/resume").status_code == 200
        wait_finished(client, run_id, "COMPLETED")
        assert recorded.read_bytes() == previous
        assert len(history.manifest(run_id)["generations"]) == 3
        monkeypatch.setattr(router, "_run_registry", RunRegistry())
        assert client.get("/api/ga/runs").json()["items"][0]["state"] == "COMPLETED"
        assert client.get(f"/api/ga/runs/{run_id}/generations/2/schedule").status_code == 200
        analysis = client.get(f"/api/ga/runs/{run_id}/generations/2/analysis?candidate=best_ever")
        assert analysis.status_code == 200 and analysis.json()["fitness_breakdown"] is not None
        for endpoint in ("generations/2/export?format=json", "generations/2/export?format=csv",
                         "history/export", "compare/export?left=0&right=2"):
            downloaded = client.get(f"/api/ga/runs/{run_id}/{endpoint}")
            assert downloaded.status_code == 200, (endpoint, downloaded.text)
            assert run_id in downloaded.headers["content-disposition"]
        comparison = client.get(f"/api/ga/runs/{run_id}/compare?left=0&right=2").json()
        assert comparison["improvement"]["best_ever_fitness"] >= 0
        assert client.get(f"/api/ga/runs/{run_id}/generations/999").status_code == 404
        assert client.get(f"/api/ga/runs/{run_id}/generations?limit=999").status_code == 422
        assert client.get(f"/api/ga/runs/{run_id}/generations/0/schedule?candidate=unknown").status_code == 422
        assert not router._ga_execution_lock.locked()


def test_safe_stop_preserves_history(isolated, monkeypatch):
    original = RunControl.capture_progress
    def stop(self, kind, data):
        original(self, kind, data)
        if data["generation"] == 1: self.request_stop()
    monkeypatch.setattr(RunControl, "capture_progress", stop)
    with TestClient(app) as client:
        response = client.post("/api/ga/run", params={"population_size": 3, "generations": 2, "fresh_chromosomes": 1})
        assert response.status_code == 200, response.text
        run_id = response.json()["run"]["run_id"]
        assert client.get("/api/ga/runs").json()["items"][0]["state"] == "STOPPED"
        assert [item["generation"] for item in history.manifest(run_id)["generations"]] == [0, 1]


@pytest.fixture
def archived(isolated):
    control = RunControl(); control.start()
    execute(control, generations=1)
    return control.run_id


def test_integrity_missing_and_input_changed(archived, monkeypatch):
    with TestClient(app) as client:
        url = f"/api/ga/runs/{archived}/generations/0"
        monkeypatch.setattr(history, "input_fingerprint", lambda: "changed")
        # Original validated observation remains inspectable; incompatible exports fail.
        assert client.get(url + "/schedule").json()["current_inputs_match"] is False
        assert client.get(url + "/export").status_code == 409
        path = history.directory(archived) / "generation-000000.json"
        original = path.read_bytes()
        path.write_bytes(original.replace(b'"generation":0', b'"generation":9', 1))
        assert client.get(url).status_code == 422
        path.unlink()
        assert client.get(url).status_code == 404


def test_comparison_distinguishes_best_ever_and_assignment_changes(archived, monkeypatch):
    left = history.get_generation(archived, 0)
    right = copy.deepcopy(history.get_generation(archived, 1))
    right["metrics"]["generation_best_fitness"] = left["metrics"]["generation_best_fitness"] + 10
    right["metrics"]["best_ever_fitness"] = left["metrics"]["best_ever_fitness"]
    right["metrics"]["average_fitness"] = left["metrics"]["average_fitness"] - 10
    right["generation_best"]["payload"]["schedule"][0]["room"] = "changed"
    right["generation_best"]["chromosome_id"] = history.candidate_id(right["generation_best"]["payload"])
    # Pure comparison-contract inputs, separate from storage's consistency gate.
    monkeypatch.setattr(history, "get_generation", lambda run_id, generation: left if generation == 0 else right)
    comparison = history.compare(archived, 0, 1)
    assert comparison["improvement"]["generation_best_fitness"] == -10
    assert comparison["improvement"]["best_ever_fitness"] == 0
    assert comparison["improvement"]["average_fitness"] == 10
    assert comparison["changes"] and not comparison["identical_chromosomes"]
    assert history.compare(archived, 0, 0)["identical_chromosomes"]
    right["metrics"]["configuration_fingerprint"] = "other"
    with pytest.raises(history.HistoryError, match="incompatible"):
        history.compare(archived, 0, 1)


def test_generation_best_and_best_ever_are_distinct_observations(isolated):
    from genetic_algorithm.utils.FitnessObservation import observed_scores
    population = isolated[0]
    unchanged = pickle.dumps(population)
    control = RunControl(); control.start()
    base = {"status": "RUNNING", "generation_limit": 2, "population_requested": 3,
            "population_actual": 1, "generation_best_fitness": 100, "best_ever_fitness": 100,
            "average_fitness": 100, "accepted_new_chromosomes_total": 1, "input_fingerprint": history.input_fingerprint(),
            "configuration_fingerprint": "same", "validation_status": "passed"}
    with history.capture_history(control, router._templates()) as writer:
        token = observed_scores.set({id(population[0]): (population[0], 100)})
        try: writer.capture({**base, "generation": 0}, [population[0]])
        finally: observed_scores.reset(token)
        token = observed_scores.set({id(population[1]): (population[1], 120)})
        try: writer.capture({**base, "generation": 1, "generation_best_fitness": 120, "average_fitness": 120}, [population[1]])
        finally: observed_scores.reset(token)
    data = history.get_generation(control.run_id, 1)
    assert pickle.dumps(population) == unchanged
    assert data["generation_best"]["payload"]["best_fitness"] == 120
    assert data["best_ever"]["payload"]["best_fitness"] == 100
    assert data["generation_best"]["chromosome_id"] != data["best_ever"]["chromosome_id"]
    assert data["best_ever"]["chromosome_id"] == history.get_generation(control.run_id, 0)["best_ever"]["chromosome_id"]


def test_atomic_write_keeps_previous_and_concurrent_readers(archived, monkeypatch):
    path = history.directory(archived) / "generation-000000.json"
    value = history.read_document(path)
    original = path.read_bytes()
    replace = checkpoints.os.replace
    monkeypatch.setattr(checkpoints.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk failure")))
    with pytest.raises(OSError): history.write_document(path, value)
    assert path.read_bytes() == original
    monkeypatch.setattr(checkpoints.os, "replace", replace)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(history.read_document, path) for _ in range(12)]
        history.write_document(path, value)
        assert all(future.result() == value for future in futures)
    assert not list(path.parent.glob("*.tmp"))


def test_index_commit_failure_keeps_previous_index_and_complete_orphan(archived, monkeypatch):
    data = copy.deepcopy(history.get_generation(archived, 0))
    control = RunControl(); control.start()
    writer = history.HistoryWriter(control, router._templates())
    data["run_id"] = control.run_id
    write = history.write_document
    def fail_index(path, value):
        if path.name == "index.json": raise OSError("isolated index failure")
        return write(path, value)
    try:
        monkeypatch.setattr(history, "write_document", fail_index)
        with pytest.raises(OSError): writer.commit(data)
        assert writer.index["generations"] == [] and writer.index["bytes_written"] == 0
        assert history.manifest(control.run_id)["generations"] == []
        orphan = history.read_document(history.directory(control.run_id) / "generation-000000.json")
        assert orphan["validation"]["status"] == "passed"
    finally:
        monkeypatch.setattr(history, "write_document", write)
        writer.close()


def test_history_storage_warnings_use_reconnectable_run_logs(isolated, monkeypatch):
    import sys
    monkeypatch.setenv("GA_HISTORY_MAX_RUN_BYTES", "1")
    stdout = sys.stdout
    with TestClient(app) as client:
        result = client.post("/api/ga/run", params={"population_size": 3, "generations": 1, "fresh_chromosomes": 1})
        assert result.status_code == 200, result.text
        run_id = result.json()["run"]["run_id"]
        entries = client.get(f"/api/ga/runs/{run_id}/logs").json()["entries"]
        warnings = [entry for entry in entries if "GENERATION HISTORY:" in entry["message"]]
        assert len(warnings) == 2 and all("GA_HISTORY_CAPACITY" in entry["message"] for entry in warnings)
        assert [entry["sequence"] for entry in entries] == sorted({entry["sequence"] for entry in entries})
        assert client.get(f"/api/ga/runs/{run_id}").json()["history_error"] == "GA_HISTORY_CAPACITY"
        assert sys.stdout is stdout


def test_invalid_candidate_never_indexed_and_retention_errors(isolated, monkeypatch):
    control = RunControl(); control.start()
    captured = []
    with history.capture_history(control, router._templates()) as writer:
        monkeypatch.setattr(writer, "commit", lambda data: captured.append(data))
        ga_service.run_genetic_algorithm(3, 1, 1, progress_callback=control.capture_progress, run_control=control)
    data = captured[0]
    data["generation_best"]["payload"]["schedule"].pop()
    data["generation_best"]["chromosome_id"] = history.candidate_id(data["generation_best"]["payload"])
    other = RunControl(); other.start()
    writer = history.HistoryWriter(other, router._templates())
    try:
        data["run_id"] = other.run_id
        with pytest.raises(ValueError): writer.commit(data)
        assert history.manifest(other.run_id)["generations"] == []
    finally: writer.close()
    monkeypatch.setenv("GA_HISTORY_MAX_RUN_BYTES", "1")
    capped = RunControl(); capped.start()
    execute(capped, generations=1)
    index = history.manifest(capped.run_id)
    assert not index["generations"]
    assert {error["code"] for error in index["errors"]} == {"GA_HISTORY_CAPACITY"}


@pytest.mark.parametrize("value", ["=SUM(A1)", "+cmd", "-1+2", "@formula", "  =a", "\tvalue", "\rvalue", "\nvalue"])
def test_csv_formula_injection(value):
    assert history.csv_content([{"value": value}], ["value"]).splitlines()[1].startswith(("'", '"\''))


def test_safe_run_ids():
    for value in ("../private", "invalid", str(uuid4()).upper()):
        with pytest.raises(history.HistoryError): history.directory(value)
