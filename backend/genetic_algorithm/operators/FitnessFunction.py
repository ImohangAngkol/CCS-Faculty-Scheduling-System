import json
import math
from pathlib import Path

import pandas as pd

from genetic_algorithm.models.Faculty import (
    Faculty
)

from genetic_algorithm.models.ga_setting import (
    GASetting
)


# =========================================================
# DATA FILES
# =========================================================

BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DATA_DIR = (
    BACKEND_DIR
    / "data"
)

PREFERENCE_FILE = (
    DATA_DIR
    / "faculty_preferences.json"
)

GA_SETTINGS_FILE = (
    DATA_DIR
    / "ga_settings.json"
)


# =========================================================
# HELPERS
# =========================================================

def _load_ga_settings():

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


def _load_dashboard_preferences():

    if not PREFERENCE_FILE.exists():

        return {}

    try:

        with open(
            PREFERENCE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rows = json.load(file)

        return {
            int(row["faculty_code"]): row
            for row in rows
        }

    except Exception:

        return {}


def _normalize_list(value):

    if value is None:
        return []

    if isinstance(
        value,
        (list, tuple, set)
    ):

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    text = str(value).strip()

    if not text:
        return []

    for separator in [
        ";",
        "|",
        "/"
    ]:

        text = text.replace(
            separator,
            ","
        )

    return [
        item.strip()
        for item in text.split(",")
        if item.strip()
    ]


def _legacy_preferences_to_map(
    df_faculty_pref
):

    result = {}

    if (
        df_faculty_pref is None
        or df_faculty_pref.empty
    ):
        return result

    prefs = (
        df_faculty_pref.copy()
    )

    if isinstance(
        prefs.columns,
        pd.MultiIndex
    ):

        prefs.columns = (
            prefs.columns
            .get_level_values(0)
        )

    prefs.columns = [
        str(column).strip()
        for column in prefs.columns
    ]

    if "Faculty_Code" not in prefs.columns:
        return result

    for faculty_code, group in (
        prefs.groupby("Faculty_Code")
    ):

        try:

            code = int(
                faculty_code
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        priority = 1

        if "Faculty_Prio" in group.columns:

            values = pd.to_numeric(
                group["Faculty_Prio"],
                errors="coerce"
            ).dropna()

            if not values.empty:
                priority = int(
                    values.iloc[0]
                )

        preferred_subjects = []

        subject_column = None

        if (
            "Preferred Subjects"
            in group.columns
        ):

            subject_column = (
                "Preferred Subjects"
            )

        elif "Subject" in group.columns:

            subject_column = "Subject"

        if subject_column:

            for value in (
                group[subject_column]
                .dropna()
            ):

                preferred_subjects.extend(
                    _normalize_list(
                        value
                    )
                )

        preferred_subjects = list(
            dict.fromkeys(
                subject.upper()
                for subject
                in preferred_subjects
            )
        )

        preferred_days = []

        day_column = None

        if (
            "Preferred Day(s)"
            in group.columns
        ):

            day_column = (
                "Preferred Day(s)"
            )

        elif "Day(s)" in group.columns:

            day_column = "Day(s)"

        if day_column:

            for value in (
                group[day_column]
                .dropna()
            ):

                preferred_days.extend(
                    Faculty._normalize_days(
                        value
                    )
                )

        preferred_days = list(
            dict.fromkeys(
                preferred_days
            )
        )

        result[code] = {

            "faculty_code": code,

            "faculty_priority":
                priority,

            "preferred_subjects":
                preferred_subjects,

            "preferred_days":
                preferred_days,

            "preferred_start_time":
                None,

            "preferred_end_time":
                None,

            "gap_preference":
                "No Preference",

            "use_subject_preference":
                True,

            "use_day_preference":
                True,

            "use_time_preference":
                True,

            "use_gap_preference":
                False,
        }

    return result


def _build_effective_preferences(
    df_faculty_pref
):

    # Start with your OLD CSV preferences
    result = _legacy_preferences_to_map(
        df_faculty_pref
    )

    # Dashboard preferences OVERRIDE
    # old CSV values.
    dashboard = (
        _load_dashboard_preferences()
    )

    for code, preference in (
        dashboard.items()
    ):

        result[code] = preference

    return result


def _time_to_minutes(value):

    if value is None:
        return None

    try:

        hour, minute = map(
            int,
            str(value)
            .strip()
            .split(":")
        )

        return (
            hour * 60
            + minute
        )

    except Exception:

        return None


def _unpack_block(entry):

    if (
        isinstance(entry, tuple)
        and len(entry) == 2
    ):

        day_value, block = entry

    else:

        block = entry

        day_value = getattr(
            block,
            "day_code",
            getattr(
                block,
                "day",
                None
            )
        )

    if day_value is None:

        return None, block

    day_text = (
        str(day_value)
        .strip()
    )

    day_code_to_name = {
        "M": "monday",
        "T": "tuesday",
        "W": "wednesday",
        "TH": "thursday",
        "F": "friday",
        "S": "saturday",
    }

    day_name = (
        day_code_to_name.get(
            day_text.upper(),
            day_text.lower()
        )
    )

    return day_name, block


def _subject_components(subject):

    components = [

        getattr(
            subject,
            "lecture_time_blocks",
            []
        ) or [],

        getattr(
            subject,
            "laboratory_time_blocks",
            []
        ) or [],
    ]

    if not any(components):

        scheduled = getattr(
            subject,
            "scheduled_time_blocks",
            None
        )

        if scheduled:

            if isinstance(
                scheduled,
                list
            ):

                components = [
                    scheduled
                ]

            else:

                components = [
                    [scheduled]
                ]

    return components


# =========================================================
# FITNESS FUNCTION
# =========================================================

def faculty_preference_fitness(
    chromosome,
    df_faculty_pref=None,
    ga_settings=None,
    return_breakdown=False,
    **legacy_kwargs
):

    """
    LOWER FITNESS = BETTER.

    Hard constraints remain OUTSIDE this
    function.

    Dashboard preferences automatically
    override legacy CSV preferences.
    
    """
    if legacy_kwargs:
            print(
                "Ignoring legacy fitness arguments:",
                list(legacy_kwargs.keys())
            )
    # =====================================================
    # SETTINGS
    # =====================================================

    if ga_settings is None:

        settings = (
            _load_ga_settings()
        )

    elif isinstance(
        ga_settings,
        GASetting
    ):

        settings = ga_settings

    else:

        settings = (
            GASetting.from_dict(
                ga_settings
            )
        )

    prefs = (
        _build_effective_preferences(
            df_faculty_pref
        )
    )

    priorities = [

        int(
            pref.get(
                "faculty_priority",
                1
            )
        )

        for pref
        in prefs.values()
    ]

    max_priority = (
        max(priorities)
        if priorities
        else 1
    )

    # =====================================================
    # BREAKDOWN
    # =====================================================

    breakdown = {

        "subject_preference": 0,

        "time_preference": 0,

        "day_preference": 0,

        "number_of_preparations": 0,

        "teaching_load_balance": 0,

        "daily_teaching_load": 0,
    }

    faculty_subjects = {}

    faculty_priority_weights = {}

    faculty_weekly_loads = {}

    faculty_daily_intervals = {}


    # =====================================================
    # SUBJECT LOOP
    # =====================================================

    for subject in chromosome:

        faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        if faculty is None:
            continue

        try:

            faculty_code = int(
                faculty.code
            )

        except (
            TypeError,
            ValueError
        ):

            faculty_code = (
                faculty.code
            )

        preference = prefs.get(
            faculty_code,
            {
                "faculty_priority": 1,

                "preferred_subjects": [],

                "preferred_days": [],

                "preferred_start_time":
                    None,

                "preferred_end_time":
                    None,

                "use_subject_preference":
                    False,

                "use_day_preference":
                    False,

                "use_time_preference":
                    False,
            }
        )

        priority = int(
            preference.get(
                "faculty_priority",
                1
            )
        )

        priority_weight = (
            max_priority
            - priority
            + 1
        )

        faculty_priority_weights[
            faculty_code
        ] = priority_weight

        # -----------------------------------------------
        # WEEKLY LOAD
        # -----------------------------------------------

        faculty_weekly_loads[
            faculty_code
        ] = (

            faculty_weekly_loads.get(
                faculty_code,
                0
            )

            + (
                getattr(
                    subject,
                    "credit_units",
                    0
                )
                or 0
            )
        )

        actual_subject = (
            str(
                subject.number
            )
            .strip()
            .upper()
        )

        faculty_subjects.setdefault(
            faculty_code,
            set()
        ).add(
            actual_subject
        )

        # -----------------------------------------------
        # 1. SUBJECT PREFERENCE
        # -----------------------------------------------

        if preference.get(
            "use_subject_preference",
            False
        ):

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
                preferred_subjects
                and actual_subject
                not in preferred_subjects
            ):

                breakdown[
                    "subject_preference"
                ] += (

                    settings.subject_penalty

                    * priority_weight
                )

        # -----------------------------------------------
        # SCHEDULE INFORMATION
        # -----------------------------------------------

        all_actual_days = set()

        time_mismatch_count = 0

        daily_blocks = []

        for component_blocks in (
            _subject_components(
                subject
            )
        ):

            if not component_blocks:
                continue

            component_time_mismatch = (
                False
            )

            for entry in component_blocks:

                actual_day, block = (
                    _unpack_block(
                        entry
                    )
                )

                if actual_day:

                    all_actual_days.add(
                        actual_day
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

                start_minutes = (
                    _time_to_minutes(
                        actual_start
                    )
                )

                end_minutes = (
                    _time_to_minutes(
                        actual_end
                    )
                )

                if (
                    actual_day
                    and start_minutes
                    is not None
                    and end_minutes
                    is not None
                    and end_minutes
                    > start_minutes
                ):

                    faculty_daily_intervals\
                        .setdefault(
                            faculty_code,
                            {}
                        )\
                        .setdefault(
                            actual_day,
                            []
                        )\
                        .append(
                            (
                                start_minutes,
                                end_minutes
                            )
                        )

                # ---------------------------------------
                # DASHBOARD TIME PREFERENCE
                # ---------------------------------------

                if preference.get(
                    "use_time_preference",
                    False
                ):

                    pref_start = (
                        _time_to_minutes(
                            preference.get(
                                "preferred_start_time"
                            )
                        )
                    )

                    pref_end = (
                        _time_to_minutes(
                            preference.get(
                                "preferred_end_time"
                            )
                        )
                    )

                    # Dashboard range exists
                    if (
                        pref_start
                        is not None
                        and pref_end
                        is not None
                        and start_minutes
                        is not None
                        and end_minutes
                        is not None
                    ):

                        if not (
                            start_minutes
                            >= pref_start
                            and end_minutes
                            <= pref_end
                        ):

                            component_time_mismatch = (
                                True
                            )

                    else:

                        # FALLBACK to old Faculty
                        # preferred TimeBlocks
                        faculty_day_map = (
                            faculty.get_day_map()
                        )

                        matching = False

                        for pref_block in (
                            faculty_day_map.get(
                                actual_day,
                                []
                            )
                        ):

                            if (
                                str(
                                    pref_block.start_time
                                )
                                ==
                                str(
                                    actual_start
                                )
                                and
                                str(
                                    pref_block.end_time
                                )
                                ==
                                str(
                                    actual_end
                                )
                                and
                                pref_block.preferred
                            ):

                                matching = True
                                break

                        if not matching:

                            component_time_mismatch = (
                                True
                            )

            if component_time_mismatch:

                time_mismatch_count += 1

        # -----------------------------------------------
        # 2. TIME PREFERENCE
        # -----------------------------------------------

        if preference.get(
            "use_time_preference",
            False
        ):

            breakdown[
                "time_preference"
            ] += (

                settings.time_penalty

                * time_mismatch_count

                * priority_weight
            )

        # -----------------------------------------------
        # 3. DAY PREFERENCE
        # -----------------------------------------------

        if preference.get(
            "use_day_preference",
            False
        ):

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
                preferred_days
                and all_actual_days
                and not all_actual_days.issubset(
                    preferred_days
                )
            ):

                breakdown[
                    "day_preference"
                ] += (

                    settings.day_penalty

                    * priority_weight
                )


    # =====================================================
    # 4. NUMBER OF PREPARATIONS
    # =====================================================

    for faculty_code, subjects in (
        faculty_subjects.items()
    ):

        number_of_preparations = (
            len(subjects)
        )

        excess = max(
            0,

            number_of_preparations
            - settings.max_preparations
        )

        if excess > 0:

            weight = (
                faculty_priority_weights.get(
                    faculty_code,
                    1
                )
            )

            breakdown[
                "number_of_preparations"
            ] += (

                settings.preparation_penalty

                * excess

                * weight
            )


    # =====================================================
    # 5. LOAD BALANCE
    # =====================================================

    tolerance = max(
        0,
        settings.load_tolerance
    )

    step_units = (
        tolerance
        if tolerance > 0
        else 1
    )

    for (
        faculty_code,
        actual_load
    ) in faculty_weekly_loads.items():

        difference = abs(
            actual_load
            - settings.target_teaching_load
        )

        excess_difference = max(
            0,

            difference
            - tolerance
        )

        if excess_difference > 0:

            load_steps = math.ceil(
                excess_difference
                / step_units
            )

            breakdown[
                "teaching_load_balance"
            ] += (

                load_steps

                * settings.load_balance_penalty
            )


    # =====================================================
    # 6. DAILY TEACHING LOAD
    # =====================================================

    def merge_intervals(
        intervals
    ):

        if not intervals:
            return []

        intervals = sorted(
            intervals
        )

        merged = [
            list(
                intervals[0]
            )
        ]

        for start, end in (
            intervals[1:]
        ):

            if (
                start
                <= merged[-1][1]
            ):

                merged[-1][1] = max(
                    merged[-1][1],
                    end
                )

            else:

                merged.append(
                    [start, end]
                )

        return merged


    for (
        faculty_code,
        day_map
    ) in faculty_daily_intervals.items():

        for (
            day,
            intervals
        ) in day_map.items():

            merged = (
                merge_intervals(
                    intervals
                )
            )

            total_minutes = sum(

                end - start

                for start, end
                in merged
            )

            excess_minutes = max(
                0,

                total_minutes
                - settings
                .max_daily_teaching_minutes
            )

            if excess_minutes > 0:

                steps = math.ceil(

                    excess_minutes

                    /
                    settings
                    .daily_load_step_minutes
                )

                breakdown[
                    "daily_teaching_load"
                ] += (

                    steps

                    * settings.daily_load_penalty
                )


    # =====================================================
    # FINAL
    # =====================================================

    total_penalty = sum(
        breakdown.values()
    )

    if return_breakdown:

        return (
            total_penalty,
            breakdown
        )

    return total_penalty