"""Real HTTP stream/control integration with bounded fixtures and isolated storage."""
import importlib
import json
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient

from main import app
from services import ga_service
from services.ga_control_service import RunRegistry
from tests.test_ga_safe_stop import isolated, bounded_run, small_population

router = importlib.import_module("routers.genetic_algorithm")


@pytest.fixture
def live_server(isolated):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="off"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(10)
        listener.close()
        assert not thread.is_alive(), "Test HTTP server must not be orphaned"


@pytest.mark.parametrize("refresh", [False, True])
def test_live_stream_registered_id_stops_through_separate_http_request(live_server, monkeypatch, refresh):
    entered, release = threading.Event(), threading.Event()
    original = ga_service.mutate_by_swapping_faculty_subjects
    mutations = []
    def held_mutation(**kwargs):
        mutations.append(1)
        entered.set()
        assert release.wait(20)
        return original(**kwargs)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", held_mutation)
    previous_latest = router.LATEST_RESULT_FILE.read_bytes()
    with httpx.Client(base_url=live_server, timeout=20) as stream_client, httpx.Client(base_url=live_server, timeout=20) as control_client:
        backend = control_client.get("/api/ga/status").json()
        assert backend["control_version"] == "3c.1"
        headers = {"X-GA-Process-ID": backend["process_instance_id"]}
        try:
            with stream_client.stream("POST", "/api/ga/stream", params={"population_size": 3, "generations": 4, "fresh_chromosomes": 0}, headers=headers) as response:
                assert response.status_code == 200
                lines = response.iter_lines()
                created = next(json.loads(line[6:]) for line in lines if line.startswith("data: "))
                assert created["type"] == "run_created"
                run_id = created["run_id"]
                assert created["data"]["run_id"] == run_id
                assert created["data"]["process_instance_id"] == backend["process_instance_id"]
                # Identity is already registered when the first network frame arrives.
                assert control_client.get(f"/api/ga/runs/{run_id}", headers=headers).status_code == 200
                assert entered.wait(20)
                if refresh:
                    response.close()  # Browser refresh detaches only its stream.
                active = control_client.get("/api/ga/status").json()["active_run"]
                assert active["run_id"] == run_id and active["state"] == "RUNNING"
                assert active["latest_progress"]["generation"] == 0
                assert active["configuration"]["generations"] == 4
                stop = control_client.post(f"/api/ga/runs/{run_id}/stop", headers=headers)
                assert stop.status_code == 200
                assert stop.json()["run_id"] == run_id
                assert stop.json()["accepted"] and stop.json()["state"] == "STOP_REQUESTED"
                assert control_client.post(f"/api/ga/runs/{run_id}/stop", headers=headers).json()["already_requested"]
                assert control_client.post("/api/ga/stream").status_code == 409
                release.set()
                if not refresh:
                    events = [json.loads(line[6:]) for line in lines if line.startswith("data: ")]
                    assert events[-1]["type"] == "done" and events[-1]["data"]["status"] == "STOPPED"
                    assert any(event["type"] == "run_state_changed" and event["data"]["state"] == "STOP_REQUESTED" for event in events)
                    assert all(event["run_id"] == run_id for event in events)
            deadline = time.monotonic() + 20
            while True:
                state = control_client.get(f"/api/ga/runs/{run_id}", headers=headers).json()
                if not state["execution_active"]:
                    break
                assert time.monotonic() < deadline
                time.sleep(0.01)
            assert state["state"] == "STOPPED"
            assert state["latest_completed_generation"] == state["latest_progress"]["generation"] == 1
            assert mutations == [1]  # Nothing advances into generation 2.
            result = control_client.get(f"/api/ga/runs/{run_id}/result").json()["data"]
            assert result["status"] == "STOPPED" and result["generations_completed"] == 1
            ga_service.validate_saved_result(result)
            assert router.LATEST_RESULT_FILE.read_bytes() == previous_latest
            assert control_client.get("/api/ga/status").json()["active_run"] is None
        finally:
            release.set()


def test_not_found_route_is_distinct_from_unknown_registered_run(isolated):
    control = router._run_registry.register()
    legacy = FastAPI()
    legacy.include_router(APIRouter(routes=[route for route in router.router.routes
                         if getattr(route, "path", None) != "/api/ga/runs/{run_id}/stop"]))
    with TestClient(legacy) as stale, TestClient(app) as current:
        # The exact reported literal comes from a missing route, even for a valid ID.
        assert stale.post(f"/api/ga/runs/{control.run_id}/stop").json() == {"detail": "Not Found"}
        unknown = current.post("/api/ga/runs/unknown/stop")
        assert unknown.status_code == 404
        assert unknown.json()["detail"]["code"] == "GA_UNKNOWN_RUN"
        assert "Not Found" not in unknown.json()["detail"]["message"]
        assert current.post(f"/api/ga/runs/{control.run_id}/stop").json()["accepted"]


def test_process_restart_or_another_worker_rejects_stale_identity(isolated, monkeypatch):
    old = router._run_registry.register()
    old_process = old.process_instance_id
    monkeypatch.setattr(router, "_run_registry", RunRegistry())
    with TestClient(app) as client:
        headers = {"X-GA-Process-ID": old_process}
        for method, path in (("GET", f"/api/ga/runs/{old.run_id}"), ("POST", f"/api/ga/runs/{old.run_id}/stop"), ("POST", "/api/ga/stream")):
            response = client.request(method, path, headers=headers)
            assert response.status_code == 409
            assert response.json()["detail"]["code"] == "GA_PROCESS_CHANGED"
        assert client.post(f"/api/ga/runs/{old.run_id}/stop").status_code == 404
        assert client.get("/api/ga/status").json()["active_run"] is None
        assert not router._ga_execution_lock.locked()


def test_completed_result_can_be_restored_by_exact_run_id(isolated):
    with TestClient(app) as client:
        result = client.post("/api/ga/run", params={"population_size": 3, "generations": 1, "fresh_chromosomes": 0}).json()["data"]
        response = client.get(f'/api/ga/runs/{result["run_id"]}/result')
        assert response.status_code == 200 and response.json()["data"] == result
        state = client.get(f'/api/ga/runs/{result["run_id"]}').json()
        assert not state["execution_active"] and state["latest_progress"]["generation"] == 1
        state["latest_progress"]["generation"] = 99
        assert client.get(f'/api/ga/runs/{result["run_id"]}').json()["latest_progress"]["generation"] == 1
