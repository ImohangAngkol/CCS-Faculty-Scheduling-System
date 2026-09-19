import random
import copy

from genetic_algorithm.utils.Functions import (
    df_faculty_pref,
    find_resource_conflicts,
)

from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)

from genetic_algorithm.operators.ElitisimSelection import (
    elitism_selection,
)

def get_subject_schedule_entries(subject):
    """Normalize lecture/lab schedules for conflict checking."""
    entries = []
    section = getattr(subject, "section", None)
    faculty = getattr(subject, "assigned_faculty", None)
    section_code = getattr(section, "code", None) if section else None
    faculty_code = getattr(faculty, "code", None) if faculty else None

    def add_entries(blocks, schedule_type, room):
        room_name = getattr(room, "name", None) if room else None
        for item in blocks or []:
            if isinstance(item, tuple) and len(item) == 2:
                day_code, block = item
            else:
                block = item
                day_code = getattr(block, "day_code", getattr(block, "day", None))
            entries.append({
                "subject": getattr(subject, "number", None),
                "title": getattr(subject, "title", None),
                "type": schedule_type,
                "day": day_code,
                "start": getattr(block, "start_time", None),
                "end": getattr(block, "end_time", None),
                "section": section_code,
                "faculty": faculty_code,
                "room": room_name,
            })

    add_entries(getattr(subject, "lecture_time_blocks", []), "Lecture",
                getattr(subject, "lecture_room", None))
    add_entries(getattr(subject, "laboratory_time_blocks", []), "Laboratory",
                getattr(subject, "laboratory_room", None))
    return entries


def update_subject_faculty_blocks(subject, new_faculty):
    """Synchronize faculty/instructor references in scheduled TimeBlocks."""
    blocks = list(getattr(subject, "lecture_time_blocks", []) or []) + \
             list(getattr(subject, "laboratory_time_blocks", []) or [])
    for item in blocks:
        block = item[1] if isinstance(item, tuple) and len(item) == 2 else item
        if hasattr(block, "faculty"):
            block.faculty = new_faculty
        if hasattr(block, "instructor"):
            block.instructor = new_faculty


def chromosome_has_conflicts(chromosome):
    """True when faculty, room, or section conflicts exist."""
    all_entries = []
    for subject in chromosome:
        all_entries.extend(get_subject_schedule_entries(subject))

    for resource in ("faculty", "room", "section"):
        if find_resource_conflicts(all_entries, resource):
            return True
    return False


def calculate_faculty_loads(chromosome):
    """Recalculate faculty teaching loads from subject assignments."""
    loads = {}
    for subject in chromosome:
        faculty = getattr(subject, "assigned_faculty", None)
        if faculty is None:
            continue
        units = getattr(subject, "credit_units", 0) or 0
        loads[faculty.code] = loads.get(faculty.code, 0) + units
    return loads


def chromosome_has_load_violation(chromosome):
    """Check min/max teaching loads after the swap."""
    loads = calculate_faculty_loads(chromosome)
    faculty_objects = {}
    for subject in chromosome:
        faculty = getattr(subject, "assigned_faculty", None)
        if faculty is not None:
            faculty_objects[faculty.code] = faculty

    for code, faculty in faculty_objects.items():
        load = loads.get(code, 0)
        minimum = getattr(faculty, "min_teaching_load", None)
        maximum = getattr(faculty, "max_teaching_load", None)
        if minimum is not None and load < minimum:
            return True
        if maximum is not None and load > maximum:
            return True
    return False


def mutate_by_swapping_faculty_subjects(population, df_faculty_pref,
                                         max_attempts=100, verbose=True):
    """
    Randomly select a chromosome, two faculty members, and one subject from
    each faculty. Swap only their faculty assignments. Restart on faculty,
    room, section, or teaching-load conflict. Accept only if the child's
    fitness is lower than the original chromosome's fitness.

    Requires existing project functions:
      faculty_preference_fitness(chromosome, df_faculty_pref)
      find_resource_conflicts(entries, resource_type)

    LOWER FITNESS = BETTER.
    """
    if not population:
        raise ValueError("Population is empty.")

    for attempt in range(1, max_attempts + 1):
        # Start again from chromosome selection on every failed attempt.
        original = random.choice(population)
        original_fitness = faculty_preference_fitness(original, df_faculty_pref)
        child = copy.deepcopy(original)

        faculty_subjects = {}
        for subject in child:
            faculty = getattr(subject, "assigned_faculty", None)
            if faculty is not None:
                faculty_subjects.setdefault(faculty.code, []).append(subject)

        valid_codes = [code for code, subjects in faculty_subjects.items() if subjects]
        if len(valid_codes) < 2:
            continue

        code1, code2 = random.sample(valid_codes, 2)
        subject1 = random.choice(faculty_subjects[code1])
        subject2 = random.choice(faculty_subjects[code2])
        faculty1 = subject1.assigned_faculty
        faculty2 = subject2.assigned_faculty

        # Swap faculty; section, schedule, and room remain unchanged.
        subject1.assigned_faculty = faculty2
        subject2.assigned_faculty = faculty1
        update_subject_faculty_blocks(subject1, faculty2)
        update_subject_faculty_blocks(subject2, faculty1)

        if verbose:
            print("=" * 70)
            print(f"MUTATION ATTEMPT {attempt}")
            print(f"Original Fitness: {original_fitness}")
            print(f"{subject1.number}-{subject1.section.code}: {faculty1.code} -> {faculty2.code}")
            print(f"{subject2.number}-{subject2.section.code}: {faculty2.code} -> {faculty1.code}")

        if chromosome_has_conflicts(child):
            if verbose:
                print("Rejected: faculty/room/section conflict. Restarting...\n")
            continue

        if chromosome_has_load_violation(child):
            if verbose:
                print("Rejected: teaching-load violation. Restarting...\n")
            continue

        child_fitness = faculty_preference_fitness(child, df_faculty_pref)
        if verbose:
            print(f"Mutated Fitness : {child_fitness}")

        if child_fitness < original_fitness:
            if verbose:
                print("MUTATION ACCEPTED")
                print(f"Improvement     : {original_fitness - child_fitness}\n")
            return child

        if verbose:
            print("Rejected: fitness did not improve. Restarting...\n")

    if verbose:
        print(f"No improved mutation found after {max_attempts} attempts.")
    return None


# Example:
# result = mutate_by_swapping_faculty_subjects(
#     population=non_elites,
#     df_faculty_pref=df_faculty_pref,
#     max_attempts=100
# )
# if result is not None:
#     mutated_child, mutated_fitness, original_fitness = result
