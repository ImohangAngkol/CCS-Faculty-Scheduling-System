"""Read-only metadata adapters over current authoritative scheduling inputs."""

import re

import pandas as pd

from genetic_algorithm.utils import Functions as scheduling
from schemas.faculty import FacultyMetadata
from schemas.subject import (
    EligibilityRecordMetadata,
    FacultyEligibilityMetadata,
    MeetingPatternMetadata,
    OfferedSubjectMetadata,
    PreassignedInstructorMetadata,
    SubjectComponentMetadata,
    SubjectMetadata,
)
from services.identity_service import (
    OFFERING_SCOPE,
    course_identity,
    external_instructor_identity,
    normalize_code,
    offering_identity,
    resolve_faculty_identity,
    section_identity,
)


def resolve_normal_faculty(reference):
    identity = resolve_faculty_identity(reference)
    for faculty in scheduling.list_faculty:
        if faculty.code == identity.faculty_code and not getattr(faculty, "is_external", False):
            return faculty
    raise ValueError(f"Faculty '{reference}' is not in the normal scheduling pool.")


def faculty_metadata(faculty):
    identity = resolve_faculty_identity(faculty.code)
    return FacultyMetadata(
        faculty_id=identity.faculty_id,
        faculty_code=identity.faculty_code,
        display_code=identity.display_code,
        name=identity.name,
        seniority_level=faculty.seniority_level,
        admin_load=faculty.admin_load,
        research_load=faculty.research_load,
        extension_load=faculty.extension_load,
        current_teaching_load=faculty.current_teaching_load,
        required_teaching_load=faculty.required_teaching_load,
        absolute_max_teaching_load=faculty.absolute_max_teaching_load,
        specializations=list(faculty.specializations),
        eligible_subject_codes=sorted(faculty.eligible_subjects),
    )


def list_faculty_metadata():
    return [faculty_metadata(faculty) for faculty in scheduling.list_faculty
            if not getattr(faculty, "is_external", False)]


def component_metadata(component_type, hours):
    """Derive only meeting alternatives the current scheduler supports."""
    if component_type == "Lecture" and hours == 2:
        schedules = scheduling.defined_two_lec_hours
    elif component_type == "Lecture" and hours == 3:
        schedules = scheduling.defined_three_lec_hours
    elif component_type == "Laboratory" and hours == 3:
        schedules = scheduling.defined_three_lab_hours
    else:
        schedules = []

    patterns = {}
    for time_range, day_string in schedules:
        start, end = time_range.split("-")
        minutes = scheduling.convert_time_to_minutes(end) - scheduling.convert_time_to_minutes(start)
        days = scheduling.parse_day_codes(day_string)
        if (minutes <= 0 or minutes * len(days) != hours * 60
                or (component_type == "Laboratory" and len(days) != 1)):
            continue
        patterns.setdefault((len(days), minutes), set()).add(tuple(days))

    meeting_patterns = [
        MeetingPatternMetadata(
            meetings_per_week=count,
            duration_minutes=minutes,
            day_combinations=[list(days) for days in sorted(day_sets)],
        )
        for (count, minutes), day_sets in sorted(patterns.items())
    ]
    single = meeting_patterns[0] if len(meeting_patterns) == 1 else None
    return SubjectComponentMetadata(
        type=component_type,
        weekly_hours=hours,
        metadata_status="supported" if meeting_patterns else "unsupported",
        duration_minutes=single.duration_minutes if single else None,
        meetings_per_week=single.meetings_per_week if single else None,
        continuous=True if meeting_patterns else None,
        fixed_duration=bool(meeting_patterns),
        meeting_patterns=meeting_patterns,
    )


def _course_fields(subject):
    code = normalize_code(subject.number)
    match = re.match(r"[A-Z]+", code)
    prefix = match.group() if match else ""
    primary = str(subject.primary_domain or "").strip() or None
    domains = list(dict.fromkeys(
        domain for domain in [primary, *subject.secondary_domains] if domain
    ))
    return dict(
        course_id=course_identity(code),
        subject_code=code,
        subject_title=str(subject.title or "").strip(),
        units=subject.credit_units,
        lecture_hours=subject.lec_hours,
        laboratory_hours=subject.lab_hours,
        prefix=prefix,
        category=prefix if prefix in {"CCC", "ITD", "ITN", "ITE", "ISY"} else "OTHER",
        primary_domain=primary,
        domains=domains,
        components=[
            component_metadata(kind, hours)
            for kind, hours in (("Lecture", subject.lec_hours), ("Laboratory", subject.lab_hours))
            if hours > 0
        ],
    )


def _optional_text(value):
    return None if pd.isna(value) else str(value).strip() or None


def _eligibility_metadata(faculty, subject):
    records = []
    for _, row in scheduling.df_faculty_subject_eligibility.iterrows():
        # Match the authoritative loader's handling of malformed legacy codes.
        try:
            legacy_code = int(row["faculty_code"])
        except (TypeError, ValueError, KeyError):
            continue
        if (legacy_code == faculty.code
                and normalize_code(row["course_no"]) == normalize_code(subject.number)):
            records.append(EligibilityRecordMetadata(
                status=normalize_code(row["eligibility_status"]).lower(),
                basis=_optional_text(row.get("eligibility_basis")),
                source=_optional_text(row.get("source")),
                notes=_optional_text(row.get("notes")),
            ))
    return FacultyEligibilityMetadata(
        explicitly_eligible=scheduling.faculty_is_explicitly_eligible_for_subject(faculty, subject),
        records=records,
    )


def list_subject_metadata(faculty=None, eligible_only=False):
    grouped = {}
    for subject in scheduling.list_subjects:
        grouped.setdefault(normalize_code(subject.number), []).append(subject)

    result = []
    for code, subjects in sorted(grouped.items()):
        fields = _course_fields(subjects[0])
        eligibility = _eligibility_metadata(faculty, subjects[0]) if faculty is not None else None
        offerings = []
        for subject in sorted(subjects, key=lambda item: normalize_code(item.section.code)):
            section = normalize_code(subject.section.code)
            declaration = subject.preassigned_assignment
            preassigned = declaration is not None
            instructor = PreassignedInstructorMetadata(
                instructor_id=external_instructor_identity(declaration.instructor_id),
                display_name=declaration.instructor_name,
                locked_room=declaration.room_name,
            ) if preassigned else None
            offerings.append(OfferedSubjectMetadata(
                **_course_fields(subject),
                offering_id=offering_identity(code, section),
                offering_key=f"{code}::{section}",
                offering_scope=OFFERING_SCOPE,
                section_id=section_identity(section),
                section=section,
                year_level=subject.year_level,
                is_preassigned=preassigned,
                assignment_type=subject.assignment_type,
                preassigned_instructor=instructor,
                can_be_assigned=(eligibility.explicitly_eligible and not preassigned)
                    if eligibility is not None else None,
            ))
        if eligible_only and not any(offering.can_be_assigned for offering in offerings):
            continue
        locked_count = sum(offering.is_preassigned for offering in offerings)
        result.append(SubjectMetadata(
            **fields,
            is_preassigned=bool(locked_count),
            preassignment_status="all" if locked_count == len(offerings)
                else "some" if locked_count else "none",
            offerings=offerings,
            eligibility=eligibility,
        ))
    return result
