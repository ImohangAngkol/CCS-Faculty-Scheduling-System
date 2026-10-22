"""D8 trusted-provider records and public findings; never client authority input."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Outcome = Literal['VERIFIED', 'UNVERIFIED', 'INVALID', 'EXPIRED', 'REVOKED', 'STALE', 'UNSUPPORTED', 'PROVIDER_UNAVAILABLE']


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)


class AuthorityPolicy(Record):
    issuer_id: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    organization_id: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    revision: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    provenance_reference: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    state: Literal['active', 'suspended', 'revoked']
    evidence_type: Literal['provider_attestation']
    verification_method: Literal['trusted_provider']
    organizations: list[str] = Field(min_length=1, max_length=100)
    terms: list[str] = Field(min_length=1, max_length=100)
    academic_years: list[str] = Field(min_length=1, max_length=20)
    subjects: list[str] = Field(min_length=1, max_length=1000)
    effective_start: str = Field(max_length=80)
    expires_at: str = Field(max_length=80)
    max_age_seconds: int = Field(ge=30, le=900)
    revocation_method: Literal['trusted_provider_status']
    allow_authorized_revisions: bool = False

    @field_validator('organizations', 'terms', 'academic_years', 'subjects')
    @classmethod
    def public_scope_only(cls, values):
        from services.evidence_sanitization import sanitize
        if any(not value.strip() or len(value)>120 or '*' in value or any(ord(c)<32 for c in value)
               or sanitize(value)!=value for value in values):
            raise ValueError('Bounded explicit public scope required')
        return values


class TrustedEvidence(Record):
    evidence_id: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    issuer_id: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    organization_id: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    evidence_type: Literal['provider_attestation']
    verification_method: Literal['trusted_provider']
    outcome: Outcome
    problem: Literal['none', 'conflicting_evidence', 'invalid_signature', 'unsupported_signature'] = 'none'
    policy_revision: str = Field(max_length=64)
    evidence_revision: str = Field(pattern=r'^[a-z][a-z0-9_.-]{0,63}$')
    source_revision: str = Field(max_length=120)
    input_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    preview_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    academic_year: str = Field(max_length=40)
    term: str = Field(max_length=120)
    supplier: str = Field(max_length=120)
    source_rows: list[int] = Field(min_length=1, max_length=200)
    coverage_mode: Literal['exact_source', 'authorized_revision']
    issued_at: str = Field(max_length=80)
    verified_at: str = Field(max_length=80)
    expires_at: str = Field(max_length=80)
    revocation_status: Literal['good', 'revoked', 'unknown']
    revocation_checked_at: str = Field(max_length=80)


EVIDENCE_LABEL = 'EVIDENCE VERIFICATION REVIEW — NOT INSTITUTIONALLY CONFIRMED OR ACTIVE IN GA'


class TrustFinding(Record):
    code: str
    explanation: str
    action: str
    source_row: int | None = None


class RowTrust(Record):
    source_row: int
    outcome: Outcome


class EvidenceTrust(Record):
    version: Literal['d8.1'] = 'd8.1'
    label: Literal['EVIDENCE VERIFICATION REVIEW — NOT INSTITUTIONALLY CONFIRMED OR ACTIVE IN GA'] = EVIDENCE_LABEL
    outcome: Outcome
    evidence_id: str | None = None
    evidence_revision: str | None = None
    verified_issuer: str | None = None
    issuing_organization: str | None = None
    evidence_type: str | None = None
    verification_method: str | None = None
    policy_revision: str | None = None
    policy_digest: str | None = None
    policy_provenance: str | None = None
    authority_organizations: list[str] = Field(default_factory=list)
    authority_terms: list[str] = Field(default_factory=list)
    authority_subjects: list[str] = Field(default_factory=list)
    source_match: bool = False
    term_match: bool = False
    coverage_mode: Literal['exact_source', 'authorized_revision'] | None = None
    verified_at: str | None = None
    valid_until: str | None = None
    revocation_status: Literal['good', 'revoked', 'unknown'] = 'unknown'
    rows: list[RowTrust]
    findings: list[TrustFinding]
    institutionally_confirmed: Literal[False] = False
    activated: Literal[False] = False
