"""Read-only explanations of recorded observations. Never invokes fitness or GA."""
import hashlib
import math
from collections import defaultdict
from pathlib import Path

from services import ga_history_service as history

CATALOG = {
    "subject_preference": ("Ranked subjects", "Per offering: subject weight × rank index / list length × importance × faculty priority multiplier. Unlisted subjects use 1; first rank uses 0."),
    "time_preference": ("Preferred times", "Subject blocks: one mismatch for each requested start absent from the raw component blocks, independently of day. Otherwise one mismatch per component extending outside the general preferred window."),
    "day_preference": ("Preferred days", "Subject blocks: one mismatch per requested day absent from the component. Otherwise one mismatch per offering with any day outside preferred days."),
    "schedule_style": ("Schedule style", "Compact: ceil(total daily gaps / 30) steps. Spread Out: one step per gap below 30 minutes. Uses each component's daily bounds; steps × gap weight × importance × priority multiplier."),
    "lecture_lab_preference": ("Lecture / laboratory days", "One weighted mismatch per offering with both components: Same Day requires any shared day; Different Days requires no shared day."),
    "number_of_preparations": ("Preparations", "Distinct subject codes above max_preparations × preparation weight × faculty priority multiplier."),
    "teaching_load_balance": ("Teaching workload", "Underload: ceil((target − actual) / target × 10) × underload weight. Overload and heavy overload use separate ceil(excess units / workload_step_units) bands. No faculty priority multiplier."),
    "daily_teaching_load": ("Daily teaching time", "Merged teaching minutes above the daily limit: ceil(excess / daily_load_step_minutes) × daily-load weight. No preference importance or priority multiplier."),
}
PENALTY_FIELDS = dict(zip(CATALOG, ["Subject_Penalty", "Time_Penalty", "Day_Penalty", "Schedule_Style_Penalty", "Lecture_Lab_Penalty", "Preparation_Penalty", "Load_Balance_Penalty", "Daily_Teaching_Load_Penalty"]))
DEFINITIONS = {
    "overall": "Overall penalty is the sum of the eight recorded components; lower is better. No separate reward branch exists in the inspected scorer.",
    "target": "max(0, 24 − administrative − research − extension release units). Legacy target_teaching_load=12 is not used.",
    "actual": "Sum of course credit units per faculty/offering; meeting hours and repeated meetings are not additional teaching units.",
    "difference": "Actual teaching units minus required teaching target.",
    "fulfillment": "100 × actual / target. Undefined when target is zero; values above 100% are retained.",
    "priority": "max(effective faculty priorities) − faculty priority + 1. Importance is clamped to 0..5; priority multiplies preference/preparation penalties, not workload/daily load.",
    "indicators": "Preference match percentages/counts are descriptive; they are not penalty amounts or additions to overall fitness.",
    "exact_schedule": "The scorer checks subject-block day and raw start-time membership independently, not a joint day/start match. A requested start may match an internal block of a longer meeting. Subject blocks bypass general day/time toggles; importance controls their influence.",
    "hard_constraints": "Eligibility, faculty/room/section conflicts, 40-unit teaching maximum, fixed schedules, external locks and component continuity remain mandatory publication gates outside fitness.",
}


def scorer_hash(preference_policy=2):
    from services.preference_scoring_policy import legacy_source
    name = "genetic_algorithm/operators/FitnessFunction.py"
    content = (Path(__file__).resolve().parents[1] / name).read_bytes()
    return hashlib.sha256(legacy_source(name, content) if preference_policy == 1 else content).hexdigest()


def capture_context(frozen, dataframe):
    """Small provenance DTO from the already-frozen run, not mutable API inputs."""
    if frozen is None:
        return None
    from genetic_algorithm.operators.FitnessFunction import _build_effective_preferences
    members = []
    for member in frozen["system_faculty"]:
        if getattr(member, "is_external", False):
            continue
        members.append({"faculty": f"Faculty {member.code}", "code": str(member.code),
                        "required_teaching_load": member.required_teaching_load,
                        "admin_load": member.admin_load, "research_load": member.research_load,
                        "extension_load": member.extension_load,
                        "overload_warning_threshold": member.overload_warning_threshold})
    policy = history.checkpoints.scoring_version(frozen)
    return {"version": 1, "preference_scoring_version": policy, "scorer_sha256": scorer_hash(policy), "input_fingerprint": frozen["input_fingerprint"],
            "faculty": members, "preferences": {str(k): v for k, v in _build_effective_preferences(dataframe).items()},
            "settings": frozen["settings"]}


def capture_assignments(candidate):
    from genetic_algorithm.operators.FitnessFunction import _component_intervals
    return [{"subject": str(s.number), "section": str(s.section.code),
             "faculty": str(s.assigned_faculty.code), "teaching_units": s.credit_units,
             "external": bool(getattr(s.assigned_faculty, "is_external", False)),
             "display_name": s.assigned_faculty.name if getattr(s.assigned_faculty, "is_external", False) else f"Faculty {s.assigned_faculty.code}",
             "lecture": _component_intervals(s.lecture_time_blocks),
             "laboratory": _component_intervals(s.laboratory_time_blocks)} for s in candidate]


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise history.HistoryError("Fitness reporting contains an invalid numeric observation.", "GA_REPORT_INVALID")
    return value


def normalized_code(value):
    # Pandas iterrows may serialize integer faculty codes as 7.0 in final rows.
    # This is a compatibility normalization, not a new identity assignment.
    try:
        number = float(value)
        if math.isfinite(number) and number.is_integer():
            return str(int(number))
    except (TypeError, ValueError):
        pass
    return str(value)


def checked_breakdown(breakdown, total):
    if breakdown is None:
        return None
    if not isinstance(breakdown, dict) or set(breakdown) != set(CATALOG):
        raise history.HistoryError("Stored fitness component contract is incompatible.", "GA_REPORT_INVALID")
    for value in breakdown.values():
        finite(value)
    if not math.isclose(sum(breakdown.values()), finite(total), rel_tol=1e-10, abs_tol=1e-7):
        raise history.HistoryError("Stored components do not reconcile with overall penalty.", "GA_REPORT_INVALID")
    return breakdown


def minutes(value):
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def day(value):
    from genetic_algorithm.models.Faculty import Faculty
    normalized = Faculty._normalize_days(value)
    return normalized[0] if normalized else str(value).lower()


def validate_assignments(assignments, payload):
    """Check the reporting DTO against the validated, immutable candidate."""
    if assignments is None:
        return
    def merge(intervals):
        result = []
        for start, end in sorted(intervals):
            finite(start); finite(end)
            if start >= end:
                raise history.HistoryError("Invalid reporting interval.", "GA_REPORT_INVALID")
            if result and start <= result[-1][1]:
                result[-1][1] = max(result[-1][1], end)
            else:
                result.append([start, end])
        return result
    raw, saved = defaultdict(list), defaultdict(list)
    offerings = set()
    for row in assignments:
        offering = (row["subject"], row["section"])
        if offering in offerings or finite(row["teaching_units"]) < 0:
            raise history.HistoryError("Duplicate/invalid reporting offering.", "GA_REPORT_INVALID")
        offerings.add(offering)
        for component in ("lecture", "laboratory"):
            for d, start, end in row[component]:
                raw[(row["subject"], row["section"], row["faculty"], component, d)].append((start, end))
    for row in payload["schedule"]:
        calendar_day = {"M": "monday", "T": "tuesday", "W": "wednesday", "TH": "thursday", "F": "friday", "S": "saturday"}.get(str(row["day"]).upper(), day(row["day"]))
        saved[(row["subject"], row["section"], row["faculty"], row["type"].lower(), calendar_day)].append((minutes(row["start"]), minutes(row["end"])))
    if {key: merge(value) for key, value in raw.items()} != {key: merge(value) for key, value in saved.items()}:
        raise history.HistoryError("Reporting intervals do not match the historical schedule.", "GA_REPORT_INVALID")


def indicator(key, matched, total, importance, enabled, explanation, penalty=None, weighted=None):
    if not enabled:
        status = "disabled"
    elif total == 0:
        status = "not_applicable"
    elif matched == total:
        status = "satisfied"
    elif matched == 0:
        status = "unmet"
    else:
        status = "partially_satisfied"
    return {"key": key, "status": status, "matched": matched, "total": total,
            "satisfaction_percent": (weighted if weighted is not None else 100 * matched / total) if enabled and total else None,
            "importance": importance, "affects_fitness": bool(enabled and importance > 0),
            "penalty": penalty, "explanation": explanation}


def preference_indicators(assignments, preference, penalties, preference_policy=2):
    """Describe recorded raw intervals using the inspected scorer's predicates.

    Does not compute a fitness score or infer missing penalty contributions.
    """
    importance = lambda key: max(0, min(5, int(preference.get(key + "_importance", 0))))
    preferred = [str(s).strip().upper() for s in preference.get("preferred_subjects", [])]
    ranks = [preferred.index(a["subject"].strip().upper()) / max(1, len(preferred)) if a["subject"].strip().upper() in preferred else 1 for a in assignments] if preferred else []
    result = [indicator("subject_preference", sum(r == 0 for r in ranks), len(ranks), importance("subject"), bool(preference.get("use_subject_preference") and preferred),
                        "Ranked match: 100% at first rank; lower ranks receive partial descriptive credit. Scoring is per offering.", penalties.get("subject_preference"),
                        100 * (1 - sum(ranks) / len(ranks)) if ranks else None)]
    if ranks and result[0]["status"] == "unmet" and any(r < 1 for r in ranks):
        result[0]["status"] = "partially_satisfied"
    counts = {"day": [0, 0], "time": [0, 0]}
    exact_used = False
    enabled = {"day": bool(preference.get("use_day_preference")), "time": bool(preference.get("use_time_preference"))}
    ranges = defaultdict(list)
    lab_matches = lab_total = 0
    blocks = preference.get("preferred_schedule_blocks", [])
    for assignment in assignments:
        exact = [b for b in blocks if str(b.get("kind", "")).strip().lower() == "subject" and str(b.get("subject_code", "")).strip().upper() == assignment["subject"].strip().upper()]
        if exact:
            exact_used = True
            enabled = {"day": preference_policy == 1 or preference.get("exact_day_preference_enabled", preference.get("use_day_preference", True)),
                       "time": preference_policy == 1 or preference.get("exact_time_preference_enabled", preference.get("use_time_preference", True))}
            for block in exact:
                intervals = assignment.get(str(block.get("component", "")).strip().lower(), [])
                checks = {"day": any(d == day(block.get("day")) for d, _, _ in intervals),
                          "time": any(start == minutes(block["start_time"]) for _, start, _ in intervals)}
                for key, match in checks.items():
                    counts[key][0] += int(match)
                    counts[key][1] += 1
        else:
            actual_days = {d for key in ("lecture", "laboratory") for d, _, _ in assignment[key]}
            from genetic_algorithm.models.Faculty import Faculty
            preferred_days = {d for value in preference.get("preferred_days", []) for d in Faculty._normalize_days(value)}
            if preference.get("use_day_preference") and actual_days and preferred_days:
                counts["day"][0] += int(actual_days.issubset(preferred_days))
                counts["day"][1] += 1
            start, end = preference.get("preferred_start_time"), preference.get("preferred_end_time")
            if preference.get("use_time_preference") and start is not None and end is not None:
                for key in ("lecture", "laboratory"):
                    if assignment[key]:
                        counts["time"][0] += int(all(s >= minutes(start) and e <= minutes(end) for _, s, e in assignment[key]))
                        counts["time"][1] += 1
        for key in ("lecture", "laboratory"):
            by_day = defaultdict(list)
            for d, start, end in assignment[key]:
                by_day[d].append((start, end))
            for d, intervals in by_day.items():
                ranges[d].append((min(s for s, _ in intervals), max(e for _, e in intervals)))
        lecture_days = {d for d, _, _ in assignment["lecture"]}
        lab_days = {d for d, _, _ in assignment["laboratory"]}
        if lecture_days and lab_days:
            choice = str(preference.get("lecture_lab_preference", "No Preference")).strip().lower()
            if choice in ("same day", "different day"):
                lab_total += 1
                lab_matches += int(bool(lecture_days & lab_days) == (choice == "same day"))
    for key in ("day", "time"):
        matched, total = counts[key]
        result.append(indicator(key + "_preference", matched, total, importance(key), enabled[key],
                                (DEFINITIONS["exact_schedule"] if preference_policy == 1 else DEFINITIONS["exact_schedule"].replace("Subject blocks bypass general day/time toggles; importance controls their influence.", "Explicit day/time flags control subject blocks; missing legacy flags retain their prior exact-block influence.")) if exact_used else CATALOG[key + "_preference"][1], penalties.get(key + "_preference")))
    gaps = []
    for intervals in ranges.values():
        ordered = sorted(intervals)
        previous = ordered[0][1]
        for start, end in ordered[1:]:
            gaps.append(max(0, start - previous))
            previous = max(previous, end)
    style = str(preference.get("gap_preference", "No Preference")).strip().lower()
    matches = sum(g == 0 if style == "compact" else g >= 30 for g in gaps)
    gap = indicator("schedule_style", matches, len(gaps), importance("gap"), bool(preference.get("use_gap_preference") and style in ("compact", "scattered")),
                    "Measured between component daily bounds: Compact prefers zero idle minutes; Spread Out requires at least 30 minutes between components.", penalties.get("schedule_style"))
    gap["idle_minutes"] = sum(gaps)
    result.append(gap)
    choice = str(preference.get("lecture_lab_preference", "No Preference")).strip().lower()
    result.append(indicator("lecture_lab_preference", lab_matches, lab_total, importance("lecture_lab"), bool(preference.get("use_lecture_lab_preference") and choice in ("same day", "different day")),
                            CATALOG["lecture_lab_preference"][1], penalties.get("lecture_lab_preference")))
    return result


def build_report(source, total, breakdown, workload, context=None, assignments=None, faculty_analysis=None, configuration=None):
    finite(total)
    checked_breakdown(breakdown, total)
    rows = []
    # Missing original policy means legacy scoring, not current reinterpretation.
    policy = (context or {}).get("preference_scoring_version", 1)
    captured_engine = (context or {}).get("engine_fingerprint") or source.get("engine_fingerprint")
    try:
        current_scorer_hash = scorer_hash(policy)
        engine_matches = captured_engine is None or captured_engine == history.checkpoints.evaluation_fingerprint({"preference_scoring_version": policy})
    except ValueError:
        # Stored observations remain readable after an unsupported future release.
        # Only new interpretation/derived indicators are unavailable.
        current_scorer_hash = None
        engine_matches = False
    profiles = {row["faculty"]: row for row in (context or {}).get("faculty", [])}
    recorded = {f"Faculty {normalized_code(row['Faculty_Code'])}": row for row in (faculty_analysis or {}).get("faculty", []) if not str(row["Faculty_Code"]).startswith("external:")}
    stored_workload = {row["faculty"]: row for row in workload}
    for label in sorted(profiles.keys() | stored_workload.keys() | recorded.keys()):
        profile = profiles.get(label, {})
        original = stored_workload.get(label, {})
        observed = recorded.get(label, {})
        code = label.removeprefix("Faculty ")
        mine = [a for a in assignments or [] if a["faculty"] == code and not a["external"]]
        actual = original.get("teaching_units", observed.get("Teaching_Load"))
        if actual is not None and observed.get("Teaching_Load") is not None and not math.isclose(finite(actual), finite(observed["Teaching_Load"])):
            raise history.HistoryError("Recorded faculty analysis and workload disagree.", "GA_REPORT_INVALID")
        if mine or (assignments is not None and profile):
            measured = sum(finite(a["teaching_units"]) for a in mine)
            if actual is not None and not math.isclose(measured, actual):
                raise history.HistoryError("Recorded workload and assignments disagree.", "GA_REPORT_INVALID")
            actual = measured
        target = original.get("required_teaching_load", profile.get("required_teaching_load"))
        if actual is not None:
            finite(actual)
            if actual < 0 or actual > 40:
                raise history.HistoryError("Normal faculty teaching load violates its hard range.", "GA_REPORT_INVALID")
        if target is not None:
            finite(target)
        difference = actual - target if actual is not None and target is not None else None
        penalties = {key: observed[field] for key, field in PENALTY_FIELDS.items() if field in observed}
        for value in penalties.values():
            finite(value)
        if observed.get("Total_Penalty") is not None:
            finite(observed["Total_Penalty"])
            if set(penalties) == set(CATALOG) and not math.isclose(sum(penalties.values()), observed["Total_Penalty"], rel_tol=1e-10, abs_tol=1e-7):
                raise history.HistoryError("Faculty components do not reconcile.", "GA_REPORT_INVALID")
        preference = (context or {}).get("preferences", {}).get(code)
        available = context is not None and assignments is not None and context.get("scorer_sha256") == current_scorer_hash and engine_matches
        indicators = preference_indicators(mine, preference or {}, penalties, policy) if available else None
        if indicators is None and observed:
            indicators = [{"key": key, "status": "unavailable" if observed.get(field) is None else "satisfied" if observed[field] == 100 else "unmet" if observed[field] == 0 else "partially_satisfied",
                           "satisfaction_percent": observed.get(field), "importance": observed.get(importance_field),
                           "affects_fitness": None, "penalty": penalties.get(key), "matched": None, "total": None,
                           "explanation": "Recorded final descriptive indicator; original enable flags and raw intervals were not preserved."}
                          for key, field, importance_field in [("subject_preference", "Subject_Satisfaction", "Subject_Importance"), ("day_preference", "Day_Satisfaction", "Day_Importance"), ("time_preference", "Time_Satisfaction", "Time_Importance")]]
        rows.append({"faculty": label, "teaching_units": actual, "required_teaching_load": target,
                     "difference": difference, "fulfillment_percent": 100 * actual / target if actual is not None and target else None,
                     "admin_load": profile.get("admin_load"), "research_load": profile.get("research_load"), "extension_load": profile.get("extension_load"),
                     "warning_threshold": profile.get("overload_warning_threshold"), "hard_maximum": 40,
                     "workload_status": "unavailable" if difference is None else "underload" if difference < 0 else "on_target" if difference == 0 else "overload",
                     "heavy_overload": actual > profile["overload_warning_threshold"] if actual is not None and "overload_warning_threshold" in profile else None,
                     "underload_steps": (math.ceil((target - actual) / target * 10) if target and actual is not None and actual < target else 0 if target is not None and actual is not None else None) if engine_matches else None,
                     "workload_penalty": penalties.get("teaching_load_balance"), "penalties": penalties,
                     "total_penalty": observed.get("Total_Penalty"), "preparations": original.get("preparations", observed.get("Preparations")),
                     "priority_multiplier": observed.get("Priority_Weight"), "preferences": indicators,
                     "unavailable_reason": ("Captured engine differs; stored indicators are shown where available, without reinterpreting preferences under current rules." if not engine_matches else "Original preference context/raw intervals were not captured; no current preferences were used.") if not available else None})
    components = [{"key": key, "label": label, "definition": definition, "penalty": breakdown.get(key) if breakdown is not None else None} for key, (label, definition) in CATALOG.items()]
    faculty_totals = [row["total_penalty"] for row in rows if row["total_penalty"] is not None]
    result = {"schema_version": 1, "source": source, "overall_penalty": total, "components": components,
              "recorded_component_sum": sum(breakdown.values()) if breakdown is not None else None,
              "breakdown_available": breakdown is not None, "faculty": rows,
              "faculty_reconciliation": {"recorded_sum": sum(faculty_totals) if faculty_totals else None,
                                         "unattributed_difference": total - sum(faculty_totals) if faculty_totals else None,
                                         "explanation": "Missing faculty contributions are not allocated or inferred to force a match."},
              "definitions": {**DEFINITIONS, "preference_scoring_policy": "Legacy policy 1 (original flags behavior)" if policy == 1 else "Policy 2 (explicit day/time flags respected)",
                              "exact_schedule": DEFINITIONS["exact_schedule"] if policy == 1 else DEFINITIONS["exact_schedule"].replace("Subject blocks bypass general day/time toggles; importance controls their influence.", "Explicit day/time flags control subject blocks; missing legacy flags retain their prior exact-block influence.")},
              "fitness_configuration": (context or {}).get("settings") or configuration,
              "external_instructors": [{"name": a["display_name"], "subject": a["subject"], "section": a["section"], "scoring": "Excluded from normal workload/preference scoring"} for a in assignments or [] if a["external"]],
              "limitations": ["No component scores are inferred from totals. Missing historical values remain unavailable.",
                              "Descriptive indicators do not add to fitness. Exact subject-block day/start matches are independent.",
                              "Release breakdown and original flags cannot be recovered from legacy results that did not capture them."]}
    # Encoding enforces finite JSON for every field, including recorded indicators.
    history.checkpoints.canonical(result)
    return result


def generation_report(run_id, generation, kind="generation_best"):
    data = history.get_generation(run_id, generation)
    selected = data[kind]
    extra = None
    path = history.directory(run_id) / f"analysis-{selected['chromosome_id']}.json"
    analysis = history.analysis(run_id, generation, kind)  # Integrity and source identity checks.
    if path.exists():
        extra = history.read_document(path)
    context = data.get("reporting_context") or (extra or {}).get("reporting_context")
    if context is not None and context.get("input_fingerprint") != data["metrics"]["input_fingerprint"]:
        raise history.HistoryError("Reporting context input identity mismatch.", "GA_REPORT_INVALID")
    if context is not None:
        context = {**context, "engine_fingerprint": data["engine_fingerprint"]}
    assignments = selected.get("reporting_assignments") or (extra or {}).get("reporting_assignments")
    validate_assignments(assignments, selected["payload"])
    report = build_report({"kind": "historical", "run_id": run_id, "generation": generation, "candidate": kind,
                         "chromosome_id": selected["chromosome_id"], "timestamp": data["timestamp"],
                         "analysis_timestamp": analysis.get("breakdown_timestamp"), "input_fingerprint": data["metrics"]["input_fingerprint"],
                         "engine_fingerprint": data["engine_fingerprint"], "validation": data["validation"],
                         "penalty_source": analysis.get("breakdown_source")}, analysis["fitness"], analysis["fitness_breakdown"],
                        selected["workload"], context, assignments, (extra or {}).get("faculty_analysis"), data.get("fitness_configuration"))
    if assignments is None:
        report["external_instructors"] = external_from_schedule(selected["payload"]["schedule"])
    return report


def external_from_schedule(schedule):
    rows = [{"name": row.get("faculty_name", "Preassigned Instructor"), "subject": row["subject"], "section": row["section"],
             "scoring": "Excluded from normal workload/preference scoring"} for row in schedule if str(row["faculty"]).startswith("external:")]
    return list({(r["name"], r["subject"], r["section"]): r for r in rows}.values())


def latest_report():
    from routers.genetic_algorithm import _read_latest_result
    data = _read_latest_result()
    if not data:
        raise history.HistoryError("No saved GA analysis is available.", "GA_REPORT_UNAVAILABLE", 404)
    run_id = data.get("run_id")
    if run_id:
        try:
            index = history.manifest(run_id)
            if index["generations"]:
                generation = index["generations"][-1]["generation"]
                snapshot = history.get_generation(run_id, generation)
                selected = snapshot["best_ever"]
                if selected["payload"]["schedule"] != data["schedule"] or selected["payload"]["best_fitness"] != data["best_fitness"]:
                    raise history.HistoryError("Latest result does not match its historical candidate.", "GA_REPORT_INVALID")
                report = generation_report(run_id, generation, "best_ever")
                recorded_breakdown = checked_breakdown(data.get("fitness_breakdown"), data["best_fitness"])
                if recorded_breakdown is not None and report["breakdown_available"] and recorded_breakdown != {row["key"]: row["penalty"] for row in report["components"]}:
                    raise history.HistoryError("Latest result and archived components disagree.", "GA_REPORT_INVALID")
                external = report["external_instructors"]
                if data.get("faculty_analysis") is not None:
                    available_breakdown = recorded_breakdown if recorded_breakdown is not None else ({row["key"]: row["penalty"] for row in report["components"]} if report["breakdown_available"] else None)
                    captured_context = snapshot.get("reporting_context")
                    if captured_context is not None:
                        captured_context = {**captured_context, "engine_fingerprint": snapshot["engine_fingerprint"]}
                    report = build_report(report["source"], data["best_fitness"], available_breakdown,
                                          selected["workload"], captured_context, selected.get("reporting_assignments"),
                                          data["faculty_analysis"], snapshot.get("fitness_configuration"))
                    report["external_instructors"] = external
                return report
        except history.HistoryError as error:
            if error.status != 404:
                raise
    report = build_report({"kind": "saved-final-result", "run_id": run_id, "generation": None, "candidate": "best_ever",
                         "chromosome_id": None, "timestamp": None, "penalty_source": "recorded-final-result"},
                        data["best_fitness"], data.get("fitness_breakdown"), [], faculty_analysis=data.get("faculty_analysis"))
    report["external_instructors"] = external_from_schedule(data["schedule"])
    return report


def comparison_report(run_id, left, right, kind="generation_best"):
    original = history.compare(run_id, left, right, kind)  # Enforce same inputs/configuration/engine.
    a, b = generation_report(run_id, left, kind), generation_report(run_id, right, kind)
    component_changes = [{"key": x["key"], "label": x["label"], "before": x["penalty"], "after": y["penalty"],
                          "reduction": x["penalty"] - y["penalty"] if x["penalty"] is not None and y["penalty"] is not None else None}
                         for x, y in zip(a["components"], b["components"])]
    faculty_before = {r["faculty"]: r for r in a["faculty"]}
    faculty_after = {r["faculty"]: r for r in b["faculty"]}
    return {"schema_version": 1, "source": {"run_id": run_id, "left": left, "right": right, "candidate": kind},
            "overall_reduction": a["overall_penalty"] - b["overall_penalty"], "component_changes": component_changes,
            "faculty_changes": [{"faculty": label, "before": faculty_before.get(label), "after": faculty_after.get(label)} for label in sorted(faculty_before.keys() | faculty_after.keys())],
            "assignment_changes": original["changes"], "definitions": DEFINITIONS,
            "explanation": "Positive reduction is improvement. Changes are measured associations, not proof that a factor caused the total change. Missing component/preference observations cannot explain a numerical reduction."}


def export_csv(report, section="fitness"):
    source = report["source"]
    provenance = {key: source.get(key) for key in ("run_id", "generation", "candidate", "chromosome_id", "timestamp")}
    if section == "workload":
        fields = [*provenance, "faculty", "required_teaching_load", "teaching_units", "difference", "fulfillment_percent", "admin_load", "research_load", "extension_load", "workload_status", "workload_penalty", "underload_steps", "warning_threshold", "hard_maximum", "underload_weight", "overload_weight", "heavy_overload_weight", "workload_step_units", "definition"]
        settings = report["fitness_configuration"] or {}
        rows = [{**provenance, **row, "underload_weight": settings.get("underload_penalty"), "overload_weight": settings.get("overload_penalty"),
                 "heavy_overload_weight": settings.get("heavy_overload_penalty"), "workload_step_units": settings.get("workload_step_units"),
                 "definition": DEFINITIONS["target"] + " " + DEFINITIONS["actual"] + " " + DEFINITIONS["difference"] + " " + DEFINITIONS["fulfillment"] + " " + CATALOG["teaching_load_balance"][1]} for row in report["faculty"]]
    else:
        fields = [*provenance, "row_type", "faculty", "component", "penalty", "status", "satisfaction_percent", "importance", "definition"]
        rows = [{**provenance, "row_type": "overall", "component": "overall", "penalty": report["overall_penalty"], "definition": DEFINITIONS["overall"]}]
        rows += [{**provenance, "row_type": "component", "component": row["key"], "penalty": row["penalty"], "status": "recorded" if row["penalty"] is not None else "unavailable", "definition": row["definition"]} for row in report["components"]]
        rows += [{**provenance, "row_type": "faculty_component", "faculty": member["faculty"], "component": key, "penalty": value, "status": "recorded", "definition": CATALOG[key][1]} for member in report["faculty"] for key, value in member["penalties"].items()]
        rows += [{**provenance, "row_type": "preference", "faculty": member["faculty"], "component": row["key"], "penalty": row["penalty"], "status": row["status"], "satisfaction_percent": row["satisfaction_percent"], "importance": row["importance"], "definition": row["explanation"] + " " + DEFINITIONS["indicators"]} for member in report["faculty"] for row in member["preferences"] or []]
    return history.csv_content(rows, fields)
