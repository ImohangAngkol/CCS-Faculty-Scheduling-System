"""Phase 3E.1 read-only validation and concurrent checkpoint regressions."""
import copy
import os
import pickle
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from services import ga_checkpoint_verification as verification
from services.ga_validation_templates import validation_templates
from services.ga_control_service import RunControl, RunRegistry
from tests.test_ga_generation_history import execute, router, history, checkpoints
from tests.test_ga_safe_stop import isolated, bounded_run, small_population
from tests.test_ga_pause_resume import wait_finished


@pytest.fixture
def paused(isolated, monkeypatch):
    control = RunControl(router._run_registry.process_instance_id)
    control.start()
    def progress(kind, metrics):
        control.capture_progress(kind, metrics)
        if metrics["generation"] == 1:
            control.request_pause()
    result = execute(control, callback=progress)
    assert isinstance(result, checkpoints.PausedRun)
    router._run_registry.runs[control.run_id] = control
    router._run_registry.release(control)
    return control


def test_validation_templates_do_not_traverse_assignment_graphs_or_change_inputs(isolated):
    raw = copy.deepcopy(router._templates())
    subject, faculty = raw[0][0], raw[1][0]
    subject.assigned_faculty = faculty
    faculty.subjects_assigned = [subject]
    # A reachable run-only reference would explode a normal deepcopy.
    class RunOnly:
        def __deepcopy__(self, memo):
            pytest.fail("Read-only validation traversed mutable assignment state")
    subject.lecture_time_blocks = [RunOnly()]
    faculty.time_blocks_monday[0].subject = RunOnly()
    before = pickle.dumps(raw[1][1:])
    rng = random.getstate()
    clean = validation_templates(raw)
    assert random.getstate() == rng
    assert clean[0][0].lecture_time_blocks == []
    assert clean[0][0].assigned_faculty is None
    assert clean[1][0].time_blocks_monday[0].subject is None
    assert raw[0][0].assigned_faculty is faculty
    assert raw[1][0].subjects_assigned == [subject]
    assert pickle.dumps(raw[1][1:]) == before
    for source, detached in zip(raw[1], clean[1]):
        for field in ("eligible_subjects", "required_teaching_load", "absolute_max_teaching_load",
                      "admin_load", "research_load", "extension_load", "preferred_subjects"):
            assert getattr(source, field) == getattr(detached, field)
    from genetic_algorithm.utils.Functions import get_fixed_section_schedule_entries
    for source, detached in zip(raw[0], clean[0]):
        assert source.preassigned_assignment == detached.preassigned_assignment
        assert get_fixed_section_schedule_entries(source.section) == get_fixed_section_schedule_entries(detached.section)


def test_concurrent_history_and_checkpoint_requests_singleflight_readonly(paused, monkeypatch):
    original = checkpoints.checkpoint_status
    entered, release = threading.Event(), threading.Event()
    calls = []
    def held(*args):
        calls.append(1)
        entered.set()
        assert release.wait(20)
        return original(*args)
    monkeypatch.setattr(checkpoints, "checkpoint_status", held)
    previous_rng = random.getstate()
    artifact = checkpoints.run_directory(paused.run_id) / paused.checkpoint
    previous = artifact.read_bytes()
    original_files = {path.name: path.read_bytes() for path in history.directory(paused.run_id).iterdir()}
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=5) as pool:
        base = f"/api/ga/runs/{paused.run_id}"
        pending = [pool.submit(client.get, base + "/checkpoint-status") for _ in range(4)]
        try:
            assert entered.wait(20)
            for generation in (0, 1):
                for suffix in ("", "/schedule", "/analysis"):
                    assert client.get(f"{base}/generations/{generation}{suffix}").status_code == 200
            assert client.get(base + "/compare?left=0&right=1").status_code == 200
            assert client.get(base).json()["state"] == "PAUSED"
            assert not router._ga_execution_lock.locked()
        finally:
            release.set()
        assert all(future.result().json()["resumable"] for future in pending)
        assert client.get(base + "/checkpoint-status").json()["resumable"]
    assert len(calls) == 1
    assert random.getstate() == previous_rng
    assert artifact.read_bytes() == previous
    assert original_files == {path.name: path.read_bytes() for path in history.directory(paused.run_id).iterdir()}
    assert not paused.execution_active


@pytest.mark.parametrize("change", ["bytes", "inputs", "engine", "profile"])
def test_cached_verification_never_bypasses_integrity_or_compatibility(paused, monkeypatch, change):
    assert verification.checkpoint_status(paused.run_id, router._templates())["resumable"]
    if change == "bytes":
        path = checkpoints.run_directory(paused.run_id) / paused.checkpoint
        stat = path.stat()
        original = bytearray(path.read_bytes())
        original[len(original)//2] ^= 1
        path.write_bytes(original)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # mtime-only caches are unsafe.
    elif change == "inputs":
        monkeypatch.setattr(checkpoints, "input_fingerprint", lambda: "changed")
    elif change == "engine":
        monkeypatch.setattr(checkpoints, "engine_fingerprint", lambda: "changed")
    else:
        monkeypatch.setattr(router.ga_service.list_faculty[0], "eligible_subjects", set())
    status = verification.checkpoint_status(paused.run_id, router._templates())
    assert not status["resumable"] and status["code"].startswith("GA_CHECKPOINT_")


def test_restart_refresh_verified_resume_preserves_population_and_history(paused, monkeypatch):
    original = history.directory(paused.run_id) / "generation-000001.json"
    previous = original.read_bytes()
    with TestClient(app) as client:
        base = f"/api/ga/runs/{paused.run_id}"
        assert client.get(base + "/checkpoint-status").json()["resumable"]
        monkeypatch.setattr(router, "_run_registry", RunRegistry())
        with verification._lock:
            verification._answers.clear()  # New process has no cached verification.
        state = client.get(base).json()
        assert state["state"] == "PAUSED" and len(state["progress_history"]) == 2
        assert client.get(base + "/generations/1/schedule").status_code == 200
        assert client.get(base + "/checkpoint-status").json()["resumable"]
        assert client.post(base + "/resume").json()["accepted"]
        assert client.post(base + "/resume").status_code == 200
        final = wait_finished(client, paused.run_id, "COMPLETED")
        assert final["run_id"] == paused.run_id
        assert [row["generation"] for row in final["progress_history"]] == [0, 1, 2]
    assert original.read_bytes() == previous


def test_changed_lifecycle_cannot_reuse_paused_verification(paused):
    assert verification.checkpoint_status(paused.run_id, router._templates())["resumable"]
    paused.state = "STOPPING"
    checkpoints.write_marker(paused)
    with TestClient(app) as client:
        result = client.get(f"/api/ga/runs/{paused.run_id}/checkpoint-status").json()
    assert result["state"] == "STOPPING" and not result["resumable"]


def test_snapshot_schema_and_schedule_validation_errors_are_distinct(paused):
    path = history.directory(paused.run_id) / "generation-000001.json"
    data = history.read_document(path)
    data["generation_best"]["payload"]["schedule"].pop()
    # Integrity, IDs and scalar counters alone are insufficient to export.
    data["generation_best"]["chromosome_id"] = history.candidate_id(data["generation_best"]["payload"])
    index = history.manifest(paused.run_id)
    index["generations"][1]["generation_best_id"] = data["generation_best"]["chromosome_id"]
    history.write_document(path, data)
    history.write_document(history.directory(paused.run_id) / "index.json", index)
    with TestClient(app) as client:
        url = f"/api/ga/runs/{paused.run_id}/generations/1"
        result = client.get(url + "/export")
        assert result.status_code == 422
        assert result.json()["detail"]["code"] == "GA_HISTORY_VALIDATION_FAILED"
        result = client.get(url + "/schedule")
        assert result.status_code == 422
        assert result.json()["detail"]["code"] == "GA_HISTORY_VALIDATION_FAILED"
        del data["fitness_configuration"]
        history.write_document(path, data)
        result = client.get(url)
        assert result.status_code == 422
        assert result.json()["detail"]["code"] == "GA_HISTORY_CORRUPT"


def test_unavailable_storage_is_not_reported_as_corrupt_history():
    class Unavailable:
        def read_bytes(self):
            raise PermissionError("temporary file access failure")
    with pytest.raises(history.HistoryError) as failure:
        history.read_document(Unavailable())
    assert failure.value.code == "GA_HISTORY_UNAVAILABLE" and failure.value.status == 503
