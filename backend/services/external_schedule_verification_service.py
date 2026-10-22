"""Trusted read-only verification boundary. No institutional verifier is configured.

Never load authority from request metadata, environment flags or source filenames.
Fictional tests inject a provider explicitly; this does not grant real authority.
"""
from dataclasses import dataclass
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json

from schemas.external_evidence import AuthorityPolicy, TrustedEvidence, EvidenceTrust, RowTrust, TrustFinding


@dataclass(frozen=True)
class Verification:
    input_fingerprint: str
    policy_version: str
    evidence_reference: str
    covered_fields: frozenset[str]
    evidence: TrustedEvidence | None = None


REQUIRED_COVERAGE = frozenset({"source", "term", "subjects", "sections", "recurrence", "resource_applicability", "corrections"})


def verification_for(input_fingerprint: str, *, context=None) -> Verification | None:
    return None


def authority_policy_for(issuer_id: str) -> AuthorityPolicy | None:
    """Deployment-owned registry boundary. No institution has supplied one yet."""
    return None


@dataclass(frozen=True)
class EvidenceContext:
    input_fingerprint: str
    source_fingerprint: str
    preview_fingerprint: str
    supplier: str
    source_revision: str
    academic_year: str
    term: str
    subjects: dict[int, str]
    changed_rows: frozenset[int]


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None: raise ValueError('Timezone required')
    return parsed.astimezone(timezone.utc)


def policy_digest(policy):
    return hashlib.sha256(json.dumps(policy.model_dump(), sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def evaluate_trust(context: EvidenceContext) -> EvidenceTrust:
    """Only trusted server hooks can supply evidence/policy. No request trust flags.

    Provider objects are strictly validated and reduced to public allowlisted
    findings; exception text, credentials and arbitrary provider payloads never
    enter responses or logs. No cryptographic document authentication is claimed.
    """
    rows = [RowTrust(source_row=line, outcome='UNVERIFIED') for line in context.subjects]
    def result(outcome, code, explanation, action, **details):
        return EvidenceTrust(outcome=outcome, rows=rows, findings=[TrustFinding(code=code, explanation=explanation, action=action)], **details)
    try:
        value = verification_for(context.input_fingerprint, context=copy.deepcopy(context))
        if value is None:
            return result('PROVIDER_UNAVAILABLE', 'PROVIDER_UNAVAILABLE', 'No trusted evidence provider is configured.', 'Obtain an institutionally authorized provider and authority policy; typed references cannot establish trust.')
        if not isinstance(value, Verification) or not isinstance(value.evidence, TrustedEvidence):
            return result('INVALID', 'INVALID_PROVIDER_RESPONSE', 'Trusted evidence details are missing or unsupported.', 'Ask the provider operator to supply the versioned contract; do not self-certify.')
        # Revalidate even model_copy/constructed records from a faulty provider.
        evidence = TrustedEvidence.model_validate(value.evidence.__dict__)
        policy = authority_policy_for(evidence.issuer_id)
        if policy is None:
            return result('UNVERIFIED', 'UNKNOWN_ISSUER', 'The issuer has no trusted authority-policy record.', 'Obtain independently authorized issuer registration.')
        if not isinstance(policy, AuthorityPolicy): raise ValueError('Invalid policy contract')
        policy = AuthorityPolicy.model_validate(policy.__dict__)
        if len(set(evidence.source_rows)) != len(evidence.source_rows) or any(type(n) is not int or n <= 0 for n in evidence.source_rows): raise ValueError('Invalid rows')
        now = datetime.now(timezone.utc)
        effective, policy_end = instant(policy.effective_start), instant(policy.expires_at)
        issued, verified, expiry, revoked_at = map(instant, (evidence.issued_at, evidence.verified_at, evidence.expires_at, evidence.revocation_checked_at))
        if effective >= policy_end or issued > verified or verified >= expiry: raise ValueError('Invalid time order')
        if policy.issuer_id != evidence.issuer_id:
            return result('INVALID', 'UNAUTHORIZED_ISSUER', 'The registry record does not authorize this issuer.', 'Resolve issuer registration with the institution.')
        if policy.state != 'active':
            return result('REVOKED', 'ISSUER_'+policy.state.upper(), 'Issuer authority is suspended or revoked.', 'Obtain a current authorized policy; previous verification cannot be reused.')
        if now < effective or issued < effective or issued >= policy_end or now >= policy_end:
            return result('EXPIRED', 'AUTHORITY_WINDOW', 'Evidence issuance or current review is outside the authority validity window.', 'Obtain evidence issued within a current authority policy.')
        if evidence.policy_revision != policy.revision or value.policy_version != policy.revision:
            return result('STALE', 'POLICY_REVISION_MISMATCH', 'Evidence references a different authority-policy revision.', 'Have the provider re-evaluate under the current policy.')
        if evidence.organization_id not in policy.organizations:
            return result('INVALID', 'ORGANIZATION_SCOPE_MISMATCH', 'Issuer is not authorized for this supplying organization.', 'Obtain evidence from an explicitly scoped issuer; institutional rank grants no inherited scope.')
        if (evidence.academic_year != context.academic_year or evidence.term != context.term
                or context.academic_year not in policy.academic_years or context.term not in policy.terms):
            return result('INVALID', 'TERM_SCOPE_MISMATCH', 'Evidence or issuer scope does not cover the reviewed academic term.', 'Obtain evidence for the exact academic year and term.')
        if evidence.evidence_type != policy.evidence_type or evidence.verification_method != policy.verification_method:
            return result('UNSUPPORTED', 'UNSUPPORTED_VERIFICATION_METHOD', 'The configured evidence mechanism does not match the policy.', 'Supply an independently supported verification mechanism.')
        if evidence.problem != 'none':
            return result('UNSUPPORTED' if evidence.problem == 'unsupported_signature' else 'INVALID',
                evidence.problem.upper(), 'The provider reports conflicting evidence or an invalid/unsupported signature.',
                'Resolve evidence with the authorized issuer. This application does not authenticate document signatures itself.')
        if evidence.outcome != 'VERIFIED':
            return result(evidence.outcome, 'PROVIDER_'+evidence.outcome, 'The trusted provider has not established acceptable evidence.', 'Resolve the provider finding through the issuer; this application cannot override it.')
        if evidence.revocation_status == 'revoked':
            return result('REVOKED', 'EVIDENCE_REVOKED', 'Trusted revocation information marks this evidence revoked.', 'Obtain replacement evidence and re-evaluate.')
        if evidence.revocation_status != 'good':
            return result('UNVERIFIED', 'REVOCATION_UNKNOWN', 'Current revocation status is not established.', 'Obtain a fresh trusted revocation check; absence of information is not proof of validity.')
        if now >= expiry:
            return result('EXPIRED', 'EVIDENCE_EXPIRED', 'Evidence has expired.', 'Obtain current evidence.')
        if (verified > now or revoked_at > now or revoked_at < issued or now-verified > timedelta(seconds=policy.max_age_seconds)
                or now-revoked_at > timedelta(seconds=policy.max_age_seconds)):
            return result('STALE', 'EVIDENCE_FRESHNESS', 'Verification or revocation information is stale or future-dated.', 'Refresh evidence and revocation status with the trusted provider.')
        if (value.input_fingerprint != context.input_fingerprint or evidence.input_fingerprint != context.input_fingerprint
                or evidence.source_fingerprint != context.source_fingerprint or evidence.preview_fingerprint != context.preview_fingerprint
                or evidence.source_revision != context.source_revision or evidence.supplier != context.supplier
                or not REQUIRED_COVERAGE <= value.covered_fields):
            return result('STALE', 'EVIDENCE_BINDING_MISMATCH', 'Evidence does not bind this source, preview, revision and completed candidate.', 'Have the provider evaluate this exact review including mappings and corrections.')
        covered = set(evidence.source_rows)
        if covered - set(context.subjects):
            return result('INVALID', 'ROW_COVERAGE_MISMATCH', 'Evidence names rows outside the reviewed source.', 'Obtain evidence with explicit original source-row coverage.')
        denied = {n for n in covered if context.subjects[n] not in policy.subjects}
        corrections = covered & context.changed_rows
        if corrections and (evidence.coverage_mode != 'authorized_revision' or not policy.allow_authorized_revisions):
            return result('UNVERIFIED', 'UNVERIFIED_CORRECTION', 'Source-only evidence cannot authorize administrator-proposed changes.', 'Obtain explicit authorized-revision evidence covering the corrected candidate.')
        accepted = covered - denied
        rows = [RowTrust(source_row=n, outcome='VERIFIED' if n in accepted else 'UNVERIFIED') for n in context.subjects]
        if denied:
            return result('INVALID', 'SUBJECT_SCOPE_MISMATCH', 'Some rows are outside the issuer course scope.', 'Obtain appropriately scoped evidence; other rows do not inherit trust.')
        if covered != set(context.subjects):
            return result('UNVERIFIED', 'PARTIAL_ROW_COVERAGE', 'Only explicitly covered source rows have verified evidence.', 'Obtain coverage for every remaining source row; batch readiness remains blocked.')
        return EvidenceTrust(outcome='VERIFIED', evidence_id=evidence.evidence_id, evidence_revision=evidence.evidence_revision,
            verified_issuer=policy.issuer_id, issuing_organization=evidence.organization_id, evidence_type=evidence.evidence_type,
            verification_method=evidence.verification_method, policy_revision=policy.revision, policy_digest=policy_digest(policy),
            policy_provenance=policy.provenance_reference, authority_organizations=policy.organizations, authority_terms=policy.terms,
            authority_subjects=policy.subjects, source_match=True, term_match=True, coverage_mode=evidence.coverage_mode,
            verified_at=evidence.verified_at, valid_until=min(expiry, policy_end, verified+timedelta(seconds=policy.max_age_seconds), revoked_at+timedelta(seconds=policy.max_age_seconds)).isoformat(),
            revocation_status='good', rows=rows, findings=[])
    except Exception:
        # Fail closed even on unavailable/malformed integrations; never log repr.
        return result('PROVIDER_UNAVAILABLE', 'PROVIDER_FAILURE', 'Evidence provider or policy could not be safely evaluated.', 'Retry through the authorized provider operator. No verification was accepted.')
