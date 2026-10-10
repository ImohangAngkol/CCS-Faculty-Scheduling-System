"""Bounded cooperative-stop checks; never write production result destinations."""
import asyncio
import copy
import importlib
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from services import chromosome_service, ga_control_service, ga_service
from services.ga_control_service import RunControl, RunRegistry, StopConflict
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from tests.test_ga_monitoring import bounded_run, small_population

router = importlib.import_module("routers.genetic_algorithm")


@pytest.fixture
def isolated(bounded_run, monkeypatch, tmp_path):
    monkeypatch.setattr(ga_control_service, "STOPPED_RUNS_DIR", tmp_path / "stopped_runs")
    monkeypatch.setattr(router, "_run_registry", RunRegistry())
    router.LATEST_RESULT_FILE.write_text('{"previous_completed": true}', encoding="utf-8")
    return bounded_run


def frames(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_control_is_observational_without_stop(isolated, monkeypatch):
    calls = []
    population_module = importlib.import_module("genetic_algorithm.operators.CreatePopulation")
    def score(*args, **kwargs):
        calls.append(1)
        return faculty_preference_fitness(*args, **kwargs)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", score)
    monkeypatch.setattr(population_module, "faculty_preference_fitness", score)
    rng = random.getstate()
    try:
        random.seed(51)
        plain = ga_service.run_genetic_algorithm(3, 2, 1, progress_callback=lambda *a: None)
        expected_rng, expected_calls = random.getstate(), len(calls)
        calls.clear()
        control = RunControl()
        control.start()
        random.seed(51)
        controlled = ga_service.run_genetic_algorithm(3, 2, 1, progress_callback=lambda *a: None, run_control=control)
        assert random.getstate() == expected_rng
        assert len(calls) == expected_calls
        for key in ("schedule", "history", "best_fitness", "fitness_breakdown", "faculty_analysis"):
            assert controlled[key] == plain[key]
        assert control.latest_completed_generation == 2 and control.finalizing
        with pytest.raises(StopConflict):
            control.request_stop()
    finally:
        random.setstate(rng)


def test_stop_before_initial_work_has_no_result_or_side_effects(isolated, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Early stop must not construct or score a chromosome")
    monkeypatch.setattr(ga_service, "generate_population", forbidden)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", forbidden)
    control = RunControl()
    control.request_stop()
    control.start()
    assert ga_service.run_genetic_algorithm(3, 2, 0, run_control=control) is None
    assert router._finish_result(control, None) is None
    assert control.state == "STOPPED" and control.latest_completed_generation is None
    assert router._read_latest_result() == {"previous_completed": True}
    assert not chromosome_service.BEST_CHROMOSOME_PATH.exists()
    assert not ga_control_service.STOPPED_RUNS_DIR.exists()


def test_stream_stop_before_initial_work_has_done_but_no_result(isolated, monkeypatch):
    original = ga_service.run_genetic_algorithm
    def stop_before_work(**kwargs):
        kwargs["run_control"].request_stop()
        return original(**kwargs)
    monkeypatch.setattr(router, "run_genetic_algorithm", stop_before_work)
    with TestClient(app) as client:
        events = frames(client.post("/api/ga/stream", params={"population_size": 3, "generations": 2}))
    assert events[-1]["data"]["status"] == "STOPPED"
    assert events[-1]["data"]["has_result"] is False
    assert not any(event["type"] in {"result", "initial_population_ready", "generation_completed", "error"} for event in events)
    assert router._read_latest_result() == {"previous_completed": True}
    assert not chromosome_service.BEST_CHROMOSOME_PATH.exists()
    assert not router._ga_execution_lock.locked()


def test_stop_during_bounded_crossover_retries_finishes_generation(isolated, monkeypatch):
    control = RunControl()
    control.start()
    attempts = []
    def rejected_child(**kwargs):
        attempts.append(1)
        if len(attempts) == 2:
            control.request_stop()
        return None
    monkeypatch.setattr(ga_service, "create_child_by_faculty_swap", rejected_child)
    result = ga_service.run_genetic_algorithm(3, 3, 0, run_control=control)
    assert len(attempts) == 40  # Existing target_children * 20; control doesn't alter retries.
    assert result["generations_completed"] == 1
    assert control.state == "STOPPING"
    ga_service.validate_saved_result(result)


@pytest.mark.parametrize("at", ["initialization", "crossover", "mutation", "generation_event", "last_generation"])
def test_stop_preserves_only_completed_valid_boundary(isolated, monkeypatch, at):
    control = RunControl()
    control.start()
    target = 0 if at == "initialization" else 2 if at == "last_generation" else 1
    operation = {"initialization": "generate_population", "crossover": "create_child_by_faculty_swap", "mutation": "mutate_by_swapping_faculty_subjects"}.get(at)
    if operation:
        original = getattr(ga_service, operation)
        def stop_in_operation(*args, **kwargs):
            control.request_stop()
            return original(*args, **kwargs)
        monkeypatch.setattr(ga_service, operation, stop_in_operation)
    events = []
    def progress(kind, data):
        events.append(data["generation"])
        if at in {"generation_event", "last_generation"} and data["generation"] == target:
            control.request_stop()
    result = ga_service.run_genetic_algorithm(3, 2, 0, progress_callback=progress, run_control=control)
    assert events == list(range(target + 1))
    assert result["generations_completed"] == control.latest_completed_generation == target
    assert control.state == "STOPPING"
    ga_service.validate_saved_result(result)
    result = router._finish_result(control, result)
    assert result["status"] == control.state == "STOPPED"
    assert result["stop_reason"] == "administrator_request"
    assert router._read_latest_result() == {"previous_completed": True}
    path = ga_control_service.STOPPED_RUNS_DIR / f"{control.run_id}.json"
    assert json.loads(path.read_text(encoding="utf-8")) == result
    assert not list(path.parent.glob("*.tmp"))
    with TestClient(app) as client:
        assert client.get(f"/api/ga/runs/{control.run_id}/result").json()["data"] == result
        # Artifacts are readable after registry loss, but no population is resumable.
        monkeypatch.setattr(router, "_run_registry", RunRegistry())
        assert client.get(f"/api/ga/runs/{control.run_id}").status_code == 404
        assert client.get(f"/api/ga/runs/{control.run_id}/result").status_code == 200
        damaged = dict(result, schedule=result["schedule"][:-1])
        path.write_text(json.dumps(damaged), encoding="utf-8")
        assert client.get(f"/api/ga/runs/{control.run_id}/result").status_code == 422


def test_stopped_run_does_not_downgrade_valid_global_best(isolated, monkeypatch):
    population = isolated[0]
    best = min(population, key=faculty_preference_fitness)
    payload = chromosome_service.chromosome_to_payload(best, faculty_preference_fitness(best))
    chromosome_service.BEST_CHROMOSOME_PATH.write_text(json.dumps(payload), encoding="utf-8")
    before = chromosome_service.BEST_CHROMOSOME_PATH.read_bytes()
    control = RunControl()
    control.start()
    def progress(kind, data):
        control.request_stop()
    result = ga_service.run_genetic_algorithm(3, 2, 0, progress_callback=progress, run_control=control)
    router._finish_result(control, result)
    assert chromosome_service.BEST_CHROMOSOME_PATH.read_bytes() == before


@pytest.mark.parametrize("endpoint", ["stream", "run"])
@pytest.mark.parametrize("at", ["initialization", "crossover", "mutation"])
def test_api_stop_idempotent_admission_and_terminal_order(isolated, monkeypatch, endpoint, at):
    entered, release = threading.Event(), threading.Event()
    operation = {"initialization": "generate_population", "crossover": "create_child_by_faculty_swap", "mutation": "mutate_by_swapping_faculty_subjects"}[at]
    original = getattr(ga_service, operation)
    blocked_once = False
    def blocked(*args, **kwargs):
        nonlocal blocked_once
        if not blocked_once:
            blocked_once = True
            entered.set()
            assert release.wait(15)
        return original(*args, **kwargs)
    monkeypatch.setattr(ga_service, operation, blocked)
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, f"/api/ga/{endpoint}", params={"population_size": 3, "generations": 3, "fresh_chromosomes": 0})
        try:
            assert entered.wait(15)
            run_id = client.get("/api/ga/status").json()["active_run"]["run_id"]
            url = f"/api/ga/runs/{run_id}/stop"
            response = client.post(url)
            assert response.status_code == 200
            assert response.json()["accepted"] and response.json()["state"] == "STOP_REQUESTED"
            repeated = client.post(url).json()
            assert repeated["accepted"] and repeated["already_requested"]
            for other in ("generate", "run", "stream"):
                assert client.post(f"/api/ga/{other}").status_code == 409
            assert client.get("/api/health").status_code == 200
        finally:
            release.set()
        response = pending.result(timeout=20)
        assert response.status_code == 200
        expected_generation = 0 if at == "initialization" else 1
        if endpoint == "stream":
            events = frames(response)
            lifecycle = [event["data"]["status"] for event in events if event["type"] == "run_state_changed"]
            assert lifecycle == ["STOP_REQUESTED", "STOPPING", "STOPPED"]
            assert events[-1]["type"] == "done" and events[-1]["data"]["status"] == "STOPPED"
            assert len({event["run_id"] for event in events}) == 1
            assert [event["sequence"] for event in events] == sorted({event["sequence"] for event in events})
            result = next(event["data"] for event in events if event["type"] == "result")
            assert not any(event["data"].get("status") == "COMPLETED" for event in events)
        else:
            result = response.json()["data"]
        assert result["generations_completed"] == expected_generation
        assert result["status"] == "STOPPED"
        assert client.get(f"/api/ga/runs/{run_id}").json()["state"] == "STOPPED"
        terminal = client.post(url).json()
        assert not terminal["accepted"] and terminal["state"] == "STOPPED"
        assert client.post("/api/ga/runs/unknown/stop").status_code == 404
        assert not router._ga_execution_lock.locked()
        # Admission is reusable and a subsequent normal run still completes.
        assert client.post("/api/ga/run", params={"population_size": 3, "generations": 1, "fresh_chromosomes": 0}).json()["data"]["status"] == "COMPLETED"


@pytest.mark.parametrize("failure", ["persistence", "operator"])
def test_cancellation_failure_is_failed_not_stopped(isolated, monkeypatch, failure):
    operation = "mutate_by_swapping_faculty_subjects"
    original = getattr(ga_service, operation)
    def stop(*args, **kwargs):
        router._run_registry.active().request_stop()
        if failure == "operator":
            raise RuntimeError("mutation failed while stopping")
        return original(*args, **kwargs)
    monkeypatch.setattr(ga_service, operation, stop)
    if failure == "persistence":
        def cannot_save(*args):
            raise OSError("stopped storage unavailable")
        monkeypatch.setattr(router, "save_stopped_result", cannot_save)
    with TestClient(app) as client:
        response = client.post("/api/ga/stream", params={"population_size": 3, "generations": 2, "fresh_chromosomes": 0})
        events = frames(response)
        assert events[-1]["data"]["status"] == "FAILED"
        assert any(event["type"] == "error" for event in events)
        assert not any(event["type"] == "result" or event["data"].get("status") == "STOPPED" for event in events)
        control = router._run_registry.get(events[0]["run_id"])
        assert control.state == "FAILED" and control.terminal_error
        assert not client.post(f"/api/ga/runs/{control.run_id}/stop").json()["accepted"]
    assert router._read_latest_result() == {"previous_completed": True}
    assert not router._ga_execution_lock.locked()


def test_stop_during_finalization_conflicts_and_stopping_holds_admission(isolated, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = router.save_stopped_result
    def persist(*args):
        entered.set()
        assert release.wait(15)
        return original(*args)
    monkeypatch.setattr(router, "save_stopped_result", persist)
    original_mutation = ga_service.mutate_by_swapping_faculty_subjects
    def mutation(**kwargs):
        router._run_registry.active().request_stop()
        return original_mutation(**kwargs)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", mutation)
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, "/api/ga/stream", params={"population_size": 3, "generations": 2, "fresh_chromosomes": 0})
        try:
            assert entered.wait(15)
            active = client.get("/api/ga/status").json()["active_run"]
            assert active["state"] == "STOPPING" and active["result_reference"] is None
            assert client.post(f'/api/ga/runs/{active["run_id"]}/stop').json()["already_requested"]
            assert client.get(f'/api/ga/runs/{active["run_id"]}/result').status_code == 404
            for other in ("generate", "run", "stream"):
                assert client.post(f"/api/ga/{other}").status_code == 409
        finally:
            release.set()
        assert frames(pending.result(timeout=20))[-1]["data"]["status"] == "STOPPED"
    control = router._run_registry.register()
    control.start()
    control.boundary(1, 1)
    assert control.seal() is False
    with TestClient(app) as client:
        assert client.post(f"/api/ga/runs/{control.run_id}/stop").status_code == 409
        control.finish("COMPLETED")
        assert client.post(f"/api/ga/runs/{control.run_id}/stop").json()["accepted"] is False


def test_disconnect_detaches_monitoring_but_explicit_stop_still_works(isolated, monkeypatch):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    mutation = ga_service.mutate_by_swapping_faculty_subjects
    def blocked(**kwargs):
        entered.set()
        assert release.wait(15)
        return mutation(**kwargs)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", blocked)
    original_release = router._release_execution
    def released(control):
        original_release(control)
        finished.set()
    monkeypatch.setattr(router, "_release_execution", released)
    response = router.stream_ga(population_size=3, generations=2, fresh_chromosomes=0, baseline_mode="fresh")
    async def disconnect():
        await anext(response.body_iterator)
        await response.body_iterator.aclose()
    try:
        asyncio.run(disconnect())
        assert entered.wait(15)
        control = router._run_registry.active()
        assert not control.stop_requested and control.state == "RUNNING"
        with TestClient(app) as client:
            assert client.post(f"/api/ga/runs/{control.run_id}/stop").json()["accepted"]
    finally:
        release.set()
    assert finished.wait(20)
    assert control.state == "STOPPED" and control.result_reference
    assert not router._ga_execution_lock.locked()


def test_atomic_stopped_write_failure_leaves_no_visible_artifact(isolated, monkeypatch):
    control = RunControl()
    def denied(*args):
        raise OSError("replace failed")
    monkeypatch.setattr(ga_control_service.os, "replace", denied)
    with pytest.raises(OSError):
        ga_control_service.save_stopped_result(control, {"status": "STOPPED"})
    assert not list(ga_control_service.STOPPED_RUNS_DIR.iterdir())


def test_stop_completion_race_has_one_winner():
    for _ in range(20):
        control = RunControl()
        control.start()
        control.boundary(1, 10)
        barrier = threading.Barrier(2)
        def stop():
            barrier.wait()
            try:
                return control.request_stop()["accepted"]
            except StopConflict:
                return False
        def seal():
            barrier.wait()
            return control.seal()
        with ThreadPoolExecutor(max_workers=2) as pool:
            requested, sealed = pool.submit(stop), pool.submit(seal)
            accepted, stopped = requested.result(), sealed.result()
        assert accepted == stopped
        control.finish("STOPPED" if stopped else "COMPLETED")
        assert not control.request_stop()["accepted"]
