"""Small API orchestration checks using real scheduling models and operators."""

import copy
import importlib
import inspect
import json
import random
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from main import app
from genetic_algorithm.utils import Functions as scheduling
from genetic_algorithm.operators.CreatePopulation import (
    generate_population,
    sort_population_by_fitness,
)
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from genetic_algorithm.operators.TournamentSelection import select_parent_pair
from services import chromosome_service, ga_service


swap = importlib.import_module("genetic_algorithm.operators.Swap")
mutation = importlib.import_module("genetic_algorithm.operators.mutation")
ga_router = importlib.import_module("routers.genetic_algorithm")


def fitness(chromosome):
    return faculty_preference_fitness(chromosome, scheduling.df_faculty_pref)


def assert_hard_constraints(chromosome, expected):
    assert Counter((s.number, s.section.code) for s in chromosome) == expected
    assert scheduling.validate_faculty_subject_eligibility(chromosome, raise_error=False)
    assert scheduling.validate_preassigned_assignments(chromosome, raise_error=False)
    assert scheduling.validate_fixed_section_conflicts(chromosome, raise_error=False)
    assert not swap.chromosome_has_load_violation(chromosome)
    assert all(load <= 40 for load in swap.calculate_faculty_loads(chromosome).values())
    entries = []
    for subject in chromosome:
        assert subject.assigned_faculty is not None
        for component, hours in (("lecture", subject.lec_hours), ("laboratory", subject.lab_hours)):
            blocks = getattr(subject, component + "_time_blocks")
            intervals = sorted((day, scheduling.time_to_minutes(block.start_time),
                                scheduling.time_to_minutes(block.end_time))
                               for day, block in blocks)
            assert len(set(intervals)) == len(intervals)
            assert sum(end - start for _, start, end in intervals) == hours * 60
            if hours:
                room = getattr(subject, component + "_room")
                assert room is not None
                assert room.type == ("Lecture" if component == "lecture" else "Laboratory")
            if component == "laboratory" and hours:
                assert all(a[0] == b[0] and a[2] == b[1]
                           for a, b in zip(intervals, intervals[1:]))
            for _, block in blocks:
                assert block.faculty.code == subject.assigned_faculty.code
        entries.extend(scheduling.get_subject_schedule_entries(subject))
    for resource in ("faculty", "room", "section"):
        assert not scheduling.find_resource_conflicts(entries, resource)
    external = [s for s in chromosome if s.number == "ITE184"]
    assert {s.section.code for s in external} == {"4A", "4B"}
    for subject in external:
        assert subject.assigned_faculty.code == "external:eddie-bouy-palad"
        assert subject.assigned_faculty.name == "Atty. Eddie Bouy Palad"
        assert "".join(subject.lecture_room.name.split()) == "ICT3A"


@pytest.fixture(scope="module")
def small_population():
    # Five real offerings keep the API regression bounded while exercising
    # CSV eligibility, fixed section calendars, laboratories, and both locks.
    subjects = copy.deepcopy([
        s for s in scheduling.list_subjects
        if s.number in {"ITE184", "ITE185", "ITD104"}
        and s.section.code in {"4A", "4B"}
    ])
    faculty = copy.deepcopy([f for f in scheduling.list_faculty if f.code in {7, 10}])
    rooms = copy.deepcopy(
        [r for r in scheduling.lst_rooms if r.type == "Lecture"][:2]
        + [r for r in scheduling.lst_rooms if r.type == "Laboratory"][:2]
    )
    assert any("".join(r.name.split()) == "ICT3A" for r in rooms)
    state = random.getstate()
    random.seed(42)
    try:
        population = generate_population(3, faculty, subjects, rooms, max_restarts=20)
    finally:
        random.setstate(state)
    assert len(population) == 3
    expected = Counter((s.number, s.section.code) for s in subjects)
    assert len(subjects) == 5
    for chromosome in population:
        assert_hard_constraints(chromosome, expected)
    return population, subjects, faculty, rooms, expected


@pytest.mark.parametrize("baseline_mode", ["fresh", "saved", "uploaded"])
@pytest.mark.parametrize("endpoint", ["run", "stream"])
def test_api_generation_uses_distinct_tournament_parents(
    small_population, monkeypatch, tmp_path, baseline_mode, endpoint,
):
    population, subjects, faculty, rooms, expected = small_population
    monkeypatch.setattr(ga_service, "list_subjects", subjects)
    monkeypatch.setattr(ga_service, "list_faculty", faculty)
    monkeypatch.setattr(ga_service, "lst_rooms", rooms)
    monkeypatch.setattr(chromosome_service, "SAVED_CHROMOSOME_DIR", tmp_path)
    monkeypatch.setattr(chromosome_service, "BEST_CHROMOSOME_PATH", tmp_path / "best.json")
    monkeypatch.setattr(chromosome_service, "UPLOADED_CHROMOSOME_PATH", tmp_path / "uploaded.json")
    monkeypatch.setattr(ga_router, "LATEST_RESULT_FILE", tmp_path / "latest.json")

    baseline = max(population, key=fitness)
    payload = chromosome_service.chromosome_to_payload(baseline, fitness(baseline))
    if baseline_mode != "fresh":
        path = (chromosome_service.BEST_CHROMOSOME_PATH if baseline_mode == "saved"
                else chromosome_service.UPLOADED_CHROMOSOME_PATH)
        chromosome_service.write_payload(payload, path)

    generated_sizes, parent_pairs, children, ranked_populations, reconstructions = [], [], [], [], []

    def generate(population_size, *args, **kwargs):
        generated_sizes.append(population_size)
        return copy.deepcopy(population[:population_size])

    def select(**kwargs):
        candidates, scores = kwargs["population"], kwargs["fitness_scores"]
        assert len(candidates) == 3
        assert scores == [fitness(c) for c in candidates]
        parent1, parent2 = select_parent_pair(**kwargs)
        assert parent1 is not parent2
        assert all(any(p is c for c in candidates) for p in (parent1, parent2))
        assert [fitness(parent1), fitness(parent2)] == sorted(scores)[:2]
        parent_pairs.append((parent1, parent2))
        return parent1, parent2

    def crossover(**kwargs):
        # Bind the genuine interface so the obsolete population keyword fails.
        inspect.signature(swap.create_child_by_faculty_swap).bind(**kwargs)
        assert kwargs["parent1"] is parent_pairs[-1][0]
        assert kwargs["parent2"] is parent_pairs[-1][1]
        # Bound operator retries only in this test; production limits are unchanged.
        kwargs["max_attempts"] = 1
        child = swap.create_child_by_faculty_swap(**kwargs)
        if child is not None:
            assert_hard_constraints(child, expected)
            assert fitness(child) < min(fitness(kwargs["parent1"]), fitness(kwargs["parent2"]))
            children.append(child)
        return child

    def mutate(**kwargs):
        kwargs.update(max_attempts=1, verbose=False)
        child = mutation.mutate_by_swapping_faculty_subjects(**kwargs)
        if child is not None:
            assert_hard_constraints(child, expected)
        return child

    def rank(candidates, preferences):
        ranked = sort_population_by_fitness(candidates, preferences)
        assert [fitness(c) for c in ranked] == sorted(fitness(c) for c in candidates)
        ranked_populations.append(ranked)
        return ranked

    def reconstruct(*args):
        chromosome = chromosome_service.payload_to_chromosome(*args)
        assert_hard_constraints(chromosome, expected)
        reconstructions.append(chromosome)
        return chromosome

    monkeypatch.setattr(ga_service, "generate_population", generate)
    monkeypatch.setattr(ga_service, "select_parent_pair", select)
    monkeypatch.setattr(ga_service, "create_child_by_faculty_swap", crossover)
    monkeypatch.setattr(ga_service, "mutate_by_swapping_faculty_subjects", mutate)
    monkeypatch.setattr(ga_service, "sort_population_by_fitness", rank)
    monkeypatch.setattr(ga_service, "payload_to_chromosome", reconstruct)

    state = random.getstate()
    random.seed(42)
    try:
        with TestClient(app) as client:
            response = client.post("/api/ga/" + endpoint, params={
                "population_size": 3, "generations": 1,
                "fresh_chromosomes": 1, "baseline_mode": baseline_mode,
            })
    finally:
        random.setstate(state)
    assert response.status_code == 200
    if endpoint == "stream":
        events = [json.loads(line[6:]) for line in response.text.splitlines()
                  if line.startswith("data: ")]
        assert not any(event["type"] == "error" for event in events)
        assert events[-1]["type"] == "done"
        result = next(event["data"] for event in events if event["type"] == "result")
    else:
        assert response.json()["status"] == "success"
        result = response.json()["data"]

    assert parent_pairs  # Both HTTP paths reached real tournament + crossover.
    assert generated_sizes == ([3, 1] if baseline_mode == "fresh" else [2, 1])
    assert len(reconstructions) == (0 if baseline_mode == "fresh" else 1)
    survivors = ranked_populations[-1][:3]
    assert len(survivors) == result["population_size"] == 3
    for chromosome in survivors:
        assert_hard_constraints(chromosome, expected)
    assert result["generations_completed"] == 1
    assert result["baseline_source"] == baseline_mode
    assert result["starting_baseline_fitness"] == (None if baseline_mode == "fresh" else fitness(baseline))
    assert result["best_fitness"] == min(fitness(c) for c in ranked_populations[-1])
    assert result["history"][-1]["best_ever_fitness"] <= result["history"][0]["best_fitness"]
    assert sum(result["fitness_breakdown"].values()) == result["best_fitness"]
    assert ga_router._read_latest_result() == result
    assert chromosome_service.load_saved_best_payload()["best_fitness"] == result["best_fitness"]
    best = chromosome_service.payload_to_chromosome(result, subjects, faculty, rooms)
    assert_hard_constraints(best, expected)
