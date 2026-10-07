"""Validate new preference writes against read-only authoritative metadata.

Legacy saved preferences remain readable. This does not evaluate or change fitness.
"""

import re
from collections import defaultdict

from schemas.faculty_preference import FacultyPreferenceUpdate
from services.metadata_service import list_subject_metadata, resolve_normal_faculty

DAYS = {"M", "T", "W", "TH", "F", "S"}


def _minutes(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError("Preference times must use HH:MM format.")
    hour, minute = map(int, value.split(":"))
    if hour > 23 or minute > 59:
        raise ValueError("Preference times must be valid clock times.")
    return hour * 60 + minute


def _time_range(start, end):
    first, last = _minutes(start), _minutes(end)
    if not 450 <= first < last <= 1320:
        raise ValueError("Preference periods must fit between 07:30 and 22:00 and end after they start.")
    return last - first


def validate_preference_write(faculty_code: int, payload: FacultyPreferenceUpdate):
    faculty = resolve_normal_faculty(faculty_code)
    subjects = {subject.subject_code: subject for subject in list_subject_metadata(faculty, eligible_only=True)}
    if len(set(payload.preferred_subjects)) != len(payload.preferred_subjects):
        raise ValueError("Preferred subject ranks must be unique.")
    for code in payload.preferred_subjects:
        if code not in subjects:
            raise ValueError(f"{code} is not an explicitly eligible offered subject for this faculty.")
    if len(set(payload.preferred_days)) != len(payload.preferred_days) or any(day not in DAYS for day in payload.preferred_days):
        raise ValueError("Preferred days must be unique teaching days.")
    if payload.preferred_start_time is not None or payload.preferred_end_time is not None:
        _time_range(payload.preferred_start_time, payload.preferred_end_time)
    groups = defaultdict(list)
    ids = set()
    for block in payload.preferred_schedule_blocks:
        if not block.id.strip() or block.id in ids:
            raise ValueError("Each preference block needs a unique nonempty ID.")
        ids.add(block.id)
        if block.day not in DAYS:
            raise ValueError("Preference blocks must use a supported teaching day.")
        _time_range(block.start_time, block.end_time)
        if block.kind == "general":
            if block.subject_code or block.component or block.subject_title:
                raise ValueError("General preferred periods cannot contain subject or component information.")
            continue
        if block.subject_code not in payload.preferred_subjects:
            raise ValueError("Subject meeting preferences must belong to a ranked preferred subject.")
        groups[(block.subject_code, block.component)].append(block)
    for (code, kind), blocks in groups.items():
        component = next((item for item in subjects[code].components if item.type == kind), None)
        if component is None:
            raise ValueError(f"{code} does not have the requested {kind or 'unspecified'} component.")
        valid = any(
            pattern.meetings_per_week == len(blocks)
            and all(_minutes(block.end_time) - _minutes(block.start_time) == pattern.duration_minutes for block in blocks)
            and any(sorted(days) == sorted(block.day for block in blocks) for days in pattern.day_combinations)
            for pattern in component.meeting_patterns
        )
        if not valid:
            raise ValueError(f"{code} {kind} must use a complete supported meeting pattern with fixed durations and days.")
