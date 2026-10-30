"""Executable F2C specification only. NOT a production service or authority.

No GA/auth/DB imports, configuration hooks, engine dispatch or persistence.
All provider implementations in this directory are explicit fictional fixtures.
"""
from dataclasses import asdict,dataclass
from datetime import datetime
from fractions import Fraction
from functools import total_ordering
import hashlib
import json
import re

CAPABILITY='zero_target_workload_exception.authorize'
MAX_BITS=4096


class ContractError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)


def fail(code):raise ContractError(code)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def ratio(value):
    if not isinstance(value,Fraction):fail('EXACT_RATIONAL_REQUIRED')
    if max(abs(value.numerator).bit_length(),value.denominator.bit_length())>MAX_BITS:fail('NUMERIC_RESOURCE_LIMIT')
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))


def parse_ratio(value):
    if type(value) is not dict or set(value)!={'numerator','denominator'}:fail('RATIONAL_SHAPE')
    n,d=value['numerator'],value['denominator']
    if type(n) is not str or type(d) is not str or len(n)>1235 or len(d)>1234:fail('RATIONAL_ENCODING')
    if not re.fullmatch(r'0|-?[1-9][0-9]*',n) or not re.fullmatch(r'[1-9][0-9]*',d):fail('RATIONAL_ENCODING')
    f=Fraction(int(n),int(d))
    if ratio(f)!=value:fail('RATIONAL_NOT_CANONICAL')
    return f


@dataclass(frozen=True)
class Evaluation:
    run_id: str
    policy_digest: str
    engine_fingerprint: str
    input_fingerprint: str
    cohort_digest: str
    constraint_digest: str
    exception_set_digest: str
    evaluation_scope: str = 'complete_chromosome'

    def __post_init__(self):
        if not self.run_id or not self.evaluation_scope:fail('EVALUATION_IDENTITY_REQUIRED')
        if any(not re.fullmatch(r'[a-f0-9]{64}',getattr(self,k)) for k in (
            'policy_digest','engine_fingerprint','input_fingerprint','cohort_digest','constraint_digest','exception_set_digest')):
            fail('IDENTITY_DIGEST_INVALID')


@total_ordering
@dataclass(frozen=True,eq=False)
class Score:
    evaluation: Evaluation
    candidate_digest: str
    value: Fraction

    def __post_init__(self):
        ratio(self.value)
        if not re.fullmatch(r'[a-f0-9]{64}',self.candidate_digest):fail('CANDIDATE_DIGEST_INVALID')

    def compatible(self,other):
        if not isinstance(other,Score):fail('UNTAGGED_COMPARISON')
        if self.evaluation!=other.evaluation:fail('MIXED_EVALUATION_IDENTITY')

    def __lt__(self,other):self.compatible(other);return self.value<other.value
    def __eq__(self,other):self.compatible(other);return self.value==other.value


def encode_score(score):
    return canonical(dict(schema_version=1,evaluation=asdict(score.evaluation),candidate_digest=score.candidate_digest,exact=ratio(score.value)))


def decode_score(blob,expected):
    # Proposed bounded, duplicate-member-rejecting passive DTO, not graph code.
    if len(blob)>16384:fail('SCORE_SIZE_LIMIT')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:fail('DUPLICATE_JSON_MEMBER')
            out[k]=v
        return out
    try:
        data=json.loads(blob,object_pairs_hook=unique,parse_constant=lambda value:fail('NONFINITE_JSON'))
        if set(data)!={'schema_version','evaluation','candidate_digest','exact'} or type(data['schema_version']) is not int or data['schema_version']!=1:fail('SCORE_SCHEMA_UNSUPPORTED')
        identity=Evaluation(**data['evaluation'])
        if identity!=expected:fail('RESUME_CONTEXT_MISMATCH')
        return Score(identity,data['candidate_digest'],parse_ratio(data['exact']))
    except ContractError:raise
    except (ValueError,TypeError,KeyError):fail('SCORE_ENCODING_INVALID')


@dataclass(frozen=True)
class ExceptionContext:
    faculty_id: str
    department_id: str
    academic_year: str
    term_id: str
    run_id: str
    policy_digest: str
    input_fingerprint: str
    faculty_profile_digest: str
    constraint_digest: str
    allowed_offerings: tuple[str,...]
    target: int = 0

    @property
    def binding(self):return digest(asdict(self))


@dataclass(frozen=True)
class Grant:
    approval_id: str
    revision: int
    event_id: str
    context_digest: str
    issuer: str
    issuer_policy_digest: str
    capability: str
    max_teaching_units: int
    issued_at: datetime
    expires_at: datetime
    state: str = 'APPROVED'


@dataclass(frozen=True)
class Mandate:
    actor_id: str
    policy_digest: str
    capabilities: tuple[str,...]
    department_ids: tuple[str,...]
    issued_at: datetime
    expires_at: datetime
    state: str = 'ACTIVE'


@dataclass(frozen=True)
class ExceptionPin:
    approval_id: str
    revision: int
    event_id: str
    context_digest: str
    issuer_policy_digest: str
    max_teaching_units: int


def valid_time(first,last,now):
    try:return bool(first.tzinfo and last.tzinfo and now.tzinfo and first<=now<last)
    except (TypeError,AttributeError):return False


def zero_admission(context,actual,used_offerings,provider,now,*,hard_findings,previous=None):
    """Specification: hard_findings come from mandatory server hard validation.

    This test model is not that validator or a real provider authentication
    implementation. A real provider must independently attest both objects.
    """
    if type(actual) is not int or actual<0:fail('INVALID_TEACHING_UNITS')
    if hard_findings or actual>40:fail('HARD_CONSTRAINT_REJECTED')
    if context.target!=0:fail('ZERO_TARGET_CONTEXT_REQUIRED')
    if actual==0:return None
    if provider is None:fail('EXCEPTION_AUTHORITY_UNAVAILABLE')
    try:grant,mandate=provider.attest(context,now)
    except Exception:fail('EXCEPTION_AUTHORITY_UNAVAILABLE')
    if not isinstance(grant,Grant) or not isinstance(mandate,Mandate):fail('EXCEPTION_NOT_APPROVED')
    if (mandate.state!='ACTIVE' or CAPABILITY not in mandate.capabilities or context.department_id not in mandate.department_ids or mandate.actor_id!=grant.issuer
            or mandate.policy_digest!=grant.issuer_policy_digest or not valid_time(mandate.issued_at,mandate.expires_at,now)):
        fail('EXCEPTION_MANDATE_INVALID')
    if grant.capability!=CAPABILITY or grant.state!='APPROVED':fail('EXCEPTION_NOT_APPROVED')
    if not valid_time(grant.issued_at,grant.expires_at,now):fail('EXCEPTION_EXPIRED_OR_NOT_YET_VALID')
    if grant.context_digest!=context.binding:fail('EXCEPTION_CONTEXT_CHANGED')
    if (type(grant.revision) is not int or grant.revision<1 or not grant.approval_id or not grant.event_id
            or type(grant.max_teaching_units) is not int or not 0<actual<=grant.max_teaching_units
            or not set(used_offerings)<=set(context.allowed_offerings)):
        fail('EXCEPTION_SCOPE_EXCEEDED')
    pin=ExceptionPin(grant.approval_id,grant.revision,grant.event_id,grant.context_digest,grant.issuer_policy_digest,grant.max_teaching_units)
    if previous is not None and pin!=previous:fail('EXCEPTION_REVISION_CHANGED')
    return pin


def workload_exact(actual,targets):
    """Positive-target formula only. Authorization never chooses its math."""
    if len(actual)!=len(targets):fail('COHORT_LENGTH_MISMATCH')
    value=Fraction()
    for a,t in zip(actual,targets):
        if type(a) is not int or type(t) is not int or not 0<=a<=40 or not 0<=t<=24:fail('INTEGER_CREDIT_DOMAIN_REQUIRED')
        if t:value+=Fraction((a-t)**2,t)
        elif a:fail('AUTHORIZED_ZERO_TARGET_NUMERIC_POLICY_UNRESOLVED')
    return value
