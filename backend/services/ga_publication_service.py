"""Non-mutating hard-constraint gate. No fitness, randomness or persistence."""
from collections import Counter

from genetic_algorithm.utils.Functions import get_fixed_section_schedule_entries, validate_preassigned_assignments
from services.chromosome_service import chromosome_to_payload, payload_to_chromosome


def validate_publication(chromosome, subjects, faculty, rooms):
    def key(subject):
        return str(subject.number), str(subject.section.code)

    expected = {key(subject): subject for subject in subjects}
    if Counter(map(key, chromosome)) != Counter(map(key, subjects)):
        raise ValueError("Publication rejected: required offerings are missing, duplicated or unknown.")
    for subject in chromosome:
        template = expected[key(subject)]
        if (subject.credit_units, subject.lec_hours, subject.lab_hours) != (
            template.credit_units, template.lec_hours, template.lab_hours
        ):
            raise ValueError(f"Publication rejected: {key(subject)} course metadata changed.")
        if subject.preassigned_assignment != template.preassigned_assignment:
            raise ValueError(f"Publication rejected: {key(subject)} preassignment declaration changed.")
        if get_fixed_section_schedule_entries(subject.section) != get_fixed_section_schedule_entries(template.section):
            raise ValueError(f"Publication rejected: {key(subject)} fixed institutional schedule changed.")
        for component in ("lecture", "laboratory"):
            room = getattr(subject, component + "_room")
            hours = getattr(template, "lec_hours" if component == "lecture" else "lab_hours")
            if hours and getattr(room, "type", None) != ("Lecture" if component == "lecture" else "Laboratory"):
                raise ValueError(f"Publication rejected: {key(subject)} {component} room compatibility violation.")
            for _, block in getattr(subject, component + "_time_blocks"):
                if getattr(block.faculty, "code", None) != getattr(subject.assigned_faculty, "code", None):
                    raise ValueError(f"Publication rejected: {key(subject)} meeting instructor is inconsistent.")
                block_room = getattr(block.room, "name", block.room)
                if str(block_room).replace(" ", "").upper() != str(getattr(room, "name", "")).replace(" ", "").upper():
                    raise ValueError(f"Publication rejected: {key(subject)} meeting room is inconsistent.")
    # Reconstruction uses deep copies of authoritative templates and rebuilds loads.
    # Reuses eligibility, resource conflict, 40-unit maximum, fixed/preassigned,
    # component duration/continuity, room type and resource calendar checks.
    try:
        validate_preassigned_assignments(chromosome)
        payload_to_chromosome(chromosome_to_payload(chromosome, 0), subjects, faculty, rooms)
    except (ValueError, RuntimeError) as error:
        raise ValueError(f"Publication rejected: {error}") from error
