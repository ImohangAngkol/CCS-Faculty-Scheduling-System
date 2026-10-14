"""Phase 3D.3 diagnostics; bounded fixtures never touch institutional artifacts."""
import builtins
import importlib
import io
import json
import random
import sys
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from services import ga_log_service as logs, ga_service
from services.ga_control_service import RunRegistry
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from tests.test_ga_safe_stop import isolated, bounded_run, small_population, frames
from tests.test_ga_pause_resume import wait_finished

router = importlib.import_module("routers.genetic_algorithm")


def test_retention_cursor_paging_long_lines_and_order(monkeypatch):
    buffer = logs.RunLogBuffer()
    monkeypatch.setattr(logs, "MAX_LINES", 210)
    for number in range(230):
        buffer.append(str(number))
    first = buffer.read(0)
    assert first["earlier_logs_truncated"] and first["has_more"]
    assert [entry["sequence"] for entry in first["entries"]] == list(range(21, 221))
    second = buffer.read(first["next_sequence"])
    assert [entry["sequence"] for entry in second["entries"]] == list(range(221, 231))
    assert not second["has_more"] and not second["earlier_logs_truncated"]
    assert not buffer.read(230)["entries"]
    assert buffer.read(999)["cursor_reset"]
    entry = buffer.append("é" * 5000)
    assert entry["line_truncated"] and len(entry["message"].encode()) <= logs.MAX_LINE_BYTES
    monkeypatch.setattr(logs, "MAX_BYTES", 10000)
    for _ in range(10):
        buffer.append("\\" * 4096)
    assert buffer.byte_count <= 10000
    assert len(json.dumps(buffer.read(0)["entries"]).encode()) <= logs.MAX_RESPONSE_BYTES


def test_capture_is_scoped_preserves_stdout_and_formats_once():
    registry = RunRegistry()
    control = registry.register()
    original_stdout, original_print = sys.stdout, builtins.print
    formats = []
    class Once:
        def __str__(self):
            formats.append(1)
            return "one"
    other_file = io.StringIO()
    with logs.capture_run_logs(registry, control):
        ga_service.print(Once(), end="")
        ga_service.print(" line")
        builtins.print("unrelated request")
        ga_service.print("explicit file", file=other_file)
        thread = threading.Thread(target=lambda: ga_service.print("other thread"))
        thread.start(); thread.join()
        ga_service.print("partial", end="")
        assert sys.stdout is original_stdout and builtins.print is original_print
    assert formats == [1]
    assert other_file.getvalue() == "explicit file\n"
    assert [entry["message"] for entry in logs.store_for(registry).buffer(control.run_id).read(0)["entries"]] == ["one line", "partial"]


def test_two_threads_do_not_mix_run_logs_or_ga_random():
    registry = RunRegistry()
    controls = [registry.register(), registry.register()]
    rng = random.getstate()
    def capture(control):
        with logs.capture_run_logs(registry, control):
            for number in range(40):
                ga_service.print(control.run_id, number)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(capture, controls))
    assert random.getstate() == rng
    for control in controls:
        entries = logs.store_for(registry).buffer(control.run_id).read(0)["entries"]
        assert [entry["sequence"] for entry in entries] == list(range(1, 41))
        assert all(entry["message"].startswith(control.run_id) for entry in entries)


def test_global_retention_keeps_executing_buffer(monkeypatch):
    monkeypatch.setattr(logs, "MAX_RUNS", 2)
    store = logs.RunLogStore()
    active = store.buffer("worker", pin=True)
    active.append("running")
    for number in range(20):
        store.buffer(str(number))
    assert len(store.buffers) == 2 and store.buffer("worker") is active


def test_concurrent_log_and_status_reads_are_observational(monkeypatch):
    registry = RunRegistry()
    control = registry.register()
    control.start()
    monkeypatch.setattr(router, "_run_registry", registry)
    buffer = logs.store_for(registry).buffer(control.run_id)
    buffer.append("running")
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", lambda *a, **k: pytest.fail("Logs cannot score"))
    rng = random.getstate()
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda i: client.get(f"/api/ga/runs/{control.run_id}" + ("/logs?after_sequence=0" if i % 2 else "")), range(24)))
        assert all(response.status_code == 200 and response.json()["state"] == control.state for response in responses)
        assert client.get(f"/api/ga/runs/{control.run_id}/logs?after_sequence=-1").status_code == 422
        assert client.get(f"/api/ga/runs/{control.run_id}/logs", headers={"X-GA-Process-ID": "wrong"}).status_code == 409
        assert client.get("/api/ga/runs/unknown/logs").status_code == 404
    assert random.getstate() == rng and registry.active() is control


@pytest.mark.parametrize("console_encoding", ["utf-8", "cp1252"])
def test_capture_preserves_rng_fitness_calls_and_schedule(isolated, monkeypatch, console_encoding):
    calls = []
    population_module = importlib.import_module("genetic_algorithm.operators.CreatePopulation")
    def score(*args, **kwargs):
        calls.append(1)
        return faculty_preference_fitness(*args, **kwargs)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", score)
    monkeypatch.setattr(population_module, "faculty_preference_fitness", score)
    original_rng = random.getstate()
    try:
        random.seed(61)
        plain = ga_service.run_genetic_algorithm(3, 2, 0, progress_callback=lambda *a: None)
        expected_rng, expected_calls = random.getstate(), len(calls)
        calls.clear()
        registry = RunRegistry()
        control = registry.register()
        monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding=console_encoding, errors="strict"))
        random.seed(61)
        with logs.capture_run_logs(registry, control):
            captured = ga_service.run_genetic_algorithm(3, 2, 0, progress_callback=lambda *a: None)
        assert random.getstate() == expected_rng and len(calls) == expected_calls
        for field in ("schedule", "history", "best_fitness", "fitness_breakdown", "faculty_analysis"):
            assert captured[field] == plain[field]
        assert logs.store_for(registry).buffer(control.run_id).read(0)["entries"]
    finally:
        random.setstate(original_rng)


@pytest.mark.parametrize("restart", [False, True])
@pytest.mark.parametrize("console_encoding", ["utf-8", "cp1252"])
def test_stream_pause_refresh_resume_reconnects_logs_before_next_generation(isolated, monkeypatch, restart, console_encoding):
    # Pause after validated generation zero; keep resumed mutation in progress
    # so diagnostic delivery is proven independently of generation completion.
    original_mutation = ga_service.mutate_by_swapping_faculty_subjects
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding=console_encoding, errors="strict"))
    entered, release = threading.Event(), threading.Event()
    workers = []
    def held(**kwargs):
        ga_service.print("RESUMED MUTATION DIAGNOSTIC")
        entered.set()
        assert release.wait(30)
        return original_mutation(**kwargs)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", held)
    def running(**kwargs):
        workers.append(kwargs.get("resume_state") is not None)
        callback = kwargs["progress_callback"]
        def progress(kind, data):
            callback(kind, data)
            if data["generation"] == 0 and not kwargs.get("resume_state"):
                kwargs["run_control"].request_pause()
        return ga_service.run_genetic_algorithm(**{**kwargs, "progress_callback": progress})
    monkeypatch.setattr(router, "run_genetic_algorithm", running)
    with TestClient(app) as client:
        response = client.post("/api/ga/stream", params={"population_size": 3, "generations": 1, "fresh_chromosomes": 0})
        events = frames(response)
        control = next(iter(router._run_registry.runs.values()))
        assert control.state == "PAUSED" and not control.execution_active
        endpoint = f"/api/ga/runs/{control.run_id}/logs"
        first = client.get(endpoint).json()
        assert first["state"] == "PAUSED" and not first["earlier_logs_truncated"]
        assert [entry["message"] for entry in first["entries"]] == [event["message"] for event in events if event["type"] == "log"]
        assert first["entries"][-1]["message"] == "GENETIC ALGORITHM PAUSED"
        assert client.get(endpoint).json()["entries"] == first["entries"]  # Refresh only reads.
        cursor = first["next_sequence"]
        if restart:
            monkeypatch.setattr(router, "_run_registry", RunRegistry())
            restored = client.get("/api/ga/status").json()["paused_runs"][0]
            assert restored["run_id"] == control.run_id
            missing = client.get(endpoint + f"?after_sequence={cursor}").json()
            assert missing["cursor_reset"] and missing["earlier_logs_truncated"] and missing["entries"] == []
            assert missing["log_epoch"] != first["log_epoch"]
            cursor = 0
        assert client.get(f"/api/ga/runs/{control.run_id}/checkpoint-status").json()["resumable"]
        try:
            assert client.post(f"/api/ga/runs/{control.run_id}/resume").json()["accepted"]
            assert entered.wait(30)
            resumed = client.get(endpoint + f"?after_sequence={cursor}").json()
            assert resumed["state"] == "RUNNING" and resumed["execution_active"]
            assert "RESUMED MUTATION DIAGNOSTIC" in [entry["message"] for entry in resumed["entries"]]
            assert client.get(f"/api/ga/runs/{control.run_id}").json()["latest_completed_generation"] == 0
            assert client.post(f"/api/ga/runs/{control.run_id}/resume").json()["already_requested"]
            assert client.post("/api/ga/stream").status_code == 409
            assert workers == [False, True]
            assert client.get(endpoint + f"?after_sequence={resumed['next_sequence']}").json()["entries"] == []
        finally:
            release.set()
        final = wait_finished(client, control.run_id, "COMPLETED")
        assert final["latest_completed_generation"] == 1
        last = client.get(endpoint + f"?after_sequence={resumed['next_sequence']}").json()
        assert last["entries"][-1]["message"] == "GENETIC ALGORITHM COMPLETED"
        assert not last["execution_active"] and not last["has_more"]


def test_fresh_python_process_recovers_checkpoint_and_logs_new_worker(isolated, tmp_path):
    from services import ga_checkpoint_service as checkpoints
    control = router._admit_execution(configuration={"population_size": 3, "generations": 1, "fresh_chromosomes": 0})
    try:
        control.request_pause()
        control.start()
        with logs.capture_run_logs(router._run_registry, control):
            ga_service.run_genetic_algorithm(3, 1, 0, run_control=control, progress_callback=control.capture_progress)
    finally:
        router._release_execution(control)
    # Only the durable fixture directory crosses the interpreter boundary.
    script = '''
import copy, importlib, json, random, sys, time
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from services import ga_service as ga, ga_checkpoint_service as cp, chromosome_service as cs
from services import ga_history_service as history
from services.preference_authorization import current_principal, PreferencePrincipal
app.dependency_overrides[current_principal] = lambda: PreferencePrincipal("admin")
from genetic_algorithm.utils import Functions as inputs
router = importlib.import_module("routers.genetic_algorithm")
sys.stdout.reconfigure(encoding="cp1252", errors="strict")
cp.CHECKPOINTS_DIR = Path(sys.argv[1])
router.LATEST_RESULT_FILE = Path(sys.argv[3]) / "child-latest.json"
cs.BEST_CHROMOSOME_PATH = Path(sys.argv[3]) / "child-best.json"
history.SNAPSHOTS_DIR = Path(sys.argv[3]) / "child-history"
ga.list_subjects = copy.deepcopy([s for s in inputs.list_subjects
    if s.number in {"ITE184", "ITE185", "ITD104"} and s.section.code in {"4A", "4B"}])
ga.list_faculty = copy.deepcopy([f for f in inputs.list_faculty if f.code in {7, 10}])
ga.lst_rooms = copy.deepcopy([r for r in inputs.lst_rooms if r.type == "Lecture"][:2]
    + [r for r in inputs.lst_rooms if r.type == "Laboratory"][:2])
ga.create_child_by_faculty_swap = lambda **k: copy.deepcopy(random.choice([k["parent1"], k["parent2"]]))
ga.mutate_by_swapping_faculty_subjects = lambda **k: copy.deepcopy(random.choice(k["population"]))
def no_initialization(population_size, *args, **kwargs):
    assert population_size == 0, "Cannot initialize on resume"
    return []
ga.generate_population = no_initialization
workers = []
original = router.run_genetic_algorithm
def worker(**kwargs):
    workers.append(1)
    return original(**kwargs)
router.run_genetic_algorithm = worker
endpoint = "/api/ga/runs/" + sys.argv[2]
with TestClient(app) as client:
    discovered = client.get("/api/ga/status").json()["paused_runs"][0]
    missing = client.get(endpoint + "/logs").json()
    assert discovered["state"] == "PAUSED" and missing["earlier_logs_truncated"] and not missing["entries"]
    assert client.post(endpoint + "/resume").json()["accepted"]
    deadline = time.monotonic() + 60
    while client.get(endpoint).json()["execution_active"]:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    final = client.get(endpoint + "/logs").json()
    assert final["state"] == "COMPLETED" and workers == [1]
    assert final["entries"][0]["message"] == "GENETIC ALGORITHM RESUMING"
    assert final["entries"][-1]["message"] == "GENETIC ALGORITHM COMPLETED"
    assert [line["sequence"] for line in final["entries"]] == list(range(1, final["next_sequence"] + 1))
    assert client.get(endpoint).json()["latest_completed_generation"] == 1
print("RECOVERED_LOGS=" + json.dumps({"run_id":final["run_id"], "entries":len(final["entries"])}))
'''
    child = subprocess.run([sys.executable, "-c", script, str(checkpoints.CHECKPOINTS_DIR), control.run_id, str(tmp_path)],
                           cwd=checkpoints.ROOT, capture_output=True, text=True, timeout=120, check=True)
    result = json.loads(next(line.split("=", 1)[1] for line in child.stdout.splitlines() if line.startswith("RECOVERED_LOGS=")))
    assert result["run_id"] == control.run_id and result["entries"] > 2
