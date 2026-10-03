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
    Select two parents independently using tournament selection.

    The function attempts to return two different chromosome
    objects when the population contains more than one chromosome.
    """

    parent1 = tournament_selection(
        population=population,
        fitness_scores=fitness_scores,
        tournament_size=tournament_size,
    )

    parent2 = tournament_selection(
        population=population,
        fitness_scores=fitness_scores,
        tournament_size=tournament_size,
    )

    # Try to avoid selecting the exact same chromosome object twice.
    if len(population) > 1:
        attempts = 0

        while parent2 is parent1 and attempts < 20:
            parent2 = tournament_selection(
                population=population,
                fitness_scores=fitness_scores,
                tournament_size=tournament_size,
            )

            attempts += 1

    return parent1, parent2