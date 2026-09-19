
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness


FACTOR_LABELS = {
    "subject_preference": "Subject\nPreference",
    "time_preference": "Time\nPreference",
    "day_preference": "Day\nPreference",
    "teaching_load_balance": "Teaching-Load\nBalance",
    "number_of_preparations": "Number of\nPreparations",
    "schedule_gaps": "Schedule\nGaps",
    "consecutive_teaching": "Consecutive\nTeaching",
}


def analyze_faculty_fitness(
    chromosome,
    df_faculty_pref,
    subject_penalty=40,
    time_penalty=5,
    day_penalty=4,
    load_balance_penalty=10,
    preparation_penalty=7,
    gap_penalty=3,
    consecutive_penalty=5,
    load_tolerance_units=3,
    load_step_units=3,
    max_preparations=3,
    gap_threshold_minutes=60,
    max_consecutive_minutes=180,
    consecutive_step_minutes=30,
):
    """
    Analyze the BEST CHROMOSOME using the same seven factors used by
    faculty_preference_fitness().

    LOWER PENALTY = BETTER.

    Returns
    -------
    result_df : one row per faculty
    factor_penalty_df : faculty x seven fitness-factor penalty matrix
    """
    prefs = df_faculty_pref.copy()

    if isinstance(prefs.columns, pd.MultiIndex):
        prefs.columns = prefs.columns.get_level_values(0)

    prefs.columns = [str(c).strip() for c in prefs.columns]

    prefs["Faculty_Code"] = pd.to_numeric(
        prefs["Faculty_Code"], errors="coerce"
    ).astype("Int64")
    prefs["Faculty_Prio"] = pd.to_numeric(
        prefs["Faculty_Prio"], errors="coerce"
    )

    valid_priorities = prefs["Faculty_Prio"].dropna()
    max_priority = valid_priorities.max() if not valid_priorities.empty else 1

    day_code_to_name = {
        "M": "monday", "T": "tuesday", "W": "wednesday",
        "TH": "thursday", "F": "friday", "S": "saturday",
    }

    def priority_weight_for(code):
        f = prefs[prefs["Faculty_Code"] == code]
        if f.empty:
            return 1
        p = f["Faculty_Prio"].dropna()
        if p.empty:
            return 1
        return int(max_priority - p.iloc[0] + 1)

    def unpack_block(entry):
        if isinstance(entry, tuple) and len(entry) == 2:
            day_value, block = entry
        else:
            block = entry
            day_value = getattr(block, "day_code", getattr(block, "day", None))
        if day_value is None:
            return None, block
        text = str(day_value).strip()
        return day_code_to_name.get(text.upper(), text.lower()), block

    def time_to_minutes(value):
        try:
            h, m = map(int, str(value).strip().split(":"))
            return h * 60 + m
        except Exception:
            return None

    def components(subject):
        result = [
            getattr(subject, "lecture_time_blocks", []) or [],
            getattr(subject, "laboratory_time_blocks", []) or [],
        ]
        if not any(result):
            old = getattr(subject, "scheduled_time_blocks", None)
            if old:
                result = [old if isinstance(old, list) else [old]]
        return result

    def merge_intervals(intervals):
        if not intervals:
            return []
        intervals = sorted(intervals)
        merged = [list(intervals[0])]
        for start, end in intervals[1:]:
            if start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        return [(s, e) for s, e in merged]

    stats = {}
    for code in prefs["Faculty_Code"].dropna().unique():
        code = int(code)
        frows = prefs[prefs["Faculty_Code"] == code]
        priority = frows["Faculty_Prio"].dropna()
        stats[code] = {
            "Faculty_Code": code,
            "Faculty_Priority": int(priority.iloc[0]) if not priority.empty else np.nan,
            "Priority_Weight": priority_weight_for(code),
            "faculty": None,
            "load": 0.0,
            "subjects": set(),
            "intervals": {},
            "subject_total": 0,
            "subject_match": 0,
            "day_total": 0,
            "day_match": 0,
            "time_component_total": 0,
            "time_component_match": 0,
            "subject_preference": 0,
            "time_preference": 0,
            "day_preference": 0,
            "teaching_load_balance": 0,
            "number_of_preparations": 0,
            "schedule_gaps": 0,
            "consecutive_teaching": 0,
            "gap_count": 0,
            "gap_minutes": 0,
            "max_consecutive_minutes": 0,
        }

    for subject in chromosome:
        faculty = getattr(subject, "assigned_faculty", None)
        if faculty is None:
            continue

        code = int(faculty.code)
        if code not in stats:
            stats[code] = {
                "Faculty_Code": code, "Faculty_Priority": np.nan,
                "Priority_Weight": priority_weight_for(code),
                "faculty": faculty, "load": 0.0, "subjects": set(),
                "intervals": {}, "subject_total": 0, "subject_match": 0,
                "day_total": 0, "day_match": 0,
                "time_component_total": 0, "time_component_match": 0,
                "subject_preference": 0, "time_preference": 0,
                "day_preference": 0, "teaching_load_balance": 0,
                "number_of_preparations": 0, "schedule_gaps": 0,
                "consecutive_teaching": 0, "gap_count": 0,
                "gap_minutes": 0, "max_consecutive_minutes": 0,
            }

        s = stats[code]
        s["faculty"] = faculty
        weight = s["Priority_Weight"]

        units = getattr(subject, "credit_units", 0) or 0
        s["load"] += float(units)
        actual_subject = str(subject.number).strip().upper()
        s["subjects"].add(actual_subject)

        frows = prefs[prefs["Faculty_Code"] == code]

        # 1) Subject preference
        preferred_subjects = (
            frows["Preferred Subjects"].dropna().astype(str)
            .str.strip().str.upper().tolist()
            if not frows.empty else []
        )
        s["subject_total"] += 1
        if not preferred_subjects or actual_subject in preferred_subjects:
            s["subject_match"] += 1
        elif actual_subject not in preferred_subjects:
            s["subject_preference"] += subject_penalty * weight

        # Preferred days
        preferred_days = set()
        if not frows.empty:
            for value in frows["Preferred Day(s)"].dropna().tolist():
                preferred_days.update(Faculty._normalize_days(value))

        actual_days = set()
        time_mismatch_count = 0

        faculty_day_map = faculty.get_day_map()

        for comp in components(subject):
            if not comp:
                continue

            s["time_component_total"] += 1
            component_mismatch = False

            for entry in comp:
                day, block = unpack_block(entry)
                if day is None:
                    continue

                actual_days.add(day)
                start = getattr(block, "start_time", None)
                end = getattr(block, "end_time", None)

                sm = time_to_minutes(start)
                em = time_to_minutes(end)
                if sm is not None and em is not None and em > sm:
                    s["intervals"].setdefault(day, []).append((sm, em))

                preferred = False
                for pblock in faculty_day_map.get(day, []):
                    if (
                        str(pblock.start_time) == str(start)
                        and str(pblock.end_time) == str(end)
                        and pblock.preferred
                    ):
                        preferred = True
                        break

                if not preferred:
                    component_mismatch = True

            if component_mismatch:
                time_mismatch_count += 1
            else:
                s["time_component_match"] += 1

        s["time_preference"] += time_penalty * time_mismatch_count * weight

        # 3) Day preference
        if actual_days:
            s["day_total"] += 1
            if not preferred_days or actual_days.issubset(preferred_days):
                s["day_match"] += 1
            else:
                s["day_preference"] += day_penalty * weight

    # 4) Teaching-load balance
    loads = [s["load"] for s in stats.values()]
    average_load = sum(loads) / len(loads) if loads else 0

    for s in stats.values():
        deviation = abs(s["load"] - average_load)
        excess = max(0.0, deviation - load_tolerance_units)
        if excess > 0:
            steps = math.ceil(excess / load_step_units)
            s["teaching_load_balance"] = load_balance_penalty * steps

    # 5) Preparations
    for s in stats.values():
        excess = max(0, len(s["subjects"]) - max_preparations)
        s["number_of_preparations"] = (
            preparation_penalty * excess * s["Priority_Weight"]
        )

    # 6-7) Gaps and consecutive teaching
    for s in stats.values():
        for intervals in s["intervals"].values():
            merged = merge_intervals(intervals)

            for previous, current in zip(merged, merged[1:]):
                gap = current[0] - previous[1]
                if gap > gap_threshold_minutes:
                    s["gap_count"] += 1
                    s["gap_minutes"] += gap
                    s["schedule_gaps"] += gap_penalty * s["Priority_Weight"]

            for start, end in merged:
                duration = end - start
                s["max_consecutive_minutes"] = max(
                    s["max_consecutive_minutes"], duration
                )
                excess = max(0, duration - max_consecutive_minutes)
                if excess > 0:
                    steps = math.ceil(excess / consecutive_step_minutes)
                    s["consecutive_teaching"] += (
                        consecutive_penalty * steps * s["Priority_Weight"]
                    )

    rows = []
    factor_cols = list(FACTOR_LABELS.keys())

    for code, s in stats.items():
        row = {
            "Faculty_Code": code,
            "Faculty_Priority": s["Faculty_Priority"],
            "Priority_Weight": s["Priority_Weight"],
            "Teaching_Load": s["load"],
            "Preparations": len(s["subjects"]),
            "Subject_Satisfaction": (
                100 * s["subject_match"] / s["subject_total"]
                if s["subject_total"] else np.nan
            ),
            "Day_Satisfaction": (
                100 * s["day_match"] / s["day_total"]
                if s["day_total"] else np.nan
            ),
            "Time_Satisfaction": (
                100 * s["time_component_match"] / s["time_component_total"]
                if s["time_component_total"] else np.nan
            ),
            "Gap_Count": s["gap_count"],
            "Gap_Hours": s["gap_minutes"] / 60.0,
            "Max_Consecutive_Hours": s["max_consecutive_minutes"] / 60.0,
        }

        for col in factor_cols:
            row[col] = s[col]

        row["Total_Penalty"] = sum(s[col] for col in factor_cols)
        rows.append(row)

    result_df = pd.DataFrame(rows)

    if not result_df.empty:
        result_df = result_df.sort_values(
            ["Faculty_Priority", "Faculty_Code"],
            na_position="last"
        ).reset_index(drop=True)

    factor_penalty_df = result_df[
        ["Faculty_Code", "Faculty_Priority"] + factor_cols + ["Total_Penalty"]
    ].copy()

    # Verification: per-faculty sum must equal chromosome fitness.
    total_from_rows = result_df["Total_Penalty"].sum()
    total_fitness = faculty_preference_fitness(
        chromosome,
        df_faculty_pref,
        subject_penalty=subject_penalty,
        time_penalty=time_penalty,
        day_penalty=day_penalty,
        load_balance_penalty=load_balance_penalty,
        preparation_penalty=preparation_penalty,
        gap_penalty=gap_penalty,
        consecutive_penalty=consecutive_penalty,
        load_tolerance_units=load_tolerance_units,
        load_step_units=load_step_units,
        max_preparations=max_preparations,
        gap_threshold_minutes=gap_threshold_minutes,
        max_consecutive_minutes=max_consecutive_minutes,
        consecutive_step_minutes=consecutive_step_minutes,
    )

    if abs(total_from_rows - total_fitness) > 1e-9:
        print(
            "WARNING: visualization penalty total does not exactly match "
            f"fitness function ({total_from_rows} vs {total_fitness})."
        )

    return result_df, factor_penalty_df


def visualize_faculty_fitness(
    chromosome,
    df_faculty_pref,
    figsize=(15, 7),
    show_values=True,
    **fitness_kwargs,
):
    """
    Heatmap of penalty contribution by faculty and fitness factor.

    Interpretation:
        0 = no penalty / best result
        larger value = larger contribution to poor fitness
    """
    result_df, factor_df = analyze_faculty_fitness(
        chromosome,
        df_faculty_pref,
        **fitness_kwargs,
    )

    if result_df.empty:
        print("No faculty results available.")
        return result_df, factor_df

    factor_cols = list(FACTOR_LABELS.keys())
    matrix = result_df[factor_cols].to_numpy(dtype=float)

    labels = []
    for _, row in result_df.iterrows():
        p = row["Faculty_Priority"]
        p_text = "?" if pd.isna(p) else str(int(p))
        labels.append(f"F{int(row['Faculty_Code'])}  |  Priority {p_text}")

    fig, ax = plt.subplots(figsize=figsize)
    image = ax.imshow(matrix, aspect="auto")

    ax.set_title(
        "Faculty Fitness Profile — Best Chromosome\n"
        "Penalty contribution by fitness-function parameter (Lower is Better)",
        fontsize=15,
        pad=16,
    )
    ax.set_xlabel("Fitness Function Parameter")
    ax.set_ylabel("Faculty (ordered by priority)")

    ax.set_xticks(np.arange(len(factor_cols)))
    ax.set_xticklabels(
        [FACTOR_LABELS[c] for c in factor_cols],
        rotation=0,
    )
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)

    if show_values:
        threshold = matrix.max() / 2 if matrix.size and matrix.max() > 0 else 0
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                value = matrix[i, j]
                ax.text(
                    j, i, f"{value:.0f}",
                    ha="center", va="center",
                    fontsize=9,
                    color="white" if value > threshold else "black",
                )

    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label("Weighted penalty")

    plt.tight_layout()
    plt.show()

    # Separate total-penalty ranking chart.
    ranking = result_df.sort_values(
        ["Total_Penalty", "Faculty_Priority"]
    ).copy()

    rank_labels = []
    for _, row in ranking.iterrows():
        p = row["Faculty_Priority"]
        p_text = "?" if pd.isna(p) else str(int(p))
        rank_labels.append(f"F{int(row['Faculty_Code'])} (P{p_text})")

    fig, ax = plt.subplots(figsize=(11, 6))
    y = np.arange(len(ranking))
    bars = ax.barh(y, ranking["Total_Penalty"])
    ax.set_yticks(y)
    ax.set_yticklabels(rank_labels)
    ax.invert_yaxis()
    ax.set_xlabel("Total weighted penalty")
    ax.set_ylabel("Faculty")
    ax.set_title(
        "Faculty Fitness Ranking — Best Chromosome\n"
        "Lower Total Penalty = Better Faculty-Level Result",
        fontsize=14,
        pad=14,
    )
    ax.grid(axis="x", alpha=0.2)

    for bar, value in zip(bars, ranking["Total_Penalty"]):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f"  {value:.0f}",
            va="center",
            fontsize=9,
        )

    plt.tight_layout()
    plt.show()

    # Operational metrics plot: not fitness units, but explains the penalties.
    metrics = result_df.sort_values(
        ["Faculty_Priority", "Faculty_Code"]
    ).copy()

    x = np.arange(len(metrics))
    faculty_labels = [
        f"F{int(row.Faculty_Code)}\nP{int(row.Faculty_Priority) if not pd.isna(row.Faculty_Priority) else '?'}"
        for _, row in metrics.iterrows()
    ]

    fig, ax = plt.subplots(figsize=(14, 6))
    width = 0.34
    ax.bar(x - width/2, metrics["Teaching_Load"], width, label="Teaching Load (units)")
    ax.bar(x + width/2, metrics["Preparations"], width, label="Preparations")
    ax.set_xticks(x)
    ax.set_xticklabels(faculty_labels)
    ax.set_ylabel("Count / units")
    ax.set_xlabel("Faculty")
    ax.set_title(
        "Faculty Workload Indicators Behind the Fitness Score",
        fontsize=14,
        pad=14,
    )
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.show()

    return result_df, factor_df


def display_faculty_fitness_summary(result_df):
    """
    Compact thesis-friendly table explaining each faculty's fitness result.
    """
    columns = [
        "Faculty_Code",
        "Faculty_Priority",
        "Teaching_Load",
        "Preparations",
        "Subject_Satisfaction",
        "Day_Satisfaction",
        "Time_Satisfaction",
        "Gap_Count",
        "Gap_Hours",
        "Max_Consecutive_Hours",
        "Total_Penalty",
    ]

    out = result_df[columns].copy()
    for col in [
        "Subject_Satisfaction",
        "Day_Satisfaction",
        "Time_Satisfaction",
        "Gap_Hours",
        "Max_Consecutive_Hours",
    ]:
        out[col] = out[col].round(2)

    return out
