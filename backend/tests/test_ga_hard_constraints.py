"""Hard-constraint regression checks, including intentionally invalid baselines.

Failures are left visible: an accepted invalid baseline is a blocker, not xfail.
All persistence checks use pytest temporary storage, never semester data files.
"""

import copy
import importlib
import random
from collections import Counter

import pytest

from genetic_algorithm.operators.CreatePopulation import generate_population
from genetic_algorithm.operators.TournamentSelection import select_parent_pair
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from genetic_algorithm.utils import Functions as scheduling
from services import chromosome_service as storage
from services import ga_service
from tests.test_ga_api_crossover import small_population


swap = importlib.import_module("genetic_algorithm.operators.Swap")
mutation = importlib.import_module("genetic_algorithm.operators.mutation")
OPERATOR_RESULTS = {}
DAYS = ("M", "T", "W", "TH", "F", "S")


def key(subject):
    return str(subject.number), str(subject.section.code)


def entry_key(entry):
    return str(entry["subject"]), str(entry["section"])


def constraint_violations(chromosome, templates):
    """Independent checks of actual assignments, not cached resource loads."""
    problems = set()
    expected = {key(subject): subject for subject in templates}
    if Counter(key(subject) for subject in chromosome) != Counter(key(s) for s in templates):
        problems.add("offerings")
    eligible = {
        (str(row.faculty_code), str(row.course_no).upper())
        for row in scheduling.df_faculty_subject_eligibility.itertuples(index=False)
        if str(row.eligibility_status).lower() == "eligible"
    }
    entries, loads = [], Counter()
    for subject in chromosome:
        template = expected.get(key(subject))
        if template is None:
            continue
        faculty = subject.assigned_faculty
        if faculty is None:
            problems.add("missing_instructor")
            continue
        declaration = template.preassigned_assignment
        if declaration is not None:
            if (not getattr(faculty, "is_external", False)
                    or faculty.code != declaration.instructor_id
                    or faculty.name != declaration.instructor_name):
                problems.add("locked_instructor")
        else:
            if getattr(faculty, "is_external", False) or (str(faculty.code), subject.number.upper()) not in eligible:
                problems.add("eligibility")
            loads[faculty.code] += template.credit_units
        for component, hours, room_type in (
            ("lecture", template.lec_hours, "Lecture"),
            ("laboratory", template.lab_hours, "Laboratory"),
        ):
            room = getattr(subject, component + "_room")
            blocks = getattr(subject, component + "_time_blocks")
            intervals = []
            if hours and (room is None or room.type != room_type):
                problems.add("room_compatibility")
            if declaration and hours and (
                room is None or "".join(room.name.upper().split()) != "".join(declaration.room_name.upper().split())
            ):
                problems.add("locked_room")
            for day, block in blocks:
                start = scheduling.time_to_minutes(block.start_time)
                end = scheduling.time_to_minutes(block.end_time)
                intervals.append((day, start, end))
                if day not in DAYS or end - start != 30:
                    problems.add("invalid_time_block")
                if getattr(block.faculty, "code", None) != faculty.code:
                    problems.add("block_instructor")
            if len(set(intervals)) != len(intervals):
                problems.add("duplicate_blocks")
            if sum(end - start for _, start, end in intervals) != hours * 60:
                problems.add("required_hours")
            if component == "laboratory" and hours:
                ordered = sorted(intervals)
                if (not ordered or len({day for day, _, _ in ordered}) != 1
                        or any(a[2] != b[1] for a, b in zip(ordered, ordered[1:]))):
                    problems.add("continuous_lab")
        current_fixed = scheduling.get_fixed_section_schedule_entries(subject.section)
        expected_fixed = scheduling.get_fixed_section_schedule_entries(template.section)
        if current_fixed != expected_fixed:
            problems.add("fixed_schedule_moved")
        subject_entries = scheduling.get_subject_schedule_entries(subject)
        if any(scheduling.schedules_overlap(meeting, fixed)
               for meeting in subject_entries for fixed in expected_fixed):
            problems.add("fixed_section")
        entries.extend(subject_entries)
    if any(load > 40 for load in loads.values()):
        problems.add("teaching_ceiling")
    for resource in ("faculty", "room", "section"):
        if scheduling.find_resource_conflicts(entries, resource):
            problems.add(resource + "_conflict")
    return problems


def assert_valid(chromosome, templates):
    assert not constraint_violations(chromosome, templates)


@pytest.fixture(autouse=True)
def restore_rng():
    state = random.getstate()
    random.seed(42)
    yield
    random.setstate(state)


@pytest.fixture(scope="module")
def full_population():
    faculty, subjects, rooms = copy.deepcopy((
        scheduling.list_faculty, scheduling.list_subjects, scheduling.lst_rooms,
    ))
    state = random.getstate()
    random.seed(42)
    try:
        # Assignment helpers consult shared globals for section availability.
        # Match the normal runtime's shared objects while isolating test state.
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(scheduling, "list_faculty", faculty)
            patch.setattr(scheduling, "list_subjects", subjects)
            patch.setattr(scheduling, "lst_rooms", rooms)
            population = generate_population(3, faculty, subjects, rooms, max_restarts=20)
            after_generation = random.getstate()
    finally:
        random.setstate(state)
    assert len(population) == 3
    return population, subjects, after_generation


def test_three_full_fresh_chromosomes_satisfy_every_hard_constraint(full_population):
    population, templates, _ = full_population
    assert len(population) == 3
    assert len(templates) == len(scheduling.list_subjects)
    for chromosome in population:
        assert_valid(chromosome, templates)
        assert scheduling.validate_faculty_subject_eligibility(chromosome)
        assert scheduling.validate_preassigned_assignments(chromosome)
        assert scheduling.validate_fixed_section_conflicts(chromosome)


@pytest.mark.parametrize("operator", ["crossover", "mutation"])
def test_repeated_operators_preserve_hard_constraints(full_population, operator):
    population, templates, after_generation = full_population
    before = [[scheduling.get_subject_schedule_entries(s) for s in c] for c in population]
    random.setstate(after_generation)
    accepted = 0
    for _ in range(12):
        if operator == "crossover":
            scores = [faculty_preference_fitness(c, scheduling.df_faculty_pref) for c in population]
            parent1, parent2 = select_parent_pair(population, scores, 3)
            assert parent1 is not parent2
            child = swap.create_child_by_faculty_swap(parent1, parent2, scheduling.df_faculty_pref, max_attempts=1)
        else:
            child = mutation.mutate_by_swapping_faculty_subjects(
                population, scheduling.df_faculty_pref, max_attempts=1, verbose=False,
            )
        if child is not None:
            accepted += 1
            assert_valid(child, templates)
    assert before == [[scheduling.get_subject_schedule_entries(s) for s in c] for c in population]
    OPERATOR_RESULTS[operator] = {"calls": 12, "accepted_children": accepted}


@pytest.mark.parametrize("load,valid", [(0, True), (40, True), (41, False)])
def test_underload_is_soft_and_40_is_absolute_ceiling(load, valid):
    faculty = copy.deepcopy(scheduling.list_faculty[0])
    assert faculty.absolute_max_teaching_load == 40
    faculty.current_teaching_load = load
    assert scheduling.validate_minimum_teaching_load([faculty], raise_error=False) is valid


def test_constructed_over_40_chromosome_is_rejected_by_operators(small_population):
    population, templates, _, _, _ = small_population
    chromosome = copy.deepcopy(population[0])
    subject = next(s for s in chromosome if s.number == "ITE185")
    subject.credit_units = 41
    assert swap.chromosome_has_load_violation(chromosome)
    assert mutation.chromosome_has_load_violation(chromosome)


def test_ineligible_assignment_is_rejected_by_validators(small_population):
    population, _, _, _, _ = small_population
    chromosome = copy.deepcopy(population[0])
    subject = next(s for s in chromosome if s.number == "ITE185")
    subject.assigned_faculty = copy.deepcopy(next(f for f in scheduling.list_faculty if f.code == 0))
    assert not scheduling.faculty_is_explicitly_eligible_for_subject(subject.assigned_faculty, subject)
    assert not scheduling.validate_faculty_subject_eligibility(chromosome, raise_error=False)
    assert swap.chromosome_has_eligibility_violation(chromosome)
    assert mutation.chromosome_has_eligibility_violation(chromosome)


def rows_for(payload, offering, component="Lecture"):
    return [row for row in payload["schedule"] if entry_key(row) == offering and row["type"] == component]


def without_component(payload, offering, component):
    return [row for row in payload["schedule"] if not (entry_key(row) == offering and row["type"] == component)]


def period(base, original, minutes, templates, *, room=None, fixed_overlap=False, forbid_day=None):
    template = next(s for s in templates if key(s) == entry_key(original))
    fixed_entries = scheduling.get_fixed_section_schedule_entries(template.section)
    for day in DAYS:
        if day == forbid_day:
            continue
        for start in range(450, 1320 - minutes + 1, 30):
            candidate = dict(original, day=day, start=storage.minutes_to_time(start),
                             end=storage.minutes_to_time(start + minutes), room=room or original["room"])
            overlaps_fixed = any(scheduling.schedules_overlap(candidate, f) for f in fixed_entries)
            if overlaps_fixed != fixed_overlap:
                continue
            if any(scheduling.find_resource_conflicts(base + [candidate], resource)
                   for resource in ("faculty", "room", "section")):
                continue
            return candidate
    raise AssertionError("No isolated time available for the constructed baseline case")


def conflicting_payload(payload, templates, rooms, resource):
    first = ("ITE185", "4A")
    second = ("ITD104", "4A") if resource == "section" else ("ITE185", "4B")
    a, b = rows_for(payload, first)[0], rows_for(payload, second)[0]
    base = [row for row in payload["schedule"]
            if not (entry_key(row) in {first, second} and row["type"] == "Lecture")]
    lecture_rooms = [room.name for room in rooms if room.type == "Lecture"]
    for day in DAYS:
        for start in range(450, 1141, 30):
            row_a = dict(a, day=day, start=storage.minutes_to_time(start),
                         end=storage.minutes_to_time(start + 180), faculty="7", room=lecture_rooms[0])
            row_b = dict(b, day=day, start=row_a["start"],
                         end=storage.minutes_to_time(start + (120 if resource == "section" else 180)),
                         faculty="7" if resource == "faculty" else "10",
                         room=lecture_rooms[0 if resource == "room" else 1])
            proposal = base + [row_a, row_b]
            conflicts = {r for r in ("faculty", "room", "section")
                         if scheduling.find_resource_conflicts(proposal, r)}
            if conflicts != {resource}:
                continue
            if any(scheduling.schedules_overlap(row, fixed)
                   for row in (row_a, row_b)
                   for s in templates if key(s) == entry_key(row)
                   for fixed in scheduling.get_fixed_section_schedule_entries(s.section)):
                continue
            payload["schedule"] = proposal
            return
    raise AssertionError("No isolated resource-conflict case could be constructed")


BASELINE_CASES = [
    ("faculty_overlap", "faculty_conflict"),
    ("room_overlap", "room_conflict"),
    ("section_overlap", "section_conflict"),
    ("palad_overlap", "faculty_conflict"),
    ("locked_instructor", "locked_instructor"),
    ("locked_room", "locked_room"),
    ("external_missing_hours", "required_hours"),
    ("missing_offering", "offerings"),
    ("ineligible_faculty", "eligibility"),
    ("over_40", "teaching_ceiling"),
    ("fixed_overlap", "fixed_section"),
    ("split_lab", "continuous_lab"),
    ("gapped_lab", "continuous_lab"),
    ("unexpected_lab", "required_hours"),
    ("missing_lab", "required_hours"),
    ("missing_lecture", "required_hours"),
    ("short_lecture", "required_hours"),
    ("lecture_in_lab_room", "room_compatibility"),
    ("lab_in_lecture_room", "room_compatibility"),
    ("duplicate_meeting", "duplicate_blocks"),
]


def invalid_baseline(case, population, original_templates, rooms):
    templates = copy.deepcopy(original_templates)
    payload = storage.chromosome_to_payload(population[0], 0)
    offering, lab = ("ITE185", "4A"), ("ITD104", "4A")
    if case in {"faculty_overlap", "room_overlap", "section_overlap"}:
        conflicting_payload(payload, templates, rooms, case.split("_")[0])
    elif case == "palad_overlap":
        copied = [dict(row, section="4B") for row in rows_for(payload, ("ITE184", "4A"))]
        payload["schedule"] = without_component(payload, ("ITE184", "4B"), "Lecture") + copied
    elif case in {"locked_instructor", "locked_room"}:
        for row in rows_for(payload, ("ITE184", "4A")):
            row["faculty" if case == "locked_instructor" else "room"] = (
                "7" if case == "locked_instructor" else "ICT 3B"
            )
    elif case == "external_missing_hours":
        target = ("ITE184", "4A")
        row = rows_for(payload, target)[0]
        row["end"] = storage.minutes_to_time(scheduling.time_to_minutes(row["start"]) + 30)
        payload["schedule"] = without_component(payload, target, "Lecture") + [row]
    elif case == "missing_offering":
        payload["schedule"] = [row for row in payload["schedule"] if entry_key(row) != offering]
    elif case == "ineligible_faculty":
        for row in rows_for(payload, offering):
            row["faculty"] = "0"  # Real GA faculty, explicitly ineligible for ITE185.
    elif case == "over_40":
        next(s for s in templates if key(s) == offering).credit_units = 41
    elif case in {"missing_lab", "missing_lecture"}:
        payload["schedule"] = without_component(payload, lab, "Laboratory" if case == "missing_lab" else "Lecture")
    elif case == "duplicate_meeting":
        payload["schedule"].extend(copy.deepcopy(rows_for(payload, offering)))
    elif case in {"split_lab", "gapped_lab"}:
        original = rows_for(payload, lab, "Laboratory")[0]
        base = without_component(payload, lab, "Laboratory")
        if case == "split_lab":
            first = period(base, original, 90, templates)
            base.append(first)
            base.append(period(base, original, 90, templates, forbid_day=first["day"]))
        else:
            window = period(base, original, 210, templates)
            start = scheduling.time_to_minutes(window["start"])
            base.extend([
                dict(window, end=storage.minutes_to_time(start + 90)),
                dict(window, start=storage.minutes_to_time(start + 120)),
            ])
        payload["schedule"] = base
    elif case == "unexpected_lab":
        original = dict(rows_for(payload, offering)[0], type="Laboratory")
        lab_room = next(room.name for room in rooms if room.type == "Laboratory")
        payload["schedule"].append(period(payload["schedule"], original, 180, templates, room=lab_room))
    else:
        component = "Laboratory" if case == "lab_in_lecture_room" else "Lecture"
        target = lab if component == "Laboratory" else offering
        original = rows_for(payload, target, component)[0]
        base = without_component(payload, target, component)
        wrong_room = None
        if case in {"lecture_in_lab_room", "lab_in_lecture_room"}:
            wrong_type = "Lecture" if component == "Laboratory" else "Laboratory"
            wrong_room = next(room.name for room in rooms if room.type == wrong_type)
        replacement = period(base, original, 30 if case == "short_lecture" else 180,
                             templates, room=wrong_room, fixed_overlap=case == "fixed_overlap")
        payload["schedule"] = base + [replacement]
    return payload, templates


@pytest.mark.parametrize("baseline_mode", ["saved", "uploaded"])
@pytest.mark.parametrize("case,violation", BASELINE_CASES, ids=[case for case, _ in BASELINE_CASES])
def test_invalid_baseline_is_rejected(small_population, monkeypatch, tmp_path, baseline_mode, case, violation):
    population, subjects, _, rooms, _ = small_population
    payload, templates = invalid_baseline(case, population, subjects, rooms)
    monkeypatch.setattr(storage, "SAVED_CHROMOSOME_DIR", tmp_path)
    monkeypatch.setattr(storage, "BEST_CHROMOSOME_PATH", tmp_path / "best.json")
    monkeypatch.setattr(storage, "UPLOADED_CHROMOSOME_PATH", tmp_path / "uploaded.json")
    path = storage.BEST_CHROMOSOME_PATH if baseline_mode == "saved" else storage.UPLOADED_CHROMOSOME_PATH
    storage.write_payload(payload, path)
    loaded = storage.load_saved_best_payload() if baseline_mode == "saved" else storage.load_uploaded_payload()
    try:
        chromosome = storage.payload_to_chromosome(loaded, templates, scheduling.list_faculty, rooms)
    except (ValueError, RuntimeError) as error:
        expected_messages = {
            "ineligible_faculty": "qualification", "over_40": "Absolute teaching-load",
            "fixed_overlap": "fixed section", "split_lab": "continuous",
            "gapped_lab": "continuous", "unexpected_lab": "unexpected Laboratory",
            "missing_lab": "missing required Laboratory", "missing_lecture": "missing required Lecture",
            "short_lecture": "weekly duration", "lecture_in_lab_room": "room compatibility",
            "lab_in_lecture_room": "room compatibility",
        }
        if case in expected_messages:
            assert expected_messages[case] in str(error)
        return
    detected = constraint_violations(chromosome, templates)
    assert violation in detected, (case, "Invalid-case construction failed", detected)
    pytest.fail(f"{baseline_mode} baseline accepted {case}; violated constraints: {sorted(detected)}")


@pytest.mark.parametrize("mode", ["fresh_roundtrip", "saved", "uploaded"])
def test_valid_baseline_roundtrip(small_population, monkeypatch, tmp_path, mode):
    population, templates, _, rooms, _ = small_population
    payload = storage.chromosome_to_payload(population[0], 0)
    if mode != "fresh_roundtrip":
        monkeypatch.setattr(storage, "SAVED_CHROMOSOME_DIR", tmp_path)
        monkeypatch.setattr(storage, "BEST_CHROMOSOME_PATH", tmp_path / "best.json")
        monkeypatch.setattr(storage, "UPLOADED_CHROMOSOME_PATH", tmp_path / "uploaded.json")
        path = storage.BEST_CHROMOSOME_PATH if mode == "saved" else storage.UPLOADED_CHROMOSOME_PATH
        storage.write_payload(payload, path)
        payload = storage.load_saved_best_payload() if mode == "saved" else storage.load_uploaded_payload()
    chromosome = storage.payload_to_chromosome(payload, templates, scheduling.list_faculty, rooms)
    assert_valid(chromosome, templates)


@pytest.mark.parametrize("mode", ["saved", "uploaded"])
@pytest.mark.parametrize("case", ["ineligible_faculty", "split_lab"])
def test_invalid_baseline_cannot_enter_api_evolution(small_population, monkeypatch, mode, case):
    population, subjects, _, rooms, _ = small_population
    payload, templates = invalid_baseline(case, population, subjects, rooms)
    monkeypatch.setattr(ga_service, "list_subjects", templates)
    monkeypatch.setattr(ga_service, "list_faculty", scheduling.list_faculty)
    monkeypatch.setattr(ga_service, "lst_rooms", rooms)
    monkeypatch.setattr(ga_service, "load_" + ("saved_best_payload" if mode == "saved" else "uploaded_payload"),
                        lambda: payload)

    def must_not_enter_evolution(*args, **kwargs):
        pytest.fail(f"Invalid {mode} {case} baseline reached API population generation")

    monkeypatch.setattr(ga_service, "generate_population", must_not_enter_evolution)
    with pytest.raises((ValueError, RuntimeError)):
        ga_service.run_genetic_algorithm(population_size=3, generations=1,
                                         fresh_chromosomes=0, baseline_mode=mode)


@pytest.mark.parametrize("resource", ["faculty", "room", "section"])
def test_controlled_resource_conflict_rejected_by_operators(small_population, resource):
    population, templates, _, rooms, _ = small_population
    payload = storage.chromosome_to_payload(population[0], 0)
    conflicting_payload(payload, templates, rooms, resource)
    assert scheduling.find_resource_conflicts(payload["schedule"], resource)
    with pytest.raises(ValueError, match=resource + " conflict"):
        storage.payload_to_chromosome(payload, templates, scheduling.list_faculty, rooms)
    # Build the same controlled conflict in a chromosome to exercise both
    # operator validators separately from the baseline loader.
    chromosome = copy.deepcopy(population[0])
    for subject in chromosome:
        lecture_rows = rows_for(payload, key(subject))
        faculty_code = lecture_rows[0]["faculty"]
        faculty = (subject.assigned_faculty if str(subject.assigned_faculty.code) == str(faculty_code)
                   else copy.deepcopy(next(f for f in scheduling.list_faculty if str(f.code) == str(faculty_code))))
        subject.assigned_faculty = faculty
        subject.lecture_time_blocks = []
        subject.lecture_room = next(r for r in rooms if r.name == lecture_rows[0]["room"])
        for row in lecture_rows:
            subject.lecture_time_blocks.extend(storage.create_component_blocks(
                day_code=row["day"], start_time=row["start"], end_time=row["end"],
                subject=subject, faculty=faculty, room=subject.lecture_room, schedule_type="Lecture",
            ))
        mutation.update_subject_faculty_blocks(subject, faculty)
    assert swap.chromosome_has_conflicts(chromosome)
    assert mutation.chromosome_has_conflicts(chromosome)


def test_baseline_loads_ignore_serialized_values_and_stale_cached_state(small_population):
    population, templates, _, rooms, _ = small_population
    faculty = copy.deepcopy(scheduling.list_faculty)
    for member in faculty:
        member.current_teaching_load = 999
    payload = storage.chromosome_to_payload(population[0], 0)
    payload["faculty_loads"] = {str(member.code): 999 for member in faculty}
    for row in payload["schedule"]:
        row.update(current_teaching_load=999, credit_units=999)
    chromosome = storage.payload_to_chromosome(payload, templates, faculty, rooms)
    assert_valid(chromosome, templates)
    expected = Counter()
    for subject in chromosome:
        if not getattr(subject.assigned_faculty, "is_external", False):
            expected[subject.assigned_faculty.code] += subject.credit_units
    for subject in chromosome:
        faculty = subject.assigned_faculty
        if not getattr(faculty, "is_external", False):
            assert faculty.current_teaching_load == expected[faculty.code]


@pytest.mark.parametrize("case,message", [
    ("ineligible_faculty", "qualification"), ("over_40", "Absolute teaching-load"),
])
def test_serialized_claims_cannot_bypass_current_baseline_rules(small_population, case, message):
    population, subjects, _, rooms, _ = small_population
    payload, templates = invalid_baseline(case, population, subjects, rooms)
    payload["faculty_loads"] = {str(member.code): 0 for member in scheduling.list_faculty}
    payload["faculty_subject_eligibility"] = {"0": ["ITE185"]}
    for row in payload["schedule"]:
        row.update(current_teaching_load=0, credit_units=0, eligible_subjects=["ITE185"])
    with pytest.raises((ValueError, RuntimeError), match=message):
        storage.payload_to_chromosome(payload, templates, scheduling.list_faculty, rooms)


@pytest.mark.parametrize("baseline_mode", ["saved", "uploaded"])
@pytest.mark.parametrize("case", ["unknown_day", "outside_calendar", "off_grid"])
def test_baseline_meetings_must_match_current_resource_calendars(
    small_population, monkeypatch, tmp_path, baseline_mode, case,
):
    population, templates, _, rooms, _ = small_population
    payload = storage.chromosome_to_payload(population[0], 0)
    offering = ("ITE185", "4A")
    original = rows_for(payload, offering)[0]
    base = without_component(payload, offering, "Lecture")
    if case == "unknown_day":
        replacement = dict(original, day="SUN", start="19:00", end="22:00")
    elif case == "outside_calendar":
        replacement = dict(original, day="M", start="03:00", end="06:00")
    else:
        # Start inside an otherwise free 3.5-hour period, offset from its grid.
        window = period(base, original, 210, templates)
        start = scheduling.time_to_minutes(window["start"]) + 15
        replacement = dict(window, start=storage.minutes_to_time(start), end=storage.minutes_to_time(start + 180))
    payload["schedule"] = base + [replacement]
    monkeypatch.setattr(storage, "SAVED_CHROMOSOME_DIR", tmp_path)
    monkeypatch.setattr(storage, "BEST_CHROMOSOME_PATH", tmp_path / "best.json")
    monkeypatch.setattr(storage, "UPLOADED_CHROMOSOME_PATH", tmp_path / "uploaded.json")
    path = storage.BEST_CHROMOSOME_PATH if baseline_mode == "saved" else storage.UPLOADED_CHROMOSOME_PATH
    storage.write_payload(payload, path)
    loaded = storage.load_saved_best_payload() if baseline_mode == "saved" else storage.load_uploaded_payload()
    with pytest.raises(ValueError, match="current resource time blocks"):
        storage.payload_to_chromosome(loaded, templates, scheduling.list_faculty, rooms)
