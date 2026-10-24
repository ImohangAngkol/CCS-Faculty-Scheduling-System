"""No client-supplied owner, faculty, approval or authoritative mapping fields."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Proposal(Strict):
    day: Literal['M', 'T', 'W', 'TH', 'F', 'S']
    start: str = Field(pattern=r'^\d{2}:\d{2}$')
    end: str = Field(pattern=r'^\d{2}:\d{2}$')
    room_id: str = Field(min_length=1, max_length=120)


class Preview(Strict):
    schedule_id: str = Field(min_length=1, max_length=120)
    revision: str = Field(pattern=r'^[a-f0-9]{64}$')
    assignment_id: str = Field(pattern=r'^[a-f0-9]{64}$')
    academic_year: str = Field(min_length=1, max_length=40)
    term: str = Field(min_length=1, max_length=120)
    proposal: Proposal
    justification: str = Field(min_length=10, max_length=2000)

    @field_validator('justification')
    @classmethod
    def printable(cls, value):
        if any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ValueError('Use printable justification text.')
        return value


class Create(Preview):
    operation_id: UUID


class Transition(Strict):
    operation_id: UUID
    expected_version: int = Field(ge=1)
