"""Fictional trusted provider ONLY for isolated tests, never deployment config."""
from datetime import datetime, timedelta, timezone
from schemas.external_evidence import AuthorityPolicy, TrustedEvidence
from services import external_schedule_verification_service as authority


def fictional(context, now):
    stamp = lambda seconds: (now+timedelta(seconds=seconds)).isoformat()
    policy = AuthorityPolicy(issuer_id='fictional-issuer', organization_id='fictional-college', revision='fictional-policy.1',
        provenance_reference='fictional-authorization', state='active', evidence_type='provider_attestation',
        verification_method='trusted_provider', organizations=['fictional-college'], terms=[context.term],
        academic_years=[context.academic_year], subjects=list(set(context.subjects.values())), effective_start=stamp(-3600),
        expires_at=stamp(3600), max_age_seconds=300, revocation_method='trusted_provider_status', allow_authorized_revisions=True)
    evidence = TrustedEvidence(evidence_id='fictional-evidence', issuer_id='fictional-issuer', organization_id='fictional-college',
        evidence_type='provider_attestation', verification_method='trusted_provider', outcome='VERIFIED', policy_revision=policy.revision,
        evidence_revision='fictional-evidence.1', source_revision=context.source_revision, input_fingerprint=context.input_fingerprint,
        source_fingerprint=context.source_fingerprint, preview_fingerprint=context.preview_fingerprint, academic_year=context.academic_year,
        term=context.term, supplier=context.supplier, source_rows=list(context.subjects), coverage_mode='authorized_revision',
        issued_at=stamp(-60), verified_at=stamp(-1), expires_at=stamp(600), revocation_status='good', revocation_checked_at=stamp(-1))
    return policy, authority.Verification(context.input_fingerprint, policy.revision, evidence.evidence_id, authority.REQUIRED_COVERAGE, evidence)


def install_fictional(monkeypatch):
    now=datetime.now(timezone.utc)
    policies={}
    def provider(key, *, context):
        policy, proof=fictional(context, now)
        policies[policy.issuer_id]=policy
        return proof
    monkeypatch.setattr(authority,'verification_for',provider)
    monkeypatch.setattr(authority,'authority_policy_for',policies.get)
