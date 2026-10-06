import math

import numpy as np
import pandas as pd

from genetic_algorithm.analysis.FacultySelectedChromosomeDashboard import (
    analyze_selected_chromosome,
)

from genetic_algorithm.models.Faculty import Faculty

from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
    _build_effective_preferences,
    _get_importance,
    _load_ga_settings,
    _subject_components,
    _time_to_minutes,
    _unpack_block,
    _normalize_schedule_day,
    _subject_schedule_preference_blocks,
    _component_intervals,
)


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
    Convert a pandas DataFrame into JSON-safe records.
    """

    records = []

    for record in dataframe.to_dict(
        orient="records"
    ):

        records.append(
            {
                key: clean_value(value)
                for key, value
                in record.items()
            }
        )

    return records


# ============================================================
# HELPERS
# ============================================================

def _faculty_code(value):

    try:
        return int(value)

    except (
        TypeError,
        ValueError
    ):
        return value


def _subjects_for_faculty(
    chromosome,
    faculty_code
):

    result = []

    for subject in chromosome:

        faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        if faculty is None:
            continue

        code = _faculty_code(
            getattr(
                faculty,
                "code",
                None
            )
        )

        if code == faculty_code:

            result.append(
                subject
            )

    return result


# ============================================================
# SUBJECT SATISFACTION
# ============================================================

def _subject_satisfaction(
    subjects,
    preference
):
    """
    Descriptive subject-preference satisfaction.

    IMPORTANT:
    Satisfaction is intentionally independent from the GA
    importance weight.  Importance controls how strongly a
    preference affects fitness; it should not hide the factual
    comparison between requested and assigned subjects.

    Returns None only when there is no usable subject preference
    to compare or there are no assigned subjects to evaluate.
    """

    if not preference.get(
        "use_subject_preference",
        False
    ):

        return None

    preferred_subjects = [

        str(subject_name)
        .strip()
        .upper()

        for subject_name
        in preference.get(
            "preferred_subjects",
            []
        )
    ]

    if (
        not preferred_subjects
        or not subjects
    ):

        return None

    scores = []

    for subject in subjects:

        actual_subject = (
            str(
                subject.number
            )
            .strip()
            .upper()
        )

        if (
            actual_subject
            not in preferred_subjects
        ):

            scores.append(
                0.0
            )

            continue

        rank_index = (
            preferred_subjects.index(
                actual_subject
            )
        )

        rank_fraction = (
            rank_index
            /
            max(
                1,
                len(
                    preferred_subjects
                )
            )
        )

        scores.append(
            100
            * (
                1
                - rank_fraction
            )
        )

    return (
        sum(scores)
        / len(scores)
    )


# ============================================================
# EXACT SUBJECT SCHEDULE SATISFACTION
# ============================================================

def _exact_schedule_satisfaction(
    subjects,
    preference
):
    """
    Compare the faculty's draggable subject calendar blocks against
    the generated chromosome.

    Day %:
        requested block day vs generated component day.

    Time %:
        requested start time vs generated component start time.

    Exact %:
        both day and start time match.

    Importance is deliberately ignored here because this is
    descriptive satisfaction, not fitness weighting.
    """

    preferred_blocks = [
        block
        for block in (
            preference.get(
                "preferred_schedule_blocks",
                []
            )
            or []
        )
        if (
            isinstance(block, dict)
            and str(
                block.get(
                    "kind",
                    ""
                )
            ).strip().lower()
            == "subject"
        )
    ]

    if not preferred_blocks:
        return None

    subject_map = {
        str(
            subject.number
        ).strip().upper(): subject
        for subject in subjects
    }

    total = len(
        preferred_blocks
    )

    day_matches = 0
    time_matches = 0
    exact_matches = 0

    for preferred_block in preferred_blocks:

        subject_code = (
            str(
                preferred_block.get(
                    "subject_code",
                    ""
                )
            )
            .strip()
            .upper()
        )

        subject = subject_map.get(
            subject_code
        )

        if subject is None:
            continue

        component_name = (
            str(
                preferred_block.get(
                    "component",
                    ""
                )
            )
            .strip()
            .lower()
        )

        if component_name == "lecture":
            component_blocks = getattr(
                subject,
                "lecture_time_blocks",
                []
            )

        elif component_name == "laboratory":
            component_blocks = getattr(
                subject,
                "laboratory_time_blocks",
                []
            )

        else:
            component_blocks = []

        actual_intervals = (
            _component_intervals(
                component_blocks
            )
        )

        preferred_day = (
            _normalize_schedule_day(
                preferred_block.get(
                    "day"
                )
            )
        )

        preferred_start = (
            _time_to_minutes(
                preferred_block.get(
                    "start_time"
                )
            )
        )

        day_match = (
            preferred_day is not None
            and any(
                day == preferred_day
                for day, _, _
                in actual_intervals
            )
        )

        time_match = (
            preferred_start is not None
            and any(
                start == preferred_start
                for _, start, _
                in actual_intervals
            )
        )

        exact_match = (
            preferred_day is not None
            and preferred_start is not None
            and any(
                day == preferred_day
                and start == preferred_start
                for day, start, _
                in actual_intervals
            )
        )

        if day_match:
            day_matches += 1

        if time_match:
            time_matches += 1

        if exact_match:
            exact_matches += 1

    return {
        "total": total,
        "day_matches": day_matches,
        "time_matches": time_matches,
        "exact_matches": exact_matches,
        "day_satisfaction":
            100 * day_matches / total,
        "time_satisfaction":
            100 * time_matches / total,
        "exact_satisfaction":
            100 * exact_matches / total,
    }


# ============================================================
# DAY SATISFACTION
# ============================================================

def _day_satisfaction(
    subjects,
    preference
):
    """
    Descriptive preferred-day satisfaction.

    This percentage is independent from day_importance.
    Importance affects the GA penalty only.
    """

    if not preference.get(
        "use_day_preference",
        False
    ):

        return None

    preferred_days = set()

    for day in preference.get(
        "preferred_days",
        []
    ):

        preferred_days.update(
            Faculty._normalize_days(
                day
            )
        )

    if (
        not preferred_days
        or not subjects
    ):

        return None

    total = 0
    matches = 0

    for subject in subjects:

        actual_days = set()

        for component in (
            _subject_components(
                subject
            )
        ):

            for entry in component:

                actual_day, _ = (
                    _unpack_block(
                        entry
                    )
                )

                if actual_day:

                    actual_days.add(
                        actual_day
                    )

        if not actual_days:
            continue

        total += 1

        if actual_days.issubset(
            preferred_days
        ):

            matches += 1

    if total == 0:
        return None

    return (
        100
        * matches
        / total
    )


# ============================================================
# TIME SATISFACTION
# ============================================================

def _time_satisfaction(
    subjects,
    preference
):
    """
    Descriptive preferred-time satisfaction.

    This percentage is independent from time_importance.
    Importance affects the GA penalty only.
    """

    if not preference.get(
        "use_time_preference",
        False
    ):
        return None

    if not subjects:
        return None

    preferred_start = _time_to_minutes(
        preference.get(
            "preferred_start_time"
        )
    )

    preferred_end = _time_to_minutes(
        preference.get(
            "preferred_end_time"
        )
    )

    # Dashboard JSON is authoritative. If the faculty has not
    # configured a complete preferred time range, there is no
    # time preference to evaluate. Do not fall back to legacy
    # Faculty TimeBlocks.
    if (
        preferred_start is None
        or preferred_end is None
    ):
        return None

    total = 0
    matches = 0

    for subject in subjects:

        for component in _subject_components(
            subject
        ):

            if not component:
                continue

            total += 1
            component_mismatch = False

            for entry in component:

                _, block = _unpack_block(
                    entry
                )

                actual_start = getattr(
                    block,
                    "start_time",
                    None
                )

                actual_end = getattr(
                    block,
                    "end_time",
                    None
                )

                start_minutes = _time_to_minutes(
                    actual_start
                )

                end_minutes = _time_to_minutes(
                    actual_end
                )

                if (
                    start_minutes is None
                    or end_minutes is None
                    or start_minutes < preferred_start
                    or end_minutes > preferred_end
                ):
                    component_mismatch = True
                    break

            if not component_mismatch:
                matches += 1

    if total == 0:
        return None

    return (
        100
        * matches
        / total
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def build_faculty_analysis(
    chromosome,
    df_faculty_pref
):

    """
    Build faculty analysis using the SAME dashboard-aware
    fitness logic used by FitnessFunction.py.

    LOWER PENALTY = BETTER.
    """

    # ========================================================
    # LOAD CURRENT SETTINGS
    # ========================================================

    settings = (
        _load_ga_settings()
    )


    # ========================================================
    # LOAD EFFECTIVE PREFERENCES
    #
    # Dashboard preferences override CSV preferences.
    # ========================================================

    effective_preferences = (
        _build_effective_preferences(
            df_faculty_pref
        )
    )


    priorities = [

        int(
            preference.get(
                "faculty_priority",
                1
            )
        )

        for preference
        in effective_preferences.values()
    ]


    max_priority = (

        max(priorities)

        if priorities

        else 1
    )


    # ========================================================
    # OLD ANALYSIS
    #
    # Keep this ONLY for:
    #
    # - teaching load
    # - daily load
    # - preparations
    # - load deviation
    #
    # Preference penalties will be replaced below.
    # ========================================================

    (
        faculty_df,
        daily_df,
        _
    ) = analyze_selected_chromosome(

        [subject for subject in chromosome
         if not getattr(getattr(subject, "assigned_faculty", None), "is_external", False)],

        df_faculty_pref,

        subject_penalty=
            settings.subject_penalty,

        time_penalty=
            settings.time_penalty,

        day_penalty=
            settings.day_penalty,

        preparation_penalty=
            settings.preparation_penalty,

        max_preparations=
            settings.max_preparations,
    )


    # ========================================================
    # REBUILD FACULTY ANALYSIS USING CURRENT FITNESS
    # ========================================================

    updated_rows = []


    for _, row in (
        faculty_df.iterrows()
    ):

        faculty_code = (
            _faculty_code(
                row[
                    "Faculty_Code"
                ]
            )
        )


        preference = (
            effective_preferences.get(
                faculty_code,
                {}
            )
        )


        faculty_priority = int(

            preference.get(

                "faculty_priority",

                row.get(
                    "Faculty_Priority",
                    1
                )
            )
        )


        priority_weight = (

            max_priority
            - faculty_priority
            + 1

            if faculty_code
            in effective_preferences

            else 1
        )


        faculty_subjects = (
            _subjects_for_faculty(
                chromosome,
                faculty_code
            )
        )


        # ----------------------------------------------------
        # Run CURRENT fitness only for this faculty.
        #
        # This guarantees the faculty penalties use the same
        # rules as the main GA fitness.
        # ----------------------------------------------------

        (
            _,
            faculty_breakdown
        ) = faculty_preference_fitness(

            faculty_subjects,

            df_faculty_pref,

            ga_settings=settings,

            return_breakdown=True,

            faculty_scope=[
                faculty_code
            ]
        )


        current = (
            row.to_dict()
        )


        # ====================================================
        # CURRENT FACULTY PRIORITY
        # ====================================================

        current[
            "Faculty_Priority"
        ] = faculty_priority


        current[
            "Priority_Weight"
        ] = priority_weight


        # ====================================================
        # IMPORTANCE VALUES
        # ====================================================

        current[
            "Subject_Importance"
        ] = _get_importance(
            preference,
            "subject_importance",
            default=0
        )


        current[
            "Day_Importance"
        ] = _get_importance(
            preference,
            "day_importance",
            default=0
        )


        current[
            "Time_Importance"
        ] = _get_importance(
            preference,
            "time_importance",
            default=0
        )


        current[
            "Gap_Importance"
        ] = _get_importance(
            preference,
            "gap_importance",
            default=0
        )


        current[
            "Lecture_Lab_Importance"
        ] = _get_importance(
            preference,
            "lecture_lab_importance",
            default=0
        )


        # ====================================================
        # CURRENT SATISFACTION VALUES
        # ====================================================

        current[
            "Subject_Satisfaction"
        ] = _subject_satisfaction(
            faculty_subjects,
            preference
        )


        exact_schedule = (
            _exact_schedule_satisfaction(
                faculty_subjects,
                preference
            )
        )


        if exact_schedule is not None:

            current[
                "Day_Satisfaction"
            ] = exact_schedule[
                "day_satisfaction"
            ]

            current[
                "Time_Satisfaction"
            ] = exact_schedule[
                "time_satisfaction"
            ]

            current[
                "Exact_Schedule_Satisfaction"
            ] = exact_schedule[
                "exact_satisfaction"
            ]

            current[
                "Preferred_Schedule_Blocks"
            ] = exact_schedule[
                "total"
            ]

            current[
                "Matched_Schedule_Blocks"
            ] = exact_schedule[
                "exact_matches"
            ]

        else:

            current[
                "Day_Satisfaction"
            ] = _day_satisfaction(
                faculty_subjects,
                preference
            )

            current[
                "Time_Satisfaction"
            ] = _time_satisfaction(
                faculty_subjects,
                preference
            )

            current[
                "Exact_Schedule_Satisfaction"
            ] = None

            current[
                "Preferred_Schedule_Blocks"
            ] = 0

            current[
                "Matched_Schedule_Blocks"
            ] = 0


        # ====================================================
        # CURRENT PENALTIES
        # ====================================================

        current[
            "Subject_Penalty"
        ] = faculty_breakdown[
            "subject_preference"
        ]


        current[
            "Time_Penalty"
        ] = faculty_breakdown[
            "time_preference"
        ]


        current[
            "Day_Penalty"
        ] = faculty_breakdown[
            "day_preference"
        ]


        current[
            "Schedule_Style_Penalty"
        ] = faculty_breakdown[
            "schedule_style"
        ]


        current[
            "Lecture_Lab_Penalty"
        ] = faculty_breakdown[
            "lecture_lab_preference"
        ]


        current[
            "Preparation_Penalty"
        ] = faculty_breakdown[
            "number_of_preparations"
        ]


        current[
            "Load_Balance_Penalty"
        ] = faculty_breakdown[
            "teaching_load_balance"
        ]


        current[
            "Daily_Teaching_Load_Penalty"
        ] = faculty_breakdown[
            "daily_teaching_load"
        ]


        current[
            "Total_Penalty"
        ] = sum(
            faculty_breakdown.values()
        )


        updated_rows.append(
            current
        )


    # ========================================================
    # CREATE UPDATED DATAFRAME
    # ========================================================

    faculty_df = pd.DataFrame(
        updated_rows
    )


    if not faculty_df.empty:

        faculty_df = (

            faculty_df

            .sort_values(
                [
                    "Faculty_Priority",
                    "Faculty_Code"
                ],
                na_position="last"
            )

            .reset_index(
                drop=True
            )
        )


        if not daily_df.empty:

            daily_df = (

                daily_df

                .set_index(
                    "Faculty_Code"
                )

                .reindex(
                    faculty_df[
                        "Faculty_Code"
                    ]
                )

                .reset_index()
            )


    # ========================================================
    # AVERAGE TEACHING LOAD
    # ========================================================

    average_teaching_load = (

        faculty_df[
            "Teaching_Load"
        ].mean()

        if not faculty_df.empty

        else 0
    )


    # ========================================================
    # OFFICIAL OVERALL FITNESS
    # ========================================================

    (
        total_fitness,
        fitness_breakdown
    ) = faculty_preference_fitness(

        chromosome,

        df_faculty_pref,

        ga_settings=settings,

        return_breakdown=True
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    current_analysis_summary = {

        "Total_Fitness":
            clean_value(
                total_fitness
            ),

        "Subject_Penalty":
            clean_value(
                fitness_breakdown[
                    "subject_preference"
                ]
            ),

        "Time_Penalty":
            clean_value(
                fitness_breakdown[
                    "time_preference"
                ]
            ),

        "Day_Penalty":
            clean_value(
                fitness_breakdown[
                    "day_preference"
                ]
            ),

        "Preparation_Penalty":
            clean_value(
                fitness_breakdown[
                    "number_of_preparations"
                ]
            ),

        "Average_Teaching_Load":
            clean_value(
                average_teaching_load
            ),
    }


    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {

        "faculty":
            dataframe_to_records(
                faculty_df
            ),

        "daily_load":
            dataframe_to_records(
                daily_df
            ),

        "summary": {

            "total_fitness":
                clean_value(
                    total_fitness
                ),

            "average_teaching_load":
                clean_value(
                    average_teaching_load
                ),

            "fitness_breakdown": {

                key:
                    clean_value(
                        value
                    )

                for key, value
                in fitness_breakdown.items()
            },


            # Keep the old response key so your frontend
            # does not break.
            #
            # The values now come from CURRENT GA fitness.
            "professor_analysis":
                current_analysis_summary,


            "parameters": {

                "subject_penalty":
                    settings.subject_penalty,

                "time_penalty":
                    settings.time_penalty,

                "day_penalty":
                    settings.day_penalty,

                "preparation_penalty":
                    settings.preparation_penalty,

                "load_balance_penalty":
                    settings.load_balance_penalty,

                "daily_load_penalty":
                    settings.daily_load_penalty,

                "max_preparations":
                    settings.max_preparations,

                "target_teaching_load":
                    settings.target_teaching_load,

                "load_tolerance":
                    settings.load_tolerance,

                "max_daily_teaching_minutes":
                    settings.max_daily_teaching_minutes,

                "daily_load_step_minutes":
                    settings.daily_load_step_minutes,


                "gap_penalty":
                    getattr(
                        settings,
                        "gap_penalty",
                        settings.time_penalty
                    ),


                "lecture_lab_penalty":
                    getattr(
                        settings,
                        "lecture_lab_penalty",
                        settings.day_penalty
                    ),
            },
        },
    }
