"""Fail-closed API admission checks, without changing scoring or frozen inputs.

Missing files retain the engine's existing defaults. Present files must be valid
UTF-8 JSON in the stored preference/settings contracts. Validation never writes,
fills defaults in storage, scores a candidate, or consumes GA randomness.
"""
import json
from dataclasses import fields

from fastapi import HTTPException

from genetic_algorithm.models.ga_setting import GASetting
from schemas.faculty_preference import FacultyPreferenceResponse, GASettingResponse
from services import preference_storage_service as storage
from services.identity_service import resolve_faculty_identity

_MISSING = object()

def _invalid(label, unavailable=False):
    return HTTPException(503, {
        "code": "GA_INPUT_UNAVAILABLE" if unavailable else "GA_INPUT_INVALID",
        "message": f"Stored {label} {'could not be read' if unavailable else 'are invalid or corrupt'}. "
                   "No optimization was started. Ask an administrator to review the input file; "
                   "do not reset preferences to retry.",
    })


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("Non-finite JSON")


def _read(path, label):
    try:
        # Match the existing engine's UTF-8 reader: a BOM must not pass here and
        # then trigger the legacy scorer's silent-default fallback.
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _MISSING
    except OSError as error:
        raise _invalid(label, unavailable=True) from error
    except UnicodeError as error:
        raise _invalid(label) from error
    try:
        return json.loads(content, object_pairs_hook=_pairs, parse_constant=_constant)
    except (ValueError, RecursionError) as error:
        raise _invalid(label) from error


def _preferences(data):
    if not isinstance(data, list):
        raise ValueError("Expected preference records")
    seen = set()
    for record in data:
        if not isinstance(record, dict) or type(record.get("faculty_code")) is not int:
            raise ValueError("Invalid faculty code")
        code = record["faculty_code"]
        if code in seen:
            raise ValueError("Duplicate faculty preference")
        seen.add(code)
        resolve_faculty_identity(code)
        # Stored-response contract preserves legacy missing fields and extra
        # metadata; only new API writes use the stricter edit/pattern contract.
        FacultyPreferenceResponse.model_validate(record, strict=True)


def _settings(data):
    if not isinstance(data, dict):
        raise ValueError("Expected settings object")
    supported = {field.name for field in fields(GASetting)}
    if set(data) - supported:
        raise ValueError("Unsupported setting")
    GASettingResponse.model_validate(data, strict=True)
    positive = {"max_preparations", "workload_step_units", "daily_load_step_minutes"}
    for key, value in data.items():
        if type(value) is not int or value < (1 if key in positive else 0):
            raise ValueError("Invalid setting value")


def validate_ga_inputs():
    # Resolve at call time so isolated tests/servers can redirect the actual
    # engine paths. Check both readers if an integration intentionally differs.
    from genetic_algorithm.operators import FitnessFunction as fitness
    from services import ga_service

    sources = (
        ({ga_service.FACULTY_PREFERENCES_FILE, fitness.PREFERENCE_FILE}, "faculty preferences", _preferences),
        ({ga_service.GA_SETTINGS_FILE, fitness.GA_SETTINGS_FILE}, "GA settings", _settings),
    )
    with storage.LOCK:
        for paths, label, validate in sources:
            for path in sorted(paths, key=str):
                data = _read(path, label)
                if data is _MISSING:
                    continue
                try:
                    validate(data)
                except (ValueError, TypeError, KeyError, RecursionError) as error:
                    raise _invalid(label) from error
