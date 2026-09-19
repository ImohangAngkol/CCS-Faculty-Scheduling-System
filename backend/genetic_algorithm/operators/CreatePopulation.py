import random
import copy
from genetic_algorithm.utils.Functions import   df_faculty_pref, get_subject_schedule_entries,find_resource_conflicts
from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)

from genetic_algorithm.operators.ElitisimSelection import (
    elitism_selection,
)
from genetic_algorithm.utils.Functions import  (
    list_faculty,
    list_subjects,
    lst_rooms,
    create_schedule_with_minimum_load,
    check_all_schedule_conflicts
)


def sort_population_by_fitness(
    population,
    df_faculty_pref
):
    """
    Sort population from LOWEST to HIGHEST fitness score.

    Lower fitness = better chromosome.
    """

    sorted_population = sorted(
        population,
        key=lambda chromosome: faculty_preference_fitness(
            chromosome,
            df_faculty_pref
        )
    )

    return sorted_population
def generate_population(
    population_size,
    list_faculty,
    list_subjects,
    lst_rooms,
    max_restarts=300
):
    """
    Generate a population of conflict-free chromosomes.

    Each chromosome is a deepcopy of list_subjects
    after a valid schedule has been generated.
    """

    chromosomes = []

    for chromosome_number in range(population_size):

        print(
            f"\nGenerating chromosome "
            f"{chromosome_number + 1}/{population_size}"
        )

        try:

            # -----------------------------------------------
            # Generate a new conflict-free schedule
            # -----------------------------------------------

            create_schedule_with_minimum_load(
                list_faculty=list_faculty,
                list_subjects=list_subjects,
                room_list=lst_rooms,
                max_restarts=max_restarts
            )

            # -----------------------------------------------
            # Validate schedule
            # -----------------------------------------------

            valid = check_all_schedule_conflicts(
                list_subjects
            )

            if valid:

                # Deepcopy because list_subjects will
                # be modified during the next iteration
                chromosome = copy.deepcopy(
                    list_subjects
                )

                chromosomes.append(
                    chromosome
                )

                print(
                    f"Chromosome "
                    f"{chromosome_number + 1} saved."
                )

            else:

                print(
                    "Schedule has conflicts. "
                    "Chromosome rejected."
                )

        except RuntimeError as error:

            print(
                f"Failed to generate chromosome: "
                f"{error}"
            )

    # -------------------------------------------------------
    # Summary
    # -------------------------------------------------------

    print("\n" + "=" * 60)

    print(
        f"Total chromosomes generated: "
        f"{len(chromosomes)}"
    )

    print("=" * 60)

    return chromosomes

def create_new_population(
    new__population,
    top_50_non_elites,
    df_faculty_pref,
    population_size
):
    """
    Combine new__population and top_50_non_elites,
    calculate fitness, sort from lowest to highest fitness,
    and return the best chromosomes.

    LOWER FITNESS = BETTER.
    """

    # Combine populations
    combined_population = (
        new__population + top_50_non_elites
    )

    # Calculate fitness
    population_with_fitness = [
        (
            chromosome,
            faculty_preference_fitness(
                chromosome,
                df_faculty_pref
            )
        )
        for chromosome in combined_population
    ]

    # Sort LOWEST fitness -> HIGHEST fitness
    population_with_fitness.sort(
        key=lambda x: x[1]
    )

    # Keep only the best 180
    top_population = population_with_fitness[
        :100000
    ]

    # Extract chromosomes
    new_population = [
        chromosome
        for chromosome, fitness in top_population
    ]
 
    return new_population


def get_top_population(
    new_population,
    df_faculty_pref,
    top_n=45
):
    """
    Sort new_population from lowest to highest fitness
    and return the top N chromosomes.

    LOWER FITNESS = BETTER.
    """

    # Calculate fitness for every chromosome
    population_with_fitness = [
        (
            chromosome,
            faculty_preference_fitness(
                chromosome,
                df_faculty_pref
            )
        )
        for chromosome in new_population
    ]

    # Sort lowest -> highest fitness
    population_with_fitness.sort(
        key=lambda x: x[1]
    )

    # Get top 45
    top_population = population_with_fitness[:top_n]

    # Return chromosomes only
    return [
        chromosome
        for chromosome, fitness in top_population
    ]