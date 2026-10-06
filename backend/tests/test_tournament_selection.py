"""Targeted parent-selection checks without running the scheduling GA."""

import importlib
import random

import pytest


selection = importlib.import_module(
    "genetic_algorithm.operators.TournamentSelection"
)


@pytest.fixture(autouse=True)
def restore_random_state():
    state = random.getstate()
    random.seed(42)
    yield
    random.setstate(state)


@pytest.mark.parametrize("population_size,tournament_size", [(3, 3), (5, 3), (2, 3), (50, 7)])
@pytest.mark.parametrize("equal_fitness", [False, True])
def test_parents_are_distinct_population_objects(population_size, tournament_size, equal_fitness):
    # Equal chromosome contents must not be confused with object identity.
    population = [["same contents"] for _ in range(population_size)]
    fitness = [10] * population_size if equal_fitness else list(range(population_size))

    for _ in range(200):
        parent1, parent2 = selection.select_parent_pair(population, fitness, tournament_size)
        assert parent1 is not parent2
        assert any(parent1 is chromosome for chromosome in population)
        assert any(parent2 is chromosome for chromosome in population)


def test_full_population_tournament_returns_best_then_best_remaining():
    population = [object(), object(), object()]
    fitness = [30, 10, 20]

    for _ in range(100):
        parent1, parent2 = selection.select_parent_pair(population, fitness, 3)
        assert parent1 is population[1]
        assert parent2 is population[2]


def test_second_tournament_preserves_fitness_alignment(monkeypatch):
    population = [object() for _ in range(5)]
    fitness = [40, 10, 30, 20, 50]
    calls = []

    def sample(candidates, size):
        calls.append((len(candidates), size))
        return [0, 1, 2]

    monkeypatch.setattr(selection.random, "sample", sample)
    parent1, parent2 = selection.select_parent_pair(population, fitness, 3)

    assert parent1 is population[1]
    assert parent2 is population[3]
    assert calls == [(5, 3), (4, 3)]


def test_all_references_to_first_parent_are_excluded():
    best, next_best, worst = object(), object(), object()
    population = [best, best, next_best, worst]

    parent1, parent2 = selection.select_parent_pair(population, [0, 0, 10, 20], 4)

    assert parent1 is best
    assert parent2 is next_best


@pytest.mark.parametrize("alias_count", [1, 3])
def test_population_without_two_distinct_objects_is_rejected(alias_count):
    chromosome = object()
    with pytest.raises(ValueError, match="at least two distinct chromosome objects"):
        selection.select_parent_pair([chromosome] * alias_count, [10] * alias_count, 3)


def test_lower_fitness_retains_selection_advantage():
    population = [object() for _ in range(5)]
    fitness = [0, 10, 20, 30, 40]
    first_counts = [0] * 5
    second_counts = [0] * 5

    for _ in range(2000):
        parent1, parent2 = selection.select_parent_pair(population, fitness, 3)
        first_counts[next(i for i, chromosome in enumerate(population) if chromosome is parent1)] += 1
        second_counts[next(i for i, chromosome in enumerate(population) if chromosome is parent2)] += 1

    assert first_counts[0] > first_counts[1] > first_counts[2]
    assert first_counts[3:] == [0, 0]
    assert sum(second_counts[:2]) > sum(second_counts[2:])
    assert second_counts[4] == 0
