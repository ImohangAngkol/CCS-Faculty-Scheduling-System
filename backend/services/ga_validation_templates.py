"""Detached validation inputs, never the mutable population or working state.

Resource calendars can point back into every generated assignment. Copying
those graphs for a read-only validation is costly and unnecessary: the existing
publication gate rebuilds assignments from schedule rows. Preserve all profile,
calendar, preference, fixed-schedule and preassignment metadata, while omitting
only assignment references which that reconstruction replaces.
"""
import copy


CALENDARS = tuple(f"time_blocks_{day}" for day in (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"))
ASSIGNMENTS = {
    "assigned_faculty": None, "assigned_room": None, "lecture_room": None,
    "laboratory_room": None, "scheduled_time_blocks": None,
    "lecture_time_blocks": [], "laboratory_time_blocks": [],
    "lecture_room_time_blocks": [], "laboratory_room_time_blocks": [],
}


def validation_templates(templates):
    subjects, faculty, rooms = templates
    owners = [*subjects, *faculty, *rooms]
    owners += [subject.section for subject in subjects]
    owners += [subject.preassigned_instructor for subject in subjects
               if getattr(subject, "preassigned_instructor", None) is not None]
    owners = list({id(owner): owner for owner in owners}.values())
    memo = {id(owner): object.__new__(type(owner)) for owner in owners}
    # Allocate every authoritative calendar cell first to preserve aliasing.
    blocks = {id(block): block for owner in owners for field in CALENDARS
              for block in getattr(owner, field, [])}
    memo.update({identity: object.__new__(type(block)) for identity, block in blocks.items()})
    for identity, block in blocks.items():
        fields = dict(vars(block))
        for field in ("faculty", "instructor", "section", "subject"):
            if field in fields and not isinstance(fields[field], (str, int, float, bool, type(None))):
                fields[field] = None
        # A room object is an assignment reference; its name is resource metadata.
        if fields.get("room") is not None and not isinstance(fields["room"], str):
            fields["room"] = getattr(fields["room"], "name", fields["room"])
        memo[identity].__dict__.update(copy.deepcopy(fields, memo))
    subject_ids = {id(subject) for subject in subjects}
    for owner in owners:
        fields = dict(vars(owner))
        if id(owner) in subject_ids:
            fields.update({field: [] if isinstance(value, list) else value
                           for field, value in ASSIGNMENTS.items()})
        if hasattr(owner, "subjects_assigned"):
            fields.update(subjects_assigned=[], current_teaching_load=0)
        memo[id(owner)].__dict__.update(copy.deepcopy(fields, memo))
    return copy.deepcopy(templates, memo)
