"""Actual V1 operators, JSON checkpoint writes/loads and deterministic continuation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
from contextlib import redirect_stdout

import pytest

from services import ga_service as engine, ga_checkpoint_service as checkpoints, chromosome_service
from services.ga_control_service import RunControl
from genetic_algorithm.utils import Functions
from genetic_algorithm.utils.FrozenInputs import scoring_inputs
from tests.d10.support import templates, preferences


@pytest.fixture
def baseline(monkeypatch, tmp_path):
    inputs = templates(compact=True)
    for name, value in zip(("list_subjects", "list_faculty", "lst_rooms"), inputs):
        monkeypatch.setattr(engine, name, value)
    # Freeze the fictional faculty universe without replacing any GA function.
    monkeypatch.setattr(Functions, "list_faculty", inputs[1])
    monkeypatch.setattr(engine, "df_faculty_pref", preferences())
    monkeypatch.setattr(chromosome_service, "BEST_CHROMOSOME_PATH", tmp_path / "best.json")
    with open(os.devnull, "w", encoding="utf-8") as sink, redirect_stdout(sink):
        yield inputs


@pytest.mark.parametrize("pause_generation", [0, 1, 2])
def test_real_current_v1_creation_restore_and_continuation(baseline, pause_generation):
    parameters = dict(population_size=2, generations=2, fresh_chromosomes=0,
                      mutation_attempts=1, max_restarts=5)
    original_rng = random.getstate()
    initial = copy.deepcopy(baseline)
    fingerprint = checkpoints.engine_fingerprint()
    inputs_fingerprint = checkpoints.input_fingerprint()
    try:
        random.seed(710)
        uninterrupted = engine.run_genetic_algorithm(**parameters)
        expected_rng = random.getstate()
        # Real scheduling resets mutable templates on every initial construction.
        for name, value in zip(("list_subjects", "list_faculty", "lst_rooms"), copy.deepcopy(initial)):
            setattr(engine, name, value)
        Functions.list_faculty = engine.list_faculty
        control = RunControl(); control.start()
        def progress(kind, data):
            control.capture_progress(kind, data)
            if data["generation"] == pause_generation:
                control.request_pause()
        random.seed(710)
        paused = engine.run_genetic_algorithm(**parameters, run_control=control, progress_callback=progress)
        assert isinstance(paused, checkpoints.PausedRun)
        artifact = checkpoints.run_directory(control.run_id) / control.checkpoint
        before = artifact.read_bytes()
        state = checkpoints.load_checkpoint(control.run_id, initial)
        assert len(state["population"]) == 2 and state["generation_completed"] == pause_generation
        assert scoring_inputs.get() is None
        control.execution_active = False; control.begin_resume()
        random.seed(999)
        resumed = engine.run_genetic_algorithm(**parameters, resume_state=state, run_control=control)
        assert random.getstate() == expected_rng
        for field in ("schedule", "history", "best_fitness", "fitness_breakdown", "faculty_analysis"):
            assert resumed[field] == uninterrupted[field]
        assert artifact.read_bytes() == before
        assert checkpoints.engine_fingerprint() == fingerprint
        assert checkpoints.input_fingerprint() == inputs_fingerprint
        if os.environ.get("D10_V1_BASELINE_RECORD"):
            path = Path(os.environ["D10_V1_BASELINE_RECORD"]) / f"fixture-{pause_generation}.json"
            record = {"fixture": "fictional-v1.1", "seed": 710, "parameters": parameters,
                "pause_generation": pause_generation, "engine_version": checkpoints.ENGINE_VERSION,
                "engine_fingerprint": fingerprint, "input_fingerprint": inputs_fingerprint,
                "fictional_templates_sha256": hashlib.sha256(checkpoints.canonical(checkpoints.encode_graph(initial))).hexdigest(),
                "checkpoint_sha256": hashlib.sha256(before).hexdigest(), "checkpoint_bytes_archived": False,
                "real_checkpoint_write_load_resume": True, "original_operators_used": True,
                "RNG_and_schedule_equivalent": True}
            path.write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    finally:
        random.setstate(original_rng)


def test_current_loader_keeps_strict_input_and_engine_checks():
    import inspect
    source = inspect.getsource(checkpoints.load_checkpoint)
    assert 'payload["input_fingerprint"] != input_fingerprint()' in source
    assert 'payload["engine_fingerprint"] != evaluation_fingerprint' in source
    assert 'GA_CHECKPOINT_INPUT_CHANGED' in source
