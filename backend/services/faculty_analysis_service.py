import math

import numpy as np
import pandas as pd

from genetic_algorithm.analysis.FacultySelectedChromosomeDashboard import (
    analyze_selected_chromosome,
)

from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)


# ============================================================
# CURRENT GA FITNESS SETTINGS
#
# Keep these synchronized with the actual GA fitness function.
# ============================================================

SUBJECT_PENALTY = 70
TIME_PENALTY = 10
DAY_PENALTY = 5
PREPARATION_PENALTY = 10

LOAD_BALANCE_PENALTY = 10
DAILY_LOAD_PENALTY = 10

MAX_PREPARATIONS = 3

TARGET_TEACHING_LOAD = 12
LOAD_TOLERANCE = 3

MAX_DAILY_TEACHING_MINUTES = 360
DAILY_LOAD_STEP_MINUTES = 60


# ============================================================
# JSON CLEANING
# ============================================================

def clean_value(value):
    """
    Convert pandas/numpy values into JSON-safe Python values.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        value = float(value)

        if math.isnan(value):
            return None

        if math.isinf(value):
            return None

        return value

    if isinstance(value, np.bool_):
        return bool(value)

    return value


def dataframe_to_records(dataframe):
    """
    Convert a pandas DataFrame to JSON-safe records.
    """

    records = []

    for record in dataframe.to_dict(
        orient="records"
    ):

        cleaned_record = {
            key: clean_value(value)
            for key, value
            in record.items()
        }

        records.append(
            cleaned_record
        )

    return records


# ============================================================
# MAIN ANALYSIS ADAPTER
# ============================================================

def build_faculty_analysis(
    chromosome,
    df_faculty_pref,
):
    """
    Convert the professor's selected-chromosome analysis
    into JSON data that can be consumed by the React frontend.

    The professor's analysis remains responsible for:
        - Subject satisfaction
        - Day satisfaction
        - Time satisfaction
        - Preparations
        - Teaching load
        - Per-faculty penalties
        - Load deviation
        - Daily teaching hours

    The current six-factor fitness function is also called
    so the overall analysis matches the GA run itself.
    """

    # --------------------------------------------------------
    # Professor's existing per-faculty analysis
    # --------------------------------------------------------

    (
        faculty_df,
        daily_df,
        professor_summary,
    ) = analyze_selected_chromosome(
        chromosome,
        df_faculty_pref,

        subject_penalty=
        SUBJECT_PENALTY,

        time_penalty=
        TIME_PENALTY,

        day_penalty=
        DAY_PENALTY,

        preparation_penalty=
        PREPARATION_PENALTY,

        max_preparations=
        MAX_PREPARATIONS,
    )


    # --------------------------------------------------------
    # Current six-factor fitness
    #
    # This keeps the dashboard aligned with the actual GA.
    # --------------------------------------------------------

    (
        total_fitness,
        fitness_breakdown,
    ) = faculty_preference_fitness(
        chromosome,
        df_faculty_pref,

        subject_penalty=
        SUBJECT_PENALTY,

        time_penalty=
        TIME_PENALTY,

        day_penalty=
        DAY_PENALTY,

        preparation_penalty=
        PREPARATION_PENALTY,

        load_balance_penalty=
        LOAD_BALANCE_PENALTY,

        daily_load_penalty=
        DAILY_LOAD_PENALTY,

        max_preparations=
        MAX_PREPARATIONS,

        target_teaching_load=
        TARGET_TEACHING_LOAD,

        load_tolerance=
        LOAD_TOLERANCE,

        max_daily_teaching_minutes=
        MAX_DAILY_TEACHING_MINUTES,

        daily_load_step_minutes=
        DAILY_LOAD_STEP_MINUTES,

        return_breakdown=True,
    )


    # --------------------------------------------------------
    # JSON-safe professor summary
    # --------------------------------------------------------

    cleaned_professor_summary = {
        key: clean_value(value)
        for key, value
        in professor_summary.items()
    }


    # --------------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------------

    return {

        "faculty": dataframe_to_records(
            faculty_df
        ),

        "daily_load": dataframe_to_records(
            daily_df
        ),

        "summary": {

            "total_fitness":
                clean_value(
                    total_fitness
                ),

            "average_teaching_load":
                clean_value(
                    professor_summary.get(
                        "Average_Teaching_Load"
                    )
                ),

            "fitness_breakdown": {
                key:
                    clean_value(value)

                for key, value
                in fitness_breakdown.items()
            },

            "professor_analysis":
                cleaned_professor_summary,

            "parameters": {
                "subject_penalty":
                    SUBJECT_PENALTY,

                "time_penalty":
                    TIME_PENALTY,

                "day_penalty":
                    DAY_PENALTY,

                "preparation_penalty":
                    PREPARATION_PENALTY,

                "load_balance_penalty":
                    LOAD_BALANCE_PENALTY,

                "daily_load_penalty":
                    DAILY_LOAD_PENALTY,

                "max_preparations":
                    MAX_PREPARATIONS,

                "target_teaching_load":
                    TARGET_TEACHING_LOAD,
            },
        },
    }