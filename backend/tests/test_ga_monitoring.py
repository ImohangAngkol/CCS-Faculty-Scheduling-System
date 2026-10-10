"""Bounded Phase 3B checks; all persistence is isolated in temporary storage."""
import copy
import importlib
import json
import pickle
import random
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from main import app
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from genetic_algorithm.utils.FitnessObservation import observed_scores
from genetic_algorithm.utils import Functions as scheduling
from services import ga_service, chromosome_service, ga_progress_service
from services.ga_publication_service import validate_publication
from tests.test_ga_api_crossover import small_population

router = importlib.import_module("routers.genetic_algorithm")


@pytest.fixture
def bounded_run(small_population, monkeypatch, tmp_path):
    population, subjects, faculty, rooms, _ = small_population
    monkeypatch.setattr(ga_service, "list_subjects", subjects)
    monkeypatch.setattr(ga_service, "list_faculty", faculty)
    monkeypatch.setattr(ga_service, "lst_rooms", rooms)
    monkeypatch.setattr(chromosome_service, "BEST_CHROMOSOME_PATH", tmp_path / "best.json")
    monkeypatch.setattr(router, "LATEST_RESULT_FILE", tmp_path / "latest.json")
    monkeypatch.setattr(ga_service, "generate_population", lambda population_size, *a, **k: copy.deepcopy(population[:population_size]))
    # Controlled valid returns exercise counting independently of operator retries.
    def crossover(**kwargs):
        return copy.deepcopy(random.choice([kwargs["parent1"], kwargs["parent2"]]))
    monkeypatch.setattr(ga_service, "create_child_by_faculty_swap", crossover)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", lambda **k: copy.deepcopy(random.choice(k["population"])))
    return population, subjects, faculty, rooms


def test_observation_equivalence_metrics_and_rng(bounded_run, monkeypatch):
    population, _, _, _ = bounded_run
    expected = [faculty_preference_fitness(candidate, scheduling.df_faculty_pref) for candidate in population]
    counts = []
    scoring_calls = []
    population_module = importlib.import_module("genetic_algorithm.operators.CreatePopulation")
    def counted_fitness(*args, **kwargs):
        scoring_calls.append(1)
        return faculty_preference_fitness(*args, **kwargs)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", counted_fitness)
    monkeypatch.setattr(population_module, "faculty_preference_fitness", counted_fitness)
    original_sort = ga_service.sort_population_by_fitness
    def sort(*args):
        counts.append(len(args[0]))
        return original_sort(*args)
    monkeypatch.setattr(ga_service, "sort_population_by_fitness", sort)
    state = random.getstate()
    try:
        random.seed(57)
        plain = ga_service.run_genetic_algorithm(3, 2, 1)
        plain_rng, plain_counts = random.getstate(), counts[:]
        plain_scoring_calls = len(scoring_calls)
        scoring_calls.clear()
        counts.clear()
        events = []
        random.seed(57)
        observed = ga_service.run_genetic_algorithm(3, 2, 1, progress_callback=lambda kind, data: events.append((kind, data)))
        assert random.getstate() == plain_rng
    finally:
        random.setstate(state)
    for key in ("best_fitness", "schedule", "history", "fitness_breakdown", "faculty_analysis"):
        assert observed[key] == plain[key]
    assert counts == plain_counts
    assert len(scoring_calls) == plain_scoring_calls  # Monitoring adds no fitness calls.
    assert observed_scores.get() is None
    assert [kind for kind, _ in events] == ["initial_population_ready", "generation_completed", "generation_completed"]
    initial = events[0][1]
    assert initial["generation"] == 0
    assert initial["average_fitness"] == pytest.approx(sum(expected) / 3)
    assert initial["worst_fitness"] == max(expected)
    assert [data["accepted_new_chromosomes_total"] for _, data in events] == [3, 7, 11]
    previous = initial["best_ever_fitness"]
    for _, data in events:
        assert data["population_actual"] == data["population_requested"] == 3
        assert data["generation_limit"] == 2
        assert data["best_ever_fitness"] <= data["generation_best_fitness"] <= data["average_fitness"] <= data["worst_fitness"]
        assert data["best_ever_fitness"] <= previous
        previous = data["best_ever_fitness"]
        assert data["fitness_evaluations_total"] is None
        assert data["validation_status"] == "passed" and data["metrics_comparable"]
        assert len(data["input_fingerprint"]) == len(data["configuration_fingerprint"]) == 64
        assert data["elapsed_ms"] >= data["generation_elapsed_ms"] >= 0


def test_stream_contract_order_persistence_and_actual_survivors(bounded_run, monkeypatch):
    population, _, _, _ = bounded_run
    monkeypatch.setattr(ga_service, "generate_population", lambda *a, **k: copy.deepcopy(population[:2]))
    with TestClient(app) as client:
        response = client.post("/api/ga/stream", params={"population_size": 3, "generations": 2, "fresh_chromosomes": 0})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert not any(event["type"] == "error" for event in events)
    assert events[0]["type"] == "run_created" and events[1]["type"] == "run_started"
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert len({event["run_id"] for event in events}) == 1
    assert all(event["schema_version"] == 1 and event["timestamp"].endswith("+00:00") for event in events)
    progress = [event for event in events if event["type"] in {"initial_population_ready", "generation_completed"}]
    assert [event["data"]["generation"] for event in progress] == [0, 1, 2]
    assert progress[0]["data"]["population_actual"] == 2
    assert progress[0]["data"]["population_requested"] == 3
    assert events.index(progress[-1]) < next(i for i, event in enumerate(events) if event["type"] == "result")
    result = next(event["data"] for event in events if event["type"] == "result")
    assert router._read_latest_result() == result
    assert chromosome_service.load_saved_best_payload()["best_fitness"] == result["best_fitness"]
    assert events[-1]["type"] == "done" and events[-1]["data"]["status"] == "COMPLETED"


def test_none_results_baseline_seeds_and_retention_are_not_new(bounded_run, monkeypatch):
    population, _, _, _ = bounded_run
    monkeypatch.setattr(ga_service, "create_child_by_faculty_swap", lambda **k: None)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", lambda **k: None)
    monkeypatch.setattr(ga_service, "load_saved_best_payload", lambda: chromosome_service.chromosome_to_payload(population[0], 0))
    events = []
    ga_service.run_genetic_algorithm(3, 1, 0, "saved", progress_callback=lambda kind, data: events.append(data))
    assert [data["accepted_new_chromosomes_total"] for data in events] == [2, 2]
    assert all(data["baseline_chromosomes"] == 1 for data in events)
    assert events[-1]["generations_without_improvement"] == 1
    assert events[-1]["best_ever_improvement"] == 0


def test_valid_underload_and_locks_are_non_mutating(small_population):
    population, subjects, faculty, rooms, _ = small_population
    candidate = copy.deepcopy(population[0])
    before, rng = pickle.dumps(candidate), random.getstate()
    validate_publication(candidate, subjects, faculty, rooms)
    assert pickle.dumps(candidate) == before and random.getstate() == rng
    normal = [s.assigned_faculty for s in candidate if not getattr(s.assigned_faculty, "is_external", False)]
    assert any(f.current_teaching_load < f.required_teaching_load for f in normal)
    assert {s.section.code for s in candidate if s.number == "ITE184"} == {"4A", "4B"}
    for subject in candidate:
        if subject.number == "ITE184":
            assert subject.assigned_faculty.name == "Atty. Eddie Bouy Palad"
            assert subject.preassigned_assignment.room_name == "ICT3A"


@pytest.mark.parametrize("case", ["missing", "duplicate", "hours", "lab_gap", "room", "instructor", "fixed", "eligibility", "overload"])
def test_publication_rejects_invalid_candidates(small_population, case):
    population, subjects, faculty, rooms, _ = small_population
    candidate = copy.deepcopy(population[0])
    normal = next(s for s in candidate if s.number == "ITD104")
    external = next(s for s in candidate if s.number == "ITE184")
    if case == "missing": candidate.pop()
    elif case == "duplicate": candidate.append(copy.deepcopy(candidate[0]))
    elif case == "hours": normal.laboratory_time_blocks.pop()
    elif case == "lab_gap":
        day, block = normal.laboratory_time_blocks[-1]
        normal.laboratory_time_blocks[-1] = ("S" if day != "S" else "M", block)
    elif case == "room": external.lecture_room = next(room for room in rooms if room.name != external.lecture_room.name and room.type == "Lecture")
    elif case == "instructor": external.assigned_faculty = normal.assigned_faculty
    elif case == "fixed":
        block = next(block for blocks in normal.section.get_day_map().values() for block in blocks if block.fixed_schedule)
        block.fixed_course = "TAMPERED"
    elif case == "eligibility":
        # A known faculty outside the two-faculty fixture is not eligible for ITD104.
        normal.assigned_faculty = next(f for f in scheduling.list_faculty if not scheduling.faculty_is_explicitly_eligible_for_subject(f, normal))
        for _, block in normal.lecture_time_blocks + normal.laboratory_time_blocks: block.faculty = normal.assigned_faculty
        faculty = scheduling.list_faculty
    elif case == "overload":
        # Authoritative units, not serialized/cached loads, determine the ceiling.
        subjects = copy.deepcopy(subjects)
        for s in subjects:
            if s.number == "ITD104": s.credit_units = 41
        normal.credit_units = 41
    with pytest.raises((ValueError, RuntimeError), match="Publication rejected"):
        validate_publication(candidate, subjects, faculty, rooms)


def test_invalid_generation_fails_before_result_or_persistence(bounded_run, monkeypatch):
    population, _, _, _ = bounded_run
    invalid = copy.deepcopy(population[0]); invalid.pop()
    monkeypatch.setattr(ga_service, "generate_population", lambda *a, **k: [invalid])
    with TestClient(app) as client:
        response = client.post("/api/ga/stream", params={"population_size": 3, "generations": 1})
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert not any(event["type"] in {"result", "initial_population_ready"} for event in events)
    assert any("Publication rejected" in event.get("message", "") for event in events)
    assert events[-1]["data"]["status"] == "FAILED"
    assert not router.LATEST_RESULT_FILE.exists() and not chromosome_service.BEST_CHROMOSOME_PATH.exists()


def test_input_change_and_observer_failure_do_not_publish(bounded_run, monkeypatch):
    version = ["initial"]
    monkeypatch.setattr(ga_progress_service, "input_fingerprint", lambda: version[0])
    def observer(kind, data): version[0] = "changed"
    with pytest.raises(ValueError, match="no longer comparable"):
        ga_service.run_genetic_algorithm(3, 1, 0, progress_callback=observer)
    assert not chromosome_service.BEST_CHROMOSOME_PATH.exists()
    version[0] = "initial"
    def failed_observer(*args): raise RuntimeError("transport failed")
    with pytest.raises(RuntimeError, match="transport failed"):
        ga_service.run_genetic_algorithm(3, 1, 0, progress_callback=failed_observer)
    assert observed_scores.get() is None and not chromosome_service.BEST_CHROMOSOME_PATH.exists()


def test_latest_and_existing_download_validate_stored_schedules(bounded_run):
    population, _, _, _ = bounded_run
    payload = chromosome_service.chromosome_to_payload(population[0], 0)
    chromosome_service.write_payload(payload, chromosome_service.BEST_CHROMOSOME_PATH)
    result = {"best_fitness": 0, "schedule": payload["schedule"], "history": [],
              "generations_completed": 0, "population_size": 3, "fitness_breakdown": {}}
    router._save_latest_result(result)
    original_bytes = chromosome_service.BEST_CHROMOSOME_PATH.read_bytes()
    with TestClient(app) as client:
        assert client.get("/api/ga/latest").json()["data"] == result
        response = client.get("/api/chromosomes/best/download")
        assert response.status_code == 200 and response.content == original_bytes
        assert "best_chromosome.json" in response.headers["content-disposition"]
        payload["schedule"].pop()  # Missing required component time.
        chromosome_service.write_payload(payload, chromosome_service.BEST_CHROMOSOME_PATH)
        result["schedule"] = payload["schedule"]
        router._save_latest_result(result)
        assert client.get("/api/ga/latest").status_code == 422
        assert client.get("/api/chromosomes/best/download").status_code == 422


@pytest.mark.parametrize("active", ["generate", "run", "stream"])
def test_shared_admission_rejects_overlaps_and_releases(monkeypatch, tmp_path, active):
    entered, release = threading.Event(), threading.Event()
    def blocked(**kwargs):
        entered.set()
        assert release.wait(10)
        return {"best_fitness": 0, "schedule": []}
    monkeypatch.setattr(router, "generate_schedule", blocked)
    monkeypatch.setattr(router, "run_genetic_algorithm", blocked)
    monkeypatch.setattr(router, "LATEST_RESULT_FILE", tmp_path / "latest.json")
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as executor:
        pending = executor.submit(client.post, "/api/ga/" + active)
        try:
            assert entered.wait(10)
            assert client.get("/api/health").status_code == 200
            for endpoint in ("generate", "run", "stream"):
                response = client.post("/api/ga/" + endpoint)
                assert response.status_code == 409
        finally:
            release.set()
        assert pending.result(timeout=10).status_code == 200
        assert not router._ga_execution_lock.locked()
