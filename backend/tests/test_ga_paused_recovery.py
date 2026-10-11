"""Read-only discovery and verification; artifacts use the isolated fixtures."""
import importlib
import random
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from services import ga_checkpoint_service as checkpoints, ga_service
from services import ga_checkpoint_verification as checkpoint_verification
from services.ga_control_service import RunRegistry
from tests.test_ga_safe_stop import isolated, bounded_run, small_population
from tests.test_ga_refresh_recovery import live_server

router = importlib.import_module("routers.genetic_algorithm")


def paused_metadata():
    registry = RunRegistry()
    control = registry.register({"population_size": 10, "generations": 2, "fresh_chromosomes": 2})
    control.durable = True
    control.state = "PAUSED"
    control.checkpoint = "checkpoint-1-test.json.gz"
    control.execution_active = False
    control.latest_completed_generation = 1
    control.latest_progress = {"generation": 1, "population_actual": 8, "population_requested": 10,
                               "best_ever_fitness": 99, "generation_best_fitness": 99,
                               "average_fitness": 149, "accepted_new_chromosomes_total": 11}
    control.progress_history = [{"generation": 0}, control.latest_progress]
    control.elapsed_offset = 1000
    control.ended_clock = control.started_clock
    checkpoints.write_marker(control)
    registry.release(control)
    return registry, control


@pytest.mark.parametrize("restart", [False, True])
def test_paused_discovery_hydrates_without_loading_any_population(monkeypatch, restart):
    registry, control = paused_metadata()
    monkeypatch.setattr(router, "_run_registry", RunRegistry() if restart else registry)
    def forbidden(*args, **kwargs):
        pytest.fail("Discovery must not deserialize or validate a population")
    monkeypatch.setattr(checkpoints, "load_checkpoint", forbidden)
    monkeypatch.setattr(checkpoints, "checkpoint_status", forbidden)
    monkeypatch.setattr(ga_service, "run_genetic_algorithm", forbidden)
    rng = random.getstate()
    with TestClient(app) as client:
        body = client.get("/api/ga/status").json()
        assert body["active_run"] is None
        run = body["paused_runs"][0]
        assert run["run_id"] == control.run_id and run["state"] == "PAUSED"
        assert run["latest_completed_generation"] == 1
        assert run["configuration"] == control.configuration
        assert run["latest_progress"] == control.latest_progress
        assert run["progress_history"] == control.progress_history
        assert run["elapsed_ms"] == 1000
        assert not run["accepting_resume"]  # Compatibility has not been verified.
        assert run["process_instance_id"] == body["process_instance_id"]
        snapshot = client.get(f"/api/ga/runs/{control.run_id}").json()
        assert snapshot["state"] == "PAUSED" and not snapshot["execution_active"]
    assert random.getstate() == rng


def test_missing_checkpoint_is_an_explicit_error_not_a_lost_paused_identity(monkeypatch):
    registry, control = paused_metadata()
    monkeypatch.setattr(router, "_run_registry", registry)
    with TestClient(app) as client:
        status = client.get(f"/api/ga/runs/{control.run_id}/checkpoint-status",
                            headers={"X-GA-Process-ID": registry.process_instance_id}).json()
        assert not status["resumable"] and status["code"] == "GA_CHECKPOINT_UNAVAILABLE"
        assert status["state"] == "PAUSED" and status["error"]
        assert status["process_instance_id"] == registry.process_instance_id
        assert client.get("/api/ga/status").json()["paused_runs"][0]["run_id"] == control.run_id
        assert registry.active() is None


def test_checkpoint_verification_rejects_another_backend_before_loading(monkeypatch):
    registry, control = paused_metadata()
    monkeypatch.setattr(router, "_run_registry", registry)
    monkeypatch.setattr(checkpoints, "checkpoint_status", lambda *args: pytest.fail("Wrong process must not verify"))
    with TestClient(app) as client:
        response = client.get(f"/api/ga/runs/{control.run_id}/checkpoint-status",
                              headers={"X-GA-Process-ID": "other-process"})
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "GA_PROCESS_CHANGED"


@pytest.mark.parametrize("changed", ["RESUMING", "STOPPING", "checkpoint"])
def test_verification_does_not_enable_resume_after_a_concurrent_transition(monkeypatch, changed):
    registry, control = paused_metadata()
    monkeypatch.setattr(router, "_run_registry", registry)
    def verification(*args):
        result = {"run_id": control.run_id, "state": "PAUSED", "resumable": True, "checkpoint": control.checkpoint}
        if changed == "checkpoint":
            control.checkpoint = "checkpoint-2-new.json.gz"
        else:
            control.state = changed
            control.execution_active = True
        return result
    # This test isolates lifecycle reconciliation, rather than artifact integrity.
    # Mock the read-only verification provider now used by the route.
    monkeypatch.setattr(checkpoint_verification, "checkpoint_status", verification)
    with TestClient(app) as client:
        result = client.get(f"/api/ga/runs/{control.run_id}/checkpoint-status").json()
        assert not result["resumable"] and result["state"] == control.state


@pytest.mark.parametrize("state", ["RUNNING", "PAUSE_REQUESTED", "PAUSING", "RESUMING", "STOPPING"])
def test_discovery_distinguishes_pending_states_and_restart_interruptions(monkeypatch, state):
    registry = RunRegistry()
    control = registry.register()
    control.durable = True
    control.state = state
    checkpoints.write_marker(control)
    monkeypatch.setattr(router, "_run_registry", registry)
    with TestClient(app) as client:
        live = client.get("/api/ga/status").json()
        assert live["active_run"]["state"] == state and live["paused_runs"] == []
        monkeypatch.setattr(router, "_run_registry", RunRegistry())
        restored = client.get(f"/api/ga/runs/{control.run_id}").json()
        assert restored["state"] == "INTERRUPTED" and not restored["accepting_resume"]
        assert client.post(f"/api/ga/runs/{control.run_id}/resume").status_code == 409


def test_valid_paused_checkpoint_status_preserves_population_metrics_and_rng(isolated, monkeypatch):
    control = router._admit_execution(configuration={"population_size": 3, "generations": 2, "fresh_chromosomes": 0})
    try:
        control.start()
        control.request_pause()
        ga_service.run_genetic_algorithm(3, 2, 0, run_control=control, progress_callback=control.capture_progress)
    finally:
        router._release_execution(control)
    checkpoint_bytes = (checkpoints.run_directory(control.run_id) / control.checkpoint).read_bytes()
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", lambda *args, **kwargs: pytest.fail("Recovery cannot score"))
    rng = random.getstate()
    with TestClient(app) as client:
        discovered = client.get("/api/ga/status").json()["paused_runs"][0]
        verified = client.get(f"/api/ga/runs/{control.run_id}/checkpoint-status").json()
        assert verified["resumable"] and verified["generation_completed"] == 0
        assert verified["next_generation"] == 1 and verified["state"] == "PAUSED"
        assert discovered["latest_progress"] == control.latest_progress
        assert discovered["progress_history"] == control.progress_history
        assert discovered["configuration"] == {"population_size": 3, "generations": 2, "fresh_chromosomes": 0}
        assert router._run_registry.active() is None
    assert random.getstate() == rng
    assert (checkpoints.run_directory(control.run_id) / control.checkpoint).read_bytes() == checkpoint_bytes


@pytest.mark.skipif(shutil.which("node") is None, reason="Node/browser integration requires Node")
def test_real_browser_pause_refresh_and_resume(live_server, monkeypatch):
    """Real UI and HTTP lifecycle with bounded real-model population fixtures."""
    original_mutation = ga_service.mutate_by_swapping_faculty_subjects
    original_population = ga_service.generate_population
    calls = []
    released = threading.Event()
    def population(population_size, *args, **kwargs):
        calls.append(population_size)
        return original_population(population_size, *args, **kwargs)
    def mutation(**kwargs):
        control = router._run_registry.active()
        deadline = time.monotonic() + 60
        # Keep the first generation open until the browser requests pause.
        while not control.pause_requested and control.resumed_at is None and not released.is_set():
            assert time.monotonic() < deadline, "Browser did not request pause"
            time.sleep(0.01)
        return original_mutation(**kwargs)
    monkeypatch.setattr(ga_service, "generate_population", population)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", mutation)
    workspace = Path(__file__).resolve().parents[2]
    try:
        reply = subprocess.run([shutil.which("node"), "--test", "tests/gaPausedRecovery.integration.mjs"],
                               cwd=workspace / "frontend", env={**os.environ, "GA_RECOVERY_TEST_URL": live_server},
                               capture_output=True, text=True, timeout=260)
        assert reply.returncode == 0, reply.stdout + reply.stderr
        assert calls.count(10) == 1, "Refresh/resume must never construct another initial population"
        control = next(iter(router._run_registry.runs.values()))
        assert control.state == "COMPLETED" and control.latest_completed_generation == 2
        assert [point["generation"] for point in control.progress_history] == [0, 1, 2]
        assert router._run_registry.active() is None
    finally:
        released.set()
        control = router._run_registry.active()
        if control:
            if control.snapshot()["accepting_stop"]:
                control.request_stop()
            deadline = time.monotonic() + 30
            while control.execution_active and time.monotonic() < deadline:
                time.sleep(0.01)
