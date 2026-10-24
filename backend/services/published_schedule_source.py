"""Guarded publication provenance/catalog; default unavailable, never GA fallback."""
from contextlib import contextmanager,ExitStack
from dataclasses import dataclass,replace,asdict
import copy
from typing import Callable
from services import adjustment_schedule_service as schedules
from services.schedule_service import problem


@dataclass(frozen=True)
class PublicationContext:
    source: schedules.ReviewSchedule
    publication_reference: str
    policy_reference: str
    session_factory: Callable
    templates: tuple
    faculty_codes: tuple[tuple[str,str],...]
    subject_codes: tuple[tuple[str,str],...]
    section_codes: tuple[tuple[str,str],...]
    capacity_applicability: str
    capacity_reference: str
    section_enrollment: tuple[tuple[str,int],...]
    room_capacity: tuple[tuple[str,int],...]


def institutional_publication_source(): return None


@contextmanager
def context(required=True):
    with ExitStack() as stack:
        try:
            provider=institutional_publication_source()
            if provider is None:
                if required:raise ValueError()
                yield None;return
            value=stack.enter_context(provider)
            if (not isinstance(value,PublicationContext) or not value.publication_reference or not value.policy_reference
                or not value.capacity_reference or value.capacity_applicability not in {'required','not_applicable'}
                or not value.source.academic_year or not value.source.term or len(value.source.revision)!=64
                or not isinstance(value.source,schedules.ReviewSchedule) or len(value.templates)!=3
                or len(value.source.meetings)>1000):raise ValueError()
            for pairs in (value.faculty_codes,value.subject_codes,value.section_codes,value.section_enrollment,value.room_capacity):
                if len(dict(pairs))!=len(pairs):raise ValueError()
            from services.identity_service import resolve_faculty_identity
            for id,code in value.faculty_codes:
                if str(code).isdecimal() and str(resolve_faculty_identity(id).faculty_code)!=str(code):raise ValueError()
        except Exception:raise problem(503,'PUBLISHED_SOURCE_UNAVAILABLE','A verified published schedule, term, resource policy and source guard are required. No GA proposal is promoted automatically.') from None
        yield value


def key(ctx):return schedules.digest({'schedule':ctx.source.schedule_id,'academic_year':ctx.source.academic_year,'term':ctx.source.term})


def complete_validation(ctx,source,meetings):
    """Full detached reconstruction through original rules; never fitness/RNG/save."""
    from services.chromosome_service import payload_to_chromosome
    from services.ga_publication_service import validate_publication
    rows=[];findings=set();room_names={r.id:r.name for r in source.rooms}
    faculty=dict(ctx.faculty_codes);subjects=dict(ctx.subject_codes);sections=dict(ctx.section_codes)
    if len({m.id for m in meetings})!=len(meetings):findings.add('DUPLICATE_ASSIGNMENT')
    for m in meetings:
        try:
            if m.subject!=subjects[m.subject_id] or m.section!=sections[m.section_id]:raise ValueError()
            rows.append({'subject':m.subject,'title':m.title,'section':m.section,'type':m.component,'day':m.day,'start':m.start,'end':m.end,'room':room_names[m.room_id],'faculty':faculty[m.faculty_id]})
            # Reuse D11's availability/overlap/GEC checks for every resulting row.
            from schemas.adjustments import Preview
            # Unchanged rows still undergo all hard checks. Full original
            # reconstruction is performed once below, with no scoring or repair.
            checking=replace(source,meetings=tuple(meetings),check_proposal=lambda *a:None)
            body=Preview(schedule_id=source.schedule_id,revision=source.revision,assignment_id=m.id,academic_year=source.academic_year,term=source.term,proposal={'day':m.day,'start':m.start,'end':m.end,'room_id':m.room_id},justification='Complete schedule validation')
            result=schedules.validate(checking,type('Owner',(),{'faculty_id':m.faculty_id})(),body,allow_unchanged=True)
            findings.update(f['code'] for f in result['validation']['findings'])
            if ctx.capacity_applicability=='required':
                enrollment=dict(ctx.section_enrollment).get(m.section_id);capacity=dict(ctx.room_capacity).get(m.room_id)
                if type(enrollment) is not int or type(capacity) is not int or enrollment<0 or capacity<0:findings.add('CAPACITY_METADATA_UNAVAILABLE')
                elif enrollment>capacity:findings.add('ROOM_CAPACITY_EXCEEDED')
        except (KeyError,ValueError,TypeError):findings.add('RESOURCE_OR_MEETING_INVALID')
    try:
        templates=copy.deepcopy(ctx.templates)
        chromosome=payload_to_chromosome({'schedule':rows},*templates)
        validate_publication(chromosome,*copy.deepcopy(ctx.templates))
    except (ValueError,RuntimeError):findings.add('COMPLETE_SCHEDULE_RULE_VIOLATION')
    return {'outcome':'VALID' if not findings else 'BLOCKED','findings':[{'code':c,'message':c.replace('_',' ').capitalize()} for c in sorted(findings)],'policy_reference':ctx.policy_reference,'capacity_applicability':ctx.capacity_applicability,'capacity_reference':ctx.capacity_reference,'fitness_recalculated':False}
