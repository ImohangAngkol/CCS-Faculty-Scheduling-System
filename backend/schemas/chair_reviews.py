from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DecisionCommand(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    operation_id: UUID
    expected_version: int = Field(ge=1)
    explanation: str = Field(min_length=10, max_length=2000)
    # Optimistic review binding; these hashes grant no authority.
    content_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    schedule_revision: str = Field(pattern=r'^[a-f0-9]{64}$')
    constraint_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
