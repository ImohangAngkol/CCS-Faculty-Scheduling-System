"""Versioned V2 requests: no client authority flags, resource IDs or snapshots."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    population_size: int = Field(default=10, ge=2, le=50)
    generations: int = Field(default=5, ge=1, le=100)
    fresh_chromosomes: int = Field(default=2, ge=0, le=20)
    mutation_attempts: int = Field(default=20, ge=1, le=100)
    max_restarts: int = Field(default=10, ge=1, le=50)
    candidate_attempts: int = Field(default=20, ge=1, le=100)
    crossover_attempts: int = Field(default=20, ge=1, le=100)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    academic_year: str = Field(min_length=9, max_length=40)
    term: str = Field(min_length=1, max_length=120)
    constraint_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    parameters: Parameters = Field(default_factory=Parameters)
    seed: Literal["fresh", "saved", "uploaded"] = "fresh"


class ControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["pause", "resume", "stop"]


class RunIdentity(BaseModel):
    run_id: UUID
