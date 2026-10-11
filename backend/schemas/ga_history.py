"""Version-one stored observation contracts; validation never evaluates fitness."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class HistoryMetrics(BaseModel):
    model_config = ConfigDict(extra="allow")
    generation: int = Field(ge=0)
    generation_limit: int = Field(ge=0)
    population_requested: int = Field(ge=1)
    population_actual: int = Field(ge=1)
    generation_best_fitness: FiniteFloat
    best_ever_fitness: FiniteFloat
    average_fitness: FiniteFloat
    accepted_new_chromosomes_total: int = Field(ge=0)
    input_fingerprint: str
    configuration_fingerprint: str
    validation_status: Literal["passed"]


class HistoricalCandidate(BaseModel):
    chromosome_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload: dict[str, Any]
    workload: list[dict[str, Any]]


class HistoryValidation(BaseModel):
    status: Literal["passed"]
    gate: Literal["phase-3b-publication"]
    validated_at: str
    conflicts: Literal[0]
    eligibility_violations: Literal[0]
    overload_violations: Literal[0]
    fixed_schedule_violations: Literal[0]
    preassignment_violations: Literal[0]
    component_duration_violations: Literal[0]


class GenerationSnapshot(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal[1]
    run_id: str
    generation: int = Field(ge=0)
    timestamp: str
    metrics: HistoryMetrics
    engine_fingerprint: str
    ga_configuration: dict[str, Any]
    fitness_configuration: dict[str, Any] | None
    generation_best: HistoricalCandidate
    best_ever: HistoricalCandidate
    fitness_breakdown: dict[str, FiniteFloat] | None
    breakdown_unavailable_reason: str
    capture_elapsed_ms: FiniteFloat
    validation_elapsed_ms: FiniteFloat
    validation: HistoryValidation


class GenerationIndex(BaseModel):
    generation: int = Field(ge=0)
    timestamp: str
    metrics: HistoryMetrics
    generation_best_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    best_ever_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    capture_elapsed_ms: FiniteFloat
    validation_elapsed_ms: FiniteFloat
    snapshot_bytes: int = Field(ge=0)


class HistoryRetention(BaseModel):
    interval: int = Field(ge=1)
    max_run_bytes: int = Field(ge=1)
    automatic_deletion: Literal[False]


class HistoryIssue(BaseModel):
    generation: int | None
    code: str
    timestamp: str


class HistoryIndex(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: Literal[1]
    run_id: str
    created_at: str
    state: str
    configuration: dict[str, Any]
    input_fingerprint: str
    engine_fingerprint: str
    retention: HistoryRetention
    generations: list[GenerationIndex]
    errors: list[HistoryIssue]
    skipped_generations: list[int]
    bytes_written: int = Field(ge=0)
