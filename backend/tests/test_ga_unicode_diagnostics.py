"""Windows encoding regressions; no institutional data or GA state is written."""
import io
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from genetic_algorithm.utils import Functions as scheduling
from services import chromosome_service, ga_log_service as logs
from services.ga_control_service import RunRegistry
from tests.test_ga_api_crossover import small_population


@pytest.mark.parametrize("encoding", ["cp1252", "cp437", "ascii", "utf-8"])
def test_run_capture_preserves_unicode_and_order_with_legacy_console(monkeypatch, encoding):
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding=encoding, errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    registry = RunRegistry()
    control = registry.register()
    events = []
    before = random.getstate()
    with logs.capture_run_logs(registry, control, events.append) as output:
        output("\u2713 NO CONFLICTS FOUND", flush=True)
        output("\u2717 Conflict detected")
        output("Faculty \u00f1 \U0001f600", end="")
    entries = logs.store_for(registry).buffer(control.run_id).read(0)["entries"]
    assert [entry["message"] for entry in entries] == [
        "\u2713 NO CONFLICTS FOUND", "\u2717 Conflict detected", "Faculty \u00f1 \U0001f600"]
    assert [entry["sequence"] for entry in entries] == [1, 2, 3]
    assert [entry["message"] for entry in events] == [entry["message"] for entry in entries]
    assert random.getstate() == before
    mirrored = raw.getvalue().decode(encoding)
    expected = "\\u2713 NO CONFLICTS FOUND" if encoding != "utf-8" else "\u2713 NO CONFLICTS FOUND"
    assert expected in mirrored
    assert sys.stdout is console  # No process-wide replacement/reconfiguration.
    assert console.encoding == encoding and console.errors == "strict"


def test_unicode_print_outside_capture_and_explicit_stderr_are_safe(monkeypatch):
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    stderr_raw = io.BytesIO()
    stderr = io.TextIOWrapper(stderr_raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    monkeypatch.setattr(sys, "stderr", stderr)
    formats = []
    class Once:
        def __str__(self):
            formats.append(1)
            return "\u2713"
    registry = RunRegistry()
    control = registry.register()
    logs.bind_diagnostics()
    scheduling.print(Once(), "validated", sep=" | ", end="!", flush=True)
    with logs.capture_run_logs(registry, control):
        scheduling.print("\u2717 stderr diagnostic", file=sys.stderr, flush=True)
        other_file = io.StringIO()
        scheduling.print("\u2713 UTF-8 compatible destination", file=other_file)
    assert formats == [1]
    assert raw.getvalue().decode("cp1252") == "\\u2713 | validated!"
    assert stderr_raw.getvalue().decode("cp1252").replace("\r\n", "\n") == "\\u2717 stderr diagnostic\n"
    assert other_file.getvalue() == "\u2713 UTF-8 compatible destination\n"
    assert not logs.store_for(registry).buffer(control.run_id).read(0)["entries"]


@pytest.mark.parametrize("declared_encoding", [None, "utf-8"])
def test_wrapper_with_missing_or_incorrect_encoding_uses_ascii_fallback(declared_encoding):
    class LegacyWrapper:
        encoding = declared_encoding
        def __init__(self):
            self.messages = []
        def write(self, text):
            text.encode("cp1252")
            self.messages.append(text)
    console = LegacyWrapper()
    logs.console_print("\u2713", file=console)
    assert console.messages == ["\\u2713\n"]


def test_real_io_and_validation_exceptions_are_not_suppressed(monkeypatch):
    class BrokenConsole:
        encoding = "utf-8"
        def write(self, text):
            raise OSError("console unavailable")
    with pytest.raises(OSError, match="console unavailable"):
        logs.console_print("\u2713", file=BrokenConsole())
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    registry = RunRegistry()
    control = registry.register()
    with pytest.raises(ValueError, match="eligibility validation failed"):
        with logs.capture_run_logs(registry, control) as output:
            output("\u2713 diagnostic")
            raise ValueError("eligibility validation failed")
    assert logs.store_for(registry).buffer(control.run_id).read(0)["entries"][0]["message"] == "\u2713 diagnostic"
    with pytest.raises(TypeError):
        logs.console_print("invalid print argument", sep=42)


def test_actual_conflict_validator_finishes_and_still_rejects_conflicts(monkeypatch, small_population):
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252", errors="strict"))
    logs.bind_diagnostics()
    population, _, _, _, _ = small_population
    assert scheduling.check_all_schedule_conflicts(population[0]) is True
    sys.stdout.flush()
    assert "\\u2713 SCHEDULE IS VALID." in raw.getvalue().decode("cp1252")
    # Keep the actual section/faculty/room checker and result semantics intact.
    entry = scheduling.get_subject_schedule_entries(population[0][0])[0]
    conflicting = {**entry, "subject": "ENCODING-CONFLICT-FIXTURE"}
    monkeypatch.setattr(scheduling, "get_subject_schedule_entries", lambda subject: [entry, conflicting])
    assert scheduling.check_all_schedule_conflicts([population[0][0]]) is False
    sys.stdout.flush()
    assert "\\u2717 SCHEDULE IS NOT VALID." in raw.getvalue().decode("cp1252")


def test_concurrent_cp1252_console_capture_keeps_runs_separate(monkeypatch):
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    registry = RunRegistry()
    controls = [registry.register(), registry.register()]
    start = threading.Barrier(2)
    def worker(control):
        with logs.capture_run_logs(registry, control) as output:
            start.wait(timeout=10)
            for number in range(20):
                output(f"{control.run_id} \u2713 {number}")
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(worker, controls))
    for control in controls:
        entries = logs.store_for(registry).buffer(control.run_id).read(0)["entries"]
        assert [entry["sequence"] for entry in entries] == list(range(1, 21))
        assert [entry["message"] for entry in entries] == [f"{control.run_id} \u2713 {number}" for number in range(20)]


def test_unicode_saved_schedule_path_cannot_fail_successful_save(monkeypatch, tmp_path, small_population):
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252", errors="strict"))
    target = tmp_path / "\u2713-best.json"
    monkeypatch.setattr(chromosome_service, "BEST_CHROMOSOME_PATH", target)
    registry = RunRegistry()
    control = registry.register()
    with logs.capture_run_logs(registry, control):
        saved, payload = chromosome_service.save_best_if_better(small_population[0][0], 0)
    assert saved and target.is_file()
    assert chromosome_service.load_saved_best_payload() == payload
    entries = logs.store_for(registry).buffer(control.run_id).read(0)["entries"]
    assert entries[-1]["message"] == f"File    : {target}"
    assert "\\u2713-best.json" in raw.getvalue().decode("cp1252")
