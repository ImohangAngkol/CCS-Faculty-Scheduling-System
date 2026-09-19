import math
import copy



def elitism_selection(
    population,
    fitness_scores,
    elite_percentage=0.10
):
    """
    Divide population into:
        1. Elites     -> best 10%
        2. Non-elites -> remaining 90%

    LOWER FITNESS = BETTER
    """

    # ---------------------------------------
    # 1. Combine chromosome and fitness
    # ---------------------------------------
    ranked_population = list(
        zip(population, fitness_scores)
    )

    # ---------------------------------------
    # 2. Sort BEST to WORST
    #    Lower fitness = better
    # ---------------------------------------
    ranked_population.sort(
        key=lambda x: x[1]
    )

    # ---------------------------------------
    # 3. Number of elites
    # ---------------------------------------
    number_of_elites = max(
        1,
        math.ceil(
            len(population) * elite_percentage
        )
    )

    # ---------------------------------------
    # 4. Split population
    # ---------------------------------------
    elite_group = ranked_population[
        :number_of_elites
    ]

    non_elite_group = ranked_population[
        number_of_elites:
    ]

    # ---------------------------------------
    # 5. Separate chromosomes and fitness
    # ---------------------------------------
    elites = [
        copy.deepcopy(chromosome)
        for chromosome, fitness in elite_group
    ]

    elite_fitness = [
        fitness
        for chromosome, fitness in elite_group
    ]

    non_elites = [
        copy.deepcopy(chromosome)
        for chromosome, fitness in non_elite_group
    ]

    non_elite_fitness = [
        fitness
        for chromosome, fitness in non_elite_group
    ]

    return (
        elites,
        elite_fitness,
        non_elites,
        non_elite_fitness
    )