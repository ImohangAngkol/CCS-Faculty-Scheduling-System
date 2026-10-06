import random
import copy

from genetic_algorithm.utils.Functions import (
    df_faculty_pref,
    get_subject_schedule_entries,
    find_resource_conflicts,
    faculty_assignment_is_valid,
    validate_preassigned_assignments,
)
from genetic_algorithm.models.PreassignedAssignment import is_preassigned

from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)

def chromosome_has_eligibility_violation(chromosome):
    """
    HARD constraint:
    GA faculty require explicit CSV eligibility. External assignments
    must match their declared instructor, locked room, and meeting hours.
    """
    return (
        any(not faculty_assignment_is_valid(subject) for subject in chromosome)
        or not validate_preassigned_assignments(chromosome, raise_error=False)
    )

def chromosome_has_conflicts(
    chromosome
):
    """
    Return True if chromosome contains:

        - faculty conflict
        - room conflict
        - section conflict

    Student conflict is represented by section conflict
    because students belonging to the same section attend
    the same section schedule.
    """

    all_entries = []

    # ==========================================
    # Extract schedules
    # ==========================================

    for subject in chromosome:

        entries = (
            get_subject_schedule_entries(
                subject
            )
        )

        all_entries.extend(
            entries
        )

    # ==========================================
    # Check FACULTY conflicts
    # ==========================================

    faculty_conflicts = (
        find_resource_conflicts(
            all_entries,
            "faculty"
        )
    )

    if faculty_conflicts:
        return True

    # ==========================================
    # Check ROOM conflicts
    # ==========================================

    room_conflicts = (
        find_resource_conflicts(
            all_entries,
            "room"
        )
    )

    if room_conflicts:
        return True

    # ==========================================
    # Check SECTION conflicts
    #
    # This also represents STUDENT conflicts
    # because students belong to sections.
    # ==========================================

    section_conflicts = (
        find_resource_conflicts(
            all_entries,
            "section"
        )
    )

    if section_conflicts:
        return True

    return False


def calculate_faculty_loads(chromosome):
    """
    Recalculate teaching loads directly from chromosome assignments.

    This is safer for crossover validation than relying on a Faculty
    object's cached current_teaching_load, because crossover changes
    subject-to-faculty assignments inside a copied chromosome.
    """

    loads = {}

    for subject in chromosome:

        faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        if faculty is None or getattr(faculty, "is_external", False):
            continue

        units = (
            getattr(
                subject,
                "credit_units",
                0
            )
            or 0
        )

        loads[faculty.code] = (
            loads.get(
                faculty.code,
                0
            )
            + units
        )

    return loads


def chromosome_has_load_violation(chromosome):
    """
    Check HARD faculty teaching-load violations after crossover.

    Confirmed project workload rules:
      * underload is SOFT and belongs in the fitness function;
      * overload above the faculty target is allowed when necessary;
      * only the absolute teaching-load ceiling is HARD.
    """

    loads = calculate_faculty_loads(
        chromosome
    )

    faculty_objects = {}

    for subject in chromosome:

        faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        if faculty is not None and not getattr(faculty, "is_external", False):
            faculty_objects[
                faculty.code
            ] = faculty

    for code, faculty in faculty_objects.items():

        load = loads.get(
            code,
            0
        )

        absolute_max = getattr(
            faculty,
            "absolute_max_teaching_load",
            getattr(
                faculty,
                "max_teaching_load",
                40
            )
        )

        if load > absolute_max:
            return True

    return False

def create_child_by_faculty_swap(
    parent1,
    parent2,
    df_faculty_pref,
    max_attempts=100
):
    """
    Create one new chromosome from two tournament-selected parents.

    Procedure
    ---------
    1. Receive two parents already chosen by Tournament Selection.
    2. Calculate their fitness values.
    3. Use the parent with LOWER fitness as the base chromosome.
    4. Randomly select a matching subject-section pair.
    5. Replace the faculty assignment in the base chromosome
       using the faculty assignment from the other parent.
    6. Check faculty, room, section, and student conflicts.
    7. Calculate the new fitness.
    8. Accept the child ONLY when:

           child_fitness < parent1_fitness
           AND
           child_fitness < parent2_fitness

    LOWER FITNESS = BETTER.

    Returns
    -------
    child, child_fitness, parent1_fitness, parent2_fitness

    If no improved child is found after max_attempts,
    returns None.
    """

    # =====================================================
    # Parents are supplied by Tournament Selection.
    # This crossover must NOT choose parents internally.
    # =====================================================

    if parent1 is None or parent2 is None:
        raise ValueError(
            "Both parent1 and parent2 are required."
        )

    if parent1 is parent2:
        raise ValueError(
            "Crossover requires two different parent chromosome objects."
        )

    # =====================================================
    # Calculate parent fitness
    # =====================================================

    parent1_fitness = faculty_preference_fitness(
        parent1,
        df_faculty_pref
    )

    parent2_fitness = faculty_preference_fitness(
        parent2,
        df_faculty_pref
    )

    print("=" * 60)
    print("SELECTED PARENTS")
    print("=" * 60)

    print(
        f"Parent 1 Fitness : {parent1_fitness}"
    )

    print(
        f"Parent 2 Fitness : {parent2_fitness}"
    )

    # =====================================================
    # Determine BETTER parent
    # =====================================================

    if parent1_fitness <= parent2_fitness:

        better_parent = parent1
        donor_parent = parent2

        better_parent_fitness = parent1_fitness

    else:

        better_parent = parent2
        donor_parent = parent1

        better_parent_fitness = parent2_fitness

    print(
        f"\nBetter Parent Fitness: "
        f"{better_parent_fitness}"
    )

    # =====================================================
    # Create lookup of subjects from donor parent
    #
    # Key:
    #     (subject number, section code)
    # =====================================================

    donor_subjects = {}

    for subject in donor_parent:

        section = getattr(
            subject,
            "section",
            None
        )

        if section is None:
            continue

        key = (
            str(subject.number),
            str(section.code)
        )

        donor_subjects[key] = subject

    # =====================================================
    # Find subjects existing in BOTH chromosomes
    # =====================================================

    matching_subjects = []

    for subject in better_parent:

        if is_preassigned(subject):
            continue

        section = getattr(
            subject,
            "section",
            None
        )

        if section is None:
            continue

        key = (
            str(subject.number),
            str(section.code)
        )

        if key not in donor_subjects:
            continue

        donor_subject = donor_subjects[key]

        if is_preassigned(donor_subject):
            continue

        # ---------------------------------------------
        # Only useful when faculty assignments differ
        # ---------------------------------------------

        better_faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        donor_faculty = getattr(
            donor_subject,
            "assigned_faculty",
            None
        )

        if (
            better_faculty is None
            or donor_faculty is None
            or getattr(better_faculty, "is_external", False)
            or getattr(donor_faculty, "is_external", False)
        ):
            continue

        if (
            better_faculty.code
            != donor_faculty.code
        ):
            matching_subjects.append(
                key
            )

    # =====================================================
    # No possible faculty swap
    # =====================================================

    if not matching_subjects:

        print(
            "\nNo matching subject-section "
            "with different faculty assignments."
        )

        return None

    # =====================================================
    # Try crossover repeatedly
    # =====================================================

    for attempt in range(
        1,
        max_attempts + 1
    ):

        # -------------------------------------------------
        # Always start again from the BETTER parent
        # -------------------------------------------------

        child = copy.deepcopy(
            better_parent
        )

        # -------------------------------------------------
        # Randomly select subject-section
        # -------------------------------------------------

        selected_key = random.choice(
            matching_subjects
        )

        subject_number = selected_key[0]
        section_code = selected_key[1]

        # -------------------------------------------------
        # Find subject in CHILD
        # -------------------------------------------------

        child_subject = None

        for subject in child:

            section = getattr(
                subject,
                "section",
                None
            )

            if section is None:
                continue

            if (
                str(subject.number)
                == subject_number
                and
                str(section.code)
                == section_code
            ):

                child_subject = subject
                break

        # -------------------------------------------------
        # Find corresponding subject in DONOR
        # -------------------------------------------------

        donor_subject = donor_subjects[
            selected_key
        ]

        if child_subject is None:
            continue

        donor_faculty = getattr(
            donor_subject,
            "assigned_faculty",
            None
        )

        if donor_faculty is None:
            continue

        old_faculty = getattr(
            child_subject,
            "assigned_faculty",
            None
        )

        # =================================================
        # Find the same faculty object inside CHILD
        # =================================================

        replacement_faculty = None

        for subject in child:

            faculty = getattr(
                subject,
                "assigned_faculty",
                None
            )

            if (
                faculty is not None
                and
                faculty.code
                == donor_faculty.code
            ):

                replacement_faculty = faculty
                break

        # If the donor faculty does not yet exist
        # in this child, copy it.

        if replacement_faculty is None:

            replacement_faculty = copy.deepcopy(
                donor_faculty
            )

        # =================================================
        # STEP 1:
        # SWAP / REPLACE FACULTY
        # =================================================

        child_subject.assigned_faculty = (
            replacement_faculty
        )

        # -------------------------------------------------
        # Also update faculty reference stored
        # inside lecture/laboratory TimeBlocks
        # -------------------------------------------------

        child_blocks = (
            getattr(
                child_subject,
                "lecture_time_blocks",
                []
            )
            +
            getattr(
                child_subject,
                "laboratory_time_blocks",
                []
            )
        )

        for block_item in child_blocks:

            # Your chromosomes may contain:
            #
            #     (day_code, TimeBlock)
            #
            # or TimeBlock directly.

            if (
                isinstance(block_item, tuple)
                and
                len(block_item) == 2
            ):

                block = block_item[1]

            else:

                block = block_item

            block.faculty = replacement_faculty
            block.instructor = replacement_faculty

        print()
        print("-" * 60)

        print(
            f"Attempt {attempt}"
        )

        print(
            f"Subject : {subject_number}"
        )

        print(
            f"Section : {section_code}"
        )

        print(
            f"Old Faculty : "
            f"{getattr(old_faculty, 'code', None)}"
        )

        print(
            f"New Faculty : "
            f"{replacement_faculty.code}"
        )

        # =================================================
        # STEP 2:
        # CHECK HARD FACULTY-SUBJECT ELIGIBILITY
        # =================================================

        if chromosome_has_eligibility_violation(
            child
        ):

            print(
                "Result: Faculty is not explicitly "
                "eligible for this subject."
            )

            print(
                "Trying another faculty swap..."
            )

            continue

        # =================================================
        # STEP 3:
        # CHECK ALL RESOURCE CONFLICTS
        # =================================================

        if chromosome_has_conflicts(
            child
        ):

            print(
                "Result: Conflict detected."
            )

            print(
                "Trying another faculty swap..."
            )

            continue

        # =================================================
        # STEP 4:
        # CHECK HARD TEACHING-LOAD CEILING
        # =================================================

        if chromosome_has_load_violation(
            child
        ):

            print(
                "Result: Absolute teaching-load "
                "ceiling exceeded."
            )

            print(
                "Trying another faculty swap..."
            )

            continue

        # =================================================
        # NO HARD CONSTRAINT VIOLATIONS
        #
        # Calculate NEW FITNESS
        # =================================================

        child_fitness = (
            faculty_preference_fitness(
                child,
                df_faculty_pref
            )
        )

        print(
            f"New Fitness : {child_fitness}"
        )

        # =================================================
        # Child must beat BOTH parents
        # =================================================

        if (
            child_fitness
            < parent1_fitness
            and
            child_fitness
            < parent2_fitness
        ):

            print()
            print("=" * 60)
            print("NEW CHILD ACCEPTED")
            print("=" * 60)

            print(
                f"Parent 1 Fitness : "
                f"{parent1_fitness}"
            )

            print(
                f"Parent 2 Fitness : "
                f"{parent2_fitness}"
            )

            print(
                f"Child Fitness    : "
                f"{child_fitness}"
            )

            return child

        # =================================================
        # No improvement
        # Try another random subject
        # =================================================

        print(
            "Child is valid but does not "
            "improve both parents."
        )

        print(
            "Trying another swap..."
        )

    # =====================================================
    # No acceptable child found
    # =====================================================

    print()
    print(
        f"No improved child found after "
        f"{max_attempts} attempts."
    )

    return None
