"""Strict operation inputs; authority never comes from request fields."""
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from schemas.external_readiness import AssessedHandoffRequest


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class ProposedRevision(Strict):
    revision_id: UUID
    record_id: UUID
    expected_version: int=Field(ge=0,strict=True)
    reason: str=Field(min_length=1,max_length=500,strict=True)
    review: AssessedHandoffRequest


class ConfirmationCommand(Strict):
    operation_id: UUID
    expected_version: int=Field(ge=0,strict=True)
    reason: str=Field(min_length=1,max_length=500,strict=True)
    review: AssessedHandoffRequest


class RevocationCommand(Strict):
    operation_id: UUID
    expected_version: int=Field(ge=1,strict=True)
    reason: str=Field(min_length=1,max_length=500,strict=True)
