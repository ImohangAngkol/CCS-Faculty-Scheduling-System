from genetic_algorithm.utils.Functions import (
    list_faculty,
    list_subjects,
    lst_rooms,
    df_faculty_pref,
    check_all_schedule_conflicts,
)

from genetic_algorithm.operators.CreatePopulation import (
    generate_population,
    sort_population_by_fitness,
)

from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)

from genetic_algorithm.operators.ElitisimSelection import (
    elitism_selection,
)

from genetic_algorithm.operators.Swap import (
    create_child_by_faculty_swap,
)

from genetic_algorithm.operators.mutation import (
    mutate_by_swapping_faculty_subjects,
)


def test_generate_population_returns_valid_chromosomes():
    chromosomes = generate_population(
        population_size=3,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=300,
    )

    assert len(chromosomes) > 0

    for chromosome in chromosomes:
        assert len(chromosome) > 0
        assert check_all_schedule_conflicts(chromosome) is True


def test_fitness_is_non_negative():
    chromosomes = generate_population(
        population_size=2,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=300,
    )

    for chromosome in chromosomes:
        fitness = faculty_preference_fitness(
            chromosome,
            df_faculty_pref,
        )

        assert fitness >= 0


def test_fitness_breakdown_matches_total():
    chromosomes = generate_population(
        population_size=1,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=300,
    )

    chromosome = chromosomes[0]

    total, breakdown = faculty_preference_fitness(
        chromosome,
        df_faculty_pref,
        return_breakdown=True,
    )

    assert sum(breakdown.values()) == total


def test_sort_population_by_fitness():
    chromosomes = generate_population(
        population_size=4,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=300,
    )

    sorted_population = sort_population_by_fitness(
        chromosomes,
        df_faculty_pref,
    )

    fitness_scores = [
        faculty_preference_fitness(
            chromosome,
            df_faculty_pref,
        )
        for chromosome in sorted_population
    ]

    assert fitness_scores == sorted(fitness_scores)


def test_elitism_returns_best_chromosomes():
    chromosomes = generate_population(
        population_size=6,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=300,
    )

    fitness_scores = [
        faculty_preference_fitness(
            chromosome,
            df_faculty_pref,
        )
        for chromosome in chromosomes
    ]

    (
        elites,
        elite_fitness,
        non_elites,
        non_elite_fitness,
    ) = elitism_selection(
        population=chromosomes,
        fitness_scores=fitness_scores,
        elite_percentage=0.10,
    )

    assert len(elites) >= 1
    assert len(elites) + len(non_elites) == len(chromosomes)

    if non_elite_fitness:
        assert max(elite_fitness) <= min(non_elite_fitness)


def test_crossover_child_if_created_is_better():
    chromosomes = generate_population(
        population_size=6,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=300,
    )

    result = create_child_by_faculty_swap(
        population=chromosomes,
        df_faculty_pref=df_faculty_pref,
        max_attempts=50,
    )

    if result is not None and result != "None":
        child_fitness = faculty_preference_fitness(
            result,
            df_faculty_pref,
        )

        parent_fitnesses = [
            faculty_preference_fitness(
                chromosome,
                df_faculty_pref,
            )
            for chromosome in chromosomes
        ]

        assert child_fitness <= max(parent_fitnesses)


def test_mutation_if_created_is_valid():
    chromosomes = generate_population(
        population_size=5,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=300,
    )

    result = mutate_by_swapping_faculty_subjects(
        population=chromosomes,
        df_faculty_pref=df_faculty_pref,
        max_attempts=50,
        verbose=False,
    )

    if result is not None and result != "None":
        assert check_all_schedule_conflicts(result) is True

        fitness = faculty_preference_fitness(
            result,
            df_faculty_pref,
        )

        assert fitness >= 0