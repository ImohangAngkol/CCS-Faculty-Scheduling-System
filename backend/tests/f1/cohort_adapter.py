"""F1 FICTIONAL-ONLY roster-first adapter. Not an institutional provider.

No application imports this test module. There is no file/database lookup,
account inference, authority grant, environment fallback or source activation.
Profiles and preference submissions must be supplied explicitly by a fixture.
"""
import copy
from dataclasses import asdict, dataclass
import hashlib
from uuid import UUID

from genetic_algorithm.models.Faculty import Faculty
from schemas.faculty_preference import FacultyPreferenceUpdate
from services.ga_checkpoint_service import canonical, encode_graph


class CohortError(ValueError):
    def __init__(self, code):
        self.code=code
        super().__init__(code)  # Do not echo identifiers or profile records.


@dataclass(frozen=True)
class Term:
    scope: str
    academic_year: str
    term: str


@dataclass(frozen=True)
class Entry:
    term: Term
    faculty_id: str
    faculty_code: int
    participates: bool = True
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class FictionalRoster:
    term: Term
    revision: str
    entries: tuple[Entry, ...]
    source_kind: str = 'FICTIONAL_TEST_ONLY'


@dataclass(frozen=True)
class Profile:
    term: Term
    faculty_id: str
    faculty: Faculty
    scoring_priority: int
    eligibility_known: bool = True


@dataclass(frozen=True)
class Submission:
    term: Term
    faculty_id: str
    faculty_code: int
    payload: FacultyPreferenceUpdate


@dataclass
class Cohort:
    faculty: list[Faculty]
    submissions: list[dict]
    priority_rows: list[dict]
    diagnostics: list[dict]
    digest: str
    source_kind: str = 'FICTIONAL_TEST_ONLY'


def fail(code):raise CohortError(code)


def identity(value):
    try:
        if type(value) is not str or str(UUID(value))!=value:fail('IDENTITY_INVALID')
    except (ValueError,AttributeError):fail('IDENTITY_INVALID')


def check_term(value):
    if not isinstance(value,Term) or any(type(x) is not str or not x.strip() or x!=x.strip()
                                         for x in (value.scope,value.academic_year,value.term)):
        fail('TERM_REQUIRED')


def build(roster, profiles, submissions=()):
    """Build only a detached fictional cohort, preserving explicit roster order.

    Missing submissions remain ABSENT, never manufactured preference records.
    Missing eligibility becomes an empty permission set with explicit provenance.
    Unknown/missing profiles reject the entire cohort; no zero-load fallback.
    """
    if not isinstance(roster,FictionalRoster) or roster.source_kind!='FICTIONAL_TEST_ONLY':fail('FICTIONAL_SOURCE_REQUIRED')
    check_term(roster.term)
    if type(roster.revision) is not str or not roster.revision.strip():fail('REVISION_REQUIRED')
    by_id={};by_code={};members={}
    for entry in roster.entries:
        if not isinstance(entry,Entry):fail('ROSTER_ROW_INVALID')
        check_term(entry.term);identity(entry.faculty_id)
        if type(entry.faculty_code) is not int or entry.faculty_code<0:fail('CODE_INVALID')
        if type(entry.participates) is not bool:fail('PARTICIPATION_INVALID')
        if (not entry.participates and (type(entry.exclusion_reason) is not str or not entry.exclusion_reason.strip())) or (entry.participates and entry.exclusion_reason is not None):
            fail('EXCLUSION_REASON_INVALID')
        if by_id.get(entry.faculty_id,entry.faculty_code)!=entry.faculty_code or by_code.get(entry.faculty_code,entry.faculty_id)!=entry.faculty_id:
            fail('IDENTITY_CODE_CONFLICT')
        by_id[entry.faculty_id]=entry.faculty_code;by_code[entry.faculty_code]=entry.faculty_id
        key=(entry.term,entry.faculty_id)
        if key in members:fail('DUPLICATE_ROSTER_IDENTITY')
        members[key]=entry
    if not any(e.term==roster.term for e in roster.entries):fail('TERM_NOT_PRESENT')
    profile_map={}
    for profile in profiles:
        if not isinstance(profile,Profile):fail('PROFILE_INVALID')
        check_term(profile.term);identity(profile.faculty_id)
        key=(profile.term,profile.faculty_id)
        if key in profile_map:fail('DUPLICATE_PROFILE')
        if key not in members or not isinstance(profile.faculty,Faculty) or type(profile.faculty.code) is not int or profile.faculty.code!=members[key].faculty_code:
            fail('PROFILE_BINDING_INVALID')
        if type(profile.scoring_priority) is not int or profile.scoring_priority<1 or type(profile.eligibility_known) is not bool:
            fail('PROFILE_METADATA_INVALID')
        profile_map[key]=profile
    submitted={}
    for row in submissions:
        if not isinstance(row,Submission):fail('SUBMISSION_INVALID')
        check_term(row.term);identity(row.faculty_id)
        key=(row.term,row.faculty_id)
        if key in submitted:fail('DUPLICATE_SUBMISSION')
        if key not in members or type(row.faculty_code) is not int or members[key].faculty_code!=row.faculty_code:
            fail('SUBMISSION_BINDING_INVALID')
        if not isinstance(row.payload,FacultyPreferenceUpdate):fail('SUBMISSION_SCHEMA_INVALID')
        # Use existing strict schema, retaining only explicitly supplied fields.
        payload=FacultyPreferenceUpdate.model_validate(row.payload.model_dump(exclude_unset=True))
        submitted[key]=payload.model_dump(exclude_unset=True)
    faculty=[];preference_rows=[];priority_rows=[];diagnostics=[]
    for entry in roster.entries:
        key=(entry.term,entry.faculty_id)
        if entry.term!=roster.term or not entry.participates:
            diagnostics.append(dict(faculty_code=entry.faculty_code,included=False,
                reason='OUTSIDE_REQUESTED_TERM' if entry.term!=roster.term else entry.exclusion_reason))
            continue
        if key not in profile_map:fail('REQUIRED_PROFILE_MISSING')
        profile=profile_map[key];member=copy.deepcopy(profile.faculty)
        if getattr(member,'is_external',False):fail('EXTERNAL_PROFILE_NOT_NORMAL_COHORT')
        if any(getattr(member,k,None) for k in ('preferred_subjects','preferred_day','preferred_time','subjects_assigned','current_teaching_load')):
            fail('PROFILE_NOT_NEUTRAL_OR_PRISTINE')
        if any(b.preferred for blocks in member.get_day_map().values() for b in blocks):fail('PROFILE_NOT_NEUTRAL_OR_PRISTINE')
        loads=[getattr(member,k,None) for k in ('admin_load','research_load','extension_load')]
        if any(type(x) is not int or x<0 for x in loads):fail('WORKLOAD_METADATA_INVALID')
        if member.required_teaching_load!=max(0,24-sum(loads)) or member.absolute_max_teaching_load!=40 or member.overload_warning_threshold!=30:
            fail('WORKLOAD_POLICY_MISMATCH')
        stable=getattr(member,'stable_id',entry.faculty_id)
        if stable!=entry.faculty_id:fail('PROFILE_BINDING_INVALID')
        member.stable_id=entry.faculty_id
        if not profile.eligibility_known:
            member.eligible_subjects=set()
        elif not isinstance(getattr(member,'eligible_subjects',None),set):
            fail('ELIGIBILITY_METADATA_INVALID')
        faculty.append(member)
        priority_rows.append(dict(Faculty_Code=member.code,Faculty_Prio=profile.scoring_priority))
        if key in submitted:
            preference_rows.append(dict(copy.deepcopy(submitted[key]),faculty_code=member.code))
        diagnostics.append(dict(faculty_code=member.code,included=True,reason='TERM_ROSTER_MEMBER',
            preferences='SUBMITTED' if key in submitted else 'MISSING_NEUTRAL',
            eligibility='KNOWN' if profile.eligibility_known else 'MISSING_DENY_ALL'))
    payload=dict(term=asdict(roster.term),revision=roster.revision,roster=[asdict(e) for e in roster.entries],
        faculty=encode_graph(faculty),submissions=preference_rows,priority_rows=priority_rows,diagnostics=diagnostics)
    for node in payload['faculty']['nodes']:
        if node['kind']=='set':node['items'].sort(key=canonical)
    return Cohort(faculty,preference_rows,priority_rows,diagnostics,hashlib.sha256(canonical(payload)).hexdigest())
