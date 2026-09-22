import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from genetic_algorithm.models.TimeBlock import TimeBlock

from genetic_algorithm.utils.Functions import (
    get_subject_schedule_entries,
    find_resource_conflicts,
)


# ============================================================
# STORAGE
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

SAVED_CHROMOSOME_DIR = (
    BACKEND_DIR
    / "saved_chromosomes"
)

BEST_CHROMOSOME_PATH = (
    SAVED_CHROMOSOME_DIR
    / "best_chromosome.json"
)

UPLOADED_CHROMOSOME_PATH = (
    SAVED_CHROMOSOME_DIR
    / "uploaded_baseline.json"
)


# ============================================================
# HELPERS
# ============================================================

def ensure_storage_directory():
    SAVED_CHROMOSOME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def subject_section_key(
    subject_number,
    section_code,
):
    return (
        f"{str(subject_number).strip()}"
        f"::"
        f"{str(section_code).strip()}"
    )


def get_section_code(subject):
    section = getattr(
        subject,
        "section",
        None,
    )

    if section is None:
        return None

    return str(
        getattr(
            section,
            "code",
            section,
        )
    )


def get_faculty_code(subject):
    faculty = getattr(
        subject,
        "assigned_faculty",
        None,
    )

    if faculty is None:
        return None

    return str(
        getattr(
            faculty,
            "code",
            faculty,
        )
    )


def normalize_payload(payload):
    """
    Accept:

    1. Our chromosome JSON format.

    2. A previously downloaded API result:
       {
           "status": "success",
           "data": {
               "best_fitness": ...,
               "schedule": [...]
           }
       }

    3. Direct GA data:
       {
           "best_fitness": ...,
           "schedule": [...]
       }
    """

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Chromosome file must contain a JSON object."
        )


    # --------------------------------------------------------
    # API wrapper
    # --------------------------------------------------------

    if (
        "data" in payload
        and
        isinstance(
            payload["data"],
            dict,
        )
        and
        "schedule" in payload["data"]
    ):
        payload = payload["data"]


    # --------------------------------------------------------
    # Already our format
    # --------------------------------------------------------

    if (
        payload.get("format")
        ==
        "ccs-ga-chromosome"
    ):
        normalized = payload.copy()

    else:

        schedule = payload.get(
            "schedule"
        )

        if not isinstance(
            schedule,
            list,
        ):
            raise ValueError(
                "Chromosome JSON must contain a "
                "'schedule' array."
            )


        normalized = {
            "format":
                "ccs-ga-chromosome",

            "version":
                1,

            "best_fitness":
                payload.get(
                    "best_fitness"
                ),

            "created_at":
                payload.get(
                    "created_at"
                ),

            "schedule":
                schedule,
        }


    if not isinstance(
        normalized.get("schedule"),
        list,
    ):
        raise ValueError(
            "Chromosome JSON contains an invalid schedule."
        )


    return normalized


# ============================================================
# CHROMOSOME -> JSON
# ============================================================

def chromosome_to_payload(
    chromosome,
    fitness,
):
    """
    Convert a real Python chromosome into a portable JSON
    representation.

    The schedule is saved using the project's existing
    get_subject_schedule_entries() function.
    """

    schedule = []

    subject_keys = []


    for subject in chromosome:

        section_code = (
            get_section_code(
                subject
            )
        )


        subject_keys.append(
            subject_section_key(
                getattr(
                    subject,
                    "number",
                    "",
                ),
                section_code,
            )
        )


        entries = (
            get_subject_schedule_entries(
                subject
            )
        )

        schedule.extend(
            entries
        )


    return {
        "format":
            "ccs-ga-chromosome",

        "version":
            1,

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "best_fitness":
            float(fitness),

        "subject_keys":
            sorted(
                subject_keys
            ),

        "schedule":
            schedule,
    }


# ============================================================
# SAVE / LOAD JSON
# ============================================================

def write_payload(
    payload,
    path,
):
    ensure_storage_directory()

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
            ensure_ascii=False,
        )


def read_payload(
    path,
):
    if not path.exists():
        return None

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        return normalize_payload(
            json.load(file)
        )


def load_saved_best_payload():
    return read_payload(
        BEST_CHROMOSOME_PATH
    )


def load_uploaded_payload():
    return read_payload(
        UPLOADED_CHROMOSOME_PATH
    )


def save_uploaded_payload(
    payload,
):
    """
    Save a JSON chromosome uploaded from the frontend.

    Full compatibility with the current semester is checked
    when it is converted into a chromosome.
    """

    normalized = normalize_payload(
        payload
    )

    write_payload(
        normalized,
        UPLOADED_CHROMOSOME_PATH,
    )

    return normalized


# ============================================================
# AUTOMATIC BEST-CHROMOSOME SAVE
# ============================================================

def save_best_if_better(
    chromosome,
    fitness,
):
    """
    Save the chromosome when:

    - no saved chromosome exists
    - current data differs from the saved semester/data
    - current fitness is LOWER than saved fitness

    LOWER FITNESS = BETTER.
    """

    current_payload = (
        chromosome_to_payload(
            chromosome,
            fitness,
        )
    )


    existing_payload = (
        load_saved_best_payload()
    )


    should_save = False


    if existing_payload is None:

        should_save = True

    else:

        current_subjects = set(
            current_payload.get(
                "subject_keys",
                [],
            )
        )

        previous_subjects = set(
            existing_payload.get(
                "subject_keys",
                [],
            )
        )


        # Different semester / offering set.
        if (
            current_subjects
            and
            previous_subjects
            and
            current_subjects
            !=
            previous_subjects
        ):

            should_save = True

        else:

            old_fitness = (
                existing_payload.get(
                    "best_fitness"
                )
            )


            if old_fitness is None:

                should_save = True

            elif (
                float(fitness)
                <
                float(old_fitness)
            ):

                should_save = True


    if should_save:

        write_payload(
            current_payload,
            BEST_CHROMOSOME_PATH,
        )

        print()
        print("=" * 60)
        print("BEST CHROMOSOME SAVED")
        print("=" * 60)

        print(
            f"Fitness : {fitness}"
        )

        print(
            f"File    : "
            f"{BEST_CHROMOSOME_PATH}"
        )


        return (
            True,
            current_payload,
        )


    return (
        False,
        existing_payload,
    )


# ============================================================
# TIME HELPERS
# ============================================================

def time_to_minutes(
    value,
):
    hour, minute = map(
        int,
        str(value)
        .strip()
        .split(":"),
    )

    return (
        hour * 60
        +
        minute
    )


def minutes_to_time(
    value,
):
    hour = (
        value // 60
    )

    minute = (
        value % 60
    )

    return (
        f"{hour:02d}:"
        f"{minute:02d}"
    )


# ============================================================
# CREATE TIME BLOCKS FROM SAVED PERIOD
# ============================================================

def create_component_blocks(
    *,
    day_code,
    start_time,
    end_time,
    subject,
    faculty,
    room,
    schedule_type,
):
    """
    Expand:

        TH 09:30-11:30

    back into:

        TH 09:30-10:00
        TH 10:00-10:30
        TH 10:30-11:00
        TH 11:00-11:30
    """

    start_minutes = (
        time_to_minutes(
            start_time
        )
    )

    end_minutes = (
        time_to_minutes(
            end_time
        )
    )


    if (
        end_minutes
        <=
        start_minutes
    ):
        raise ValueError(
            "Baseline chromosome contains "
            "an invalid time range."
        )


    if (
        (
            end_minutes
            -
            start_minutes
        )
        % 30
        != 0
    ):
        raise ValueError(
            "Baseline schedule periods must "
            "use 30-minute increments."
        )


    blocks = []


    current = start_minutes


    while current < end_minutes:

        block_start = (
            minutes_to_time(
                current
            )
        )

        block_end = (
            minutes_to_time(
                current + 30
            )
        )


        block = TimeBlock(
            start_time=block_start,
            end_time=block_end,
            is_available=False,
            preferred=False,
            room=(
                getattr(
                    room,
                    "name",
                    None,
                )
                if room
                else None
            ),
        )


        # Keep the reconstructed block compatible with
        # existing crossover, mutation and analysis code.

        block.subject = subject

        block.faculty = faculty

        block.instructor = faculty

        block.section = getattr(
            subject,
            "section",
            None,
        )

        block.type = schedule_type

        block.day_code = (
            str(day_code)
            .strip()
            .upper()
        )

        block.day = block.day_code


        blocks.append(
            (
                block.day_code,
                block,
            )
        )


        current += 30


    return blocks


# ============================================================
# JSON -> REAL CHROMOSOME
# ============================================================

def payload_to_chromosome(
    payload,
    list_subjects,
    list_faculty,
    room_list,
):
    """
    Reconstruct a real chromosome using the CURRENT semester's
    Subject / Faculty / Room templates.

    This prevents an uploaded JSON file from silently injecting
    unknown faculty, rooms or subjects.
    """

    payload = normalize_payload(
        payload
    )


    schedule = payload[
        "schedule"
    ]


    if not schedule:
        raise ValueError(
            "Baseline chromosome contains no schedule entries."
        )


    # --------------------------------------------------------
    # Copy current semester objects
    # --------------------------------------------------------

    chromosome = deepcopy(
        list_subjects
    )


    faculty_objects = {
        str(faculty.code):
            deepcopy(faculty)

        for faculty
        in list_faculty
    }


    room_objects = {
        str(room.name):
            deepcopy(room)

        for room
        in room_list
    }


    # Reset copied faculty assignment state while preserving
    # preferences / priority / limits.

    for faculty in (
        faculty_objects.values()
    ):

        faculty.current_teaching_load = 0

        faculty.subjects_assigned = []


    # --------------------------------------------------------
    # Index current subjects
    # --------------------------------------------------------

    subject_map = {}


    for subject in chromosome:

        section_code = (
            get_section_code(
                subject
            )
        )


        key = subject_section_key(
            subject.number,
            section_code,
        )


        subject_map[key] = subject


        # Reset assignment state.

        subject.assigned_faculty = None

        subject.assigned_room = None

        subject.lecture_room = None

        subject.laboratory_room = None

        subject.scheduled_time_blocks = None

        subject.lecture_time_blocks = []

        subject.laboratory_time_blocks = []

        subject.lecture_room_time_blocks = []

        subject.laboratory_room_time_blocks = []


    # --------------------------------------------------------
    # Group uploaded rows by Subject + Section
    # --------------------------------------------------------

    grouped = {}


    for entry in schedule:

        subject_number = str(
            entry.get(
                "subject",
                "",
            )
        ).strip()


        section_code = str(
            entry.get(
                "section",
                "",
            )
        ).strip()


        key = subject_section_key(
            subject_number,
            section_code,
        )


        grouped.setdefault(
            key,
            [],
        ).append(
            entry
        )


    # --------------------------------------------------------
    # Compatibility check
    # --------------------------------------------------------

    expected_keys = set(
        subject_map.keys()
    )

    uploaded_keys = set(
        grouped.keys()
    )


    missing = (
        expected_keys
        -
        uploaded_keys
    )

    extra = (
        uploaded_keys
        -
        expected_keys
    )


    if missing:

        example = ", ".join(
            sorted(missing)[:5]
        )

        raise ValueError(
            "Baseline chromosome does not match "
            "the current subject offerings. "
            f"Missing: {example}"
        )


    if extra:

        example = ", ".join(
            sorted(extra)[:5]
        )

        raise ValueError(
            "Baseline chromosome contains subjects "
            "that are not in the current offerings. "
            f"Unknown: {example}"
        )


    # --------------------------------------------------------
    # Rebuild each Subject
    # --------------------------------------------------------

    for key, entries in (
        grouped.items()
    ):

        subject = (
            subject_map[key]
        )


        # ----------------------------------------------------
        # FACULTY
        # ----------------------------------------------------

        faculty_codes = {
            str(
                entry.get(
                    "faculty"
                )
            ).strip()

            for entry
            in entries

            if entry.get(
                "faculty"
            )
            is not None
        }


        if len(
            faculty_codes
        ) != 1:

            raise ValueError(
                f"{key} must have exactly one "
                "assigned faculty member."
            )


        faculty_code = next(
            iter(
                faculty_codes
            )
        )


        faculty = (
            faculty_objects.get(
                faculty_code
            )
        )


        if faculty is None:

            raise ValueError(
                f"Faculty {faculty_code} "
                "from the baseline file does not "
                "exist in the current faculty data."
            )


        subject.assigned_faculty = (
            faculty
        )


        # ----------------------------------------------------
        # PROCESS LECTURE / LAB
        # ----------------------------------------------------

        for schedule_type in (
            "Lecture",
            "Laboratory",
        ):

            component_entries = [

                entry

                for entry
                in entries

                if str(
                    entry.get(
                        "type",
                        ""
                    )
                )
                .strip()
                .lower()

                ==
                schedule_type.lower()

            ]


            if not component_entries:
                continue


            room_names = {
                str(
                    entry.get(
                        "room"
                    )
                ).strip()

                for entry
                in component_entries

                if entry.get(
                    "room"
                )
            }


            if len(
                room_names
            ) != 1:

                raise ValueError(
                    f"{key} {schedule_type} "
                    "must use exactly one room."
                )


            room_name = next(
                iter(
                    room_names
                )
            )


            room = (
                room_objects.get(
                    room_name
                )
            )


            if room is None:

                raise ValueError(
                    f"Room '{room_name}' from "
                    "the baseline file does not "
                    "exist in the current room data."
                )


            component_blocks = []


            for entry in (
                component_entries
            ):

                day = entry.get(
                    "day"
                )

                start = entry.get(
                    "start"
                )

                end = entry.get(
                    "end"
                )


                component_blocks.extend(
                    create_component_blocks(
                        day_code=day,
                        start_time=start,
                        end_time=end,
                        subject=subject,
                        faculty=faculty,
                        room=room,
                        schedule_type=schedule_type,
                    )
                )


            if (
                schedule_type
                ==
                "Lecture"
            ):

                subject.lecture_room = (
                    room
                )

                subject.lecture_time_blocks = (
                    component_blocks
                )


            else:

                subject.laboratory_room = (
                    room
                )

                subject.laboratory_time_blocks = (
                    component_blocks
                )


        # ----------------------------------------------------
        # GENERAL ASSIGNMENT STATE
        # ----------------------------------------------------

        subject.assigned_room = (
            subject.lecture_room
            or
            subject.laboratory_room
        )


        subject.scheduled_time_blocks = (
            subject.lecture_time_blocks
            +
            subject.laboratory_time_blocks
        )


        faculty.subjects_assigned.append(
            subject
        )


        faculty.current_teaching_load += (
            getattr(
                subject,
                "credit_units",
                0,
            )
            or 0
        )


    # --------------------------------------------------------
    # VALIDATE CONFLICTS
    # --------------------------------------------------------

    all_entries = []


    for subject in chromosome:

        all_entries.extend(
            get_subject_schedule_entries(
                subject
            )
        )


    for resource in (
        "faculty",
        "room",
        "section",
    ):

        conflicts = (
            find_resource_conflicts(
                all_entries,
                resource,
            )
        )


        if conflicts:

            raise ValueError(
                "Baseline chromosome is invalid: "
                f"{resource} conflict detected."
            )


    return chromosome


# ============================================================
# METADATA
# ============================================================

def get_saved_best_metadata():

    payload = (
        load_saved_best_payload()
    )


    if payload is None:

        return {
            "exists": False,
            "fitness": None,
            "created_at": None,
        }


    return {
        "exists": True,

        "fitness":
            payload.get(
                "best_fitness"
            ),

        "created_at":
            payload.get(
                "created_at"
            ),
    }


def get_best_chromosome_path():
    return BEST_CHROMOSOME_PATH