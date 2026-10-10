from typing import Any, Literal
from pydantic import BaseModel


class GAEvent(BaseModel):
    schema_version: Literal[1] = 1
    run_id: str
    sequence: int
    type: Literal["run_created", "run_started", "initial_population_ready",
                  "generation_completed", "log", "result", "error", "done"]
    timestamp: str
    data: dict[str, Any]
