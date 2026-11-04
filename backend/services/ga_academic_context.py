"""Server-owned academic-context boundary. No database, environment or client adapter."""
from datetime import datetime, timezone
import hashlib
import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from services.ga_history_service import HistoryError


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class AcademicContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: Literal[1] = 1
    academic_year_id: str
    term_id: str
    scope_id: str
    academic_year: str = Field(min_length=1, max_length=100)
    term: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=160)
    dataset_id: str = Field(min_length=1, max_length=160)
    dataset_revision: str = Field(min_length=1, max_length=100)
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("version", mode="before")
    @classmethod
    def schema(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported academic-context schema.")
        return value

    @field_validator("academic_year_id", "term_id", "scope_id")
    @classmethod
    def identifier(cls, value):
        if str(UUID(value)) != value:
            raise ValueError("Use a canonical recorded identity.")
        return value

    @field_validator("academic_year", "term", "department", "dataset_id", "dataset_revision")
    @classmethod
    def text(cls, value):
        if value != value.strip() or any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("Context labels must be explicit canonical text.")
        return value

    @property
    def digest(self):
        return hashlib.sha256(canonical(self.model_dump())).hexdigest()

    def public(self):
        return {"kind": "verified-recorded-context", **self.model_dump(), "context_sha256": self.digest}


class ContextVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    context: AcademicContext
    state: Literal["VERIFIED"]
    verification_reference: str = Field(min_length=1, max_length=160)
    issued_at: str
    expires_at: str


def verification_for(_technical_identity):
    """Genuine integration is deliberately unconfigured; no env flag or request override.

    A separately reviewed provider must verify term/scope/dataset stewardship and
    effective lifecycle. Administrator/Chair roles alone cannot supply this fact.
    """
    return None


def verified_context(identity):
    try:
        supplied = verification_for(dict(identity))
        if supplied is None:
            return None
        if not isinstance(supplied, ContextVerification):
            raise ValueError()
        # Revalidate even model_construct/model_copy inputs from a provider.
        checked = ContextVerification.model_validate(supplied.model_dump())
        issued, expires = (datetime.fromisoformat(value) for value in (checked.issued_at, checked.expires_at))
        now = datetime.now(timezone.utc)
        if issued.tzinfo is None or expires.tzinfo is None or not issued <= now < expires:
            raise ValueError()
        if checked.context.input_fingerprint != identity["input_fingerprint"]:
            raise ValueError()
        return checked
    except Exception as error:
        raise HistoryError("Academic context verification is unavailable or invalid; no verified provenance was accepted.",
                           "GA_ACADEMIC_CONTEXT_UNVERIFIABLE", 503) from error
