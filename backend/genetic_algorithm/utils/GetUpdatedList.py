import copy

from Functions import list_faculty, lst_rooms


def get_updated_lists(chromosome):
    """
    Generate updated list_rooms and list_faculty
    based only on the selected chromosome.

    Parameters
    ----------
    chromosome : list
        Selected chromosome containing scheduled Subject objects.

    Returns
    -------
    updated_list_rooms
    updated_list_faculty
    """

    # ---------------------------------------------------------
    # Create fresh copies of the ORIGINAL resources
    # ---------------------------------------------------------

    updated_list_rooms = copy.deepcopy(lst_rooms)
    updated_list_faculty = copy.deepcopy(list_faculty)


    # ---------------------------------------------------------
    # Lookups
    # ---------------------------------------------------------

    faculty_lookup = {
        faculty.code: faculty
        for faculty in updated_list_faculty
    }

    room_lookup = {
        room.name: room
        for room in updated_list_rooms
    }


    # ---------------------------------------------------------
    # Reset faculty schedules
    # ---------------------------------------------------------

    for faculty in updated_list_faculty:

        faculty.current_teaching_load = 0
        faculty.subjects_assigned = []

        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday"
        ]:

            blocks = getattr(
                faculty,
                f"time_blocks_{day}"
            )

            for block in blocks:

                block.is_available = True
                block.subject = None
                block.instructor = None
                block.section = None
                block.type = None


    # ---------------------------------------------------------
    # Reset room schedules
    # ---------------------------------------------------------

    for room in updated_list_rooms:

        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday"
        ]:

            blocks = getattr(
                room,
                f"time_blocks_{day}"
            )

            for block in blocks:

                block.is_available = True
                block.subject = None
                block.instructor = None
                block.section = None
                block.type = None
                block.room = room.name


    # ---------------------------------------------------------
    # Day mapping
    # ---------------------------------------------------------

    day_mapping = {
        "M": "monday",
        "T": "tuesday",
        "W": "wednesday",
        "TH": "thursday",
        "F": "friday",
        "S": "saturday"
    }


    def normalize_day(day):

        day = str(day).strip()

        return day_mapping.get(
            day.upper(),
            day.lower()
        )


    # ---------------------------------------------------------
    # Find corresponding TimeBlock in a Faculty/Room
    # ---------------------------------------------------------

    def find_block(
        resource,
        day,
        start_time,
        end_time
    ):

        day = normalize_day(day)

        blocks = getattr(
            resource,
            f"time_blocks_{day}",
            []
        )

        for block in blocks:

            if (
                str(block.start_time) == str(start_time)
                and
                str(block.end_time) == str(end_time)
            ):

                return block

        return None


    # ---------------------------------------------------------
    # Process chromosome
    # ---------------------------------------------------------

    for subject in chromosome:

        original_faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        if original_faculty is None:
            continue


        # =====================================================
        # FACULTY
        # =====================================================

        faculty = faculty_lookup.get(
            original_faculty.code
        )

        if faculty is None:
            continue


        # Add subject
        faculty.subjects_assigned.append(
            subject
        )

        # Update load
        faculty.current_teaching_load += (
            getattr(
                subject,
                "credit_units",
                0
            )
            or 0
        )


        # =====================================================
        # LECTURE
        # =====================================================

        lecture_room = getattr(
            subject,
            "lecture_room",
            None
        )

        updated_lecture_room = None

        if lecture_room is not None:

            updated_lecture_room = room_lookup.get(
                lecture_room.name
            )


        lecture_blocks = getattr(
            subject,
            "lecture_time_blocks",
            []
        ) or []


        for entry in lecture_blocks:

            if (
                isinstance(entry, tuple)
                and len(entry) == 2
            ):

                day, original_block = entry

            else:

                original_block = entry

                day = getattr(
                    original_block,
                    "day_code",
                    None
                )


            if day is None:
                continue


            # ---------------------------------------------
            # Faculty block
            # ---------------------------------------------

            faculty_block = find_block(
                faculty,
                day,
                original_block.start_time,
                original_block.end_time
            )


            if faculty_block is not None:

                faculty_block.is_available = False
                faculty_block.subject = subject
                faculty_block.instructor = faculty
                faculty_block.faculty = faculty
                faculty_block.section = subject.section
                faculty_block.type = "Lecture"
                faculty_block.day_code = day


            # ---------------------------------------------
            # Room block
            # ---------------------------------------------

            if updated_lecture_room is not None:

                room_block = find_block(
                    updated_lecture_room,
                    day,
                    original_block.start_time,
                    original_block.end_time
                )


                if room_block is not None:

                    room_block.is_available = False
                    room_block.subject = subject
                    room_block.instructor = faculty
                    room_block.faculty = faculty
                    room_block.section = subject.section
                    room_block.type = "Lecture"
                    room_block.day_code = day
                    room_block.room = (
                        updated_lecture_room.name
                    )


        # =====================================================
        # LABORATORY
        # =====================================================

        laboratory_room = getattr(
            subject,
            "laboratory_room",
            None
        )

        updated_laboratory_room = None


        if laboratory_room is not None:

            updated_laboratory_room = (
                room_lookup.get(
                    laboratory_room.name
                )
            )


        laboratory_blocks = getattr(
            subject,
            "laboratory_time_blocks",
            []
        ) or []


        for entry in laboratory_blocks:

            if (
                isinstance(entry, tuple)
                and len(entry) == 2
            ):

                day, original_block = entry

            else:

                original_block = entry

                day = getattr(
                    original_block,
                    "day_code",
                    None
                )


            if day is None:
                continue


            # ---------------------------------------------
            # Faculty block
            # ---------------------------------------------

            faculty_block = find_block(
                faculty,
                day,
                original_block.start_time,
                original_block.end_time
            )


            if faculty_block is not None:

                faculty_block.is_available = False
                faculty_block.subject = subject
                faculty_block.instructor = faculty
                faculty_block.faculty = faculty
                faculty_block.section = subject.section
                faculty_block.type = "Laboratory"
                faculty_block.day_code = day


            # ---------------------------------------------
            # Room block
            # ---------------------------------------------

            if updated_laboratory_room is not None:

                room_block = find_block(
                    updated_laboratory_room,
                    day,
                    original_block.start_time,
                    original_block.end_time
                )


                if room_block is not None:

                    room_block.is_available = False
                    room_block.subject = subject
                    room_block.instructor = faculty
                    room_block.faculty = faculty
                    room_block.section = subject.section
                    room_block.type = "Laboratory"
                    room_block.day_code = day
                    room_block.room = (
                        updated_laboratory_room.name
                    )


    return (
        updated_list_rooms,
        updated_list_faculty
    )