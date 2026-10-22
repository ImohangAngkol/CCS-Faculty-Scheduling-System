"""Trusted read-only verification boundary. No institutional verifier is configured.

Never load authority from request metadata, environment flags or source filenames.
Fictional tests inject a provider explicitly; this does not grant real authority.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Verification:
    input_fingerprint: str
    policy_version: str
    evidence_reference: str
    covered_fields: frozenset[str]


REQUIRED_COVERAGE = frozenset({"source", "term", "subjects", "sections", "recurrence", "resource_applicability", "corrections"})


def verification_for(input_fingerprint: str) -> Verification | None:
    return None
