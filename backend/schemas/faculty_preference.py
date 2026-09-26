from pydantic import BaseModel, Field


# =========================================================
# FACULTY PREFERENCES
# =========================================================

class FacultyPreferenceBase(BaseModel):

    faculty_priority: int = Field(
        default=1,
        ge=1
    )

    preferred_subjects: list[str] = Field(
        default_factory=list
    )

    preferred_days: list[str] = Field(
        default_factory=list
    )

    preferred_start_time: str | None = None
    preferred_end_time: str | None = None

    gap_preference: str = "No Preference"

    use_subject_preference: bool = True
    use_day_preference: bool = True
    use_time_preference: bool = True
    use_gap_preference: bool = False


class FacultyPreferenceUpdate(
    FacultyPreferenceBase
):
    pass


class FacultyPreferenceResponse(
    FacultyPreferenceBase
):

    faculty_code: int


# =========================================================
# GA SETTINGS
# =========================================================

class GASettingBase(BaseModel):

    subject_penalty: int = Field(
        default=70,
        ge=0
    )

    time_penalty: int = Field(
        default=10,
        ge=0
    )

    day_penalty: int = Field(
        default=5,
        ge=0
    )

    preparation_penalty: int = Field(
        default=10,
        ge=0
    )

    load_balance_penalty: int = Field(
        default=10,
        ge=0
    )

    daily_load_penalty: int = Field(
        default=10,
        ge=0
    )

    max_preparations: int = Field(
        default=3,
        ge=1
    )

    target_teaching_load: int = Field(
        default=12,
        ge=0
    )

    load_tolerance: int = Field(
        default=3,
        ge=0
    )

    max_daily_teaching_minutes: int = Field(
        default=360,
        ge=0
    )

    daily_load_step_minutes: int = Field(
        default=60,
        ge=1
    )


class GASettingUpdate(GASettingBase):
    pass


class GASettingResponse(GASettingBase):
    pass