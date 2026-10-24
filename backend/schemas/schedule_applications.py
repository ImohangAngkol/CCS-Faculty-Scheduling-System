from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field


class ApplicationCommand(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    operation_id: UUID
    decision_id: UUID
    decision_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
    expected_revision: str=Field(pattern=r'^[a-f0-9]{64}$')
    expected_sequence: int=Field(ge=1)
    constraint_digest: str=Field(pattern=r'^[a-f0-9]{64}$')
