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
    """
    Keep only system-level faculty priority from the legacy CSV.

    Old CSV subject/day/time preferences are no longer used by
    the current dashboard-based GA preference system.

    This prevents legacy preferences from silently contributing
    penalties when a faculty member has not yet configured the
    new preference form.
    """

    result = {}

    if (
        df_faculty_pref is None
        or df_faculty_pref.empty
    ):
        return result

    prefs = df_faculty_pref.copy()

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

        # ---------------------------------------------
        # Keep legacy priority temporarily.
        # ---------------------------------------------

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

        # ---------------------------------------------
        # IMPORTANT:
        # All actual preference fields are NEUTRAL.
        #
        # Dashboard JSON is now the authoritative
        # source for faculty preferences.
        # ---------------------------------------------

        result[code] = {

            "faculty_code":
                code,

            "faculty_priority":
                priority,

            "preferred_subjects":
                [],

            "subject_importance":
                0,

            "preferred_days":
                [],

            "day_importance":
                0,

            "preferred_start_time":
                None,

            "preferred_end_time":
                None,

            "time_importance":
                0,

            "gap_preference":
                "No Preference",

            "gap_importance":
                0,

            "lecture_lab_preference":
                "No Preference",

            "lecture_lab_importance":
                0,

            "use_subject_preference":
                False,

            "use_day_preference":
                False,

            "use_time_preference":
                False,

            "use_gap_preference":
                False,

            "use_lecture_lab_preference":
                False,
        }

    return result


def _normalize_dashboard_preference(
    preference
):
    """
    Normalize old and new dashboard preference records.

    Missing importance values are treated as 0 (Ignore).
    This keeps older JSON records consistent with the
    current preference model.
    """

    preference = dict(
        preference
        or {}
    )

    return {

        "faculty_code":
            preference.get(
                "faculty_code"
            ),

        "faculty_priority":
            preference.get(
                "faculty_priority",
                1
            ),

        "preferred_schedule_blocks":
            preference.get(
                "preferred_schedule_blocks",
                []
            )
            or [],

        "preferred_subjects":
            preference.get(
                "preferred_subjects",
                []
            )
            or [],

        "subject_importance":
            _get_importance(
                preference,
                "subject_importance",
                default=0
            ),

        "preferred_days":
            preference.get(
                "preferred_days",
                []
            )
            or [],

        "day_importance":
            _get_importance(
                preference,
                "day_importance",
                default=0
            ),

        "preferred_start_time":
            preference.get(
                "preferred_start_time"
            ),

        "preferred_end_time":
            preference.get(
                "preferred_end_time"
            ),

        "time_importance":
            _get_importance(
                preference,
                "time_importance",
                default=0
            ),

        "gap_preference":
            preference.get(
                "gap_preference",
                "No Preference"
            )
            or "No Preference",

        "gap_importance":
            _get_importance(
                preference,
                "gap_importance",
                default=0
            ),

        "lecture_lab_preference":
            preference.get(
                "lecture_lab_preference",
                "No Preference"
            )
            or "No Preference",

        "lecture_lab_importance":
            _get_importance(
                preference,
                "lecture_lab_importance",
                default=0
            ),

        "use_subject_preference":
            bool(
                preference.get(
                    "use_subject_preference",
                    False
                )
            ),

        "use_day_preference":
            bool(
                preference.get(
                    "use_day_preference",
                    False
                )
            ),

        "use_time_preference":
            bool(
                preference.get(
                    "use_time_preference",
                    False
                )
            ),

        "use_gap_preference":
            bool(
                preference.get(
                    "use_gap_preference",
                    False
                )
            ),

        "use_lecture_lab_preference":
            bool(
                preference.get(
                    "use_lecture_lab_preference",
                    False
                )
            ),
    }


def _build_effective_preferences(
    df_faculty_pref
):
    """
    Build the effective preference map.

    Legacy CSV:
        Faculty priority only.

    Dashboard JSON:
        Authoritative source for all actual
        faculty preference fields.
    """

    # ---------------------------------------------
    # Start with faculty priority only.
    # ---------------------------------------------

    result = (
        _legacy_preferences_to_map(
            df_faculty_pref
        )
    )

    # ---------------------------------------------
    # Dashboard preference records override the
    # neutral legacy records.
    # ---------------------------------------------

    dashboard = (
        _load_dashboard_preferences()
    )

    for code, preference in (
        dashboard.items()
    ):

        normalized = (
            _normalize_dashboard_preference(
                preference
            )
        )

        # Keep the legacy/system priority only if an
        # old dashboard record does not contain one.
        if (
            "faculty_priority"
            not in preference
            and code in result
        ):

            normalized[
                "faculty_priority"
            ] = result[
                code
            ].get(
                "faculty_priority",
                1
            )

        result[code] = normalized

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


def _get_importance(
    preference,
    field_name,
    default=1
):
    """Return a faculty preference importance clamped to 0..5."""

    try:
        value = int(
            preference.get(
                field_name,
                default
            )
        )
    except (
        TypeError,
        ValueError
    ):
        value = default

    return max(
        0,
        min(
            5,
            value
        )
    )


def _days_from_blocks(blocks):
    """Return normalized day names used by a schedule block collection."""

    days = set()

    for entry in (
        blocks
        or []
    ):
        day, _ = _unpack_block(
            entry
        )

        if day:
            days.add(
                day
            )

    return days


def _normalize_schedule_day(value):
    """
    Normalize a dashboard schedule-block day to the same lowercase
    day names produced by _unpack_block().
    """

    if value is None:
        return None

    normalized = Faculty._normalize_days(
        value
    )

    if normalized:
        return str(
            normalized[0]
        ).strip().lower()

    text = str(value).strip().lower()

    return text or None


def _subject_schedule_preference_blocks(
    preference,
    subject_code
):
    """
    Return subject-specific draggable calendar blocks for one subject.

    General preferred-time blocks continue to use the legacy
    preferred_days/start/end summary and are not handled here.
    """

    actual_code = (
        str(subject_code)
        .strip()
        .upper()
    )

    result = []

    for block in preference.get(
        "preferred_schedule_blocks",
        []
    ) or []:

        if not isinstance(
            block,
            dict
        ):
            continue

        if str(
            block.get(
                "kind",
                ""
            )
        ).strip().lower() != "subject":
            continue

        preferred_code = (
            str(
                block.get(
                    "subject_code",
                    ""
                )
            )
            .strip()
            .upper()
        )

        if preferred_code != actual_code:
            continue

        result.append(block)

    return result


def _component_intervals(
    component_blocks
):
    """
    Convert one lecture/laboratory component into normalized
    (day, start_minutes, end_minutes) intervals.
    """

    intervals = []

    for entry in (
        component_blocks
        or []
    ):

        day, block = _unpack_block(
            entry
        )

        start = _time_to_minutes(
            getattr(
                block,
                "start_time",
                None
            )
        )

        end = _time_to_minutes(
            getattr(
                block,
                "end_time",
                None
            )
        )

        if (
            day
            and start is not None
            and end is not None
            and end > start
        ):

            intervals.append(
                (
                    str(day)
                    .strip()
                    .lower(),
                    start,
                    end
                )
            )

    return intervals


def _score_exact_subject_schedule_blocks(
    subject,
    preference,
    settings,
    priority_weight
):
    """
    Score exact subject calendar placements.

    The current preference tray still creates one-hour blocks by
    default because the subject endpoint does not yet expose the real
    lecture/laboratory duration.  For this checkpoint, TIME matching
    therefore compares the preferred START TIME rather than requiring
    the generated class to fit inside the temporary one-hour block.

    Day and time importance still control GA influence:
      importance 0 -> descriptive only, no GA penalty.
    """

    actual_subject = (
        str(subject.number)
        .strip()
        .upper()
    )

    preferred_blocks = (
        _subject_schedule_preference_blocks(
            preference,
            actual_subject
        )
    )

    if not preferred_blocks:
        return {
            "has_exact_blocks": False,
            "day_penalty": 0,
            "time_penalty": 0,
        }

    lecture_intervals = (
        _component_intervals(
            getattr(
                subject,
                "lecture_time_blocks",
                []
            )
        )
    )

    laboratory_intervals = (
        _component_intervals(
            getattr(
                subject,
                "laboratory_time_blocks",
                []
            )
        )
    )

    component_map = {
        "lecture": lecture_intervals,
        "laboratory": laboratory_intervals,
    }

    day_importance = _get_importance(
        preference,
        "day_importance",
        default=0
    )

    time_importance = _get_importance(
        preference,
        "time_importance",
        default=0
    )

    day_penalty = 0
    time_penalty = 0

    for preferred_block in preferred_blocks:

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

        actual_intervals = (
            component_map.get(
                component_name,
                []
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

        if (
            not day_match
            and day_importance > 0
        ):
            day_penalty += (
                settings.day_penalty
                * day_importance
                * priority_weight
            )

        if (
            not time_match
            and time_importance > 0
        ):
            time_penalty += (
                settings.time_penalty
                * time_importance
                * priority_weight
            )

    return {
        "has_exact_blocks": True,
        "day_penalty": day_penalty,
        "time_penalty": time_penalty,
    }


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

        "schedule_style": 0,

        "lecture_lab_preference": 0,

        "number_of_preparations": 0,

        "teaching_load_balance": 0,

        "daily_teaching_load": 0,
    }

    faculty_subjects = {}

    faculty_priority_weights = {}

    faculty_weekly_loads = {}

    # Keep the actual Faculty object for each faculty code so the
    # workload fitness can use that faculty member's own required
    # teaching load (after admin/research/extension adjustments).
    faculty_objects = {}

    faculty_daily_intervals = {}

    # One interval per lecture/laboratory component.
    # This is used for Compact/Scattered preference scoring.
    faculty_component_intervals = {}


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

                "preferred_schedule_blocks": [],

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

        faculty_objects[
            faculty_code
        ] = faculty

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

        exact_schedule_result = (
            _score_exact_subject_schedule_blocks(
                subject,
                preference,
                settings,
                priority_weight
            )
        )

        if exact_schedule_result[
            "has_exact_blocks"
        ]:

            breakdown[
                "day_preference"
            ] += exact_schedule_result[
                "day_penalty"
            ]

            breakdown[
                "time_preference"
            ] += exact_schedule_result[
                "time_penalty"
            ]

        # -----------------------------------------------
        # 1. SUBJECT PREFERENCE
        # -----------------------------------------------

        if preference.get(
            "use_subject_preference",
            False
        ):

            subject_importance = (
                _get_importance(
                    preference,
                    "subject_importance",
                    default=1
                )
            )

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
                subject_importance > 0
                and preferred_subjects
            ):

                if actual_subject in preferred_subjects:

                    rank_index = (
                        preferred_subjects.index(
                            actual_subject
                        )
                    )

                    # Priority 1 = zero ranking penalty.
                    # Lower-ranked preferred subjects receive
                    # gradually larger penalties, while still
                    # remaining better than an unlisted subject.
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

                else:

                    # Qualified but not listed as preferred.
                    rank_fraction = 1

                breakdown[
                    "subject_preference"
                ] += (

                    settings.subject_penalty

                    * rank_fraction

                    * subject_importance

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

            component_day_ranges = {}

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

                    current_range = (
                        component_day_ranges.get(
                            actual_day
                        )
                    )

                    if current_range is None:

                        component_day_ranges[
                            actual_day
                        ] = [
                            start_minutes,
                            end_minutes
                        ]

                    else:

                        current_range[0] = min(
                            current_range[0],
                            start_minutes
                        )

                        current_range[1] = max(
                            current_range[1],
                            end_minutes
                        )

                # ---------------------------------------
                # DASHBOARD TIME PREFERENCE
                # ---------------------------------------

                if (
                    not exact_schedule_result[
                        "has_exact_blocks"
                    ]
                    and preference.get(
                        "use_time_preference",
                        False
                    )
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

                    # If no dashboard time range is configured,
                    # do not fall back to the old Faculty TimeBlocks.
                    # Dashboard JSON is the authoritative preference source.
                    # Missing start/end times therefore mean there is no
                    # active time-range constraint to score.

            if component_time_mismatch:

                time_mismatch_count += 1

            for (
                component_day,
                component_range
            ) in component_day_ranges.items():

                faculty_component_intervals\
                    .setdefault(
                        faculty_code,
                        {}
                    )\
                    .setdefault(
                        component_day,
                        []
                    )\
                    .append(
                        (
                            component_range[0],
                            component_range[1]
                        )
                    )

        # -----------------------------------------------
        # 2. TIME PREFERENCE
        # -----------------------------------------------

        if (
            not exact_schedule_result[
                "has_exact_blocks"
            ]
            and preference.get(
                "use_time_preference",
                False
            )
        ):

            time_importance = (
                _get_importance(
                    preference,
                    "time_importance",
                    default=1
                )
            )

            breakdown[
                "time_preference"
            ] += (

                settings.time_penalty

                * time_mismatch_count

                * time_importance

                * priority_weight
            )

        # -----------------------------------------------
        # 3. DAY PREFERENCE
        # -----------------------------------------------

        if (
            not exact_schedule_result[
                "has_exact_blocks"
            ]
            and preference.get(
                "use_day_preference",
                False
            )
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

                day_importance = (
                    _get_importance(
                        preference,
                        "day_importance",
                        default=1
                    )
                )

                breakdown[
                    "day_preference"
                ] += (

                    settings.day_penalty

                    * day_importance

                    * priority_weight
                )
        # -----------------------------------------------
        # 4. LECTURE / LAB DAY PREFERENCE
        # -----------------------------------------------

        if preference.get(
            "use_lecture_lab_preference",
            False
        ):

            lecture_lab_importance = (
                _get_importance(
                    preference,
                    "lecture_lab_importance",
                    default=1
                )
            )

            lecture_lab_preference = (
                str(
                    preference.get(
                        "lecture_lab_preference",
                        "No Preference"
                    )
                )
                .strip()
                .lower()
            )

            lecture_days = (
                _days_from_blocks(
                    getattr(
                        subject,
                        "lecture_time_blocks",
                        []
                    )
                )
            )

            laboratory_days = (
                _days_from_blocks(
                    getattr(
                        subject,
                        "laboratory_time_blocks",
                        []
                    )
                )
            )

            if (
                lecture_lab_importance > 0
                and lecture_days
                and laboratory_days
            ):

                same_day = bool(
                    lecture_days
                    & laboratory_days
                )

                mismatch = False

                if (
                    lecture_lab_preference
                    == "same day"
                ):

                    mismatch = (
                        not same_day
                    )

                elif (
                    lecture_lab_preference
                    == "different day"
                ):

                    mismatch = (
                        same_day
                    )

                if mismatch:

                    lecture_lab_base_penalty = (
                        getattr(
                            settings,
                            "lecture_lab_penalty",
                            settings.day_penalty
                        )
                    )

                    breakdown[
                        "lecture_lab_preference"
                    ] += (

                        lecture_lab_base_penalty

                        * lecture_lab_importance

                        * priority_weight
                    )


    # =====================================================
    # 5. NUMBER OF PREPARATIONS
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
    # 6. FACULTY WORKLOAD
    # =====================================================
    #
    # LOWER PENALTY = BETTER.
    #
    # Each faculty member is evaluated against their own
    # ``required_teaching_load`` instead of one global
    # 12-unit target.
    #
    # Rules:
    #   * below required load -> underload penalty
    #   * exactly required load -> no workload penalty
    #   * above required load -> overload penalty
    #   * above overload warning threshold -> heavier penalty
    #   * absolute maximum remains a HARD scheduling rule and
    #     is enforced by the scheduler/validator, not optimized
    #     as a soft preference here.
    # =====================================================

    workload_step_units = max(
        1,
        int(
            getattr(
                settings,
                "workload_step_units",
                3
            )
        )
    )

    underload_penalty = int(
        getattr(
            settings,
            "underload_penalty",
            settings.load_balance_penalty
        )
    )

    overload_penalty = int(
        getattr(
            settings,
            "overload_penalty",
            settings.load_balance_penalty
        )
    )

    heavy_overload_penalty = int(
        getattr(
            settings,
            "heavy_overload_penalty",
            overload_penalty
        )
    )

    default_regular_load = int(
        getattr(
            settings,
            "regular_teaching_load",
            18
        )
    )

    default_warning_threshold = int(
        getattr(
            settings,
            "overload_warning_threshold",
            30
        )
    )

    for (
        faculty_code,
        actual_load
    ) in faculty_weekly_loads.items():

        faculty = faculty_objects.get(
            faculty_code
        )

        # Faculty.py now stores the faculty-specific teaching
        # requirement loaded from the admin/research/extension
        # workload source. Fall back safely for older objects.
        required_load = getattr(
            faculty,
            "required_teaching_load",
            getattr(
                faculty,
                "min_teaching_load",
                default_regular_load
            )
        )

        try:
            required_load = int(
                required_load
            )
        except (
            TypeError,
            ValueError
        ):
            required_load = (
                default_regular_load
            )

        required_load = max(
            0,
            required_load
        )

        warning_threshold = getattr(
            faculty,
            "overload_warning_threshold",
            default_warning_threshold
        )

        try:
            warning_threshold = int(
                warning_threshold
            )
        except (
            TypeError,
            ValueError
        ):
            warning_threshold = (
                default_warning_threshold
            )

        warning_threshold = max(
            required_load,
            warning_threshold
        )

        # -----------------------------------------------
        # UNDERLOAD
        # -----------------------------------------------

        if actual_load < required_load:

            deficit_units = (
                required_load
                - actual_load
            )

            underload_steps = math.ceil(
                deficit_units
                / workload_step_units
            )

            breakdown[
                "teaching_load_balance"
            ] += (
                underload_steps
                * underload_penalty
            )

            continue

        # -----------------------------------------------
        # NORMAL / OVERLOAD
        # -----------------------------------------------

        overload_units = max(
            0,
            min(
                actual_load,
                warning_threshold
            )
            - required_load
        )

        if overload_units > 0:

            overload_steps = math.ceil(
                overload_units
                / workload_step_units
            )

            breakdown[
                "teaching_load_balance"
            ] += (
                overload_steps
                * overload_penalty
            )

        # -----------------------------------------------
        # HEAVY OVERLOAD
        # -----------------------------------------------

        heavy_units = max(
            0,
            actual_load
            - warning_threshold
        )

        if heavy_units > 0:

            heavy_steps = math.ceil(
                heavy_units
                / workload_step_units
            )

            breakdown[
                "teaching_load_balance"
            ] += (
                heavy_steps
                * heavy_overload_penalty
            )


    # =====================================================
    # INTERVAL HELPER
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


    # =====================================================
    # 7. SCHEDULE STYLE (COMPACT / SCATTERED)
    # =====================================================

    for (
        faculty_code,
        day_map
    ) in faculty_component_intervals.items():

        preference = prefs.get(
            faculty_code,
            {}
        )

        if not preference.get(
            "use_gap_preference",
            False
        ):
            continue

        gap_importance = (
            _get_importance(
                preference,
                "gap_importance",
                default=1
            )
        )

        if gap_importance <= 0:
            continue

        gap_preference = (
            str(
                preference.get(
                    "gap_preference",
                    "No Preference"
                )
            )
            .strip()
            .lower()
        )

        if (
            gap_preference
            == "no preference"
        ):
            continue

        priority_weight = (
            faculty_priority_weights.get(
                faculty_code,
                1
            )
        )

        gap_base_penalty = (
            getattr(
                settings,
                "gap_penalty",
                settings.time_penalty
            )
        )

        for intervals in day_map.values():

            if len(intervals) < 2:
                continue

            ordered = sorted(
                intervals
            )

            gaps = []

            previous_end = (
                ordered[0][1]
            )

            for start, end in (
                ordered[1:]
            ):

                gap_minutes = max(
                    0,
                    start
                    - previous_end
                )

                gaps.append(
                    gap_minutes
                )

                previous_end = max(
                    previous_end,
                    end
                )

            if (
                gap_preference
                == "compact"
            ):

                # Every 30 minutes of idle time
                # between classes adds one step.
                total_gap_minutes = sum(
                    gaps
                )

                gap_steps = math.ceil(
                    total_gap_minutes
                    / 30
                )

                breakdown[
                    "schedule_style"
                ] += (

                    gap_steps

                    * gap_base_penalty

                    * gap_importance

                    * priority_weight
                )

            elif (
                gap_preference
                == "scattered"
            ):

                # Scattered does not reward huge gaps.
                # It only penalizes classes that are
                # immediately adjacent with no break.
                adjacent_count = sum(
                    1
                    for gap in gaps
                    if gap < 30
                )

                breakdown[
                    "schedule_style"
                ] += (

                    adjacent_count

                    * gap_base_penalty

                    * gap_importance

                    * priority_weight
                )


    # =====================================================
    # 8. DAILY TEACHING LOAD
    # =====================================================

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