import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


# ================================================================
# MAIN ANALYSIS FUNCTION
# ================================================================

def analyze_faculty_preferences(
    best_chromosome,
    df_faculty_pref
):
    """
    Compare faculty preferences with the actual assignments
    in the best chromosome.

    Compares:
        1. Preferred Subject
        2. Preferred Day
        3. Preferred Time

    Returns:
        detail_df
        summary_df
    """

    # ============================================================
    # COPY DATAFRAME
    # ============================================================

    prefs = df_faculty_pref.copy()

    # ============================================================
    # FIX MULTIINDEX COLUMNS IF PRESENT
    # ============================================================

    if isinstance(
        prefs.columns,
        pd.MultiIndex
    ):

        prefs.columns = (
            prefs.columns
            .get_level_values(0)
        )

    # ============================================================
    # CLEAN COLUMN NAMES
    # ============================================================

    prefs.columns = [
        str(column).strip()
        for column in prefs.columns
    ]

    print("\nDetected columns:")
    print(
        prefs.columns.tolist()
    )

    # ============================================================
    # FIND COLUMN NAMES SAFELY
    # ============================================================

    def normalize_column_name(name):

        return (
            str(name)
            .strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
        )

    column_lookup = {

        normalize_column_name(column):
            column

        for column
        in prefs.columns
    }

    def find_column(*names):

        for name in names:

            normalized = (
                normalize_column_name(
                    name
                )
            )

            if normalized in column_lookup:

                return (
                    column_lookup[
                        normalized
                    ]
                )

        raise KeyError(
            f"Could not find any of these columns: "
            f"{names}\n"
            f"Available columns: "
            f"{prefs.columns.tolist()}"
        )

    faculty_code_col = (
        find_column(
            "Faculty_Code",
            "Faculty Code",
            "FacultyCode"
        )
    )

    faculty_priority_col = (
        find_column(
            "Faculty_Prio",
            "Faculty Priority",
            "FacultyPrio"
        )
    )

    subject_pref_col = (
        find_column(
            "Preferred Subjects",
            "PreferredSubjects",
            "Subject"
        )
    )

    day_pref_col = (
        find_column(
            "Preferred Day(s)",
            "Preferred Days",
            "Day(s)"
        )
    )

    schedule_pref_col = (
        find_column(
            "PreferredSchedule",
            "Preferred Schedule",
            "New Schedule"
        )
    )

    # ============================================================
    # NORMALIZE FACULTY CODE
    # ============================================================

    prefs[
        faculty_code_col
    ] = pd.to_numeric(
        prefs[
            faculty_code_col
        ],
        errors="coerce"
    )

    # Nullable integer
    prefs[
        faculty_code_col
    ] = (
        prefs[
            faculty_code_col
        ]
        .astype("Int64")
    )

    # ============================================================
    # DAY CODE MAPPING
    # ============================================================

    day_code_to_name = {

        "M":
            "monday",

        "T":
            "tuesday",

        "W":
            "wednesday",

        "TH":
            "thursday",

        "F":
            "friday",

        "S":
            "saturday"
    }

    # ============================================================
    # NORMALIZE DAY
    # ============================================================

    def normalize_day(
        day_value
    ):

        if (
            day_value is None
            or pd.isna(
                day_value
            )
        ):

            return None

        text = (
            str(day_value)
            .strip()
        )

        # If already full day name
        lower_text = (
            text.lower()
        )

        full_days = {

            "monday":
                "monday",

            "tuesday":
                "tuesday",

            "wednesday":
                "wednesday",

            "thursday":
                "thursday",

            "friday":
                "friday",

            "saturday":
                "saturday"
        }

        if (
            lower_text
            in full_days
        ):

            return (
                full_days[
                    lower_text
                ]
            )

        # Handle abbreviated codes
        return (
            day_code_to_name
            .get(
                text.upper(),
                lower_text
            )
        )

    # ============================================================
    # TIME -> MINUTES
    # ============================================================

    def time_to_minutes(
        time_value
    ):

        if (
            time_value is None
        ):

            return None

        text = (
            str(time_value)
            .strip()
        )

        try:

            hour, minute = (
                text.split(":")
            )

            hour = int(hour)

            minute = int(minute)

            return (
                hour * 60
                +
                minute
            )

        except Exception:

            return None

    # ============================================================
    # NORMALIZE TIME
    # ============================================================

    def normalize_time(
        time_value
    ):

        minutes = (
            time_to_minutes(
                time_value
            )
        )

        if (
            minutes is None
        ):

            return None

        hour = (
            minutes // 60
        )

        minute = (
            minutes % 60
        )

        return (
            f"{hour:02d}:"
            f"{minute:02d}"
        )

    # ============================================================
    # PARSE PREFERRED SCHEDULE
    # ============================================================

    def parse_schedule(
        schedule
    ):

        if (
            schedule is None
            or pd.isna(
                schedule
            )
        ):

            return (
                None,
                None
            )

        schedule = (
            str(schedule)
            .strip()
        )

        try:

            start_text, end_text = [

                value.strip()

                for value
                in schedule.split(
                    "-",
                    maxsplit=1
                )
            ]

            start_time = (
                normalize_time(
                    start_text
                )
            )

            end_time = (
                normalize_time(
                    end_text
                )
            )

            return (
                start_time,
                end_time
            )

        except Exception:

            return (
                None,
                None
            )

    # ============================================================
    # UNPACK TIME BLOCK
    # ============================================================

    def unpack_block(
        entry
    ):

        if (
            isinstance(
                entry,
                tuple
            )
            and
            len(entry) == 2
        ):

            day_value = (
                entry[0]
            )

            block = (
                entry[1]
            )

        else:

            block = entry

            day_value = (
                getattr(
                    block,
                    "day_code",
                    getattr(
                        block,
                        "day",
                        None
                    )
                )
            )

        day_name = (
            normalize_day(
                day_value
            )
        )

        return (
            day_name,
            block
        )

    # ============================================================
    # DEBUG: CHECK CHROMOSOME FACULTY CODES
    # ============================================================

    chromosome_codes = set()

    for subject in best_chromosome:

        faculty = (
            getattr(
                subject,
                "assigned_faculty",
                None
            )
        )

        if (
            faculty is None
        ):

            continue

        try:

            code = int(
                float(
                    faculty.code
                )
            )

        except Exception:

            code = (
                faculty.code
            )

        chromosome_codes.add(
            code
        )

    preference_codes = set(

        prefs[
            faculty_code_col
        ]
        .dropna()
        .astype(int)
        .tolist()
    )

    print(
        "\nChromosome faculty codes:"
    )

    print(
        sorted(
            chromosome_codes,
            key=str
        )
    )

    print(
        "\nPreference faculty codes:"
    )

    print(
        sorted(
            preference_codes,
            key=str
        )
    )

    print(
        "\nMatching faculty codes:"
    )

    matching_codes = (
        chromosome_codes
        &
        preference_codes
    )

    print(
        sorted(
            matching_codes,
            key=str
        )
    )

    print(
        "\nMissing faculty codes:"
    )

    print(
        sorted(
            chromosome_codes
            -
            preference_codes,
            key=str
        )
    )

    # ============================================================
    # STORE RESULTS
    # ============================================================

    rows = []

    # ============================================================
    # LOOP THROUGH SUBJECTS
    # ============================================================

    for subject in best_chromosome:

        faculty = (
            getattr(
                subject,
                "assigned_faculty",
                None
            )
        )

        if (
            faculty is None
        ):

            continue

        # ========================================================
        # FACULTY CODE
        # ========================================================

        try:

            faculty_code = (
                int(
                    float(
                        faculty.code
                    )
                )
            )

        except Exception:

            faculty_code = (
                faculty.code
            )

        # ========================================================
        # GET PREFERENCE RECORDS
        # ========================================================

        faculty_pref = (

            prefs[

                prefs[
                    faculty_code_col
                ]

                ==

                faculty_code
            ]
        )

        if (
            faculty_pref.empty
        ):

            print(
                f"WARNING: "
                f"Faculty {faculty_code} "
                f"not found in preference "
                f"data."
            )

            continue

        # ========================================================
        # FACULTY PRIORITY
        # ========================================================

        faculty_priority = (

            faculty_pref[
                faculty_priority_col
            ]
            .iloc[0]
        )

        # ========================================================
        # SUBJECT PREFERENCE
        # ========================================================

        preferred_subjects = (

            faculty_pref[
                subject_pref_col
            ]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .unique()
            .tolist()
        )

        actual_subject = (

            str(
                subject.number
            )
            .strip()
            .upper()
        )

        subject_match = (

            actual_subject
            in
            preferred_subjects
        )

        # ========================================================
        # PREFERRED DAY-TIME PAIRS
        # ========================================================

        preferred_pairs = []

        for _, pref_row in (
            faculty_pref.iterrows()
        ):

            preferred_day = (
                normalize_day(
                    pref_row[
                        day_pref_col
                    ]
                )
            )

            preferred_start, preferred_end = (
                parse_schedule(
                    pref_row[
                        schedule_pref_col
                    ]
                )
            )

            if (
                preferred_day
                is not None

                and

                preferred_start
                is not None

                and

                preferred_end
                is not None
            ):

                preferred_pairs.append(
                    (
                        preferred_day,
                        preferred_start,
                        preferred_end
                    )
                )

        preferred_days = {

            pair[0]

            for pair
            in preferred_pairs
        }

        # ========================================================
        # ACTUAL SCHEDULE
        # ========================================================

        lecture_blocks = (

            getattr(
                subject,
                "lecture_time_blocks",
                []
            )

            or []
        )

        laboratory_blocks = (

            getattr(
                subject,
                "laboratory_time_blocks",
                []
            )

            or []
        )

        # Fallback
        if (
            not lecture_blocks
            and
            not laboratory_blocks
        ):

            scheduled = (
                getattr(
                    subject,
                    "scheduled_time_blocks",
                    None
                )
            )

            if (
                scheduled
            ):

                if isinstance(
                    scheduled,
                    list
                ):

                    lecture_blocks = (
                        scheduled
                    )

                else:

                    lecture_blocks = [
                        scheduled
                    ]

        # ========================================================
        # ACTUAL DAYS
        # ========================================================

        actual_days = set()

        actual_schedule_strings = []

        all_actual_blocks = (

            lecture_blocks
            +
            laboratory_blocks
        )

        for entry in (
            all_actual_blocks
        ):

            actual_day, block = (
                unpack_block(
                    entry
                )
            )

            if (
                actual_day
                is not None
            ):

                actual_days.add(
                    actual_day
                )

        # ========================================================
        # DAY MATCH
        # ========================================================

        if (
            preferred_days
            and
            actual_days
        ):

            day_match = (

                actual_days
                .issubset(
                    preferred_days
                )
            )

        else:

            day_match = False

        # ========================================================
        # TIME MATCH
        # ========================================================

        total_time_blocks = 0

        matching_time_blocks = 0

        for entry in (
            all_actual_blocks
        ):

            actual_day, block = (
                unpack_block(
                    entry
                )
            )

            if (
                actual_day
                is None
            ):

                continue

            actual_start = (
                normalize_time(
                    getattr(
                        block,
                        "start_time",
                        None
                    )
                )
            )

            actual_end = (
                normalize_time(
                    getattr(
                        block,
                        "end_time",
                        None
                    )
                )
            )

            if (
                actual_start
                is None
                or
                actual_end
                is None
            ):

                continue

            total_time_blocks += 1

            actual_schedule_strings.append(
                f"{actual_day.capitalize()} "
                f"{actual_start}-"
                f"{actual_end}"
            )

            actual_start_minutes = (
                time_to_minutes(
                    actual_start
                )
            )

            actual_end_minutes = (
                time_to_minutes(
                    actual_end
                )
            )

            block_match = False

            # ----------------------------------------------------
            # Match actual time against preference
            # for SAME DAY
            # ----------------------------------------------------

            for (
                pref_day,
                pref_start,
                pref_end
            ) in preferred_pairs:

                if (
                    pref_day
                    !=
                    actual_day
                ):

                    continue

                pref_start_minutes = (
                    time_to_minutes(
                        pref_start
                    )
                )

                pref_end_minutes = (
                    time_to_minutes(
                        pref_end
                    )
                )

                if (
                    actual_start_minutes
                    >=
                    pref_start_minutes

                    and

                    actual_end_minutes
                    <=
                    pref_end_minutes
                ):

                    block_match = True

                    break

            if (
                block_match
            ):

                matching_time_blocks += 1

        # ========================================================
        # TIME SCORE
        # ========================================================

        if (
            total_time_blocks
            > 0
        ):

            time_match_score = (

                matching_time_blocks
                /
                total_time_blocks
            )

            time_match = (

                matching_time_blocks
                ==
                total_time_blocks
            )

        else:

            time_match_score = 0

            time_match = False

        # ========================================================
        # SECTION
        # ========================================================

        section = (
            getattr(
                subject,
                "section",
                None
            )
        )

        section_code = (
            getattr(
                section,
                "code",
                ""
            )
        )

        # ========================================================
        # PREFERRED SCHEDULE TEXT
        # ========================================================

        preferred_schedule_text = []

        for (
            pref_day,
            pref_start,
            pref_end
        ) in preferred_pairs:

            preferred_schedule_text.append(

                f"{pref_day.capitalize()} "
                f"{pref_start}-"
                f"{pref_end}"
            )

        # ========================================================
        # APPEND RESULT
        # ========================================================

        rows.append(
            {

                "Faculty_Code":
                    faculty_code,

                "Faculty_Priority":
                    faculty_priority,

                "Subject":
                    subject.number,

                "Section":
                    section_code,

                "Subject_Match":
                    subject_match,

                "Day_Match":
                    day_match,

                "Time_Match":
                    time_match,

                "Time_Match_Score":
                    time_match_score,

                "Preferred_Subjects":
                    ", ".join(
                        preferred_subjects
                    ),

                "Preferred_Days":
                    ", ".join(
                        sorted(
                            day.capitalize()
                            for day
                            in preferred_days
                        )
                    ),

                "Preferred_Schedules":
                    "; ".join(
                        preferred_schedule_text
                    ),

                "Actual_Days":
                    ", ".join(
                        sorted(
                            day.capitalize()
                            for day
                            in actual_days
                        )
                    ),

                "Actual_Schedule":
                    "; ".join(
                        actual_schedule_strings
                    )
            }
        )

    # ============================================================
    # CREATE DETAIL DATAFRAME
    # ============================================================

    detail_df = (
        pd.DataFrame(
            rows
        )
    )

    # ============================================================
    # CHECK IF EMPTY
    # ============================================================

    if (
        detail_df.empty
    ):

        print(
            "\nNo comparison records "
            "were created."
        )

        print(
            "Check assigned_faculty "
            "inside the chromosome."
        )

        return (
            detail_df,
            pd.DataFrame()
        )

    # ============================================================
    # CREATE FACULTY SUMMARY
    # ============================================================

    summary_df = (

        detail_df

        .groupby(
            [
                "Faculty_Code",
                "Faculty_Priority"
            ]
        )

        .agg(

            Subjects_Assigned=(
                "Subject",
                "count"
            ),

            Subject_Match=(
                "Subject_Match",
                "mean"
            ),

            Day_Match=(
                "Day_Match",
                "mean"
            ),

            Time_Match=(
                "Time_Match_Score",
                "mean"
            )
        )

        .reset_index()
    )

    # ============================================================
    # CONVERT TO PERCENTAGE
    # ============================================================

    summary_df[
        "Subject_Match"
    ] = (

        summary_df[
            "Subject_Match"
        ]

        * 100
    )

    summary_df[
        "Day_Match"
    ] = (

        summary_df[
            "Day_Match"
        ]

        * 100
    )

    summary_df[
        "Time_Match"
    ] = (

        summary_df[
            "Time_Match"
        ]

        * 100
    )

    # ============================================================
    # OVERALL MATCH
    # ============================================================

    summary_df[
        "Overall_Match"
    ] = (

        summary_df[
            [
                "Subject_Match",
                "Day_Match",
                "Time_Match"
            ]
        ]

        .mean(
            axis=1
        )
    )

    # ============================================================
    # SORT BY FACULTY PRIORITY
    # ============================================================

    summary_df = (

        summary_df

        .sort_values(
            [
                "Faculty_Priority",
                "Faculty_Code"
            ]
        )

        .reset_index(
            drop=True
        )
    )

    return (
        detail_df,
        summary_df
    )


# ================================================================
# VISUALIZATION FUNCTION
# ================================================================

def visualize_faculty_preferences(
    best_chromosome,
    df_faculty_pref,
    figsize=(16, 9)
):

    # ============================================================
    # ANALYZE
    # ============================================================

    detail_df, summary_df = (
        analyze_faculty_preferences(
            best_chromosome,
            df_faculty_pref
        )
    )

    if (
        summary_df.empty
    ):

        print(
            "\nCannot create visualization "
            "because summary is empty."
        )

        return (
            detail_df,
            summary_df
        )

    # ============================================================
    # LABELS
    # ============================================================

    faculty_labels = [

        f"Faculty {row['Faculty_Code']}\n"
        f"P{int(row['Faculty_Priority'])}"

        for _, row
        in summary_df.iterrows()
    ]

    x = np.arange(
        len(
            faculty_labels
        )
    )

    width = 0.23

    # ============================================================
    # FIGURE
    # ============================================================

    fig, ax = (
        plt.subplots(
            figsize=figsize
        )
    )

    # ============================================================
    # SUBJECT BAR
    # ============================================================

    subject_bars = (
        ax.bar(

            x - width,

            summary_df[
                "Subject_Match"
            ],

            width,

            label=(
                "Subject Preference"
            )
        )
    )

    # ============================================================
    # DAY BAR
    # ============================================================

    day_bars = (
        ax.bar(

            x,

            summary_df[
                "Day_Match"
            ],

            width,

            label=(
                "Day Preference"
            )
        )
    )

    # ============================================================
    # TIME BAR
    # ============================================================

    time_bars = (
        ax.bar(

            x + width,

            summary_df[
                "Time_Match"
            ],

            width,

            label=(
                "Time Preference"
            )
        )
    )

    # ============================================================
    # OVERALL LINE
    # ============================================================

    ax.plot(

        x,

        summary_df[
            "Overall_Match"
        ],

        marker="o",

        linewidth=2.5,

        label=(
            "Overall Match"
        )
    )

    # ============================================================
    # ADD BAR LABELS
    # ============================================================

    for bars in [

        subject_bars,
        day_bars,
        time_bars

    ]:

        for bar in bars:

            height = (
                bar.get_height()
            )

            ax.annotate(

                f"{height:.0f}%",

                xy=(
                    bar.get_x()
                    +
                    bar.get_width()
                    / 2,

                    height
                ),

                xytext=(
                    0,
                    3
                ),

                textcoords=(
                    "offset points"
                ),

                ha="center",

                va="bottom",

                fontsize=8
            )

    # ============================================================
    # OVERALL LABELS
    # ============================================================

    for index, value in (
        enumerate(
            summary_df[
                "Overall_Match"
            ]
        )
    ):

        ax.annotate(

            f"{value:.1f}%",

            xy=(
                x[index],
                value
            ),

            xytext=(
                0,
                10
            ),

            textcoords=(
                "offset points"
            ),

            ha="center",

            fontsize=9
        )

    # ============================================================
    # FORMAT
    # ============================================================

    ax.set_title(

        "Faculty Preference Satisfaction "
        "of Best Chromosome\n"
        "Subject, Day, and Time Preferences",

        fontsize=16,

        pad=20
    )

    ax.set_xlabel(
        "Faculty"
    )

    ax.set_ylabel(
        "Preference Satisfaction (%)"
    )

    ax.set_xticks(
        x
    )

    ax.set_xticklabels(

        faculty_labels,

        rotation=45,

        ha="right"
    )

    ax.set_ylim(
        0,
        115
    )

    ax.set_yticks(
        np.arange(
            0,
            101,
            10
        )
    )

    ax.axhline(

        100,

        linestyle="--",

        alpha=0.3
    )

    ax.grid(

        axis="y",

        alpha=0.25
    )

    ax.legend(
        loc="best"
    )

    plt.tight_layout()

    plt.show()

    return (
        detail_df,
        summary_df
    )


# ================================================================
# OPTIONAL: DISPLAY DETAILED COMPARISON
# ================================================================

def display_faculty_preference_details(
    detail_df
):

    if (
        detail_df.empty
    ):

        print(
            "No preference comparison "
            "data available."
        )

        return

    columns = [

        "Faculty_Code",
        "Faculty_Priority",
        "Subject",
        "Section",
        "Subject_Match",
        "Day_Match",
        "Time_Match",
        "Preferred_Subjects",
        "Preferred_Days",
        "Preferred_Schedules",
        "Actual_Days",
        "Actual_Schedule"

    ]

    return (
        detail_df[
            columns
        ]
        .sort_values(
            [
                "Faculty_Priority",
                "Faculty_Code",
                "Subject",
                "Section"
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ================================================================
# OPTIONAL: PRINT FACULTY SUMMARY
# ================================================================

def display_faculty_preference_summary(
    summary_df
):

    if (
        summary_df.empty
    ):

        print(
            "No faculty summary "
            "available."
        )

        return

    result = (
        summary_df.copy()
    )

    for column in [

        "Subject_Match",
        "Day_Match",
        "Time_Match",
        "Overall_Match"

    ]:

        result[column] = (

            result[column]

            .round(2)
        )

    return result