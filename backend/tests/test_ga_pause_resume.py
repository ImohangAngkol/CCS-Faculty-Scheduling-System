"""Bounded exact-continuation checks; all artifacts are isolated by fixtures."""
import copy
import gzip
import importlib
import json
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from services import ga_service, ga_checkpoint_service as checkpoints
from services.ga_control_service import RunControl, RunRegistry
from genetic_algorithm.utils.FrozenInputs import scoring_inputs
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from tests.test_ga_safe_stop import isolated, bounded_run, small_population
from tests.test_ga_refresh_recovery import live_server

router = importlib.import_module("routers.genetic_algorithm")


def wait_finished(client, run_id, expected):
    deadline = time.monotonic() + 30
    while True:
        state = client.get(f"/api/ga/runs/{run_id}").json()
        # Registry release precedes history lifecycle flush/admission cleanup.
        # Do not tear down temporary storage or begin another test in that gap.
        if not state["execution_active"] and not router._ga_execution_lock.locked():
            assert state["state"] == expected, state
            return state
        assert time.monotonic() < deadline, state
        time.sleep(0.01)


@pytest.mark.parametrize("generation", [0, 1, 3])
def test_uninterrupted_and_json_restored_population_are_exactly_equivalent(isolated, monkeypatch, generation):
    calls = []
    population_module = importlib.import_module("genetic_algorithm.operators.CreatePopulation")
    def counted(*a, **k):
        calls.append(1)
        return faculty_preference_fitness(*a, **k)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", counted)
    monkeypatch.setattr(population_module, "faculty_preference_fitness", counted)
    before = random.getstate()
    try:
        random.seed(153)
        plain = ga_service.run_genetic_algorithm(3, 3, 1, progress_callback=lambda *a: None)
        plain_rng, plain_calls = random.getstate(), len(calls)
        calls.clear()
        control = RunControl(configuration={"population_size": 3, "generations": 3, "fresh_chromosomes": 1})
        control.start()
        events = []
        def progress(kind, data):
            control.capture_progress(kind, data)
            events.append(data["generation"])
            if data["generation"] == generation:
                control.request_pause()
        random.seed(153)
        paused = ga_service.run_genetic_algorithm(3, 3, 1, progress_callback=progress, run_control=control)
        assert isinstance(paused, checkpoints.PausedRun) and control.state == "PAUSED"
        assert scoring_inputs.get() is None
        state = checkpoints.load_checkpoint(control.run_id, (
            ga_service.list_subjects, ga_service.list_faculty, ga_service.lst_rooms))
        assert len(state["population"]) == 3 and state["next_generation"] == generation + 1
        assert state["random_state"] == random.getstate()
        # Admit continuation only after the original worker has exited.
        control.execution_active = False
        control.begin_resume()
        random.seed(999)  # A different run may have used global random meanwhile.
        resumed = ga_service.run_genetic_algorithm(**state["parameters"], resume_state=state,
                                                  progress_callback=lambda kind, data: events.append(data["generation"]),
                                                  run_control=control)
        assert random.getstate() == plain_rng
        assert len(calls) == plain_calls
        assert events == [0, 1, 2, 3]
        for field in ("schedule", "history", "best_fitness", "fitness_breakdown", "faculty_analysis"):
            assert resumed[field] == plain[field]
    finally:
        random.setstate(before)


def test_pause_before_generation_zero_waits_for_a_valid_complete_population(isolated):
    control = RunControl()
    control.request_pause()
    control.start()
    paused = ga_service.run_genetic_algorithm(3, 2, 0, run_control=control, progress_callback=control.capture_progress)
    assert isinstance(paused, checkpoints.PausedRun)
    state = checkpoints.load_checkpoint(control.run_id, router._templates())
    assert state["generation_completed"] == 0 and len(state["population"]) == 3


@pytest.mark.parametrize("when", ["retry", "checkpoint"])
def test_stop_overrides_pending_pause_without_another_generation(isolated, monkeypatch, when):
    control = RunControl()
    control.start()
    mutations = []
    def mutation(**kwargs):
        mutations.append(1)
        control.request_pause()
        if when == "retry":
            control.request_stop()
        return None
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", mutation)
    original = ga_service.save_checkpoint
    def saving(*args):
        filename = original(*args)
        control.request_stop()
        return filename
    if when == "checkpoint":
        monkeypatch.setattr(ga_service, "save_checkpoint", saving)
    result = ga_service.run_genetic_algorithm(3, 3, 0, run_control=control, progress_callback=control.capture_progress)
    assert isinstance(result, dict) and control.state == "STOPPING"
    assert result["generations_completed"] == 1 and mutations == [1]


def pause_api(client):
    original = ga_service.mutate_by_swapping_faculty_subjects
    control = router._run_registry.active()
    assert control is not None
    assert client.post(f"/api/ga/runs/{control.run_id}/pause").json()["accepted"]
    assert client.post(f"/api/ga/runs/{control.run_id}/pause").json()["already_requested"]
    return original


def test_api_pause_registry_restart_resume_and_concurrent_admission(isolated, monkeypatch):
    original = ga_service.mutate_by_swapping_faculty_subjects
    entered, release = threading.Event(), threading.Event()
    def held(**kwargs):
        entered.set()
        assert release.wait(30)
        return original(**kwargs)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", held)
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(client.post, "/api/ga/run", params={"population_size": 3, "generations": 3, "fresh_chromosomes": 0})
        try:
            assert entered.wait(30)
            pause_api(client)
        finally:
            release.set()
        reply = pending.result(30).json()
        assert reply["status"] == "paused"
        run_id = reply["run"]["run_id"]
        state = wait_finished(client, run_id, "PAUSED")
        old_process = state["process_instance_id"]
        assert client.get(f"/api/ga/runs/{run_id}/checkpoint-status").json()["resumable"]
        monkeypatch.setattr(router, "_run_registry", RunRegistry())  # Restart: no old population or worker.
        recovered = client.get("/api/ga/status").json()
        assert recovered["active_run"] is None
        assert recovered["paused_runs"][0]["run_id"] == run_id
        assert recovered["paused_runs"][0]["process_instance_id"] != old_process
        assert client.post(f"/api/ga/runs/{run_id}/resume", headers={"X-GA-Process-ID": old_process}).status_code == 409
        entered.clear()
        release.clear()
        responses = list(pool.map(lambda _: client.post(f"/api/ga/runs/{run_id}/resume"), range(2)))
        assert any(response.status_code == 200 and response.json()["accepted"] for response in responses)
        assert entered.wait(30)
        assert client.post("/api/ga/stream").status_code == 409
        assert client.post(f"/api/ga/runs/{run_id}/resume").json()["already_requested"]
        release.set()
        final = wait_finished(client, run_id, "COMPLETED")
        assert final["latest_completed_generation"] == 3
        assert [point["generation"] for point in final["progress_history"]] == [0, 1, 2, 3]
        assert client.get(f"/api/ga/runs/{run_id}/result").json()["data"]["run_id"] == run_id


def test_checkpoint_failure_is_failed_not_paused_and_preserves_previous_checkpoint(isolated, monkeypatch):
    control = RunControl()
    control.start()
    control.request_pause()
    ga_service.run_genetic_algorithm(3, 2, 0, run_control=control, progress_callback=control.capture_progress)
    path = checkpoints.run_directory(control.run_id) / control.checkpoint
    original = path.read_bytes()
    restored = checkpoints.load_checkpoint(control.run_id, router._templates())
    control.execution_active = False
    control.begin_resume()
    def failed(*a, **k):
        raise OSError("Checkpoint disk failed")
    monkeypatch.setattr(checkpoints, "atomic_write", failed)
    control.resumed()
    control.request_pause()
    with pytest.raises(OSError):
        ga_service.run_genetic_algorithm(**restored["parameters"], resume_state=restored,
                                        run_control=control, progress_callback=control.capture_progress)
    control.fail(OSError("Checkpoint disk failed"))
    assert control.state == "FAILED" and path.read_bytes() == original


@pytest.mark.parametrize("case", ["corrupt", "engine", "input", "invalid"])
def test_corrupt_incompatible_or_invalid_checkpoints_never_resume(isolated, monkeypatch, case):
    control = RunControl()
    control.start()
    control.request_pause()
    ga_service.run_genetic_algorithm(3, 2, 0, run_control=control, progress_callback=control.capture_progress)
    path = checkpoints.run_directory(control.run_id) / control.checkpoint
    if case == "corrupt":
        path.write_bytes(b"bad checkpoint")
    elif case == "engine":
        monkeypatch.setattr(checkpoints, "engine_fingerprint", lambda: "changed")
    elif case == "input":
        monkeypatch.setattr(checkpoints, "input_fingerprint", lambda: "changed")
    else:
        envelope = json.loads(gzip.decompress(path.read_bytes()))
        state = checkpoints.decode_graph(envelope["payload"]["graph"])
        state["population"][0][0].assigned_faculty = None
        envelope["payload"]["graph"] = checkpoints.encode_graph(state)
        import hashlib
        envelope["sha256"] = hashlib.sha256(checkpoints.canonical(envelope["payload"])).hexdigest()
        path.write_bytes(gzip.compress(checkpoints.canonical(envelope)))
    rng = random.getstate()
    with pytest.raises(checkpoints.CheckpointError):
        checkpoints.load_checkpoint(control.run_id, router._templates())
    assert random.getstate() == rng


def test_uncheckpointed_restart_is_interrupted_and_not_resumable(isolated, monkeypatch):
    control = router._admit_execution()
    router._release_execution(control)
    monkeypatch.setattr(router, "_run_registry", RunRegistry())
    with TestClient(app) as client:
        state = client.get(f"/api/ga/runs/{control.run_id}").json()
        assert state["state"] == "INTERRUPTED"
        assert client.post(f"/api/ga/runs/{control.run_id}/resume").status_code == 409


def test_json_graph_preserves_aliases_and_rejects_executable_types():
    subject = ga_service.list_subjects[0]
    value = [subject, subject, {"ordered": (1, 2)}]
    restored = checkpoints.decode_graph(checkpoints.encode_graph(value))
    assert restored[0] is restored[1]
    assert restored[2]["ordered"] == (1, 2)
    with pytest.raises(checkpoints.CheckpointError):
        checkpoints.decode_graph({"root": {"ref": 0}, "nodes": [{"kind": "subprocess", "items": []}]})


def test_pause_during_crossover_retries_preserves_the_complete_boundary(isolated, monkeypatch):
    control = RunControl()
    control.start()
    attempts = []
    def rejected(**kwargs):
        attempts.append(1)
        if len(attempts) == 2:
            control.request_pause()
        return None
    monkeypatch.setattr(ga_service, "create_child_by_faculty_swap", rejected)
    result = ga_service.run_genetic_algorithm(3, 3, 0, run_control=control,
                                            progress_callback=control.capture_progress)
    assert isinstance(result, checkpoints.PausedRun)
    assert len(attempts) == 40 and control.latest_completed_generation == 1
    assert checkpoints.load_checkpoint(control.run_id, router._templates())["next_generation"] == 2


def test_pause_completion_race_is_linearized():
    from services.ga_control_service import StopConflict
    completion = RunControl()
    completion.start()
    completion.boundary(1, 0)
    assert not completion.begin_pause(final=True)
    with pytest.raises(StopConflict):
        completion.request_pause()
    pause = RunControl()
    pause.start()
    pause.boundary(1, 0)
    pause.request_pause()
    assert pause.begin_pause(final=True) and pause.state == "PAUSING"
    assert not pause.finalizing


def test_frozen_scoring_inputs_ignore_mutable_loader_changes(isolated, monkeypatch):
    from genetic_algorithm.utils.FrozenInputs import capture_inputs
    import genetic_algorithm.operators.FitnessFunction as fitness_module
    frozen = capture_inputs()
    token = scoring_inputs.set(frozen)
    try:
        candidate = isolated[0][0]
        before = fitness_module.faculty_preference_fitness(candidate, ga_service.df_faculty_pref)
        monkeypatch.setattr(fitness_module.json, "load", lambda *a: pytest.fail("Frozen scoring must not reread disk"))
        assert fitness_module.faculty_preference_fitness(candidate, ga_service.df_faculty_pref) == before
        assert fitness_module._load_dashboard_preferences() == frozen["preferences"]
        assert fitness_module._load_ga_settings().to_dict() == frozen["settings"]
    finally:
        scoring_inputs.reset(token)


def test_real_http_pause_stream_then_resume_without_reinitializing(live_server, monkeypatch):
    import httpx
    original = ga_service.mutate_by_swapping_faculty_subjects
    entered, release = threading.Event(), threading.Event()
    def held(**kwargs):
        entered.set()
        assert release.wait(30)
        return original(**kwargs)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", held)
    previous = router.LATEST_RESULT_FILE.read_bytes()
    with httpx.Client(base_url=live_server, timeout=30) as stream, httpx.Client(base_url=live_server, timeout=30) as client:
        try:
            with stream.stream("POST", "/api/ga/stream", params={"population_size": 3, "generations": 2, "fresh_chromosomes": 0}) as reply:
                lines = reply.iter_lines()
                created = next(json.loads(line[6:]) for line in lines if line.startswith("data: "))
                run_id = created["run_id"]
                assert entered.wait(30)
                assert client.post(f"/api/ga/runs/{run_id}/pause").json()["state"] == "PAUSE_REQUESTED"
                assert client.get("/api/health").status_code == 200
                assert client.post(f"/api/ga/runs/{run_id}/pause").json()["already_requested"]
                release.set()
                events = [json.loads(line[6:]) for line in lines if line.startswith("data: ")]
                assert events[-1]["data"]["status"] == "PAUSED"
                assert events[-1]["data"]["has_result"] is False
                assert not any(event["type"] == "result" for event in events)
            assert not router._ga_execution_lock.locked()
            assert router.LATEST_RESULT_FILE.read_bytes() == previous
            assert client.get(f"/api/ga/runs/{run_id}/checkpoint-status").json()["resumable"]
            def no_initialization(population_size, *args, **kwargs):
                assert population_size == 0, "Resume must not initialize a fresh population"
                return []  # The unchanged generation loop still requests zero immigrants.
            monkeypatch.setattr(ga_service, "generate_population", no_initialization)
            assert client.post(f"/api/ga/runs/{run_id}/resume").json()["accepted"]
            final = wait_finished(client, run_id, "COMPLETED")
            assert [point["generation"] for point in final["progress_history"]] == [0, 1, 2]
        finally:
            release.set()


def test_new_python_process_continues_the_same_population_and_rng(isolated, tmp_path):
    """A fresh interpreter has none of the original model identities or globals."""
    before = random.getstate()
    try:
        random.seed(817)
        plain = ga_service.run_genetic_algorithm(3, 2, 0, progress_callback=lambda *a: None)
        expected_rng = checkpoints.rng_to_json(random.getstate())
        control = RunControl()
        control.start()
        def progress(kind, data):
            control.capture_progress(kind, data)
            if data["generation"] == 1:
                control.request_pause()
        random.seed(817)
        assert isinstance(ga_service.run_genetic_algorithm(3, 2, 0, run_control=control,
                          progress_callback=progress), checkpoints.PausedRun)
        script = '''
import copy, contextlib, io, json, random, sys
from pathlib import Path
from services import ga_service as ga, ga_checkpoint_service as cp, chromosome_service as cs
from genetic_algorithm.utils import Functions as inputs
cp.CHECKPOINTS_DIR = Path(sys.argv[1])
ga.list_subjects = copy.deepcopy([s for s in inputs.list_subjects
    if s.number in {"ITE184", "ITE185", "ITD104"} and s.section.code in {"4A", "4B"}])
ga.list_faculty = copy.deepcopy([f for f in inputs.list_faculty if f.code in {7, 10}])
ga.lst_rooms = copy.deepcopy([r for r in inputs.lst_rooms if r.type == "Lecture"][:2]
    + [r for r in inputs.lst_rooms if r.type == "Laboratory"][:2])
cs.BEST_CHROMOSOME_PATH = Path(sys.argv[3]) / "child-best.json"
ga.create_child_by_faculty_swap = lambda **k: copy.deepcopy(random.choice([k["parent1"], k["parent2"]]))
ga.mutate_by_swapping_faculty_subjects = lambda **k: copy.deepcopy(random.choice(k["population"]))
def no_initialization(population_size, *args, **kwargs):
    assert population_size == 0, "Cannot initialize on resume"
    return []
ga.generate_population = no_initialization
state = cp.load_checkpoint(sys.argv[2], (ga.list_subjects, ga.list_faculty, ga.lst_rooms))
events = []
with contextlib.redirect_stdout(io.StringIO()):
    result = ga.run_genetic_algorithm(**state["parameters"], resume_state=state,
        progress_callback=lambda kind, data: events.append(data["generation"]))
print("CONTINUATION=" + json.dumps({"result": result, "rng": cp.rng_to_json(random.getstate()), "events": events}))
'''
        child = subprocess.run([sys.executable, "-c", script, str(checkpoints.CHECKPOINTS_DIR),
                                control.run_id, str(tmp_path)], cwd=checkpoints.ROOT,
                               capture_output=True, text=True, timeout=90, check=True)
        recovered = json.loads(next(line.split("=", 1)[1] for line in child.stdout.splitlines()
                                    if line.startswith("CONTINUATION=")))
        assert recovered["rng"] == expected_rng and recovered["events"] == [2]
        for field in ("schedule", "history", "best_fitness", "fitness_breakdown", "faculty_analysis"):
            assert recovered["result"][field] == json.loads(json.dumps(plain[field]))
    finally:
        random.setstate(before)


def test_stopping_an_idle_paused_run_preserves_its_valid_boundary(isolated):
    control = router._admit_execution(configuration={"population_size": 3, "generations": 2, "fresh_chromosomes": 0})
    control.start()
    control.request_pause()
    try:
        assert isinstance(ga_service.run_genetic_algorithm(3, 2, 0, run_control=control,
                          progress_callback=control.capture_progress), checkpoints.PausedRun)
    finally:
        router._release_execution(control)
    previous = router.LATEST_RESULT_FILE.read_bytes()
    with TestClient(app) as client:
        assert client.post(f"/api/ga/runs/{control.run_id}/stop").json()["accepted"]
        final = wait_finished(client, control.run_id, "STOPPED")
        assert final["latest_completed_generation"] == 0
        result = client.get(f"/api/ga/runs/{control.run_id}/result").json()["data"]
        assert result["generations_completed"] == 0
        ga_service.validate_saved_result(result)
        assert router.LATEST_RESULT_FILE.read_bytes() == previous
        assert not client.post(f"/api/ga/runs/{control.run_id}/resume").json()["accepted"]
        assert not client.post(f"/api/ga/runs/{control.run_id}/pause").json()["accepted"]
        for action in ("pause", "resume"):
            assert client.post(f"/api/ga/runs/unknown/{action}").json()["detail"]["code"] == "GA_UNKNOWN_RUN"


def test_failed_durable_paused_marker_never_acknowledges_pause(isolated, monkeypatch):
    control = router._admit_execution()
    control.start()
    control.request_pause()
    try:
        ga_service.run_genetic_algorithm(3, 2, 0, run_control=control, progress_callback=control.capture_progress)
    finally:
        router._release_execution(control)
    previous_path = checkpoints.run_directory(control.run_id) / control.checkpoint
    previous = previous_path.read_bytes()
    original_marker = checkpoints.write_marker
    failure_boundary = threading.Event()
    def marker(*args, **kwargs):
        if kwargs.get("state") == "PAUSED":
            failure_boundary.set()
            raise OSError("PAUSED marker could not be committed")
        return original_marker(*args, **kwargs)
    monkeypatch.setattr(checkpoints, "write_marker", marker)
    original_mutation = ga_service.mutate_by_swapping_faculty_subjects
    def pause_again(**kwargs):
        control.request_pause()
        return original_mutation(**kwargs)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", pause_again)
    with TestClient(app) as client:
        acknowledgement = client.post(f"/api/ga/runs/{control.run_id}/resume").json()
        assert acknowledgement["accepted"] and acknowledgement["state"] != "PAUSED"
        # Cold checkpoint serialization/validation can exceed the lifecycle wait.
        # Synchronize with the injected failure before testing terminal cleanup;
        # never tear down fixtures underneath a still-checkpointing worker.
        assert failure_boundary.wait(120), "Worker never reached the injected durable-marker failure"
        final = wait_finished(client, control.run_id, "FAILED")
        assert "could not be committed" in final["terminal_error"]
        assert checkpoints.read_marker(control.run_id)["state"] == "FAILED"
        assert previous_path.read_bytes() == previous
        assert not client.get(f"/api/ga/runs/{control.run_id}/checkpoint-status").json()["resumable"]
        assert router._read_latest_result() == {"previous_completed": True}


def test_input_change_during_freezing_is_rejected(monkeypatch):
    from genetic_algorithm.utils.FrozenInputs import capture_inputs
    from services import ga_progress_service
    values = iter(["before", "after"])
    monkeypatch.setattr(ga_progress_service, "input_fingerprint", lambda: next(values))
    with pytest.raises(ValueError, match="while freezing"):
        capture_inputs()


def test_input_change_between_freezing_and_monitor_creation_is_rejected():
    from genetic_algorithm.utils.FrozenInputs import capture_inputs
    from services.ga_progress_service import GenerationMonitor
    frozen = capture_inputs()
    frozen["input_fingerprint"] = "stale-input-snapshot"
    token = scoring_inputs.set(frozen)
    try:
        with pytest.raises(ValueError, match="inputs/configuration changed"):
            GenerationMonitor(None, 3, 2, {})
    finally:
        scoring_inputs.reset(token)


def test_initial_state_persistence_failure_releases_worker_admission(monkeypatch):
    monkeypatch.setattr(router, "_run_registry", RunRegistry())
    original_marker = checkpoints.write_marker
    def marker(*args, **kwargs):
        if kwargs.get("state") == "INITIALIZING":
            raise OSError("Initial lifecycle persistence failed")
        return original_marker(*args, **kwargs)
    monkeypatch.setattr(checkpoints, "write_marker", marker)
    def forbidden(**kwargs):
        raise AssertionError("A failed initialization must not execute the GA")
    monkeypatch.setattr(router, "run_genetic_algorithm", forbidden)
    with TestClient(app) as client:
        response = client.post("/api/ga/run")
        assert response.status_code == 500
        assert "Initial lifecycle persistence failed" in response.json()["detail"]
        assert not router._ga_execution_lock.locked() and router._run_registry.active() is None
        control = next(iter(router._run_registry.runs.values()))
        assert control.state == "FAILED" and not control.execution_active
        assert checkpoints.read_marker(control.run_id)["state"] == "FAILED"
