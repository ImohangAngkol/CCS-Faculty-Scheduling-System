"""Read-only projection of the existing latest result. No scoring or persistence."""
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

from schemas.schedule import FacultyAssignment, FacultyScheduleSource, MyScheduleResponse

MAX_SOURCE_BYTES = 32 * 1024 * 1024


def problem(status, code, message):
    # Do not echo validation failures, other assignments, file paths or run data.
    return HTTPException(status, {"code": code, "message": message})


def _signature(stat):
    # On Windows/Python 3.14 fstat/stat may expose different ctime semantics
    # (change time versus creation time). Identity/size/mtime are comparable.
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("Non-finite JSON")


def _read(path: Path):
    try:
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > MAX_SOURCE_BYTES:
                raise ValueError("Oversized source")
            raw = stream.read(MAX_SOURCE_BYTES + 1)
            after = os.fstat(stream.fileno())
        if _signature(before) != _signature(after) or _signature(after) != _signature(path.stat()):
            raise problem(409, "SCHEDULE_SOURCE_CHANGED", "The saved proposal changed during this read. Refresh to try again.")
        if len(raw) > MAX_SOURCE_BYTES:
            raise ValueError("Oversized source")
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant), after
    except FileNotFoundError:
        return None, None
    except (OSError, ValueError, RecursionError):
        raise problem(503, "SCHEDULE_SOURCE_UNAVAILABLE", "The saved proposal is unavailable or unreadable. Ask an administrator to review it; no schedule was changed.") from None


def _check_unchanged(path, signature):
    try:
        unchanged = _signature(path.stat()) == _signature(signature)
    except OSError:
        unchanged = False
    if not unchanged:
        raise problem(409, "SCHEDULE_SOURCE_CHANGED", "The saved proposal changed during this read. Refresh to try again.")


def own_schedule(identity):
    # Resolve the existing reader alias at call time: fixtures redirect this path
    # already, and no independent institutional-storage destination is introduced.
    from routers import genetic_algorithm as ga_router
    from services import ga_service

    path = ga_router.LATEST_RESULT_FILE
    payload, signature = _read(path)
    if signature is None:
        return MyScheduleResponse(availability="missing", faculty_id=identity.faculty_id,
                                  faculty_code=identity.faculty_code,
                                  source=FacultyScheduleSource(compatibility="not_available"), assignments=[])
    if not isinstance(payload, dict) or not isinstance(payload.get("schedule"), list):
        raise problem(503, "SCHEDULE_SOURCE_UNAVAILABLE", "The saved proposal has an unsupported format. Ask an administrator to review it.")
    if payload.get("status", "COMPLETED") != "COMPLETED":
        raise problem(409, "SCHEDULE_SOURCE_STALE", "The saved source is not a completed GA proposal. Ask an administrator to review it.")
    try:
        # Existing hard-compatibility validation reconstructs detached copies;
        # it does not evaluate fitness, sample randomness or write artifacts.
        ga_service.validate_saved_result(copy.deepcopy(payload))
    except ValueError:
        raise problem(409, "SCHEDULE_SOURCE_STALE", "The saved proposal is incompatible with the loaded scheduling inputs. Ask an administrator to review it.") from None
    except Exception:
        raise problem(503, "SCHEDULE_SOURCE_UNAVAILABLE", "The saved proposal could not be validated. Try again or contact an administrator.") from None
    assignments = []
    try:
        for row in payload["schedule"]:
            # Current saved-result semantics use canonical legacy numeric codes.
            # Do not authorize by name/display label, external ID or a client ID.
            if str(row.get("faculty")) != str(identity.faculty_code):
                continue
            assignments.append(FacultyAssignment(
                subject=row["subject"], title=row.get("title") or None,
                section=row["section"], type=row["type"].strip().title(),
                day=row["day"], start=row["start"], end=row["end"],
                room=row.get("room") or None,
            ))
    except (KeyError, AttributeError, TypeError, ValidationError):
        raise problem(503, "SCHEDULE_SOURCE_UNAVAILABLE", "The saved proposal contains unsupported timetable data. Ask an administrator to review it.") from None
    _check_unchanged(path, signature)
    return MyScheduleResponse(
        availability="available" if assignments else "empty", faculty_id=identity.faculty_id,
        faculty_code=identity.faculty_code,
        source=FacultyScheduleSource(compatibility="checked_against_loaded_inputs",
                                    saved_at=datetime.fromtimestamp(signature.st_mtime, timezone.utc)),
        assignments=assignments,
    )
