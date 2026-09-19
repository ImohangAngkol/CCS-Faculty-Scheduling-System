
"""
FacultySelectedChromosomeDashboard.py

Visual dashboard for ONE selected chromosome.

Displays:
1. Subject preference satisfaction (%)
2. Day preference satisfaction (%)
3. Time preference satisfaction (%)
4. Number of preparations per faculty
5. Teaching-load distribution / balance
6. Daily teaching load per faculty
7. Faculty summary table

IMPORTANT
---------
The CURRENT fitness function uses only:
    Subject Preference      = 40
    Time Preference         = 5
    Day Preference          = 4
    Number of Preparations  = 7

Teaching-load balance and daily teaching load are shown only as
DIAGNOSTIC / INTERPRETIVE measures. They do NOT affect chromosome fitness.

Lower fitness = better chromosome.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness

DAY_ORDER = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
]

DAY_SHORT = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
}

DAY_CODE_TO_NAME = {
    "M": "monday",
    "T": "tuesday",
    "W": "wednesday",
    "TH": "thursday",
    "F": "friday",
    "S": "saturday",
}


# =====================================================================
# HELPERS
# =====================================================================

def _normalize_day(day_value):
    if day_value is None:
        return None

    text = str(day_value).strip()
    return DAY_CODE_TO_NAME.get(
        text.upper(),
        text.lower(),
    )


def _time_to_minutes(value):
    if value is None:
        return None

    try:
        hour, minute = map(
            int,
            str(value).strip().split(":")
        )
        return hour * 60 + minute
    except (TypeError, ValueError):
        return None


def _unpack_block(entry):
    """
    Accept either:
        (day_code, TimeBlock)
    or:
        TimeBlock
    """
    if isinstance(entry, tuple) and len(entry) == 2:
        day_value, block = entry
    else:
        block = entry
        day_value = getattr(
            block,
            "day_code",
            getattr(block, "day", None),
        )

    return _normalize_day(day_value), block


def _subject_components(subject):
    """
    Return lecture and laboratory schedule components.
    Falls back to scheduled_time_blocks for older chromosomes.
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


def _merge_intervals(intervals):
    """
    Merge overlapping/adjacent intervals.
    Useful so that 08:00-08:30 and 08:30-09:00
    become one continuous 08:00-09:00 interval.
    """
    if not intervals:
        return []

    intervals = sorted(intervals)
    merged = [list(intervals[0])]

    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(
                merged[-1][1],
                end,
            )
        else:
            merged.append([start, end])

    return [
        (start, end)
        for start, end in merged
    ]


# =====================================================================
# ANALYSIS
# =====================================================================

def analyze_selected_chromosome(
    chromosome,
    df_faculty_pref,
    subject_penalty=40,
    time_penalty=10,
    day_penalty=4,
    preparation_penalty=7,
    max_preparations=3,
):
    """
    Analyze one chromosome and return:

    faculty_df
        One row per faculty.

    daily_df
        Daily teaching-hours matrix.

    chromosome_summary
        Overall fitness and fitness-component totals.

    Notes
    -----
    Subject/Day/Time satisfaction are descriptive percentages.

    Preparation penalty follows the CURRENT fitness function:
        excess preparations above max_preparations
        x preparation_penalty
        x faculty priority weight

    Teaching load and daily load are displayed only for interpretation.
    """

    prefs = df_faculty_pref.copy()

    if isinstance(prefs.columns, pd.MultiIndex):
        prefs.columns = prefs.columns.get_level_values(0)

    prefs.columns = [
        str(column).strip()
        for column in prefs.columns
    ]

    prefs["Faculty_Code"] = pd.to_numeric(
        prefs["Faculty_Code"],
        errors="coerce",
    ).astype("Int64")

    prefs["Faculty_Prio"] = pd.to_numeric(
        prefs["Faculty_Prio"],
        errors="coerce",
    )

    priorities = prefs["Faculty_Prio"].dropna()
    max_priority = (
        priorities.max()
        if not priorities.empty
        else 1
    )

    def priority_weight_for(code):
        rows = prefs[
            prefs["Faculty_Code"] == code
        ]

        if rows.empty:
            return 1

        values = rows[
            "Faculty_Prio"
        ].dropna()

        if values.empty:
            return 1

        return int(
            max_priority
            - values.iloc[0]
            + 1
        )

    # ---------------------------------------------------------
    # Create faculty records
    # ---------------------------------------------------------
    stats = {}

    # Include faculty from preference file, even if no assignment.
    for code in prefs[
        "Faculty_Code"
    ].dropna().unique():

        code = int(code)

        faculty_rows = prefs[
            prefs["Faculty_Code"] == code
        ]

        prio = faculty_rows[
            "Faculty_Prio"
        ].dropna()

        stats[code] = {
            "Faculty_Code": code,
            "Faculty_Priority": (
                int(prio.iloc[0])
                if not prio.empty
                else np.nan
            ),
            "Priority_Weight": priority_weight_for(code),

            "faculty": None,
            "subjects": set(),
            "teaching_load": 0.0,

            "subject_total": 0,
            "subject_match": 0,

            "day_total": 0,
            "day_match": 0,

            "time_total": 0,
            "time_match": 0,

            "subject_penalty": 0.0,
            "day_penalty": 0.0,
            "time_penalty": 0.0,
            "preparation_penalty": 0.0,

            "daily_intervals": {
                day: []
                for day in DAY_ORDER
            },
        }

    # ---------------------------------------------------------
    # Examine every scheduled subject
    # ---------------------------------------------------------
    for subject in chromosome:

        faculty = getattr(
            subject,
            "assigned_faculty",
            None,
        )

        if faculty is None:
            continue

        try:
            code = int(faculty.code)
        except (TypeError, ValueError):
            code = faculty.code

        if code not in stats:
            stats[code] = {
                "Faculty_Code": code,
                "Faculty_Priority": np.nan,
                "Priority_Weight": priority_weight_for(code),
                "faculty": faculty,
                "subjects": set(),
                "teaching_load": 0.0,
                "subject_total": 0,
                "subject_match": 0,
                "day_total": 0,
                "day_match": 0,
                "time_total": 0,
                "time_match": 0,
                "subject_penalty": 0.0,
                "day_penalty": 0.0,
                "time_penalty": 0.0,
                "preparation_penalty": 0.0,
                "daily_intervals": {
                    day: []
                    for day in DAY_ORDER
                },
            }

        s = stats[code]
        s["faculty"] = faculty

        priority_weight = s[
            "Priority_Weight"
        ]

        # -----------------------------------------------------
        # Teaching load = credit units
        # -----------------------------------------------------
        units = (
            getattr(
                subject,
                "credit_units",
                0,
            )
            or 0
        )

        s["teaching_load"] += float(units)

        # -----------------------------------------------------
        # Unique subject preparation
        # -----------------------------------------------------
        actual_subject = (
            str(subject.number)
            .strip()
            .upper()
        )

        s["subjects"].add(
            actual_subject
        )

        faculty_pref = prefs[
            prefs["Faculty_Code"] == code
        ]

        # =====================================================
        # 1. SUBJECT PREFERENCE
        # =====================================================
        preferred_subjects = []

        if not faculty_pref.empty:
            preferred_subjects = (
                faculty_pref[
                    "Preferred Subjects"
                ]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
                .unique()
                .tolist()
            )

        s["subject_total"] += 1

        # If no preference was supplied, do not penalize it
        # and count it as satisfied.
        if (
            not preferred_subjects
            or actual_subject in preferred_subjects
        ):
            s["subject_match"] += 1

        else:
            s["subject_penalty"] += (
                subject_penalty
                * priority_weight
            )

        # =====================================================
        # Preferred days
        # =====================================================
        preferred_days = set()

        if not faculty_pref.empty:
            for value in (
                faculty_pref[
                    "Preferred Day(s)"
                ]
                .dropna()
                .tolist()
            ):
                preferred_days.update(
                    Faculty._normalize_days(
                        value
                    )
                )

        # =====================================================
        # 2. TIME PREFERENCE
        # 3. DAY PREFERENCE
        # =====================================================
        actual_days = set()

        faculty_day_map = (
            faculty.get_day_map()
            if hasattr(
                faculty,
                "get_day_map",
            )
            else {}
        )

        for component in _subject_components(
            subject
        ):
            if not component:
                continue

            s["time_total"] += 1

            component_is_preferred = True

            for entry in component:

                actual_day, block = (
                    _unpack_block(entry)
                )

                if actual_day is None:
                    continue

                actual_days.add(
                    actual_day
                )

                start_time = getattr(
                    block,
                    "start_time",
                    None,
                )

                end_time = getattr(
                    block,
                    "end_time",
                    None,
                )

                start_min = _time_to_minutes(
                    start_time
                )

                end_min = _time_to_minutes(
                    end_time
                )

                # Store actual teaching interval
                if (
                    actual_day in DAY_ORDER
                    and start_min is not None
                    and end_min is not None
                    and end_min > start_min
                ):
                    s[
                        "daily_intervals"
                    ][
                        actual_day
                    ].append(
                        (
                            start_min,
                            end_min,
                        )
                    )

                matching_preferred = False

                for pref_block in (
                    faculty_day_map.get(
                        actual_day,
                        [],
                    )
                ):
                    if (
                        str(
                            pref_block.start_time
                        )
                        ==
                        str(start_time)
                        and
                        str(
                            pref_block.end_time
                        )
                        ==
                        str(end_time)
                        and
                        pref_block.preferred
                    ):
                        matching_preferred = True
                        break

                if not matching_preferred:
                    component_is_preferred = False

            if component_is_preferred:
                s["time_match"] += 1

            else:
                s["time_penalty"] += (
                    time_penalty
                    * priority_weight
                )

        # One day result per subject
        if actual_days:
            s["day_total"] += 1

            if (
                not preferred_days
                or actual_days.issubset(
                    preferred_days
                )
            ):
                s["day_match"] += 1

            else:
                s["day_penalty"] += (
                    day_penalty
                    * priority_weight
                )

    # ---------------------------------------------------------
    # 4. NUMBER OF PREPARATIONS
    # ---------------------------------------------------------
    for s in stats.values():

        preparations = len(
            s["subjects"]
        )

        excess = max(
            0,
            preparations
            - max_preparations,
        )

        s[
            "preparation_penalty"
        ] = (
            preparation_penalty
            * excess
            * s["Priority_Weight"]
        )

    # ---------------------------------------------------------
    # Convert stats -> faculty dataframe
    # ---------------------------------------------------------
    rows = []
    daily_rows = []

    for code, s in stats.items():

        subject_pct = (
            100
            * s["subject_match"]
            / s["subject_total"]
            if s["subject_total"]
            else np.nan
        )

        day_pct = (
            100
            * s["day_match"]
            / s["day_total"]
            if s["day_total"]
            else np.nan
        )

        time_pct = (
            100
            * s["time_match"]
            / s["time_total"]
            if s["time_total"]
            else np.nan
        )

        preparation_count = len(
            s["subjects"]
        )

        total_penalty = (
            s["subject_penalty"]
            + s["day_penalty"]
            + s["time_penalty"]
            + s["preparation_penalty"]
        )

        row = {
            "Faculty_Code": code,
            "Faculty_Priority": s[
                "Faculty_Priority"
            ],
            "Priority_Weight": s[
                "Priority_Weight"
            ],
            "Subject_Satisfaction": subject_pct,
            "Day_Satisfaction": day_pct,
            "Time_Satisfaction": time_pct,
            "Preparations": preparation_count,
            "Teaching_Load": s[
                "teaching_load"
            ],
            "Subject_Penalty": s[
                "subject_penalty"
            ],
            "Day_Penalty": s[
                "day_penalty"
            ],
            "Time_Penalty": s[
                "time_penalty"
            ],
            "Preparation_Penalty": s[
                "preparation_penalty"
            ],
            "Total_Penalty": total_penalty,
        }

        rows.append(row)

        daily_row = {
            "Faculty_Code": code
        }

        for day in DAY_ORDER:

            merged = _merge_intervals(
                s[
                    "daily_intervals"
                ][day]
            )

            total_minutes = sum(
                end - start
                for start, end
                in merged
            )

            daily_row[
                DAY_SHORT[day]
            ] = (
                total_minutes
                / 60.0
            )

        daily_rows.append(
            daily_row
        )

    faculty_df = pd.DataFrame(
        rows
    )

    daily_df = pd.DataFrame(
        daily_rows
    )

    if not faculty_df.empty:

        faculty_df = (
            faculty_df
            .sort_values(
                [
                    "Faculty_Priority",
                    "Faculty_Code",
                ],
                na_position="last",
            )
            .reset_index(
                drop=True
            )
        )

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

    # ---------------------------------------------------------
    # Descriptive teaching-load balance
    # ---------------------------------------------------------
    average_load = (
        faculty_df[
            "Teaching_Load"
        ].mean()
        if not faculty_df.empty
        else 0
    )

    faculty_df[
        "Load_Deviation"
    ] = (
        faculty_df[
            "Teaching_Load"
        ]
        - average_load
    )

    faculty_df[
        "Absolute_Load_Deviation"
    ] = (
        faculty_df[
            "Load_Deviation"
        ]
        .abs()
    )

    # ---------------------------------------------------------
    # Confirm actual chromosome fitness using current file
    # ---------------------------------------------------------
    total_fitness, fitness_breakdown = (
        faculty_preference_fitness(
            chromosome,
            df_faculty_pref,
            subject_penalty=subject_penalty,
            time_penalty=time_penalty,
            day_penalty=day_penalty,
            preparation_penalty=preparation_penalty,
            max_preparations=max_preparations,
            return_breakdown=True,
        )
    )

    chromosome_summary = {
        "Total_Fitness": total_fitness,
        "Subject_Penalty": fitness_breakdown[
            "subject_preference"
        ],
        "Time_Penalty": fitness_breakdown[
            "time_preference"
        ],
        "Day_Penalty": fitness_breakdown[
            "day_preference"
        ],
        "Preparation_Penalty": fitness_breakdown[
            "number_of_preparations"
        ],
        "Average_Teaching_Load": average_load,
    }

    return (
        faculty_df,
        daily_df,
        chromosome_summary,
    )


# =====================================================================
# DASHBOARD
# =====================================================================

def visualize_selected_chromosome_dashboard(
    chromosome,
    df_faculty_pref,
    chromosome_name="Selected Chromosome",
    subject_penalty=40,
    time_penalty=5,
    day_penalty=4,
    preparation_penalty=7,
    max_preparations=3,
    figsize=(22, 14),
    save_path=None,
):
    """
    Create an Image-1-style dashboard for one selected chromosome.

    Returns
    -------
    faculty_df
    daily_df
    chromosome_summary
    figure

    Example
    -------
    faculty_df, daily_df, summary, fig = (
        visualize_selected_chromosome_dashboard(
            best_chromosome,
            df_faculty_pref,
            chromosome_name="Best Chromosome"
        )
    )
    """

    (
        faculty_df,
        daily_df,
        summary,
    ) = analyze_selected_chromosome(
        chromosome,
        df_faculty_pref,
        subject_penalty=subject_penalty,
        time_penalty=time_penalty,
        day_penalty=day_penalty,
        preparation_penalty=preparation_penalty,
        max_preparations=max_preparations,
    )

    if faculty_df.empty:
        raise ValueError(
            "No faculty assignments were found "
            "for the selected chromosome."
        )

    # Faculty labels sorted by priority
    labels = []

    for _, row in (
        faculty_df.iterrows()
    ):
        priority = (
            "?"
            if pd.isna(
                row["Faculty_Priority"]
            )
            else int(
                row["Faculty_Priority"]
            )
        )

        labels.append(
            f"F{int(row['Faculty_Code'])}\n"
            f"P{priority}"
        )

    x = np.arange(
        len(faculty_df)
    )

    # ---------------------------------------------------------
    # One large dashboard figure
    # ---------------------------------------------------------
    fig = plt.figure(
        figsize=figsize,
        constrained_layout=True,
    )

    grid = fig.add_gridspec(
        nrows=5,
        ncols=12,
        height_ratios=[
            0.70,
            2.7,
            2.7,
            2.7,
            2.0,
        ],
    )

    # =========================================================
    # HEADER
    # =========================================================
    ax_header = fig.add_subplot(
        grid[0, :]
    )

    ax_header.axis("off")

    ax_header.text(
        0.5,
        0.72,
        (
            "Faculty Performance Analysis — "
            f"{chromosome_name}"
        ),
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
    )

    ax_header.text(
        0.5,
        0.25,
        (
            "Fitness Parameters: "
            f"Subject ({subject_penalty})  |  "
            f"Time ({time_penalty})  |  "
            f"Day ({day_penalty})  |  "
            f"Preparations ({preparation_penalty})"
        ),
        ha="center",
        va="center",
        fontsize=12,
    )

    # =========================================================
    # 1. SUBJECT SATISFACTION
    # =========================================================
    ax_subject = fig.add_subplot(
        grid[1, 0:4]
    )

    subject_values = (
        faculty_df[
            "Subject_Satisfaction"
        ]
        .fillna(0)
    )

    bars = ax_subject.bar(
        x,
        subject_values,
    )

    ax_subject.set_title(
        "1. Subject Preference Satisfaction",
        fontweight="bold",
    )

    ax_subject.set_ylabel(
        "Match (%)"
    )

    ax_subject.set_ylim(
        0,
        110,
    )

    ax_subject.set_xticks(
        x
    )

    ax_subject.set_xticklabels(
        labels
    )

    ax_subject.grid(
        axis="y",
        alpha=0.20,
    )

    for bar, value in zip(
        bars,
        subject_values,
    ):
        ax_subject.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 2,
            f"{value:.0f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # =========================================================
    # 2. DAY SATISFACTION
    # =========================================================
    ax_day = fig.add_subplot(
        grid[1, 4:8]
    )

    day_values = (
        faculty_df[
            "Day_Satisfaction"
        ]
        .fillna(0)
    )

    bars = ax_day.bar(
        x,
        day_values,
    )

    ax_day.set_title(
        "2. Day Preference Satisfaction",
        fontweight="bold",
    )

    ax_day.set_ylabel(
        "Match (%)"
    )

    ax_day.set_ylim(
        0,
        110,
    )

    ax_day.set_xticks(
        x
    )

    ax_day.set_xticklabels(
        labels
    )

    ax_day.grid(
        axis="y",
        alpha=0.20,
    )

    for bar, value in zip(
        bars,
        day_values,
    ):
        ax_day.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 2,
            f"{value:.0f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # =========================================================
    # 3. TIME SATISFACTION
    # =========================================================
    ax_time = fig.add_subplot(
        grid[1, 8:12]
    )

    time_values = (
        faculty_df[
            "Time_Satisfaction"
        ]
        .fillna(0)
    )

    bars = ax_time.bar(
        x,
        time_values,
    )

    ax_time.set_title(
        "3. Time Preference Satisfaction",
        fontweight="bold",
    )

    ax_time.set_ylabel(
        "Match (%)"
    )

    ax_time.set_ylim(
        0,
        110,
    )

    ax_time.set_xticks(
        x
    )

    ax_time.set_xticklabels(
        labels
    )

    ax_time.grid(
        axis="y",
        alpha=0.20,
    )

    for bar, value in zip(
        bars,
        time_values,
    ):
        ax_time.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 2,
            f"{value:.0f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # =========================================================
    # 4. PREPARATIONS
    # =========================================================
    ax_prep = fig.add_subplot(
        grid[2, 0:4]
    )

    preparations = faculty_df[
        "Preparations"
    ]

    bars = ax_prep.bar(
        x,
        preparations,
    )

    ax_prep.axhline(
        max_preparations,
        linestyle="--",
        linewidth=1.5,
        label=(
            "Maximum without penalty "
            f"({max_preparations})"
        ),
    )

    ax_prep.set_title(
        "4. Number of Preparations per Faculty",
        fontweight="bold",
    )

    ax_prep.set_ylabel(
        "Unique Subjects"
    )

    ax_prep.set_xticks(
        x
    )

    ax_prep.set_xticklabels(
        labels
    )

    ax_prep.grid(
        axis="y",
        alpha=0.20,
    )

    ax_prep.legend(
        fontsize=8
    )

    for bar, value in zip(
        bars,
        preparations,
    ):
        ax_prep.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 0.08,
            f"{int(value)}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # =========================================================
    # 5. TEACHING LOAD DISTRIBUTION
    # =========================================================
    ax_load = fig.add_subplot(
        grid[2, 4:8]
    )

    loads = faculty_df[
        "Teaching_Load"
    ]

    average_load = summary[
        "Average_Teaching_Load"
    ]

    bars = ax_load.bar(
        x,
        loads,
        label="Assigned teaching load",
    )

    ax_load.axhline(
        average_load,
        linestyle="--",
        linewidth=1.5,
        label=(
            "Average load "
            f"({average_load:.2f})"
        ),
    )

    ax_load.set_title(
        "5. Teaching Load Distribution (Diagnostic)",
        fontweight="bold",
    )

    ax_load.set_ylabel(
        "Credit Units"
    )

    ax_load.set_xticks(
        x
    )

    ax_load.set_xticklabels(
        labels
    )

    ax_load.grid(
        axis="y",
        alpha=0.20,
    )

    ax_load.legend(
        fontsize=8
    )

    for bar, value in zip(
        bars,
        loads,
    ):
        ax_load.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + 0.15,
            f"{value:g}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # =========================================================
    # 6. LOAD BALANCE DISTRIBUTION
    # =========================================================
    ax_balance = fig.add_subplot(
        grid[2, 8:12]
    )

    deviations = faculty_df[
        "Load_Deviation"
    ]

    bars = ax_balance.bar(
        x,
        deviations,
    )

    ax_balance.axhline(
        0,
        linewidth=1.3,
    )

    ax_balance.set_title(
        "6. Load Balance vs. Faculty Average",
        fontweight="bold",
    )

    ax_balance.set_ylabel(
        "Deviation from Average (Units)"
    )

    ax_balance.set_xticks(
        x
    )

    ax_balance.set_xticklabels(
        labels
    )

    ax_balance.grid(
        axis="y",
        alpha=0.20,
    )

    for bar, value in zip(
        bars,
        deviations,
    ):
        offset = (
            0.12
            if value >= 0
            else -0.35
        )

        ax_balance.text(
            bar.get_x()
            + bar.get_width() / 2,
            value + offset,
            f"{value:+.1f}",
            ha="center",
            fontsize=8,
        )

    # =========================================================
    # 7. DAILY LOAD DISTRIBUTION
    # =========================================================
    ax_daily = fig.add_subplot(
        grid[3, 0:12]
    )

    bottom = np.zeros(
        len(daily_df)
    )

    for day in [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
    ]:
        values = (
            daily_df[day]
            .fillna(0)
            .to_numpy()
        )

        ax_daily.bar(
            x,
            values,
            bottom=bottom,
            label=day,
        )

        bottom = (
            bottom
            + values
        )

    ax_daily.set_title(
        "7. Daily Teaching Load per Faculty",
        fontweight="bold",
    )

    ax_daily.set_ylabel(
        "Scheduled Teaching Hours"
    )

    ax_daily.set_xlabel(
        "Faculty"
    )

    ax_daily.set_xticks(
        x
    )

    ax_daily.set_xticklabels(
        labels
    )

    ax_daily.grid(
        axis="y",
        alpha=0.20,
    )

    ax_daily.legend(
        ncol=6,
        loc="upper center",
        bbox_to_anchor=(
            0.5,
            1.12,
        ),
        fontsize=8,
    )

    # Total weekly scheduled hours
    for index, total in enumerate(
        bottom
    ):
        ax_daily.text(
            index,
            total + 0.10,
            f"{total:.1f}h",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    # =========================================================
    # 8. SUMMARY TABLE
    # =========================================================
    ax_table = fig.add_subplot(
        grid[4, 0:9]
    )

    ax_table.axis("off")

    table_df = faculty_df[
        [
            "Faculty_Code",
            "Faculty_Priority",
            "Subject_Satisfaction",
            "Day_Satisfaction",
            "Time_Satisfaction",
            "Preparations",
            "Teaching_Load",
            "Load_Deviation",
            "Total_Penalty",
        ]
    ].copy()

    table_df.columns = [
        "Faculty",
        "Priority",
        "Subject %",
        "Day %",
        "Time %",
        "Prep.",
        "Load",
        "Load Δ",
        "Fitness\nPenalty",
    ]

    table_values = []

    for _, row in (
        table_df.iterrows()
    ):
        table_values.append(
            [
                f"F{int(row['Faculty'])}",
                (
                    "?"
                    if pd.isna(
                        row["Priority"]
                    )
                    else int(
                        row["Priority"]
                    )
                ),
                (
                    "-"
                    if pd.isna(
                        row["Subject %"]
                    )
                    else f"{row['Subject %']:.0f}%"
                ),
                (
                    "-"
                    if pd.isna(
                        row["Day %"]
                    )
                    else f"{row['Day %']:.0f}%"
                ),
                (
                    "-"
                    if pd.isna(
                        row["Time %"]
                    )
                    else f"{row['Time %']:.0f}%"
                ),
                int(
                    row["Prep."]
                ),
                f"{row['Load']:.1f}",
                f"{row['Load Δ']:+.1f}",
                f"{row['Fitness\nPenalty']:.0f}",
            ]
        )

    table = ax_table.table(
        cellText=table_values,
        colLabels=table_df.columns,
        cellLoc="center",
        loc="center",
    )

    table.auto_set_font_size(
        False
    )

    table.set_fontsize(
        8
    )

    table.scale(
        1,
        1.35,
    )

    ax_table.set_title(
        "Faculty Summary — Selected Chromosome",
        fontweight="bold",
        loc="left",
    )

    # =========================================================
    # 9. CHROMOSOME SUMMARY
    # =========================================================
    ax_summary = fig.add_subplot(
        grid[4, 9:12]
    )

    ax_summary.axis("off")

    summary_text = (
        f"TOTAL FITNESS\n"
        f"{summary['Total_Fitness']:.0f}\n\n"
        f"Fitness Penalties\n"
        f"Subject: {summary['Subject_Penalty']:.0f}\n"
        f"Time: {summary['Time_Penalty']:.0f}\n"
        f"Day: {summary['Day_Penalty']:.0f}\n"
        f"Preparations: {summary['Preparation_Penalty']:.0f}\n\n"
        f"Average Teaching Load\n"
        f"{summary['Average_Teaching_Load']:.2f} units\n\n"
        f"Lower fitness is better.\n"
        f"Load balance and daily load\n"
        f"are diagnostics only."
    )

    ax_summary.text(
        0.05,
        0.95,
        summary_text,
        va="top",
        ha="left",
        fontsize=11,
        linespacing=1.35,
    )

    # ---------------------------------------------------------
    # Save optional copy
    # ---------------------------------------------------------
    if save_path is not None:
        fig.savefig(
            save_path,
            dpi=300,
            bbox_inches="tight",
        )

    plt.show()

    return (
        faculty_df,
        daily_df,
        summary,
        fig,
    )


# =====================================================================
# OPTIONAL COMPACT TABLE
# =====================================================================

def display_faculty_dashboard_summary(
    faculty_df
):
    """
    Return a compact dataframe suitable for Jupyter display.
    """

    columns = [
        "Faculty_Code",
        "Faculty_Priority",
        "Subject_Satisfaction",
        "Day_Satisfaction",
        "Time_Satisfaction",
        "Preparations",
        "Teaching_Load",
        "Load_Deviation",
        "Subject_Penalty",
        "Day_Penalty",
        "Time_Penalty",
        "Preparation_Penalty",
        "Total_Penalty",
    ]

    result = faculty_df[
        columns
    ].copy()

    numeric_columns = [
        "Subject_Satisfaction",
        "Day_Satisfaction",
        "Time_Satisfaction",
        "Teaching_Load",
        "Load_Deviation",
        "Subject_Penalty",
        "Day_Penalty",
        "Time_Penalty",
        "Preparation_Penalty",
        "Total_Penalty",
    ]

    for column in numeric_columns:
        result[column] = (
            result[column]
            .round(2)
        )

    return result
