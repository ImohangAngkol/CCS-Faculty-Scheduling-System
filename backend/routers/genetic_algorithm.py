import asyncio
import io
import json
import queue
import sys
import threading
from pathlib import Path

from contextlib import redirect_stdout
from services.ga_progress_service import EventEmitter

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
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


def _admit_execution():
    if not _ga_execution_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another Genetic Algorithm execution is already in progress.")


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

    return {
        "status": "ready",
        "message": (
            "Genetic Algorithm API is available."
        ),
    }


# ============================================================
# LATEST COMPLETED GA RESULT
# ============================================================

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

    _admit_execution()
    try:

        result = generate_schedule(
            population_size=population_size
        )

        return {
            "status": "success",
            "data": result,
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    finally:
        _ga_execution_lock.release()


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

    _admit_execution()
    try:

        result = run_genetic_algorithm(
            population_size=population_size,
            generations=generations,
            fresh_chromosomes=fresh_chromosomes,
            baseline_mode=baseline_mode,
        )

        _save_latest_result(
            result
        )


        return {
            "status": "success",
            "data": result,
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    finally:
        _ga_execution_lock.release()


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

):

    _admit_execution()
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

    emitter = EventEmitter(enqueue)

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

    def worker():
        writer = QueueWriter(LogSink(), sys.stdout)
        status = "FAILED"
        try:
            requested = {"population_size": population_size, "generations": generations,
                         "fresh_chromosomes": fresh_chromosomes, "baseline_mode": baseline_mode}
            emitter.emit("run_created", {"status": "CREATED", "configuration": requested})
            emitter.emit("run_started", {"status": "RUNNING", "phase": "initializing"})
            emitter.emit("log", {"message": "GENETIC ALGORITHM STARTED"})
            with redirect_stdout(writer):
                result = run_genetic_algorithm(
                    **requested, progress_callback=emitter.emit,
                )
            writer.flush_remaining()
            _save_latest_result(result)
            emitter.emit("result", result)
            status = "COMPLETED"
            emitter.emit("log", {"message": "GENETIC ALGORITHM COMPLETED"})
        except Exception as error:
            terminal("error", {"status": "FAILED", "code": "GA_EXECUTION_FAILED", "message": str(error)})
        finally:
            try:
                terminal("done", {"status": status})
            finally:
                _ga_execution_lock.release()

    thread = threading.Thread(target=worker, daemon=True)
    try:
        thread.start()
    except Exception:
        _ga_execution_lock.release()
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
