import random
import copy

from genetic_algorithm.utils.Functions import (
    df_faculty_pref,
    get_subject_schedule_entries,
    find_resource_conflicts,
)

from genetic_algorithm.operators.FitnessFunction import (
    faculty_preference_fitness,
)

from genetic_algorithm.operators.ElitisimSelection import (
    elitism_selection,
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

def create_child_by_faculty_swap(
    population,
    df_faculty_pref,
    max_attempts=100
):
    """
    Create one new chromosome from two randomly selected parents.

    Procedure
    ---------
    1. Randomly select two parents.
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
    # Select TWO RANDOM parents
    # =====================================================

    if len(population) < 2:
        raise ValueError(
            "Population must contain at least two chromosomes."
        )

    parent1, parent2 = random.sample(
        population,
        2
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

        return "None"

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
        # CHECK ALL CONFLICTS
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
        # NO CONFLICTS
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

    return "None"