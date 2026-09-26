import copy

from services.faculty_analysis_service import (
    build_faculty_analysis,
)

from genetic_algorithm.utils.Functions import (
    list_faculty,
    list_subjects,
    lst_rooms,
    df_faculty_pref,
    get_subject_schedule_entries,
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
from genetic_algorithm.utils.Functions import (
    get_subject_schedule_entries,
    list_faculty,
    list_subjects,
    lst_rooms,
    df_faculty_pref,
)

from genetic_algorithm.operators.CreatePopulation import (
    generate_population,
    sort_population_by_fitness,
)

from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)

from genetic_algorithm.operators.BestChromosome import (
    best_chromosome_to_dataframe,
)

from services.chromosome_service import (
    load_saved_best_payload,
    load_uploaded_payload,
    payload_to_chromosome,
    save_best_if_better,
)
import json
from pathlib import Path

import pandas as pd

from genetic_algorithm.models.ga_setting import (
    GASetting
)


BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATA_DIR = (
    BACKEND_DIR
    / "data"
)

FACULTY_PREFERENCES_FILE = (
    DATA_DIR
    / "faculty_preferences.json"
)

GA_SETTINGS_FILE = (
    DATA_DIR
    / "ga_settings.json"
)


def load_dashboard_preferences():

    if not FACULTY_PREFERENCES_FILE.exists():

        return []

    try:

        with open(
            FACULTY_PREFERENCES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return []


def load_ga_settings():

    if not GA_SETTINGS_FILE.exists():

        return GASetting()

    try:

        with open(
            GA_SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return GASetting.from_dict(
            data
        )

    except Exception:

        return GASetting()


def get_dashboard_preferences_dataframe():

    preferences = (
        load_dashboard_preferences()
    )

    if not preferences:

        return pd.DataFrame()

    rows = []

    for preference in preferences:

        rows.append({

            "Faculty_Code":
                preference["faculty_code"],

            "Faculty_Prio":
                preference.get(
                    "faculty_priority",
                    1
                ),

            "Preferred Subjects":
                preference.get(
                    "preferred_subjects",
                    []
                ),

            "Preferred Day(s)":
                preference.get(
                    "preferred_days",
                    []
                ),

            "Preferred Start Time":
                preference.get(
                    "preferred_start_time"
                ),

            "Preferred End Time":
                preference.get(
                    "preferred_end_time"
                ),

            "Gap Preference":
                preference.get(
                    "gap_preference",
                    "No Preference"
                ),

            "Use Subject Preference":
                preference.get(
                    "use_subject_preference",
                    True
                ),

            "Use Day Preference":
                preference.get(
                    "use_day_preference",
                    True
                ),

            "Use Time Preference":
                preference.get(
                    "use_time_preference",
                    True
                ),

            "Use Gap Preference":
                preference.get(
                    "use_gap_preference",
                    False
                ),
        })

    return pd.DataFrame(
        rows
    )

def generate_schedule(
    population_size: int = 10,
    max_restarts: int = 2000,
):
    """
    Generate an initial GA population and return
    the best chromosome in JSON-friendly form.

    LOWER FITNESS = BETTER.
    """

    chromosomes = generate_population(
        population_size=population_size,
        list_faculty=list_faculty,
        list_subjects=list_subjects,
        lst_rooms=lst_rooms,
        max_restarts=max_restarts,
    )

    if not chromosomes:
        raise RuntimeError(
            "No valid chromosomes were generated."
        )

    chromosomes = sort_population_by_fitness(
        chromosomes,
        df_faculty_pref,
    )

    best_chromosome = chromosomes[0]

    best_fitness = faculty_preference_fitness(
        best_chromosome,
        df_faculty_pref,
    )

    # schedule_df = best_chromosome_to_dataframe(
    #     best_chromosome
    # )

    # schedule = schedule_df.to_dict(
    #     orient="records"
    # )
    schedule = []

    for subject in best_chromosome:
        schedule.extend(
        get_subject_schedule_entries(subject)
    )

    return {
        "fitness": best_fitness,
        "population_generated": len(chromosomes),
        "schedule": schedule,
    }

def run_genetic_algorithm(
    population_size=20,
    generations=5,
    fresh_chromosomes=5,
    baseline_mode="fresh",
    mutation_attempts=100,
    max_restarts=300,
):
    """
    Run the full Genetic Algorithm.

    LOWER FITNESS = BETTER.

    The best-ever chromosome is preserved across generations.
    A new chromosome only replaces the baseline when its
    fitness is lower than the previous best.
    """

    # =====================================================
    # 1. INITIAL POPULATION
    # =====================================================

    # population = generate_population(
    #     population_size=population_size,
    #     list_faculty=list_faculty,
    #     list_subjects=list_subjects,
    #     lst_rooms=lst_rooms,
    #     max_restarts=max_restarts,
    # )
        # ========================================================
    # OPTIONAL BASELINE CHROMOSOME
    # ========================================================

    baseline_mode = (
        str(
            baseline_mode
        )
        .strip()
        .lower()
    )


    if baseline_mode not in {
        "fresh",
        "saved",
        "uploaded",
    }:

        raise ValueError(
            "baseline_mode must be "
            "'fresh', 'saved', or 'uploaded'."
        )


    baseline_payload = None

    baseline_chromosome = None

    baseline_fitness = None

    baseline_source = "fresh"


    # --------------------------------------------------------
    # USE AUTOMATICALLY SAVED BEST
    # --------------------------------------------------------

    if (
        baseline_mode
        ==
        "saved"
    ):

        baseline_payload = (
            load_saved_best_payload()
        )


        if baseline_payload is None:

            raise ValueError(
                "No saved best chromosome exists yet."
            )


        baseline_source = (
            "saved"
        )


    # --------------------------------------------------------
    # USE UPLOADED JSON
    # --------------------------------------------------------

    elif (
        baseline_mode
        ==
        "uploaded"
    ):

        baseline_payload = (
            load_uploaded_payload()
        )


        if baseline_payload is None:

            raise ValueError(
                "No uploaded baseline chromosome exists."
            )


        baseline_source = (
            "uploaded"
        )


    # --------------------------------------------------------
    # RECONSTRUCT BASELINE
    # --------------------------------------------------------

    if baseline_payload is not None:

        baseline_chromosome = (
            payload_to_chromosome(
                baseline_payload,
                list_subjects,
                list_faculty,
                lst_rooms,
            )
        )


        baseline_fitness = (
            faculty_preference_fitness(
                baseline_chromosome,
                df_faculty_pref,
            )
        )


        print()
        print("=" * 60)

        print(
            "BASELINE CHROMOSOME LOADED"
        )

        print("=" * 60)

        print(
            f"Source  : "
            f"{baseline_source}"
        )

        print(
            f"Fitness : "
            f"{baseline_fitness}"
        )


    # ========================================================
    # INITIAL POPULATION
    # ========================================================

    number_to_generate = (
        population_size
        -
        (
            1
            if baseline_chromosome
            is not None
            else 0
        )
    )


    population = (
        generate_population(
            number_to_generate,
            list_faculty,
            list_subjects,
            lst_rooms,
        )
    )


    # Seed baseline as chromosome #1.

    if (
        baseline_chromosome
        is not None
    ):

        population.insert(
            0,
            baseline_chromosome,
        )


    if not population:

        raise RuntimeError(
            "Unable to create an initial population."
        )


    population = (
        sort_population_by_fitness(
            population,
            df_faculty_pref,
        )
    )

    if not population:
        raise RuntimeError(
            "No valid chromosomes were generated."
        )

    population = sort_population_by_fitness(
        population,
        df_faculty_pref,
    )

    # =====================================================
    # 2. BEST-EVER BASELINE
    # =====================================================

    best_ever = copy.deepcopy(
        population[0]
    )

    best_ever_fitness = (
        faculty_preference_fitness(
            best_ever,
            df_faculty_pref,
        )
    )

    history = [
        {
            "generation": 0,
            "best_fitness": best_ever_fitness,
        }
    ]

    # =====================================================
    # 3. GENERATION LOOP
    # =====================================================

    for generation in range(
        1,
        generations + 1,
    ):

        # -----------------------------------------------
        # Calculate fitness
        # -----------------------------------------------

        fitness_scores = [
            faculty_preference_fitness(
                chromosome,
                df_faculty_pref,
            )
            for chromosome in population
        ]

        # -----------------------------------------------
        # Keep best 10%
        # -----------------------------------------------

        (
            elites,
            elite_fitness,
            non_elites,
            non_elite_fitness,
        ) = elitism_selection(
            population=population,
            fitness_scores=fitness_scores,
            elite_percentage=0.10,
        )

        # -----------------------------------------------
        # Select top 50% of non-elites
        # -----------------------------------------------

        if non_elites:

            non_elite_scores = [
                faculty_preference_fitness(
                    chromosome,
                    df_faculty_pref,
                )
                for chromosome in non_elites
            ]

            (
                top_non_elites,
                _,
                _,
                _,
            ) = elitism_selection(
                population=non_elites,
                fitness_scores=non_elite_scores,
                elite_percentage=0.50,
            )

        else:
            top_non_elites = elites

        # -----------------------------------------------
        # Generate children
        # -----------------------------------------------

        new_population = []

        target_children = max(
            1,
            int(population_size * 0.9),
        )

        attempts = 0

        max_child_attempts = (
            target_children * 20
        )

        while (
            len(new_population)
            < target_children
            and attempts < max_child_attempts
        ):

            attempts += 1

            if not top_non_elites:
                break

            result = (
                create_child_by_faculty_swap(
                    population=top_non_elites,
                    df_faculty_pref=df_faculty_pref,
                    max_attempts=100,
                )
            )

            if (
                result is not None
                and result != "None"
            ):
                new_population.append(
                    result
                )

        # -----------------------------------------------
        # Keep selected parents
        # -----------------------------------------------

        for chromosome in top_non_elites:

            if chromosome not in new_population:
                new_population.append(
                    chromosome
                )

        # -----------------------------------------------
        # Mutation
        # -----------------------------------------------

        if new_population:

            result = (
                mutate_by_swapping_faculty_subjects(
                    population=new_population,
                    df_faculty_pref=df_faculty_pref,
                    max_attempts=mutation_attempts,
                )
            )

            if (
                result is not None
                and result != "None"
            ):
                new_population.append(
                    result
                )

        # -----------------------------------------------
        # Add elites
        # -----------------------------------------------

        for elite in elites:

            if elite not in new_population:
                new_population.append(
                    elite
                )

        # -----------------------------------------------
        # Add BEST-EVER chromosome explicitly
        # -----------------------------------------------

        new_population.append(
            copy.deepcopy(
                best_ever
            )
        )

        # -----------------------------------------------
        # Add fresh chromosomes
        # -----------------------------------------------

        fresh_population = (
            generate_population(
                population_size=fresh_chromosomes,
                list_faculty=list_faculty,
                list_subjects=list_subjects,
                lst_rooms=lst_rooms,
                max_restarts=max_restarts,
            )
        )

        new_population.extend(
            fresh_population
        )

        # -----------------------------------------------
        # Remove invalid objects
        # -----------------------------------------------

        valid_population = []

        for chromosome in new_population:

            try:
                if len(chromosome) > 0:
                    valid_population.append(
                        chromosome
                    )

            except TypeError:
                continue

        if not valid_population:
            raise RuntimeError(
                f"Generation {generation} "
                "produced no valid chromosomes."
            )

        # -----------------------------------------------
        # Sort by fitness
        # -----------------------------------------------

        valid_population = (
            sort_population_by_fitness(
                valid_population,
                df_faculty_pref,
            )
        )

        current_best = (
            valid_population[0]
        )

        current_best_fitness = (
            faculty_preference_fitness(
                current_best,
                df_faculty_pref,
            )
        )

        # =================================================
        # BEST-EVER REPLACEMENT
        # =================================================

        if (
            current_best_fitness
            < best_ever_fitness
        ):

            best_ever = copy.deepcopy(
                current_best
            )

            best_ever_fitness = (
                current_best_fitness
            )

        history.append(
            {
                "generation": generation,
                "generation_best_fitness":
                    current_best_fitness,
                "best_ever_fitness":
                    best_ever_fitness,
            }
        )

        # -----------------------------------------------
        # Prepare next generation
        # -----------------------------------------------

        population = (
            valid_population[
                :population_size
            ]
        )

    # =====================================================
    # 4. CONVERT BEST-EVER TO JSON
    # =====================================================

    schedule = []

    for subject in best_ever:

        schedule.extend(
            get_subject_schedule_entries(
                subject
            )
        )

    # =====================================================
    # 5. GET FITNESS BREAKDOWN
    # =====================================================

    best_fitness, fitness_breakdown = (
        faculty_preference_fitness(
            best_ever,
            df_faculty_pref,
            return_breakdown=True,
        )
    )
        # ========================================================
    # SAVE BEST CHROMOSOME TO DISK
    # ========================================================

    (
        saved_best_updated,
        saved_best_payload,
    ) = save_best_if_better(
        best_ever,
        best_fitness,
    )


    saved_best_fitness = None


    if saved_best_payload:

        saved_best_fitness = (
            saved_best_payload.get(
                "best_fitness"
            )
        )
        # ========================================================
    # PER-FACULTY ANALYSIS
    # ========================================================

    faculty_analysis = (
        build_faculty_analysis(
            best_ever,
            df_faculty_pref,
        )
    )

    # =====================================================
    # 6. RETURN RESULT
    # =====================================================

    return {
        "best_fitness": best_fitness,

        "fitness_breakdown":
            fitness_breakdown,

        "generations_completed":
            generations,

        "population_size":
            population_size,

        "history":
            history,

        "schedule":
            schedule,

        "faculty_analysis":
            faculty_analysis,
                "baseline_source":
            baseline_source,

        "starting_baseline_fitness":
            baseline_fitness,

        "saved_best_updated":
            saved_best_updated,

        "saved_best_fitness":
            saved_best_fitness,
}