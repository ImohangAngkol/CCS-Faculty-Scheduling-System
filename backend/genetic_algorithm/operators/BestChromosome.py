import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def compare_faculty_preferences(
    faculty_preferences_csv,
    best_chromosome_csv
):
    """
    Compare faculty preferences against the assignments
    in the best chromosome and visualize the results.

    Parameters
    ----------
    faculty_preferences_csv : str
        Path to Faculty_preferences.csv

    best_chromosome_csv : str
        Path to Best_chromosome.csv

    Returns
    -------
    df_comparison : DataFrame
        Detailed comparison for every assigned subject.

    df_summary : DataFrame
        Percentage satisfaction per faculty.

    df_overall : DataFrame
        Overall Subject, Day, Time and Day-Time match percentages.
    """

    # ============================================================
    # 1. LOAD CSV FILES
    # ============================================================

    df_pref = pd.read_csv(
        faculty_preferences_csv
    )

    df_best = pd.read_csv(
        best_chromosome_csv
    )


    # ============================================================
    # 2. REMOVE UNNAMED COLUMNS
    # ============================================================

    df_pref = df_pref.loc[
        :,
        ~df_pref.columns.str.startswith("Unnamed")
    ].copy()

    df_best = df_best.loc[
        :,
        ~df_best.columns.str.startswith("Unnamed")
    ].copy()


    # ============================================================
    # 3. NORMALIZE FACULTY CODE
    # ============================================================

    df_pref["Faculty_Code"] = pd.to_numeric(
        df_pref["Faculty_Code"],
        errors="coerce"
    ).astype("Int64")

    df_best["Faculty_Code"] = pd.to_numeric(
        df_best["Faculty_Code"],
        errors="coerce"
    ).astype("Int64")


    # ============================================================
    # HELPER FUNCTIONS
    # ============================================================

    def normalize_subject(value):

        if pd.isna(value):
            return None

        return (
            str(value)
            .strip()
            .upper()
        )


    def normalize_day(value):

        if pd.isna(value):
            return None

        return (
            str(value)
            .strip()
            .lower()
        )


    def time_to_minutes(value):

        try:

            hour, minute = map(
                int,
                str(value)
                .strip()
                .split(":")
            )

            return (
                hour * 60
                +
                minute
            )

        except Exception:

            return None


    def parse_schedule(schedule):

        if pd.isna(schedule):
            return None

        try:

            start, end = [
                x.strip()
                for x
                in str(schedule).split(
                    "-",
                    1
                )
            ]

            start_minutes = (
                time_to_minutes(start)
            )

            end_minutes = (
                time_to_minutes(end)
            )

            if (
                start_minutes is None
                or
                end_minutes is None
            ):
                return None

            return (
                start_minutes,
                end_minutes
            )

        except Exception:

            return None


    # ============================================================
    # 4. DETAILED COMPARISON
    # ============================================================

    comparison_rows = []


    for _, assigned in df_best.iterrows():

        faculty_code = (
            assigned[
                "Faculty_Code"
            ]
        )

        assigned_subject = (
            normalize_subject(
                assigned[
                    "Assigned Subjects"
                ]
            )
        )

        assigned_day = (
            normalize_day(
                assigned[
                    "Days"
                ]
            )
        )

        assigned_schedule = (
            assigned[
                "Assigned Schedule"
            ]
        )

        assigned_range = (
            parse_schedule(
                assigned_schedule
            )
        )


        # ========================================================
        # FACULTY PREFERENCE RECORDS
        # ========================================================

        faculty_pref = (
            df_pref[
                df_pref[
                    "Faculty_Code"
                ]
                ==
                faculty_code
            ]
            .copy()
        )


        # ========================================================
        # SUBJECT MATCH
        # ========================================================

        preferred_subjects = set(

            faculty_pref[
                "Preferred Subjects"
            ]

            .dropna()

            .apply(
                normalize_subject
            )
        )


        subject_match = (

            assigned_subject
            in
            preferred_subjects

        )


        # ========================================================
        # DAY MATCH
        # ========================================================

        preferred_days = set(

            faculty_pref[
                "Preferred Day(s)"
            ]

            .dropna()

            .apply(
                normalize_day
            )
        )


        day_match = (

            assigned_day
            in
            preferred_days

        )


        # ========================================================
        # TIME MATCH
        #
        # Time is matched independently of day.
        #
        # Preferred = 09:00-12:00
        # Assigned  = 09:30-11:30
        #
        # -> MATCH
        # ========================================================

        time_match = False


        if assigned_range is not None:

            assigned_start = (
                assigned_range[0]
            )

            assigned_end = (
                assigned_range[1]
            )


            for pref_schedule in (

                faculty_pref[
                    "PreferredSchedule"
                ]
                .dropna()

            ):

                pref_range = (
                    parse_schedule(
                        pref_schedule
                    )
                )

                if pref_range is None:
                    continue


                pref_start = (
                    pref_range[0]
                )

                pref_end = (
                    pref_range[1]
                )


                if (
                    assigned_start
                    >=
                    pref_start

                    and

                    assigned_end
                    <=
                    pref_end
                ):

                    time_match = True

                    break


        # ========================================================
        # DAY + TIME MATCH
        #
        # Assigned time must fall inside a preferred time
        # recorded for the SAME DAY.
        # ========================================================

        day_time_match = False


        if assigned_range is not None:

            assigned_start = (
                assigned_range[0]
            )

            assigned_end = (
                assigned_range[1]
            )


            for _, pref_row in (
                faculty_pref.iterrows()
            ):

                pref_day = (
                    normalize_day(
                        pref_row[
                            "Preferred Day(s)"
                        ]
                    )
                )


                pref_range = (
                    parse_schedule(
                        pref_row[
                            "PreferredSchedule"
                        ]
                    )
                )


                if pref_range is None:
                    continue


                if (
                    pref_day
                    !=
                    assigned_day
                ):
                    continue


                pref_start = (
                    pref_range[0]
                )

                pref_end = (
                    pref_range[1]
                )


                if (
                    assigned_start
                    >=
                    pref_start

                    and

                    assigned_end
                    <=
                    pref_end
                ):

                    day_time_match = True

                    break


        # ========================================================
        # FACULTY PRIORITY
        # ========================================================

        if not faculty_pref.empty:

            faculty_priority = (
                faculty_pref[
                    "Faculty_Prio"
                ]
                .iloc[0]
            )

        else:

            faculty_priority = np.nan


        # ========================================================
        # OVERALL ASSIGNMENT SCORE
        # ========================================================

        overall_match = (

            (
                int(subject_match)
                +
                int(day_match)
                +
                int(time_match)
            )

            / 3

            * 100
        )


        # ========================================================
        # SAVE
        # ========================================================

        comparison_rows.append(
            {
                "Faculty_Code":
                    faculty_code,

                "Faculty_Prio":
                    faculty_priority,

                "Assigned Subject":
                    assigned_subject,

                "Assigned Day":
                    assigned[
                        "Days"
                    ],

                "Assigned Schedule":
                    assigned_schedule,

                "Subject Match":
                    subject_match,

                "Day Match":
                    day_match,

                "Time Match":
                    time_match,

                "Day-Time Match":
                    day_time_match,

                "Overall Match (%)":
                    overall_match
            }
        )


    # ============================================================
    # 5. CREATE DETAILED DATAFRAME
    # ============================================================

    df_comparison = (
        pd.DataFrame(
            comparison_rows
        )
    )


    # ============================================================
    # 6. SUMMARY PER FACULTY
    # ============================================================

    df_summary = (

        df_comparison

        .groupby(
            [
                "Faculty_Code",
                "Faculty_Prio"
            ],
            dropna=False
        )

        .agg(

            Assignments=(
                "Assigned Subject",
                "count"
            ),

            Subject_Match=(
                "Subject Match",
                "mean"
            ),

            Day_Match=(
                "Day Match",
                "mean"
            ),

            Time_Match=(
                "Time Match",
                "mean"
            ),

            Day_Time_Match=(
                "Day-Time Match",
                "mean"
            )

        )

        .reset_index()
    )


    # ============================================================
    # 7. CONVERT TO %
    # ============================================================

    for column in [
        "Subject_Match",
        "Day_Match",
        "Time_Match",
        "Day_Time_Match"
    ]:

        df_summary[
            column
        ] = (

            df_summary[
                column
            ]

            * 100
        )


    # ============================================================
    # 8. OVERALL PER FACULTY
    # ============================================================

    df_summary[
        "Overall_Match"
    ] = (

        df_summary[
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
    # 9. SORT BY PRIORITY
    # ============================================================

    df_summary = (

        df_summary

        .sort_values(
            [
                "Faculty_Prio",
                "Faculty_Code"
            ]
        )

        .reset_index(
            drop=True
        )
    )


    # ============================================================
    # 10. OVERALL SUMMARY
    # ============================================================

    df_overall = pd.DataFrame(
        {
            "Preference": [
                "Subject",
                "Day",
                "Time",
                "Day + Time"
            ],

            "Match (%)": [

                df_comparison[
                    "Subject Match"
                ].mean() * 100,

                df_comparison[
                    "Day Match"
                ].mean() * 100,

                df_comparison[
                    "Time Match"
                ].mean() * 100,

                df_comparison[
                    "Day-Time Match"
                ].mean() * 100
            ]
        }
    )


    # ============================================================
    # DISPLAY TABLES
    # ============================================================

    # print(
    #     "\nDETAILED COMPARISON"
    # )

    # display(
    #     df_comparison
    # )


    # print(
    #     "\nFACULTY SUMMARY"
    # )

    # display(
    #     df_summary
    # )


    # print(
    #     "\nOVERALL SUMMARY"
    # )

    # display(
    # #     df_overall
    # # )


    # # ============================================================
    # # 11. FACULTY VISUALIZATION
    # # ============================================================

    # faculty_labels = [
    #     f"F{int(row['Faculty_Code'])}\nPriority {int(row['Faculty_Prio'])}"
    #     for _, row in df_summary.iterrows()
    # ]


    # x = np.arange(
    #     len(
    #         faculty_labels
    #     )
    # )


    # width = 0.24


    # fig, ax = plt.subplots(
    #     figsize=(16, 8)
    # )


    # # ------------------------------------------------------------
    # # SUBJECT
    # # ------------------------------------------------------------

    # subject_bars = ax.bar(

    #     x - width,

    #     df_summary[
    #         "Subject_Match"
    #     ],

    #     width,

    #     label="Subject"
    # )


    # # ------------------------------------------------------------
    # # DAY
    # # ------------------------------------------------------------

    # day_bars = ax.bar(

    #     x,

    #     df_summary[
    #         "Day_Match"
    #     ],

    #     width,

    #     label="Day"
    # )


    # # ------------------------------------------------------------
    # # TIME
    # # ------------------------------------------------------------

    # time_bars = ax.bar(

    #     x + width,

    #     df_summary[
    #         "Time_Match"
    #     ],

    #     width,

    #     label="Time"
    # )


    # # ------------------------------------------------------------
    # # OVERALL
    # # ------------------------------------------------------------

    # ax.plot(

    #     x,

    #     df_summary[
    #         "Overall_Match"
    #     ],

    #     marker="o",

    #     linewidth=2.5,

    #     label="Overall"
    # )


    # # ============================================================
    # # LABEL BARS
    # # ============================================================

    # for bars in [
    #     subject_bars,
    #     day_bars,
    #     time_bars
    # ]:

    #     for bar in bars:

    #         height = (
    #             bar.get_height()
    #         )

    #         ax.annotate(

    #             f"{height:.0f}%",

    #             xy=(
    #                 bar.get_x()
    #                 +
    #                 bar.get_width()
    #                 / 2,

    #                 height
    #             ),

    #             xytext=(
    #                 0,
    #                 3
    #             ),

    #             textcoords=(
    #                 "offset points"
    #             ),

    #             ha="center",

    #             va="bottom",

    #             fontsize=8
    #         )


    # # ============================================================
    # # FORMAT FACULTY CHART
    # # ============================================================

    # ax.set_title(
    #     "Faculty Preference Satisfaction vs Best Chromosome",
    #     fontsize=16,
    #     pad=20
    # )


    # ax.set_xlabel(
    #     "Faculty"
    # )


    # ax.set_ylabel(
    #     "Preference Match (%)"
    # )


    # ax.set_xticks(
    #     x
    # )


    # ax.set_xticklabels(
    #     faculty_labels,
    #     rotation=45,
    #     ha="right"
    # )


    # ax.set_ylim(
    #     0,
    #     110
    # )


    # ax.set_yticks(
    #     np.arange(
    #         0,
    #         101,
    #         10
    #     )
    # )


    # ax.grid(
    #     axis="y",
    #     alpha=0.2
    # )


    # ax.legend()


    # plt.tight_layout()

    # plt.show()


    # # ============================================================
    # # 12. OVERALL VISUALIZATION
    # # ============================================================

    # fig, ax = plt.subplots(
    #     figsize=(9, 6)
    # )


    # bars = ax.bar(

    #     df_overall[
    #         "Preference"
    #     ],

    #     df_overall[
    #         "Match (%)"
    #     ]
    # )


    # # Add %
    # for bar in bars:

    #     value = (
    #         bar.get_height()
    #     )

    #     ax.text(

    #         bar.get_x()
    #         +
    #         bar.get_width()
    #         / 2,

    #         value + 1,

    #         f"{value:.1f}%",

    #         ha="center"
    #     )


    # ax.set_title(
    #     "Overall Faculty Preference Satisfaction"
    # )


    # ax.set_ylabel(
    #     "Match (%)"
    # )


    # ax.set_ylim(
    #     0,
    #     110
    # )


    # ax.grid(
    #     axis="y",
    #     alpha=0.2
    # )


    # plt.tight_layout()

    # plt.show()


    # ============================================================
    # RETURN ALL RESULTS
    # ============================================================

    return (
        df_comparison,
        df_summary,
        df_overall
    )

def best_chromosome_to_dataframe(best_chromosome):

    # ONLY USE FIRST CHROMOSOME
    chromosome = best_chromosome

    rows = []

    day_names = {
        "M": "Monday",
        "T": "Tuesday",
        "W": "Wednesday",
        "TH": "Thursday",
        "F": "Friday",
        "S": "Saturday"
    }

    # =========================================================
    # COLLAPSE TIME BLOCKS
    # =========================================================
    def collapse_blocks(blocks):

        if not blocks:
            return []

        grouped = {}

        for entry in blocks:

            # Your schedule normally stores:
            # (day_code, TimeBlock)
            if isinstance(entry, tuple) and len(entry) == 2:

                day = str(entry[0]).strip().upper()
                block = entry[1]

            else:

                block = entry

                day = getattr(
                    block,
                    "day_code",
                    getattr(block, "day", None)
                )

                if day is None:
                    continue

                day = str(day).strip().upper()

            grouped.setdefault(
                day,
                []
            ).append(block)

        results = []

        for day, day_blocks in grouped.items():

            # Sort by start time
            day_blocks = sorted(
                day_blocks,
                key=lambda x: x.start_time
            )

            if not day_blocks:
                continue

            start = day_blocks[0].start_time
            end = day_blocks[0].end_time

            for block in day_blocks[1:]:

                # Consecutive block
                if block.start_time == end:

                    end = block.end_time

                else:

                    results.append(
                        (
                            day,
                            start,
                            end
                        )
                    )

                    start = block.start_time
                    end = block.end_time

            results.append(
                (
                    day,
                    start,
                    end
                )
            )

        return results


    # =========================================================
    # LOOP THROUGH SUBJECTS OF best_chromosome[0]
    # =========================================================

    for subject in chromosome:

        faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        if faculty is None:
            continue

        faculty_code = getattr(
            faculty,
            "code",
            None
        )

        faculty_priority = getattr(
            faculty,
            "seniority_level",
            None
        )

        subject_number = getattr(
            subject,
            "number",
            None
        )


        # =====================================================
        # LECTURE
        # =====================================================

        lecture_blocks = getattr(
            subject,
            "lecture_time_blocks",
            []
        ) or []

        lecture_schedules = collapse_blocks(
            lecture_blocks
        )

        for day, start, end in lecture_schedules:

            rows.append(
                {
                    "Faculty_Code":
                        faculty_code,

                    "Faculty_Priority":
                        faculty_priority,

                    "Assigned Schedule":
                        f"{start}-{end}",

                    "Assigned Subjects":
                        subject_number,

                    "Days":
                        day_names.get(
                            day,
                            day
                        )
                }
            )


        # =====================================================
        # LABORATORY
        # =====================================================

        laboratory_blocks = getattr(
            subject,
            "laboratory_time_blocks",
            []
        ) or []

        laboratory_schedules = collapse_blocks(
            laboratory_blocks
        )

        for day, start, end in laboratory_schedules:

            rows.append(
                {
                    "Faculty_Code":
                        faculty_code,

                    "Faculty_Priority":
                        faculty_priority,

                    "Assigned Schedule":
                        f"{start}-{end}",

                    "Assigned Subjects":
                        subject_number,

                    "Days":
                        day_names.get(
                            day,
                            day
                        )
                }
            )


    # =========================================================
    # CREATE DATAFRAME
    # =========================================================

    df = pd.DataFrame(
        rows,
        columns=[
            "Faculty_Code",
            "Faculty_Priority",
            "Assigned Schedule",
            "Assigned Subjects",
            "Days"
        ]
    )

    df = (
        df
        .sort_values(
            by=[
                "Faculty_Priority",
                "Faculty_Code",
                "Days",
                "Assigned Schedule"
            ]
        )
        .reset_index(drop=True)
    )

    return df