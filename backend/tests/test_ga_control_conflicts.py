"""Lifecycle/admission races use private markers and no production evolution."""
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from services import ga_checkpoint_service as checkpoints
from tests.test_ga_paused_recovery import paused_metadata, router


@pytest.mark.parametrize("action", ["stop", "resume"])
def test_status_remains_readable_during_control_checkpoint_validation(monkeypatch, action):
    registry, control = paused_metadata()
    monkeypatch.setattr(router, "_run_registry", registry)
    entered, release = threading.Event(), threading.Event()
    rng = random.getstate()

    def validation(*args):
        entered.set()
        assert release.wait(10)
        raise checkpoints.CheckpointError("Checkpoint inputs changed.", "GA_CHECKPOINT_INPUT_CHANGED")

    monkeypatch.setattr(checkpoints, "load_checkpoint", validation)
    monkeypatch.setattr(router, "run_genetic_algorithm", lambda **kwargs: pytest.fail("Invalid checkpoint must not start a worker"))
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=4) as pool:
        pending = pool.submit(client.post, f"/api/ga/runs/{control.run_id}/{action}")
        try:
            assert entered.wait(5)
            snapshot = pool.submit(client.get, f"/api/ga/runs/{control.run_id}").result(1).json()
            assert snapshot["state"] == "PAUSED" and not snapshot["stop_requested"]
            assert not snapshot["execution_active"]
            discovery = pool.submit(client.get, "/api/ga/status").result(1).json()
            assert discovery["paused_runs"][0]["run_id"] == control.run_id
            # Admission stays exclusive while compatibility is verified.
            duplicate = client.post(f"/api/ga/runs/{control.run_id}/{action}")
            assert duplicate.status_code == 409
            assert duplicate.json()["detail"]["code"] == "GA_EXECUTION_BUSY"
        finally:
            release.set()
        rejected = pending.result(5)
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["code"] == "GA_CHECKPOINT_INPUT_CHANGED"
        assert client.get(f"/api/ga/runs/{control.run_id}").json()["state"] == "PAUSED"
    assert registry.active() is None and not router._ga_execution_lock.locked()
    assert random.getstate() == rng


@pytest.mark.parametrize("state", ["STOP_REQUESTED", "STOPPING", "STOPPED"])
def test_stopping_and_terminal_runs_never_advertise_a_resumable_checkpoint(monkeypatch, state):
    registry, control = paused_metadata()
    control.state = state
    control.stop_requested = True
    checkpoints.write_marker(control)
    monkeypatch.setattr(router, "_run_registry", registry)
    monkeypatch.setattr(checkpoints, "load_checkpoint", lambda *args: pytest.fail("Stopping runs must not verify for resume"))
    with TestClient(app) as client:
        snapshot = client.get(f"/api/ga/runs/{control.run_id}").json()
        verified = client.get(f"/api/ga/runs/{control.run_id}/checkpoint-status").json()
        assert snapshot["state"] == verified["state"] == state
        assert snapshot["stop_requested"] and not snapshot["accepting_resume"]
        assert not verified["resumable"]
        assert client.get("/api/ga/status").json()["paused_runs"] == []
        response = client.post(f"/api/ga/runs/{control.run_id}/resume")
        if state == "STOPPED":
            assert response.status_code == 200 and not response.json()["accepted"]
        else:
            assert response.status_code == 409


@pytest.mark.parametrize("changed", ["STOPPING", "checkpoint"])
def test_admission_rechecks_paused_state_and_checkpoint_after_validation(monkeypatch, changed):
    registry, control = paused_metadata()
    monkeypatch.setattr(router, "_run_registry", registry)

    def validation(*args):
        if changed == "checkpoint":
            control.checkpoint = "checkpoint-2-other.json.gz"
        else:
            control.state = changed
        checkpoints.write_marker(control)
        return {}  # The race must reject before reading/restoring GA parameters.

    monkeypatch.setattr(checkpoints, "load_checkpoint", validation)
    monkeypatch.setattr(router, "run_genetic_algorithm", lambda **kwargs: pytest.fail("Changed run must not start a worker"))
    with TestClient(app) as client:
        response = client.post(f"/api/ga/runs/{control.run_id}/resume")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "GA_RESUME_CONFLICT"
    assert registry.active() is None and not router._ga_execution_lock.locked()
