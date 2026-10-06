import random


def tournament_selection(
    population,
    fitness_scores,
    tournament_size=3,
):
    """
    Select one chromosome using tournament selection.

    LOWER fitness/penalty = BETTER.

    Parameters
    ----------
    population : list
        Current GA population.

    fitness_scores : list
        Fitness/penalty corresponding to each chromosome.

    tournament_size : int
        Number of chromosomes randomly selected to compete.

    Returns
    -------
    chromosome
        The winning chromosome with the lowest fitness/penalty
        among the randomly selected candidates.
    """

    if not population:
        raise ValueError(
            "Tournament selection requires a non-empty population."
        )

    if len(population) != len(fitness_scores):
        raise ValueError(
            "Population and fitness_scores must have the same length."
        )

    if tournament_size < 2:
        raise ValueError(
            "tournament_size must be at least 2."
        )

    # Do not request more competitors than currently exist.
    actual_tournament_size = min(
        tournament_size,
        len(population),
    )

    candidate_indices = random.sample(
        range(len(population)),
        actual_tournament_size,
    )

    # LOWER fitness is better in this scheduling GA.
    winner_index = min(
        candidate_indices,
        key=lambda index: fitness_scores[index],
    )

    return population[winner_index]


def select_parent_pair(
    population,
    fitness_scores,
    tournament_size=3,
):
    """
    Select two distinct parent objects using tournament selection.

    The second tournament excludes all references to the first parent,
    while retaining the fitness scores of the remaining chromosomes.
    At least two distinct chromosome objects are required.
    """

    parent1 = tournament_selection(
        population=population,
        fitness_scores=fitness_scores,
        tournament_size=tournament_size,
    )

    remaining_population = []
    remaining_fitness_scores = []

    for chromosome, fitness in zip(population, fitness_scores):
        if chromosome is not parent1:
            remaining_population.append(chromosome)
            remaining_fitness_scores.append(fitness)

    if not remaining_population:
        raise ValueError(
            "Parent selection requires at least two distinct chromosome objects."
        )

    parent2 = tournament_selection(
        population=remaining_population,
        fitness_scores=remaining_fitness_scores,
        tournament_size=tournament_size,
    )

    return parent1, parent2
