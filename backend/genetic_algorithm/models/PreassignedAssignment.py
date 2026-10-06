"""Declared external assignments, separate from the GA faculty pool."""

import json
from dataclasses import dataclass

from genetic_algorithm.models.TimeBlock import TimeBlock


def normalize_room_name(value):
    return "".join(str(value).upper().split())


@dataclass(frozen=True)
class PreassignedAssignment:
    instructor_id: str
    instructor_name: str
    room_name: str


class ExternalInstructor:
    """A shared scheduling resource with no faculty workload target."""

    is_external = True

    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.subjects_assigned = []
        # Assignment bookkeeping only; never used for workload fitness.
        self.current_teaching_load = 0
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday"):
            blocks = []
            for start in range(7 * 60 + 30, 22 * 60, 30):
                end = start + 30
                blocks.append(TimeBlock(
                    f"{start // 60:02d}:{start % 60:02d}",
                    f"{end // 60:02d}:{end % 60:02d}",
                ))
            setattr(self, f"time_blocks_{day}", blocks)


def is_preassigned(subject):
    return getattr(subject, "preassigned_assignment", None) is not None


def apply_preassigned_assignments(subjects, config_path):
    """Bind configured offerings to shared resources using stable string IDs."""
    with config_path.open(encoding="utf-8") as file:
        config = json.load(file)
    instructors = {}
    for code, name in config["external_instructors"].items():
        if not code.startswith("external:") or not name.strip():
            raise ValueError("External instructors require an external: ID and a name.")
        instructors[code] = ExternalInstructor(code, name)
    offerings = {(str(s.number).upper(), str(s.section.code).upper()): s for s in subjects}
    for row in config["assignments"]:
        key = (row["course_no"].upper(), row["section"].upper())
        if key not in offerings:
            raise ValueError(f"Preassigned offering does not exist: {key}")
        subject = offerings[key]
        if is_preassigned(subject):
            raise ValueError(f"Duplicate preassigned offering: {key}")
        instructor = instructors[row["instructor_id"]]
        subject.preassigned_assignment = PreassignedAssignment(
            instructor.code, instructor.name, row["room"],
        )
        subject.preassigned_instructor = instructor
    return instructors


def declared_instructor_matches(subject, instructor):
    declaration = getattr(subject, "preassigned_assignment", None)
    return bool(
        declaration is not None
        and instructor is not None
        and getattr(instructor, "is_external", False)
        and instructor.code == declaration.instructor_id
        and instructor.name == declaration.instructor_name
    )


def preassigned_schedule_is_valid(subject):
    """Validate locked resources and required hours without fixing meeting times."""
    if not is_preassigned(subject):
        return True
    if not declared_instructor_matches(subject, subject.assigned_faculty):
        return False
    declaration = subject.preassigned_assignment
    for component, hours in (("lecture", subject.lec_hours), ("laboratory", subject.lab_hours)):
        blocks = getattr(subject, f"{component}_time_blocks", [])
        room = getattr(subject, f"{component}_room", None)
        if hours == 0:
            if blocks:
                return False
            continue
        if not blocks or normalize_room_name(getattr(room, "name", "")) != normalize_room_name(declaration.room_name):
            return False
        if room.type != ("Lecture" if component == "lecture" else "Laboratory"):
            return False
        intervals = []
        for day, block in blocks:
            start = sum(int(part) * factor for part, factor in zip(block.start_time.split(":"), (60, 1)))
            end = sum(int(part) * factor for part, factor in zip(block.end_time.split(":"), (60, 1)))
            if (day not in {"M", "T", "W", "TH", "F", "S"}
                    or end - start != 30
                    or not declared_instructor_matches(subject, getattr(block, "faculty", None))
                    or normalize_room_name(block.room) != normalize_room_name(declaration.room_name)):
                return False
            intervals.append((day, start, end))
        if len(set(intervals)) != len(intervals) or sum(end - start for _, start, end in intervals) != hours * 60:
            return False
        if component == "laboratory":
            ordered = sorted(intervals)
            if any(a[0] != z[0] or a[2] != z[1] for a, z in zip(ordered, ordered[1:])):
                return False
    return True
