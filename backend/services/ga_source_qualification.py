"""Read-only U5C diagnostics. Projection equality is NOT run-consumption attestation.

No provider is installed here. No result classification, capture, admission, GA
model, frozen input, checkpoint or Saved Best path calls this diagnostic.
"""
from datetime import datetime, timezone
import csv
import hashlib
from io import BytesIO
import math
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.ga_academic_context import AcademicContext, canonical

CONTRACT = "ga-source-qualification-inspection-v1"
COMPONENTS = frozenset({"identities", "faculty", "eligibility", "specialization", "preferences",
    "offerings", "sections", "rooms", "availability", "time_patterns", "workload",
    "preassignments", "settings", "configuration"})
HASH_PATTERN = r"^[0-9a-f]{64}$"
ROOT = Path(__file__).resolve().parents[1]
# These five frames have no loader mutations. Preferences and load frames DO.
TABLES = (
    ("offerings_source", "first_sem_bsit_subjects.csv", "df_subjects"),
    ("fixed_section_source", "BSIT_Consolidated_Subject_Schedules.csv", "df_section_schedules"),
    ("qualification_source", "faculty_qualifications.csv", "df_faculty_qualifications"),
    ("eligibility_source", "faculty_subject_eligibility.csv", "df_faculty_subject_eligibility"),
    ("domain_source", "subject_domains.csv", "df_subject_domains"),
)


class SourceDeclaration(BaseModel):
    """Metadata is a declaration, never proof of institutional approval.

    This model is not exposed as an HTTP input. A future authority adapter must
    authenticate stewardship/lifecycle and bind these claims to consumed inputs.
    """
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    context: AcademicContext
    origin: Literal["INSTITUTIONAL_DECLARATION", "FICTIONAL_FIXTURE", "UNVERIFIED_HISTORY"]
    owner_reference: str = Field(min_length=1, max_length=160)
    authority_reference: str | None = Field(default=None, min_length=1, max_length=160)
    approval_status: Literal["CLAIMED_APPROVED", "NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    approval_reference: str | None = Field(default=None, min_length=1, max_length=160)
    effective_from: str
    effective_until: str
    manifest_sha256: str = Field(pattern=HASH_PATTERN)

    @field_validator("owner_reference", "authority_reference", "approval_reference")
    @classmethod
    def explicit_text(cls, value):
        if value is not None and (value != value.strip() or not value or any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise ValueError("Use explicit canonical references.")
        return value

    @field_validator("effective_from", "effective_until")
    @classmethod
    def aware_time(cls, value):
        if datetime.fromisoformat(value).tzinfo is None:
            raise ValueError("Effective periods require a timezone.")
        return value


class ModelProjection(BaseModel):
    """A caller-supplied, complete semantic projection, not a live GA receipt."""
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    context: AcademicContext
    engine_fingerprint: str = Field(pattern=HASH_PATTERN)
    scoring_policy: Literal["preference-policy-2"]
    configuration_fingerprint: str = Field(pattern=HASH_PATTERN)
    components: dict[str, str]

    @field_validator("components")
    @classmethod
    def complete(cls, value):
        if set(value) != COMPONENTS or any(len(v) != 64 or any(c not in "0123456789abcdef" for c in v) for v in value.values()):
            raise ValueError("A complete canonical component projection is required.")
        return dict(value)

    @property
    def digest(self):
        return hashlib.sha256(canonical(self.model_dump())).hexdigest()


def compare_projection(declaration, expected, loaded, *, now=None):
    """Deterministic fictional/adapter qualification precheck; never grants CURRENT.

    Revalidate even model_copy/model_construct objects. No hashes supplied by a
    client can prove ownership, authority, freshness or optimizer consumption.
    """
    reasons = ["INSTITUTIONAL_AUTHORITY_NOT_CONNECTED", "RUN_CONSUMPTION_BINDING_UNAVAILABLE"]
    try:
        if not isinstance(declaration, SourceDeclaration) or not isinstance(expected, ModelProjection) or not isinstance(loaded, ModelProjection):
            raise ValueError()
        declaration = SourceDeclaration.model_validate(declaration.model_dump())
        expected = ModelProjection.model_validate(expected.model_dump())
        loaded = ModelProjection.model_validate(loaded.model_dump())
        now = now or datetime.now(timezone.utc)
        start, end = (datetime.fromisoformat(v) for v in (declaration.effective_from, declaration.effective_until))
        if now.tzinfo is None or not start <= now < end:
            reasons.append("SOURCE_OUTSIDE_EFFECTIVE_PERIOD")
        if declaration.context != expected.context or expected.context != loaded.context:
            reasons.append("ACADEMIC_CONTEXT_MISMATCH")
        if declaration.manifest_sha256 != expected.digest:
            reasons.append("DECLARED_MANIFEST_MISMATCH")
        if expected.engine_fingerprint != loaded.engine_fingerprint:
            reasons.append("ENGINE_MISMATCH")
        if expected.configuration_fingerprint != loaded.configuration_fingerprint:
            reasons.append("CONFIGURATION_MISMATCH")
        changed = sorted(key for key in COMPONENTS if expected.components[key] != loaded.components[key])
        if changed:
            reasons.append("SEMANTIC_COMPONENT_MISMATCH")
        if not declaration.authority_reference or not declaration.approval_reference or declaration.approval_status != "CLAIMED_APPROVED":
            reasons.append("SOURCE_APPROVAL_NOT_ESTABLISHED")
        if declaration.origin != "INSTITUTIONAL_DECLARATION":
            reasons.append(declaration.origin)
        technically_matching = len(reasons) == 2 or set(reasons[2:]) <= {"SOURCE_APPROVAL_NOT_ESTABLISHED", "FICTIONAL_FIXTURE", "UNVERIFIED_HISTORY"}
        return {"technical_projection": "MATCH" if technically_matching else "MISMATCH", "changed_components": changed,
                "eligible_for_current": False, "reasons": reasons}
    except (ValueError, TypeError, AttributeError):
        return {"technical_projection": "UNVERIFIABLE", "changed_components": [], "eligible_for_current": False,
                "reasons": [*reasons, "SOURCE_METADATA_INVALID_OR_MISSING"]}


def table_digest(frame):
    """Preserve order, types, NaN and exact finite floats; never export row data."""
    if len(frame) > 20000 or len(frame.columns) > 100 or not frame.columns.is_unique:
        raise ValueError("Unsupported table shape")
    def cell(value):
        if hasattr(value, "item"):
            value = value.item()
        if value is None:
            return ["none"]
        if type(value) is float:
            return ["float", "nan" if math.isnan(value) else value.hex()]
        if type(value) in (str, int, bool):
            return [type(value).__name__, value]
        raise ValueError("Unsupported cell type")
    return hashlib.sha256(canonical({"columns": [cell(c) for c in frame.columns],
        "rows": [[cell(v) for v in row] for row in frame.itertuples(index=False, name=None)]})).hexdigest()


def inspect_table(path, cached):
    """Compare one allowlisted source to a cache; no reload/mutation of the cache."""
    try:
        import pandas as pd
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError()
        raw = path.read_bytes()
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError()
        rows = list(csv.reader(raw.decode("utf-8-sig").splitlines(), strict=True))
        header = rows[0]
        if len(rows) > 20001 or not header or len(header) > 100 or len(header) != len(set(header)) or any(len(row) != len(header) for row in rows[1:] if row):
            raise ValueError()
        fresh = pd.read_csv(BytesIO(raw))
        source_digest, cached_digest = table_digest(fresh), table_digest(cached)
        if path.read_bytes() != raw:
            return {"status": "CHANGED_DURING_INSPECTION"}
        return {"status": "MATCH" if source_digest == cached_digest else "STALE_OR_DIFFERENT_CACHE",
                "source_sha256": hashlib.sha256(raw).hexdigest(), "source_model_sha256": source_digest,
                "cached_model_sha256": cached_digest, "row_count": len(fresh)}
    except Exception:
        # Never publish exception strings, source records or filesystem paths.
        return {"status": "UNVERIFIABLE"}


def status():
    """Safe administrator observation only. Never imports/rebuilds GA models."""
    from services.ga_progress_service import input_fingerprint
    module = sys.modules.get("genetic_algorithm.utils.Functions")
    tables = []
    try:
        before = input_fingerprint()
        for label, filename, attribute in TABLES:
            finding = inspect_table(ROOT / "data" / filename, getattr(module, attribute, None)) if module else {"status": "CACHE_NOT_LOADED"}
            tables.append({"source": label, **finding})
        stable = input_fingerprint() == before
    except Exception:
        stable, before = False, None
    return {"contract": CONTRACT, "qualification": "BLOCKED", "eligible_for_current": False,
            "institutional_approval": "NOT_ESTABLISHED", "source_metadata": None,
            "input_fingerprint": before, "file_set_stable_during_inspection": stable,
            "cached_tables": tables, "reasons": ["INSTITUTIONAL_SOURCE_NOT_CONFIGURED",
                "RUN_CONSUMPTION_BINDING_UNAVAILABLE", "FULL_TRANSFORMED_MODEL_MAPPING_UNVERIFIED",
                *([] if stable else ["SOURCE_SET_UNSTABLE_OR_UNREADABLE"])],
            "scope": "Read-only diagnostic; matching caches do not verify full optimizer inputs or authorize CURRENT, Saved Best or publication."}
