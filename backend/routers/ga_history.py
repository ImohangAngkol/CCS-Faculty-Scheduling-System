"""Read-only history routes. None admit workers or change live GA context."""
from typing import Literal
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from services import ga_history_service as history

router = APIRouter(prefix="/api/ga", tags=["Generation History"])
Candidate = Literal["generation_best", "best_ever"]
logger = logging.getLogger(__name__)


def read(operation):
    try:
        return operation()
    except history.HistoryError as error:
        raise HTTPException(error.status, {"code": error.code, "message": str(error)}) from error
    except OSError as error:
        logger.exception("Generation history storage unavailable")
        raise HTTPException(503, {"code": "GA_HISTORY_UNAVAILABLE", "message": "History storage is temporarily unavailable. Check backend storage and retry."}) from error
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        logger.exception("Unexpected generation history read/validation failure")
        raise HTTPException(422, {"code": "GA_HISTORY_INVALID", "message": "History could not be read or validated."}) from error


def lifecycle(index, discover=True):
    # Existing lifecycle service is authoritative, including restart INTERRUPTED.
    from routers.genetic_algorithm import _run_registry
    if discover:
        _run_registry.discover()
    control = _run_registry.get(index["run_id"])
    state = control.state if control is not None else index["state"]
    if control is None and state not in {"PAUSED", "STOPPED", "COMPLETED", "FAILED"}:
        state = "INTERRUPTED"
    latest = index["generations"][-1] if index["generations"] else None
    return {"schema_version": 1, "run_id": index["run_id"], "state": state,
            "created_at": index["created_at"], "updated_at": index.get("updated_at"),
            "started_at": index.get("started_at"),
            "ended_at": control.ended_at if control is not None else index.get("ended_at"),
            "generations_recorded": len(index["generations"]), "latest": latest,
            "retention": index["retention"], "bytes_written": index["bytes_written"],
            "errors": index["errors"], "skipped_generations": index["skipped_generations"],
            "history_error": getattr(control, "history_error", None) if control is not None else None}


@router.get("/runs")
def runs(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    def operation():
        items, errors = [], []
        from routers.genetic_algorithm import _run_registry
        _run_registry.discover()
        if history.SNAPSHOTS_DIR.exists():
            for path in history.SNAPSHOTS_DIR.iterdir():
                if not path.is_dir():
                    continue
                try:
                    items.append(lifecycle(history.manifest(path.name), discover=False))
                except history.HistoryError as error:
                    # Never leak invalid directory names/raw paths.
                    if error.status != 404:
                        errors.append({"code": error.code, "message": "An archived run index cannot be read."})
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return {"schema_version": 1, "items": items[offset:offset + limit], "total": len(items),
                "offset": offset, "limit": limit, "errors": errors}
    return read(operation)


@router.get("/runs/{run_id}/generations")
def generations(run_id: str, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    def operation():
        index = history.manifest(run_id)
        return {"schema_version": 1, "run": lifecycle(index), "items": index["generations"][offset:offset + limit],
                "total": len(index["generations"]), "offset": offset, "limit": limit}
    return read(operation)


@router.get("/runs/{run_id}/generations/{generation}")
def generation_detail(run_id: str, generation: int):
    return read(lambda: history.get_generation(run_id, generation))


def validated(run_id, generation, candidate):
    from routers.genetic_algorithm import _templates
    data = history.get_generation(run_id, generation)
    selected = data[candidate]
    history.checked_payload(selected["payload"], _templates(), data["metrics"]["input_fingerprint"])
    return data, selected


@router.get("/runs/{run_id}/generations/{generation}/schedule")
def schedule(run_id: str, generation: int, candidate: Candidate = "generation_best"):
    def operation():
        data = history.get_generation(run_id, generation)
        selected = data[candidate]
        current_inputs_match = data["metrics"]["input_fingerprint"] == history.input_fingerprint()
        if current_inputs_match:
            from routers.genetic_algorithm import _templates
            history.checked_payload(selected["payload"], _templates(), data["metrics"]["input_fingerprint"])
        return {"schema_version": 1, "run_id": run_id, "generation": generation, "candidate": candidate,
                "chromosome_id": selected["chromosome_id"], "schedule": selected["payload"]["schedule"],
                "validation": data["validation"], "validation_context": "original-inputs-at-capture",
                "current_inputs_match": current_inputs_match}
    return read(operation)


@router.get("/runs/{run_id}/generations/{generation}/analysis")
def analysis(run_id: str, generation: int, candidate: Candidate = "generation_best"):
    return read(lambda: history.analysis(run_id, generation, candidate))


@router.get("/runs/{run_id}/compare")
def comparison(run_id: str, left: int = Query(..., ge=0), right: int = Query(..., ge=0), candidate: Candidate = "generation_best"):
    return read(lambda: history.compare(run_id, left, right, candidate))


def download(content, name, media_type):
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{name}"',
                                                           "Cache-Control": "no-store"})


@router.get("/runs/{run_id}/generations/{generation}/export")
def export_candidate(run_id: str, generation: int, candidate: Candidate = "generation_best", format: Literal["json", "csv"] = "json"):
    def operation():
        data, selected = validated(run_id, generation, candidate)
        name = f"run-{run_id}-generation-{generation}-{candidate}.{format}"
        if format == "json":
            # Reuse the upload-compatible chromosome schema; observation metadata is additive.
            payload = {**selected["payload"], "history": {"schema_version": 1, "run_id": run_id,
                       "generation": generation, "candidate": candidate, "chromosome_id": selected["chromosome_id"],
                       "validation": data["validation"], "metrics": data["metrics"],
                       "export_validation": {"status": "passed", "validated_at": history.utc()}}}
            return download(history.checkpoints.canonical(payload), name, "application/json")
        fields = ["subject", "title", "section", "type", "faculty", "room", "day", "start", "end"]
        rows = [{**row, "faculty": faculty_label(row["faculty"])} for row in selected["payload"]["schedule"]]
        return download(history.csv_content(rows, fields), name, "text/csv")
    return read(operation)


def faculty_label(code):
    return f"Faculty {code}" if str(code).isdigit() else "Preassigned Instructor" if str(code).startswith("external:") else str(code)


@router.get("/runs/{run_id}/history/export")
def export_history(run_id: str):
    def operation():
        index = history.manifest(run_id)
        rows = [{"run_id": run_id, "timestamp": item["timestamp"], **item["metrics"]} for item in index["generations"]]
        fields = ["run_id", "timestamp", "generation", "population_requested", "population_actual", "generation_best_fitness",
                  "best_ever_fitness", "average_fitness", "worst_fitness", "accepted_new_chromosomes_total", "elapsed_ms"]
        return download(history.csv_content(rows, fields), f"run-{run_id}-fitness-history.csv", "text/csv")
    return read(operation)


@router.get("/runs/{run_id}/compare/export")
def export_comparison(run_id: str, left: int = Query(..., ge=0), right: int = Query(..., ge=0), candidate: Candidate = "generation_best"):
    def operation():
        # Comparison JSON contains schedules too: both must pass the hard gate.
        validated(run_id, left, candidate)
        validated(run_id, right, candidate)
        data = history.compare(run_id, left, right, candidate)
        return download(history.checkpoints.canonical(data), f"run-{run_id}-compare-{left}-{right}-{candidate}.json", "application/json")
    return read(operation)
