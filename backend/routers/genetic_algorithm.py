import asyncio
import json
import queue
import threading
import os
import time
from pathlib import Path

from services.ga_progress_service import EventEmitter
from services.ga_log_service import capture_run_logs, console_print, store_for
from services import ga_control_service
from services import ga_checkpoint_service as checkpoints
from services import ga_service
from services.ga_history_service import capture_history, HistoryGenerationMonitor, update_lifecycle
from services.ga_control_service import RunRegistry, StopConflict, save_stopped_result, timestamp
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Header,
)

from fastapi.responses import StreamingResponse

from services.ga_service import (
    generate_schedule,
    run_genetic_algorithm,
    validate_saved_result,
)


router = APIRouter(
    prefix="/api/ga",
    tags=["Genetic Algorithm"],
)


# ============================================================
# Single-process admission across every API GA execution path
# ============================================================

_ga_execution_lock = threading.Lock()
_run_registry = RunRegistry()
# Context-local observational adapter; engine/checkpoint source hashes stay intact.
ga_service.GenerationMonitor = HistoryGenerationMonitor


def _execute_with_history(control, **parameters):
    def warning(message):
        # Complete lines go directly to the thread-safe run buffer, preserving
        # foreground partial-line capture and reconnectable warning delivery.
        console_print(message)
        store_for(_run_registry).buffer(control.run_id).append(message)
    with capture_history(control, _templates(), parameters.get("resume_state"), warning) as history:
        result = run_genetic_algorithm(**parameters)
        if history is not None and isinstance(result, dict):
            history.record_result(result)
        return result


def _admit_execution(cancellable=True, configuration=None):
    if not _ga_execution_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another Genetic Algorithm execution is already in progress.")
    try:
        control = _run_registry.register(configuration)
        control.finalizing = not cancellable
        if cancellable:
            control.durable = True
            checkpoints.write_marker(control)
        return control
    except Exception:
        if "control" in locals():
            with _run_registry.lock:
                _run_registry.active_id = None
                _run_registry.runs.pop(control.run_id, None)
        _ga_execution_lock.release()
        raise


def _release_execution(control):
    try:
        _run_registry.release(control)
    finally:
        try:
            update_lifecycle(control)
        except Exception:
            control.history_error = "GA_HISTORY_LIFECYCLE_WRITE_FAILED"
        finally:
            _ga_execution_lock.release()


def _finish_result(control, result):
    stopped = control.seal()
    if result is None:
        if not stopped or control.latest_completed_generation is not None:
            raise RuntimeError("GA returned no result after a validated generation.")
        control.finish("STOPPED")
        return None
    result = dict(result)
    result.update(run_id=control.run_id, status="STOPPED" if stopped else "COMPLETED")
    if stopped:
        if control.latest_completed_generation is None:
            raise RuntimeError("Cannot publish a stopped result without a validated boundary.")
        validate_saved_result(result)
        result.update(created_at=control.created_at, started_at=control.started_at,
                      stopped_at=timestamp(), stop_requested_at=control.stop_requested_at,
                      stop_reason=control.stop_reason, termination_reason="administrator_request",
                      elapsed_ms=control.snapshot()["elapsed_ms"])
        reference = save_stopped_result(control, result)
        control.finish("STOPPED", reference, result["stopped_at"])
    else:
        _save_latest_result(result)
        control.finish("COMPLETED", "latest_ga_result.json")
    return result


# ============================================================
# LATEST COMPLETED GA RESULT
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]
LATEST_RESULT_FILE = (
    BACKEND_DIR / "saved_chromosomes" / "latest_ga_result.json"
)


def _save_latest_result(result):
    """
    Persist the latest completed GA result shown by the frontend.

    This is intentionally separate from the saved-best chromosome:
    latest result = most recent completed run
    saved best    = best baseline chromosome across runs
    """
    LATEST_RESULT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        LATEST_RESULT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            indent=2,
            default=str,
        )


def _read_latest_result():
    if not LATEST_RESULT_FILE.exists():
        return None

    try:
        with open(
            LATEST_RESULT_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return None


# ============================================================
# GA STATUS
# ============================================================

@router.get("/status")
def get_ga_status():
    _run_registry.discover()
    active = _run_registry.active()
    return {
        "status": "ready",
        "active_run": active.snapshot() if active else None,
        "control_version": "3c.1",
        "process_instance_id": _run_registry.process_instance_id,
        "process_id": os.getpid(),
        "monitoring": "snapshot_polling",
        "pause_resume_version": "3d.1",
        # Discovery must not deserialize/validate every population. Verify only
        # the selected run through checkpoint-status before enabling resume.
        "paused_runs": [{**control.snapshot(), "accepting_resume": False}
                        for control in _run_registry.paused()],
        "message": (
            "Genetic Algorithm API is available."
        ),
    }


# ============================================================
# LATEST COMPLETED GA RESULT
# ============================================================

def _require_process(process_instance_id, run_id=None):
    if isinstance(process_instance_id, str) and process_instance_id != _run_registry.process_instance_id:
        raise HTTPException(status_code=409, detail={"code": "GA_PROCESS_CHANGED",
                            "message": "This backend process does not own the observed run. It restarted or the request reached another worker; no cancellation occurred.",
                            "run_id": run_id, "process_instance_id": _run_registry.process_instance_id})


def _owned_run(run_id, process_instance_id=None):
    _require_process(process_instance_id, run_id)
    _run_registry.discover()
    control = _run_registry.get(run_id)
    if control is None:
        raise HTTPException(status_code=404, detail={"code": "GA_UNKNOWN_RUN",
                            "message": "Run is unknown in this server process. Verify the run ID and backend instance; no cancellation occurred.",
                            "run_id": run_id, "process_instance_id": _run_registry.process_instance_id})
    return control


@router.get("/runs/{run_id}")
def get_run_state(run_id: str, process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    return {**control.snapshot(), "history_error": getattr(control, "history_error", None)}


@router.get("/runs/{run_id}/logs")
def get_run_logs(run_id: str, after_sequence: int = Query(default=0, ge=0),
                 process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    # No population/checkpoint restore, fitness calls or giant history copy.
    with control.lock:
        lifecycle = {"run_id": control.run_id, "process_instance_id": control.process_instance_id,
                     "state": control.state, "execution_active": control.execution_active}
    buffer = store_for(_run_registry).buffer(run_id, history_unavailable=control.state != "CREATED")
    return {**buffer.read(after_sequence), **lifecycle}


@router.post("/runs/{run_id}/stop")
def stop_run(run_id: str, process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    try:
        if control.state == "PAUSED" and not control.execution_active:
            return _launch_resume(control, stopping=True)
        if control.state == "INTERRUPTED":
            raise StopConflict("The interrupted worker no longer exists; no cancellation occurred.")
        return control.request_stop()
    except StopConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _templates():
    from services.ga_validation_templates import validation_templates
    return validation_templates((ga_service.list_subjects, ga_service.list_faculty, ga_service.lst_rooms))


def _checkpoint_error(error):
    return HTTPException(status_code=503 if error.code == "GA_CHECKPOINT_UNAVAILABLE" else 409 if error.code in {
        "GA_CHECKPOINT_INCOMPATIBLE", "GA_CHECKPOINT_INPUT_CHANGED"} else 422,
                         detail={"code": error.code, "message": str(error)})


@router.post("/runs/{run_id}/pause")
def pause_run(run_id: str, process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    try:
        if control.state == "INTERRUPTED" or not control.durable:
            raise StopConflict("This execution has no resumable population checkpoint capability.")
        return control.request_pause()
    except StopConflict as error:
        raise HTTPException(status_code=409, detail={"code": "GA_PAUSE_CONFLICT", "message": str(error)}) from error


@router.get("/runs/{run_id}/checkpoint-status")
def get_checkpoint_status(run_id: str, process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    try:
        from services.ga_checkpoint_verification import checkpoint_status
        verified = checkpoint_status(run_id, _templates())
        # Another client may resume/stop during the expensive validation.
        with control.lock:
            verified.update(process_instance_id=control.process_instance_id, state=control.state)
            verified["resumable"] = (verified["resumable"] and control.state == "PAUSED"
                                     and not control.execution_active and verified["checkpoint"] == control.checkpoint)
        return verified
    except checkpoints.CheckpointError as error:
        raise _checkpoint_error(error) from error


def _launch_resume(control, stopping=False):
    if not _ga_execution_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail={"code": "GA_EXECUTION_BUSY", "message": "Another GA worker owns execution admission."})
    claimed = False
    try:
        with control.lock:
            if control.state != "PAUSED" or control.execution_active:
                raise StopConflict("Only a durably paused run with no worker can resume.")
            marker = checkpoints.read_marker(control.run_id)
            if marker is None or marker["state"] != "PAUSED":
                raise checkpoints.CheckpointError("The durable record is not PAUSED.")
            checkpoint = control.checkpoint
        # Admission remains exclusive, but expensive compatibility/constraint
        # validation must not block read-only lifecycle/status requests.
        from services.ga_checkpoint_verification import load_checkpoint
        restored = load_checkpoint(control.run_id, _templates())
        with control.lock:
            marker = checkpoints.read_marker(control.run_id)
            if (control.state != "PAUSED" or control.execution_active
                    or control.checkpoint != checkpoint or marker is None
                    or marker["state"] != "PAUSED" or marker["checkpoint"] != checkpoint):
                raise StopConflict("The paused run changed during checkpoint validation; no worker was started.")
            _run_registry.claim(control)
            claimed = True
            if stopping:
                control.elapsed_offset = control.snapshot()["elapsed_ms"]
                control.started_clock = time.monotonic()
                acknowledgement = control.request_stop()
                control.execution_active = True
                control.ended_clock = None
            else:
                control.begin_resume()
                acknowledgement = {**control.snapshot(), "accepted": True, "already_requested": False}
        def worker():
            try:
                with capture_run_logs(_run_registry, control) as log:
                    log("GENETIC ALGORITHM STOPPING" if stopping else "GENETIC ALGORITHM RESUMING")
                    result = _execute_with_history(control, **restored["parameters"], resume_state=restored,
                                                  run_control=control, progress_callback=control.capture_progress)
                    if not isinstance(result, checkpoints.PausedRun):
                        _finish_result(control, result)
                    log(f"GENETIC ALGORITHM {control.state}")
            except Exception as error:
                control.fail(error)
                with capture_run_logs(_run_registry, control) as log:
                    log(f"GENETIC ALGORITHM FAILED: {error}")
            finally:
                _release_execution(control)
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return acknowledgement
    except checkpoints.CheckpointError as error:
        if claimed:
            _release_execution(control)
        else:
            _ga_execution_lock.release()
        raise _checkpoint_error(error) from error
    except Exception as error:
        if claimed:
            try:
                control.fail(error)
            finally:
                _release_execution(control)
        else:
            _ga_execution_lock.release()
        if isinstance(error, StopConflict):
            raise HTTPException(status_code=409, detail={"code": "GA_RESUME_CONFLICT", "message": str(error)}) from error
        raise


@router.post("/runs/{run_id}/resume")
def resume_run(run_id: str, process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    with control.lock:
        if control.state in {"RESUMING", "RUNNING"} and control.resumed_at:
            return {**control.snapshot(), "accepted": True, "already_requested": True}
        if control.state in {"STOPPED", "COMPLETED", "FAILED"}:
            return {**control.snapshot(), "accepted": False, "already_requested": False}
    return _launch_resume(control)


@router.get("/runs/{run_id}/result")
def get_stopped_result(run_id: str):
    # Canonical UUIDs prevent path traversal; stopped artifacts survive registry loss.
    try:
        if str(UUID(run_id)) != run_id:
            raise ValueError("Noncanonical run ID")
    except ValueError:
        raise HTTPException(status_code=404, detail="No preserved stopped result exists.")
    _run_registry.discover()
    path = ga_control_service.STOPPED_RUNS_DIR / f"{run_id}.json"
    control = _run_registry.get(run_id)
    expected_status = "STOPPED"
    if control is not None and control.state == "COMPLETED" and control.result_reference == "latest_ga_result.json":
        path = LATEST_RESULT_FILE
        expected_status = "COMPLETED"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No preserved stopped result exists.")
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Preserved stopped result cannot be read.") from error
    try:
        if result.get("run_id") != run_id or result.get("status") != expected_status:
            raise ValueError("Stopped artifact identity/state mismatch.")
        validate_saved_result(result)
    except (ValueError, AttributeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "success", "data": result}


@router.get("/latest")
def get_latest_ga_result():
    result = _read_latest_result()

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No completed GA result has been saved yet.",
        )

    try:
        validate_saved_result(result)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "status": "success",
        "data": result,
    }


# ============================================================
# INITIAL POPULATION
# ============================================================

@router.post("/generate")
def generate_ga_schedule(

    population_size: int = Query(
        default=10,
        ge=1,
        le=500,
    ),

):

    control = _admit_execution(cancellable=False)
    try:
        with capture_run_logs(_run_registry, control):
            control.start()

            result = generate_schedule(
                population_size=population_size
            )

            control.seal()
            control.finish("COMPLETED")
            return {
                "status": "success",
                "data": result,
            }


    except Exception as error:
        control.fail(error)

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    finally:
        _release_execution(control)


# ============================================================
# NORMAL GA RUN
# ============================================================

@router.post("/run")
def run_ga(

    population_size: int = Query(
        default=20,
        ge=2,
        le=500,
    ),

    generations: int = Query(
        default=5,
        ge=1,
        le=10000,
    ),

    fresh_chromosomes: int = Query(
        default=5,
        ge=0,
        le=500,
    ),

    baseline_mode: str = Query(
        default="fresh",
        pattern="^(fresh|saved|uploaded)$",
    ),

):

    control = _admit_execution(configuration={"population_size": population_size, "generations": generations,
                                            "fresh_chromosomes": fresh_chromosomes, "baseline_mode": baseline_mode})
    try:
        with capture_run_logs(_run_registry, control):
            control.start()

            result = _execute_with_history(control,
                population_size=population_size,
                generations=generations,
                fresh_chromosomes=fresh_chromosomes,
                baseline_mode=baseline_mode,
                run_control=control,
                progress_callback=control.capture_progress,
            )

            if isinstance(result, checkpoints.PausedRun):
                return {"status": "paused", "data": None, "run": control.snapshot()}
            result = _finish_result(control, result)


            return {
                "status": "success",
                "data": result,
                "run": control.snapshot(),
            }


    except Exception as error:
        control.fail(error)

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    finally:
        _release_execution(control)


# ============================================================
# LIVE GA STREAM
# ============================================================

@router.post("/stream")
def stream_ga(

    population_size: int = Query(
        default=20,
        ge=2,
        le=500,
    ),

    generations: int = Query(
        default=5,
        ge=1,
        le=10000,
    ),

    fresh_chromosomes: int = Query(
        default=5,
        ge=0,
        le=500,
    ),

    baseline_mode: str = Query(
        default="fresh",
        pattern="^(fresh|saved|uploaded)$",
    ),

    process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID"),

):

    _require_process(process_instance_id)
    requested = {"population_size": population_size, "generations": generations,
                 "fresh_chromosomes": fresh_chromosomes, "baseline_mode": baseline_mode}
    control = _admit_execution(configuration=requested)
    event_queue = queue.Queue(maxsize=1024)
    disconnected = threading.Event()

    def enqueue(event):
        if disconnected.is_set():
            return  # Detaching monitoring is not GA cancellation.
        try:
            if event["type"] == "log":
                event_queue.put_nowait(event)
            else:
                event_queue.put(event, timeout=0.1)
        except queue.Full:
            if event["type"] == "log":
                return  # Console logs are best effort; structured metrics are not.
            raise RuntimeError("Monitoring consumer is too slow; structured event delivery failed.")

    emitter = EventEmitter(enqueue, control.run_id)

    def terminal(event_type, data):
        # Reserve terminal delivery even when a slow client filled the queue.
        try:
            emitter.emit(event_type, data)
        except RuntimeError:
            try:
                event_queue.get_nowait()
            except queue.Empty:
                pass
            emitter.emit(event_type, data)

    control.on_state = terminal

    def progress(event_type, data):
        control.capture_progress(event_type, data)
        emitter.emit(event_type, data)

    def worker():
        status = "FAILED"
        try:
            with capture_run_logs(_run_registry, control, lambda entry: emitter.emit("log", entry)) as log:
                control.start()
                emitter.emit("run_started", {**control.snapshot(), "phase": "initializing"})
                log("GENETIC ALGORITHM STARTED")
                result = _execute_with_history(control,
                    **requested, progress_callback=progress, run_control=control,
                )
                result = None if isinstance(result, checkpoints.PausedRun) else _finish_result(control, result)
                status = control.state
                if result is not None:
                    terminal("result", result)
                log(f"GENETIC ALGORITHM {status}")
        except Exception as error:
            control.fail(error)
            status = control.state
            with capture_run_logs(_run_registry, control, lambda entry: emitter.emit("log", entry)) as log:
                log(f"GENETIC ALGORITHM FAILED: {error}")
            if status == "FAILED":
                terminal("error", {"status": "FAILED", "code": "GA_EXECUTION_FAILED", "message": str(error)})
        finally:
            try:
                _release_execution(control)
            finally:
                terminal("done", {"status": status, "has_result": control.result_reference is not None,
                                  "latest_completed_generation": control.latest_completed_generation})

    thread = threading.Thread(target=worker, daemon=True)
    try:
        # Registration and the first event precede the tracked worker's launch.
        with control.lock:
            emitter.emit("run_created", control.snapshot())
        thread.start()
    except Exception as error:
        try:
            control.fail(error)
        finally:
            _release_execution(control)
        raise

    def next_event():
        try:
            return event_queue.get(timeout=0.5)
        except queue.Empty:
            return None

    async def event_generator():
        try:
            while True:
                event = await asyncio.to_thread(next_event)
                if event is None:
                    continue
                yield f"data: {json.dumps(event, allow_nan=False, default=str)}\n\n"
                if event["type"] == "done":
                    break
        finally:
            disconnected.set()
            # Worker continues and preserves its validated final result.
            while not event_queue.empty():
                try:
                    event_queue.get_nowait()
                except queue.Empty:
                    break

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no",
    })
