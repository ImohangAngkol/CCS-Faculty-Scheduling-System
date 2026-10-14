"""Observation-only Phase 3F reports; never admits an optimization worker."""
from typing import Literal
from fastapi import APIRouter, Query
from routers.ga_history import read, download
from services import fitness_reporting_service as reports
from services import ga_history_service as history

router = APIRouter(prefix="/api/ga", tags=["Fitness Analysis"])
Candidate = Literal["generation_best", "best_ever"]
Format = Literal["json", "csv"]
Section = Literal["fitness", "workload"]


@router.get("/fitness-analysis/latest")
def latest():
    return read(reports.latest_report)


@router.get("/runs/{run_id}/generations/{generation}/fitness-analysis")
def generation(run_id: str, generation: int, candidate: Candidate = "generation_best"):
    return read(lambda: reports.generation_report(run_id, generation, candidate))


@router.get("/runs/{run_id}/fitness-comparison")
def comparison(run_id: str, left: int = Query(..., ge=0), right: int = Query(..., ge=0), candidate: Candidate = "generation_best"):
    return read(lambda: reports.comparison_report(run_id, left, right, candidate))


def exported(report, format, section, name):
    if format == "csv":
        content = reports.export_csv(report, section)
    else:
        content = history.checkpoints.canonical({**report, "report_kind": section} if section == "fitness" else
                  {"schema_version": 1, "source": report["source"], "report_kind": section,
                   "definitions": report["definitions"], "fitness_configuration": report["fitness_configuration"],
                   "faculty": [{k: v for k, v in row.items() if k not in ("preferences", "penalties")} for row in report["faculty"]]})
    return download(content, f"{name}-{section}.{format}", "text/csv" if format == "csv" else "application/json")


@router.get("/fitness-analysis/latest/export")
def latest_export(format: Format = "json", section: Section = "fitness"):
    return read(lambda: exported(reports.latest_report(), format, section, "latest-analysis"))


@router.get("/runs/{run_id}/generations/{generation}/fitness-analysis/export")
def generation_export(run_id: str, generation: int, candidate: Candidate = "generation_best", format: Format = "json", section: Section = "fitness"):
    return read(lambda: exported(reports.generation_report(run_id, generation, candidate), format, section,
                                f"run-{run_id}-generation-{generation}-{candidate}"))
