import asyncio
import io
import json
import queue
import sys
import threading

from contextlib import redirect_stdout

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from fastapi.responses import StreamingResponse

from services.ga_service import (
    generate_schedule,
    run_genetic_algorithm,
)


router = APIRouter(
    prefix="/api/ga",
    tags=["Genetic Algorithm"],
)


# ============================================================
# Prevent multiple streamed GA runs at the same time
# ============================================================

_ga_stream_lock = threading.Lock()


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

    try:

        result = run_genetic_algorithm(
            population_size=population_size,
            generations=generations,
            fresh_chromosomes=fresh_chromosomes,
            baseline_mode=baseline_mode,
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

    async def event_generator():

        event_queue = queue.Queue()


        # ====================================================
        # BACKGROUND WORKER
        # ====================================================

        def worker():

            acquired = (
                _ga_stream_lock.acquire(
                    blocking=False
                )
            )


            if not acquired:

                event_queue.put(
                    {
                        "type": "error",
                        "message": (
                            "Another Genetic Algorithm "
                            "run is already in progress."
                        ),
                    }
                )

                event_queue.put(
                    {
                        "type": "done",
                    }
                )

                return


            original_stdout = sys.stdout


            writer = QueueWriter(
                event_queue,
                original_stdout,
            )


            try:

                # --------------------------------------------
                # INITIAL LIVE LOG
                # --------------------------------------------

                event_queue.put(
                    {
                        "type": "log",
                        "message": "=" * 60,
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": (
                            "GENETIC ALGORITHM STARTED"
                        ),
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": "=" * 60,
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": (
                            f"Population Size   : "
                            f"{population_size}"
                        ),
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": (
                            f"Generations       : "
                            f"{generations}"
                        ),
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": (
                            f"Fresh Chromosomes : "
                            f"{fresh_chromosomes}"
                        ),
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": (
                            f"Baseline Mode     : "
                            f"{baseline_mode}"
                        ),
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": "",
                    }
                )


                # --------------------------------------------
                # RUN GA AND CAPTURE print()
                # --------------------------------------------

                with redirect_stdout(
                    writer
                ):

                    result = (
                        run_genetic_algorithm(

                            population_size=
                            population_size,

                            generations=
                            generations,

                            fresh_chromosomes=
                            fresh_chromosomes,

                            baseline_mode=
                            baseline_mode,

                        )
                    )


                writer.flush_remaining()


                # --------------------------------------------
                # COMPLETE
                # --------------------------------------------

                event_queue.put(
                    {
                        "type": "log",
                        "message": "",
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": "=" * 60,
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": (
                            "GENETIC ALGORITHM COMPLETED"
                        ),
                    }
                )


                event_queue.put(
                    {
                        "type": "log",
                        "message": "=" * 60,
                    }
                )


                # Send final result
                event_queue.put(
                    {
                        "type": "result",
                        "data": result,
                    }
                )


            except Exception as error:

                writer.flush_remaining()


                event_queue.put(
                    {
                        "type": "error",
                        "message": str(error),
                    }
                )


            finally:

                _ga_stream_lock.release()


                event_queue.put(
                    {
                        "type": "done",
                    }
                )


        # ====================================================
        # START THREAD
        # ====================================================

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        thread.start()


        # ====================================================
        # SEND EVENTS TO FRONTEND
        # ====================================================

        while True:

            event = await asyncio.to_thread(
                event_queue.get
            )


            payload = json.dumps(
                event,
                default=str,
            )


            yield (
                f"data: {payload}\n\n"
            )


            if (
                event.get("type")
                ==
                "done"
            ):
                break


    return StreamingResponse(

        event_generator(),

        media_type="text/event-stream",

        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },

    )