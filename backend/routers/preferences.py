"""Preference reads and fail-closed, atomic writes. No production auth bypass."""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from schemas.faculty_preference import FacultyPreferenceUpdate, FacultyPreferenceResponse, GASettingUpdate, GASettingResponse
from genetic_algorithm.models.faculty_preference import FacultyPreference
from genetic_algorithm.models.ga_setting import GASetting
from services.preference_validation_service import validate_preference_write
from services.metadata_service import resolve_normal_faculty
from services.preference_authorization import authorize_faculty, require_admin
from services import preference_storage_service as storage

router = APIRouter(prefix="/preferences", tags=["Preferences"])
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PREFERENCE_FILE = DATA_DIR / "faculty_preferences.json"
GA_SETTINGS_FILE = DATA_DIR / "ga_settings.json"


def _validate_records(records):
    if not isinstance(records, list):
        raise ValueError("Expected preference list")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or type(record.get("faculty_code")) is not int:
            raise ValueError("Invalid faculty record")
        code = record["faculty_code"]
        if code in seen:
            raise ValueError("Duplicate faculty record")
        seen.add(code)
        resolve_normal_faculty(code)
        FacultyPreferenceResponse.model_validate(record)


def _read_preferences():
    return storage.read(PREFERENCE_FILE, list, _validate_records)


def _write_preferences(records):
    storage.atomic_write(PREFERENCE_FILE, records)


def _validate_settings(data):
    if not isinstance(data, dict):
        raise ValueError("Expected settings object")
    GASettingResponse.model_validate(data)


def _read_ga_settings():
    data = storage.read(GA_SETTINGS_FILE, lambda: GASetting().to_dict(), _validate_settings)
    return GASetting.from_dict(data)


def _write_ga_settings(settings):
    storage.atomic_write(GA_SETTINGS_FILE, settings.to_dict())


@router.get("/ga-settings", response_model=GASettingResponse, dependencies=[Depends(require_admin)])
def get_ga_settings():
    return _read_ga_settings().to_dict()


@router.put("/ga-settings", response_model=GASettingResponse)
def update_ga_settings(payload: GASettingUpdate, principal=Depends(require_admin)):
    data = storage.update(GA_SETTINGS_FILE, lambda: GASetting().to_dict(), _validate_settings,
                          lambda current: {**current, **payload.model_dump(exclude_unset=True)})
    return GASetting.from_dict(data).to_dict()


@router.get("", response_model=list[FacultyPreferenceResponse], dependencies=[Depends(require_admin)])
def get_all_preferences():
    return _read_preferences()


@router.get("/{faculty_code}", response_model=FacultyPreferenceResponse)
def get_faculty_preference(faculty_code: int, principal=Depends(authorize_faculty)):
    try:
        resolve_normal_faculty(faculty_code)
    except ValueError as error:
        raise HTTPException(404, "Unknown optimization faculty ID.") from error
    return next((record for record in _read_preferences() if record["faculty_code"] == faculty_code),
                FacultyPreference(faculty_code=faculty_code).to_dict())


@router.put("/{faculty_code}", response_model=FacultyPreferenceResponse)
def update_faculty_preference(faculty_code: int, payload: FacultyPreferenceUpdate,
                              principal=Depends(authorize_faculty)):
    def change(records):
        previous = next((record for record in records if record["faculty_code"] == faculty_code), None)
        base = previous or FacultyPreference(faculty_code=faculty_code).to_dict()
        submitted = payload.model_dump(exclude_unset=True)
        if principal.role != "admin" and submitted.get("faculty_priority", base.get("faculty_priority", 1)) != base.get("faculty_priority", 1):
            raise HTTPException(403, "Faculty priority is an administrator-only setting.")
        merged = {**base, **submitted, "faculty_code": faculty_code}
        try:
            editable = FacultyPreferenceUpdate.model_validate(
                {key: value for key, value in merged.items() if key in FacultyPreferenceUpdate.model_fields})
            validate_preference_write(faculty_code, editable)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        return [merged if record["faculty_code"] == faculty_code else record for record in records] if previous is not None else [*records, merged]

    records = storage.update(PREFERENCE_FILE, list, _validate_records, change)
    return next(record for record in records if record["faculty_code"] == faculty_code)


@router.delete("/{faculty_code}")
def reset_faculty_preference(faculty_code: int, principal=Depends(require_admin)):
    try:
        resolve_normal_faculty(faculty_code)
    except ValueError as error:
        raise HTTPException(422, "Unknown optimization faculty ID.") from error
    def change(records):
        remaining = [record for record in records if record["faculty_code"] != faculty_code]
        if len(remaining) == len(records):
            raise HTTPException(404, "Faculty preference not found.")
        return remaining
    storage.update(PREFERENCE_FILE, list, _validate_records, change)
    return {"message": "Faculty preference reset."}
