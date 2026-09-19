import math
import pandas as pd
from genetic_algorithm.models.Faculty import Faculty


def faculty_preference_fitness(
    chromosome,
    df_faculty_pref,
    subject_penalty=70,
    time_penalty=10,
    day_penalty=5,
    preparation_penalty=10,
    load_balance_penalty=10,
    daily_load_penalty=10,
    max_preparations=3,
    target_teaching_load=12,
    load_tolerance=3,
    max_daily_teaching_minutes=360,
    daily_load_step_minutes=60,
    return_breakdown=False,
):
    """
    Calculate chromosome fitness using SIX soft-constraint factors.

    LOWER FITNESS = BETTER.

    Factors
    -------
    1. Subject preference       -> default penalty = 40
    2. Time preference          -> default penalty = 5
    3. Day preference           -> default penalty = 4
    4. Number of preparations   -> default penalty = 40
    5. Teaching-load balance     -> default penalty = 10
    6. Daily teaching load       -> default penalty = 10 per excess step

    Notes
    -----
    - Faculty priority is retained from the original model.
      Priority 1 receives the largest priority weight.
    - A preparation is one UNIQUE subject number assigned to a faculty member.
      Multiple sections of the same subject count as one preparation.
    - Only preparations above max_preparations are penalized.
    - Hard constraints such as faculty, room, section, fixed-schedule,
      and minimum/maximum teaching-load violations should continue to be
      handled outside this fitness function.
    - Teaching-load balance and daily teaching load are soft constraints.
    - Faculty priority weights are applied only to preference/preparation
      penalties; workload-quality penalties are applied equally to faculty.
    """

    # ================================================================
    # 0. PREPARE FACULTY PREFERENCE DATA
    # ================================================================
    prefs = df_faculty_pref.copy()

    if isinstance(prefs.columns, pd.MultiIndex):
        prefs.columns = prefs.columns.get_level_values(0)

    prefs.columns = [str(column).strip() for column in prefs.columns]

    prefs["Faculty_Code"] = pd.to_numeric(
        prefs["Faculty_Code"],
        errors="coerce",
    ).astype("Int64")

    prefs["Faculty_Prio"] = pd.to_numeric(
        prefs["Faculty_Prio"],
        errors="coerce",
    )

    valid_priorities = prefs["Faculty_Prio"].dropna()
    max_priority = (
        valid_priorities.max()
        if not valid_priorities.empty
        else 1
    )

    day_code_to_name = {
        "M": "monday",
        "T": "tuesday",
        "W": "wednesday",
        "TH": "thursday",
        "F": "friday",
        "S": "saturday",
    }

    # Penalty contribution of each fitness factor.
    breakdown = {
        "subject_preference": 0,
        "time_preference": 0,
        "day_preference": 0,
        "number_of_preparations": 0,
        "teaching_load_balance": 0,
        "daily_teaching_load": 0,
    }

    # ================================================================
    # HELPER FUNCTIONS
    # ================================================================
    def priority_weight_for(faculty_code):
        """Return faculty-priority weight; Priority 1 receives the largest."""
        faculty_pref = prefs[
            prefs["Faculty_Code"] == faculty_code
        ]

        if faculty_pref.empty:
            return 1

        priority = faculty_pref["Faculty_Prio"].dropna()

        if priority.empty:
            return 1

        return int(
            max_priority
            - priority.iloc[0]
            + 1
        )

    def unpack_block(entry):
        """Return (normalized_day_name, TimeBlock)."""
        if isinstance(entry, tuple) and len(entry) == 2:
            day_value, block = entry
        else:
            block = entry
            day_value = getattr(
                block,
                "day_code",
                getattr(block, "day", None),
            )

        if day_value is None:
            return None, block

        day_text = str(day_value).strip()
        day_name = day_code_to_name.get(
            day_text.upper(),
            day_text.lower(),
        )

        return day_name, block

    def subject_components(subject):
        """
        Return lecture/laboratory components.
        Falls back to scheduled_time_blocks for older schedules.
        """
        components = [
            getattr(subject, "lecture_time_blocks", []) or [],
            getattr(subject, "laboratory_time_blocks", []) or [],
        ]

        if not any(components):
            scheduled = getattr(
                subject,
                "scheduled_time_blocks",
                None,
            )

            if scheduled:
                if isinstance(scheduled, list):
                    components = [scheduled]
                else:
                    components = [[scheduled]]

        return components

    # ================================================================
    # COLLECT UNIQUE SUBJECT PREPARATIONS PER FACULTY
    # ================================================================
    faculty_subjects = {}
    faculty_priority_weights = {}
    faculty_weekly_loads = {}
    faculty_daily_intervals = {}

    # ================================================================
    # 1-3. SUBJECT, TIME, AND DAY PREFERENCES
    # ================================================================
    for subject in chromosome:
        faculty = getattr(
            subject,
            "assigned_faculty",
            None,
        )

        if faculty is None:
            continue

        try:
            faculty_code = int(faculty.code)
        except (TypeError, ValueError):
            faculty_code = faculty.code

        priority_weight = priority_weight_for(
            faculty_code
        )

        faculty_priority_weights[
            faculty_code
        ] = priority_weight

        # Track weekly teaching load once per subject assignment.
        faculty_weekly_loads[faculty_code] = (
            faculty_weekly_loads.get(faculty_code, 0)
            + (getattr(subject, "credit_units", 0) or 0)
        )

        actual_subject = (
            str(subject.number)
            .strip()
            .upper()
        )

        # Record one preparation per UNIQUE subject number.
        faculty_subjects.setdefault(
            faculty_code,
            set(),
        ).add(actual_subject)

        faculty_pref = prefs[
            prefs["Faculty_Code"] == faculty_code
        ]

        # ------------------------------------------------------------
        # 1. SUBJECT PREFERENCE
        # ------------------------------------------------------------
        if not faculty_pref.empty:
            preferred_subjects = (
                faculty_pref["Preferred Subjects"]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
                .unique()
                .tolist()
            )

            if (
                preferred_subjects
                and actual_subject not in preferred_subjects
            ):
                breakdown[
                    "subject_preference"
                ] += (
                    subject_penalty
                    * priority_weight
                )

        # ------------------------------------------------------------
        # PREPARE PREFERRED DAYS
        # ------------------------------------------------------------
        preferred_days = set()

        if not faculty_pref.empty:
            for value in (
                faculty_pref["Preferred Day(s)"]
                .dropna()
                .tolist()
            ):
                preferred_days.update(
                    Faculty._normalize_days(value)
                )

        # ------------------------------------------------------------
        # GET ACTUAL DAYS AND CHECK TIME PREFERENCE
        # ------------------------------------------------------------
        all_actual_days = set()
        time_mismatch_count = 0

        faculty_day_map = faculty.get_day_map()

        for component_blocks in subject_components(subject):
            if not component_blocks:
                continue

            # One time penalty per lecture/laboratory component
            # when at least one block is outside preferred time.
            component_has_time_mismatch = False

            for entry in component_blocks:
                actual_day, block = unpack_block(entry)

                if actual_day is None:
                    continue

                all_actual_days.add(actual_day)

                actual_start = getattr(
                    block,
                    "start_time",
                    None,
                )

                actual_end = getattr(
                    block,
                    "end_time",
                    None,
                )

                # Track daily teaching intervals for workload analysis.
                try:
                    start_minutes = Faculty._time_to_minutes(actual_start)
                    end_minutes = Faculty._time_to_minutes(actual_end)
                except (TypeError, ValueError, AttributeError):
                    start_minutes = None
                    end_minutes = None

                if (
                    start_minutes is not None
                    and end_minutes is not None
                    and end_minutes > start_minutes
                ):
                    faculty_daily_intervals.setdefault(
                        faculty_code, {}
                    ).setdefault(
                        actual_day, []
                    ).append(
                        (start_minutes, end_minutes)
                    )

                matching_preferred = False

                for pref_block in faculty_day_map.get(
                    actual_day,
                    [],
                ):
                    if (
                        str(pref_block.start_time)
                        == str(actual_start)
                        and str(pref_block.end_time)
                        == str(actual_end)
                        and pref_block.preferred
                    ):
                        matching_preferred = True
                        break

                if not matching_preferred:
                    component_has_time_mismatch = True

            if component_has_time_mismatch:
                time_mismatch_count += 1

        # ------------------------------------------------------------
        # 2. TIME PREFERENCE
        # ------------------------------------------------------------
        breakdown["time_preference"] += (
            time_penalty
            * time_mismatch_count
            * priority_weight
        )

        # ------------------------------------------------------------
        # 3. DAY PREFERENCE
        # One penalty per subject if any scheduled day is not preferred.
        # ------------------------------------------------------------
        if preferred_days and all_actual_days:
            if not all_actual_days.issubset(
                preferred_days
            ):
                breakdown[
                    "day_preference"
                ] += (
                    day_penalty
                    * priority_weight
                )

    # ================================================================
    # 4. NUMBER OF PREPARATIONS
    # ================================================================
    # Example:
    #   CCC121 - Section A
    #   CCC121 - Section B
    # counts as ONE preparation.
    #
    # If max_preparations = 3:
    #   3 preparations -> no penalty
    #   4 preparations -> 1 preparation penalty
    #   5 preparations -> 2 preparation penalties
    # ================================================================
    for faculty_code, subjects in faculty_subjects.items():
        number_of_preparations = len(subjects)

        excess_preparations = max(
            0,
            number_of_preparations
            - max_preparations,
        )

        if excess_preparations > 0:
            priority_weight = (
                faculty_priority_weights.get(
                    faculty_code,
                    1,
                )
            )

            breakdown[
                "number_of_preparations"
            ] += (
                preparation_penalty
                * excess_preparations
                * priority_weight
            )

    # ================================================================
    # 5. TEACHING-LOAD BALANCE
    # ================================================================
    # Faculty within +/- load_tolerance units of target_teaching_load
    # receive no penalty. Each additional load_tolerance-sized step away
    # from the acceptable band adds load_balance_penalty.
    #
    # Example with target=12 and tolerance=3:
    #   9-15 units -> no penalty
    #   6 or 18    -> 10 penalty
    # ================================================================
    tolerance = max(0, load_tolerance)
    step_units = tolerance if tolerance > 0 else 1

    for faculty_code, actual_load in faculty_weekly_loads.items():
        difference = abs(actual_load - target_teaching_load)
        excess_difference = max(0, difference - tolerance)

        if excess_difference > 0:
            load_steps = math.ceil(excess_difference / step_units)
            breakdown["teaching_load_balance"] += (
                load_steps * load_balance_penalty
            )

    # ================================================================
    # 6. DAILY TEACHING LOAD
    # ================================================================
    # Merge overlapping/contiguous teaching intervals first so lecture/lab
    # blocks that represent one continuous class are not double-counted.
    # A penalty is added for each daily_load_step_minutes beyond the
    # maximum desirable daily teaching duration.
    # ================================================================
    def merge_intervals(intervals):
        if not intervals:
            return []

        sorted_intervals = sorted(intervals)
        merged = [list(sorted_intervals[0])]

        for start, end in sorted_intervals[1:]:
            if start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])

        return [(start, end) for start, end in merged]

    daily_step = max(1, daily_load_step_minutes)

    for faculty_code, day_map in faculty_daily_intervals.items():
        for day, intervals in day_map.items():
            merged_intervals = merge_intervals(intervals)
            total_daily_minutes = sum(
                end - start
                for start, end in merged_intervals
            )

            excess_minutes = max(
                0,
                total_daily_minutes - max_daily_teaching_minutes,
            )

            if excess_minutes > 0:
                excess_steps = math.ceil(
                    excess_minutes / daily_step
                )
                breakdown["daily_teaching_load"] += (
                    excess_steps * daily_load_penalty
                )

    # ================================================================
    # FINAL FITNESS
    # ================================================================
    total_penalty = sum(
        breakdown.values()
    )

    if return_breakdown:
        return total_penalty, breakdown

    return total_penalty
