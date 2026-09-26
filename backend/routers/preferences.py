import json
from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException
)

from schemas.faculty_preference import (
    FacultyPreferenceUpdate,
    FacultyPreferenceResponse,
    GASettingUpdate,
    GASettingResponse,
)

from genetic_algorithm.models.faculty_preference import (
    FacultyPreference
)

from genetic_algorithm.models.ga_setting import (
    GASetting
)


router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"]
)


# =========================================================
# FILE LOCATIONS
# =========================================================

BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DATA_DIR = BACKEND_DIR / "data"

PREFERENCE_FILE = (
    DATA_DIR
    / "faculty_preferences.json"
)

GA_SETTINGS_FILE = (
    DATA_DIR
    / "ga_settings.json"
)


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# HELPERS
# =========================================================

def _read_preferences() -> list[dict]:

    if not PREFERENCE_FILE.exists():
        return []

    try:

        with open(
            PREFERENCE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


def _write_preferences(
    preferences: list[dict]
):

    with open(
        PREFERENCE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            preferences,
            file,
            indent=4
        )


def _read_ga_settings() -> GASetting:

    if not GA_SETTINGS_FILE.exists():

        settings = GASetting()

        _write_ga_settings(
            settings
        )

        return settings

    try:

        with open(
            GA_SETTINGS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return GASetting.from_dict(
            data
        )

    except (
        json.JSONDecodeError,
        OSError
    ):

        return GASetting()


def _write_ga_settings(
    settings: GASetting
):

    with open(
        GA_SETTINGS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            settings.to_dict(),
            file,
            indent=4
        )


# =========================================================
# GA SETTINGS ROUTES
#
# IMPORTANT:
# Put these BEFORE /{faculty_code}
# =========================================================

@router.get(
    "/ga-settings",
    response_model=GASettingResponse
)
def get_ga_settings():

    settings = _read_ga_settings()

    return settings.to_dict()


@router.put(
    "/ga-settings",
    response_model=GASettingResponse
)
def update_ga_settings(
    payload: GASettingUpdate
):

    settings = GASetting.from_dict(
        payload.model_dump()
    )

    _write_ga_settings(
        settings
    )

    return settings.to_dict()


# =========================================================
# GET ALL FACULTY PREFERENCES
# =========================================================

@router.get(
    "",
    response_model=list[
        FacultyPreferenceResponse
    ]
)
def get_all_preferences():

    return _read_preferences()


# =========================================================
# GET ONE FACULTY
# =========================================================

@router.get(
    "/{faculty_code}",
    response_model=FacultyPreferenceResponse
)
def get_faculty_preference(
    faculty_code: int
):

    preferences = _read_preferences()

    for preference in preferences:

        if int(
            preference[
                "faculty_code"
            ]
        ) == faculty_code:

            return preference

    # Create default preference if
    # this faculty has never saved one.
    preference = FacultyPreference(
        faculty_code=faculty_code
    )

    preferences.append(
        preference.to_dict()
    )

    _write_preferences(
        preferences
    )

    return preference.to_dict()


# =========================================================
# SAVE / UPDATE FACULTY
# =========================================================

@router.put(
    "/{faculty_code}",
    response_model=FacultyPreferenceResponse
)
def update_faculty_preference(
    faculty_code: int,
    payload: FacultyPreferenceUpdate
):

    preferences = _read_preferences()

    updated = FacultyPreference(
        faculty_code=faculty_code,

        faculty_priority=(
            payload.faculty_priority
        ),

        preferred_subjects=(
            payload.preferred_subjects
        ),

        preferred_days=(
            payload.preferred_days
        ),

        preferred_start_time=(
            payload.preferred_start_time
        ),

        preferred_end_time=(
            payload.preferred_end_time
        ),

        gap_preference=(
            payload.gap_preference
        ),

        use_subject_preference=(
            payload.use_subject_preference
        ),

        use_day_preference=(
            payload.use_day_preference
        ),

        use_time_preference=(
            payload.use_time_preference
        ),

        use_gap_preference=(
            payload.use_gap_preference
        ),
    )

    found = False

    for index, preference in enumerate(
        preferences
    ):

        if int(
            preference["faculty_code"]
        ) == faculty_code:

            preferences[index] = (
                updated.to_dict()
            )

            found = True
            break

    if not found:

        preferences.append(
            updated.to_dict()
        )

    _write_preferences(
        preferences
    )

    return updated.to_dict()


# =========================================================
# OPTIONAL RESET
# =========================================================

@router.delete(
    "/{faculty_code}"
)
def reset_faculty_preference(
    faculty_code: int
):

    preferences = _read_preferences()

    new_preferences = [
        preference
        for preference in preferences

        if int(
            preference["faculty_code"]
        ) != faculty_code
    ]

    if (
        len(new_preferences)
        == len(preferences)
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Faculty preference "
                "not found."
            )
        )

    _write_preferences(
        new_preferences
    )

    return {
        "message":
            "Faculty preference reset."
    }