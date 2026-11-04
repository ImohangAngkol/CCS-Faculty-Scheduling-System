"""Read-only actual-cache observation. Suppress private legacy import diagnostics."""
import contextlib
import io
import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]/"backend"))
from sqlalchemy.engine import Engine


def forbidden(*_args, **_kwargs):
    raise AssertionError("Database access forbidden in source observation")


Engine.connect = forbidden
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    import main  # Load the actual existing application/loader, without startup.
    from services.ga_source_qualification import status
    from services.ga_academic_context import verification_for
    before = random.getstate()
    result = status()
    assert random.getstate() == before
    assert verification_for({}) is None
assert result["qualification"] == "BLOCKED" and result["eligible_for_current"] is False
print(json.dumps({"scope": "Read-only observed caches; no GA execution, DB connection or institutional approval.",
    "default_academic_provider": "UNCONFIGURED", "rng_unchanged_during_inspection": True,
    "observation": result}, sort_keys=True))
