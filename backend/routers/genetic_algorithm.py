import asyncio
import io
import json
import queue
import sys
import threading
import os
from pathlib import Path

from contextlib import redirect_stdout
from services.ga_progress_service import EventEmitter
from services import ga_control_service
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


def _admit_execution(cancellable=True, configuration=None):
    if not _ga_execution_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another Genetic Algorithm execution is already in progress.")
    try:
        control = _run_registry.register(configuration)
        control.finalizing = not cancellable
        return control
    except Exception:
        _ga_execution_lock.release()
        raise


def _release_execution(control):
    _run_registry.release(control)
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
# STDOUT CAPTURE
# ============================================================

class QueueWriter(io.TextIOBase):

    def __init__(
        self,
        event_queue,
        original_stdout,
    ):
        super().__init__()

        self.event_queue = event_queue
        self.owner_thread = threading.get_ident()
        self.original_stdout = original_stdout

        self.buffer = ""

        self.lock = threading.Lock()


    def writable(self):
        return True


    def write(self, text):

        if not text:
            return 0


        # Keep showing output in VS Code terminal
        self.original_stdout.write(text)
        self.original_stdout.flush()


        if threading.get_ident() != self.owner_thread:
            return len(text)

        # Also send output to frontend
        with self.lock:

            normalized = (
                text
                .replace("\r\n", "\n")
                .replace("\r", "\n")
            )

            self.buffer += normalized


            while "\n" in self.buffer:

                line, self.buffer = (
                    self.buffer.split(
                        "\n",
                        1,
                    )
                )

                self.event_queue.put(
                    {
                        "type": "log",
                        "message": line,
                    }
                )


        return len(text)


    def flush(self):
        self.original_stdout.flush()


    def flush_remaining(self):

        with self.lock:

            if self.buffer:

                self.event_queue.put(
                    {
                        "type": "log",
                        "message": self.buffer,
                    }
                )

                self.buffer = ""


# ============================================================
# GA STATUS
# ============================================================

@router.get("/status")
def get_ga_status():
    active = _run_registry.active()
    return {
        "status": "ready",
        "active_run": active.snapshot() if active else None,
        "control_version": "3c.1",
        "process_instance_id": _run_registry.process_instance_id,
        "process_id": os.getpid(),
        "monitoring": "snapshot_polling",
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
    control = _run_registry.get(run_id)
    if control is None:
        raise HTTPException(status_code=404, detail={"code": "GA_UNKNOWN_RUN",
                            "message": "Run is unknown in this server process. Verify the run ID and backend instance; no cancellation occurred.",
                            "run_id": run_id, "process_instance_id": _run_registry.process_instance_id})
    return control


@router.get("/runs/{run_id}")
def get_run_state(run_id: str, process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    return control.snapshot()


@router.post("/runs/{run_id}/stop")
def stop_run(run_id: str, process_instance_id: str | None = Header(default=None, alias="X-GA-Process-ID")):
    control = _owned_run(run_id, process_instance_id)
    try:
        return control.request_stop()
    except StopConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/runs/{run_id}/result")
def get_stopped_result(run_id: str):
    # Canonical UUIDs prevent path traversal; stopped artifacts survive registry loss.
    try:
        if str(UUID(run_id)) != run_id:
            raise ValueError("Noncanonical run ID")
    except ValueError:
        raise HTTPException(status_code=404, detail="No preserved stopped result exists.")
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
    control.start()
    try:

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
    control.start()
    try:

        result = run_genetic_algorithm(
            population_size=population_size,
            generations=generations,
            fresh_chromosomes=fresh_chromosomes,
            baseline_mode=baseline_mode,
            run_control=control,
            progress_callback=control.capture_progress,
        )

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
            event_queue.put(event, timeout=0.1)
        except queue.Full:
            if event["type"] == "log":
                return  # Console logs are best effort; structured metrics are not.
            raise RuntimeError("Monitoring consumer is too slow; structured event delivery failed.")

    emitter = EventEmitter(enqueue, control.run_id)

    class LogSink:
        def put(self, event):
            emitter.emit("log", {"message": event["message"]})

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
        writer = QueueWriter(LogSink(), sys.stdout)
        status = "FAILED"
        try:
            control.start()
            emitter.emit("run_started", {**control.snapshot(), "phase": "initializing"})
            emitter.emit("log", {"message": "GENETIC ALGORITHM STARTED"})
            with redirect_stdout(writer):
                result = run_genetic_algorithm(
                    **requested, progress_callback=progress, run_control=control,
                )
            writer.flush_remaining()
            result = _finish_result(control, result)
            status = control.state
            if result is not None:
                terminal("result", result)
            emitter.emit("log", {"message": f"GENETIC ALGORITHM {status}"})
        except Exception as error:
            control.fail(error)
            status = control.state
            if status == "FAILED":
                terminal("error", {"status": "FAILED", "code": "GA_EXECUTION_FAILED", "message": str(error)})
        finally:
            try:
                terminal("done", {"status": status, "has_result": control.result_reference is not None,
                                  "latest_completed_generation": control.latest_completed_generation})
            finally:
                _release_execution(control)

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
