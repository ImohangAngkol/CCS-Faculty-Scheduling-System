"""Targeted external-resource checks; no GA generations or persistence writes."""

import copy
import importlib
import json

import pytest

from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.models.PreassignedAssignment import ExternalInstructor, PreassignedAssignment
from genetic_algorithm.models.Room import Room
from genetic_algorithm.models.Section import Section
from genetic_algorithm.models.Subject import Subject
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from genetic_algorithm.utils import Functions as scheduling
from services.chromosome_service import chromosome_to_payload, payload_to_chromosome


@pytest.fixture
def resources(monkeypatch):
    external = ExternalInstructor("external:test-instructor", "External instructor")
    room = Room("ICT 3A", "Lecture")
    other_room = Room("ICT 3B", "Lecture")
    subjects = [Subject(code, code, 3, 3, 0, Section(section))
                for code, section in (("PRE1", "TEST-A"), ("PRE2", "TEST-B"),
                                      ("GA1", "TEST-C"), ("GA2", "TEST-D"))]
    for subject in subjects[:2]:
        subject.preassigned_assignment = PreassignedAssignment(external.code, external.name, "ICT3A")
        subject.preassigned_instructor = external
    faculty = [Faculty(0, 1, eligible_subjects={"GA1", "GA2"}),
               Faculty(1, 2, eligible_subjects={"GA1", "GA2"})]
    monkeypatch.setattr(scheduling, "list_subjects", subjects)
    monkeypatch.setattr(scheduling, "list_faculty", faculty)
    return subjects, faculty, external, [room, other_room]


def assign(subject, instructor, period, rooms):
    return scheduling.assign_schedule_to_faculty(
        instructor, subject, period, "Lecture", room_list=rooms,
    )


def complete(resources):
    subjects, faculty, external, rooms = resources
    for subject, instructor, period in zip(
            subjects, [external, external, *faculty],
            [("7:30 - 10:30", "M"), ("7:30 - 10:30", "T"),
             ("10:30 - 13:30", "M"), ("10:30 - 13:30", "T")]):
        assert assign(subject, instructor, period, rooms)
    return subjects


def assert_locks(subjects):
    assert scheduling.validate_preassigned_assignments(subjects)
    for subject in subjects[:2]:
        assert subject.assigned_faculty.code == "external:test-instructor"
        assert subject.lecture_room.name == "ICT 3A"


def test_authoritative_ite184_config_and_normal_preflight():
    # Read fresh templates, independent of test fixture resource substitutions.
    from genetic_algorithm.utils.Functions import list_subjects, list_faculty
    offerings = [subject for subject in list_subjects if subject.number == "ITE184"]
    assert {subject.section.code for subject in offerings} == {"4A", "4B"}
    assert len(list_faculty) == 11
    assert offerings[0].preassigned_instructor is offerings[1].preassigned_instructor
    for subject in offerings:
        assert subject.assignment_type == "preassigned_external"
        assert subject.preassigned_assignment.instructor_id == "external:eddie-bouy-palad"
        assert subject.preassigned_assignment.instructor_name == "Atty. Eddie Bouy Palad"
        assert subject.preassigned_assignment.room_name == "ICT3A"
        assert not any(scheduling.faculty_is_explicitly_eligible_for_subject(f, subject)
                       for f in list_faculty)


def test_external_overlap_and_future_preassignment(resources):
    subjects, _, external, rooms = resources
    assert assign(subjects[0], external, ("7:30 - 10:30", "M"), rooms)
    assert not assign(subjects[1], external, ("7:30 - 10:30", "M"), rooms)
    # A future course in a DIFFERENT locked room still shares Palad's calendar.
    subjects[1].preassigned_assignment = PreassignedAssignment(external.code, external.name, "ICT3B")
    assert not assign(subjects[1], external, ("7:30 - 10:30", "M"), rooms)
    assert assign(subjects[1], external, ("10:30 - 13:30", "M"), rooms)


def test_room_and_section_conflicts_apply(resources):
    subjects, faculty, external, rooms = resources
    assert assign(subjects[0], external, ("7:30 - 10:30", "M"), rooms)
    assert not assign(subjects[2], faculty[0], ("7:30 - 10:30", "M"), [rooms[0]])
    subjects[2].section = subjects[0].section
    assert not assign(subjects[2], faculty[0], ("7:30 - 10:30", "M"), [rooms[1]])


def test_reset_and_rollback_preserve_declarations(resources):
    subjects, faculty, external, rooms = resources
    complete(resources)
    declarations = [s.preassigned_assignment for s in subjects[:2]]
    scheduling.rollback_subject_assignment(subjects[0])
    assert subjects[0].preassigned_assignment is declarations[0]
    assert subjects[0].preassigned_instructor is external
    scheduling.reset_complete_schedule(faculty, subjects, rooms)
    assert external.current_teaching_load == 0
    assert not external.subjects_assigned
    assert all(block.is_available for blocks in scheduling.get_faculty_day_blocks(external).values()
               for block in blocks)
    assert all(block.is_available for room in rooms
               for blocks in scheduling.get_room_day_blocks(room).values() for block in blocks)
    assert [s.preassigned_assignment for s in subjects[:2]] == declarations
    complete(resources)
    assert_locks(subjects)


def test_locked_identity_room_duration_and_ga_eligibility(resources):
    subjects, faculty, external, rooms = resources
    assert not assign(subjects[0], faculty[0], ("7:30 - 10:30", "M"), rooms)
    assert not assign(subjects[2], external, ("7:30 - 10:30", "M"), rooms)
    assert not assign(subjects[0], external, ("7:30 - 10:30", "M"), [rooms[1]])
    complete(resources)
    assert scheduling.validate_faculty_subject_eligibility(subjects)
    subjects[2].assigned_faculty.eligible_subjects.clear()
    assert not scheduling.validate_faculty_subject_eligibility(subjects, raise_error=False)
    subjects[0].lecture_time_blocks.pop()
    assert not scheduling.validate_preassigned_assignments(subjects, raise_error=False)


def test_external_is_excluded_from_fitness_and_load_ceiling(resources):
    subjects, _, external, _ = resources
    complete(resources)
    external.current_teaching_load = 100
    external.required_teaching_load = 24
    external.absolute_max_teaching_load = 40
    assert faculty_preference_fitness(subjects) == faculty_preference_fitness(subjects[2:])
    for module_name in ("Swap", "mutation"):
        operator = importlib.import_module(f"genetic_algorithm.operators.{module_name}")
        assert external.code not in operator.calculate_faculty_loads(subjects)
        assert not operator.chromosome_has_load_violation(subjects)
        subjects[2].credit_units = 41
        assert operator.chromosome_has_load_violation(subjects)
        subjects[2].credit_units = 3


def test_json_roundtrip_and_tampered_locks(resources):
    subjects, faculty, _, rooms = resources
    complete(resources)
    payload = json.loads(json.dumps(chromosome_to_payload(subjects, 0)))
    external_rows = [r for r in payload["schedule"] if r.get("assignment_type") == "preassigned_external"]
    assert len(external_rows) == 2
    assert all(r["faculty_name"] == "External instructor" for r in external_rows)
    restored = payload_to_chromosome(payload, subjects, faculty, rooms)
    assert_locks(restored)
    assert restored[0].preassigned_instructor is restored[1].preassigned_instructor
    assert not scheduling.schedule_is_available(restored[0].preassigned_instructor, "M", "7:30 - 10:30")
    for change, value in (("faculty", "0"), ("room", "ICT 3B"), ("end", "09:30")):
        tampered = copy.deepcopy(payload)
        tampered["schedule"][0][change] = value
        # Uploaded flags cannot downgrade current authoritative declarations.
        tampered["schedule"][0]["assignment_type"] = "ga_managed"
        with pytest.raises(ValueError):
            payload_to_chromosome(tampered, subjects, faculty, rooms)


def test_mutation_preserves_locked_resources(resources, monkeypatch):
    subjects = complete(resources)
    mutation = importlib.import_module("genetic_algorithm.operators.mutation")
    monkeypatch.setattr(mutation, "faculty_preference_fitness",
                        lambda chromosome, _: 100 if chromosome[2].assigned_faculty.code == 0 else 0)
    child = mutation.mutate_by_swapping_faculty_subjects([subjects], None, max_attempts=1, verbose=False)
    assert child is not None
    assert_locks(child)
    assert_locks(subjects)


def test_crossover_preserves_locked_resources(resources, monkeypatch):
    subjects = complete(resources)
    swap = importlib.import_module("genetic_algorithm.operators.Swap")
    donor = copy.deepcopy(subjects)
    donor[2].assigned_faculty, donor[3].assigned_faculty = donor[3].assigned_faculty, donor[2].assigned_faculty
    def fitness(chromosome, _):
        codes = tuple(s.assigned_faculty.code for s in chromosome[2:])
        return {(0, 1): 100, (1, 0): 150}.get(codes, 0)
    monkeypatch.setattr(swap, "faculty_preference_fitness", fitness)
    monkeypatch.setattr(swap.random, "choice", lambda choices: choices[0])
    child = swap.create_child_by_faculty_swap(subjects, donor, None, max_attempts=1)
    assert child is not None
    assert_locks(child)
    assert_locks(subjects)
