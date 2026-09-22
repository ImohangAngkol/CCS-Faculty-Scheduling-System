from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)

from genetic_algorithm.utils.Functions import (
    list_faculty,
    list_subjects,
    lst_rooms,
    df_faculty_pref,
    get_subject_schedule_entries,
)

from services.chromosome_service import (
    payload_to_chromosome,
)

from services.faculty_analysis_service import (
    build_faculty_analysis,
)


def analyze_chromosome_payload(
    payload,
    source="uploaded",
):
    """
    Load and analyze an existing chromosome WITHOUT
    running the Genetic Algorithm.

    No:
        - generations
        - crossover
        - mutation
        - population generation

    The chromosome is reconstructed, validated,
    evaluated, and converted to the same result shape
    used by the frontend.
    """

    # ========================================================
    # RECONSTRUCT REAL PYTHON CHROMOSOME
    # ========================================================

    chromosome = payload_to_chromosome(
        payload,
        list_subjects,
        list_faculty,
        lst_rooms,
    )


    # ========================================================
    # FITNESS
    # ========================================================

    (
        fitness,
        fitness_breakdown,
    ) = faculty_preference_fitness(
        chromosome,
        df_faculty_pref,
        return_breakdown=True,
    )


    # ========================================================
    # PROFESSOR-STYLE FACULTY ANALYSIS
    # ========================================================

    faculty_analysis = build_faculty_analysis(
        chromosome,
        df_faculty_pref,
    )


    # ========================================================
    # SERIALIZE SCHEDULE
    # ========================================================

    schedule = []


    for subject in chromosome:

        entries = get_subject_schedule_entries(
            subject
        )

        schedule.extend(
            entries
        )


    # ========================================================
    # RESULT
    # ========================================================

    return {
        "best_fitness":
            fitness,

        "fitness_breakdown":
            fitness_breakdown,

        # No GA was executed.
        "generations_completed":
            0,

        "population_size":
            0,

        "history":
            [],

        "schedule":
            schedule,

        "faculty_analysis":
            faculty_analysis,

        # Important for frontend
        "result_source":
            "loaded_chromosome",

        "loaded_chromosome_source":
            source,

        "optimization_performed":
            False,

        "baseline_source":
            None,

        "starting_baseline_fitness":
            None,

        "saved_best_updated":
            False,

        "saved_best_fitness":
            None,
    }