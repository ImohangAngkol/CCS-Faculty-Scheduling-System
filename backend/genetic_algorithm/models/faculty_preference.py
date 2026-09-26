from dataclasses import dataclass, field, asdict


@dataclass
class FacultyPreference:
    faculty_code: int

    # =====================================================
    # FACULTY PRIORITY
    # =====================================================

    # Existing faculty priority.
    # We keep this for backward compatibility.
    faculty_priority: int = 1


    # =====================================================
    # SUBJECT PREFERENCE
    # =====================================================

    preferred_subjects: list[str] = field(
        default_factory=list
    )

    # 0 = Ignore
    # 1 = Very Low
    # 2 = Low
    # 3 = Medium
    # 4 = High
    # 5 = Very High
    subject_importance: int = 3


    # =====================================================
    # DAY PREFERENCE
    # =====================================================

    preferred_days: list[str] = field(
        default_factory=list
    )

    day_importance: int = 3


    # =====================================================
    # TIME PREFERENCE
    # =====================================================

    preferred_start_time: str | None = None
    preferred_end_time: str | None = None

    time_importance: int = 3


    # =====================================================
    # SCHEDULE STYLE
    # =====================================================

    # Valid values:
    # "Compact"
    # "Scattered"
    # "No Preference"

    gap_preference: str = "No Preference"

    gap_importance: int = 0


    # =====================================================
    # LECTURE / LAB DAY PREFERENCE
    # =====================================================

    # Valid values:
    # "Same Day"
    # "Different Day"
    # "No Preference"

    lecture_lab_preference: str = "No Preference"

    lecture_lab_importance: int = 0


    # =====================================================
    # EXISTING ENABLE/DISABLE FLAGS
    # =====================================================
    #
    # Keep these for now because your current backend
    # and frontend already use them.
    #
    # Later we can simplify them once the new preference
    # scoring is completely working.
    # =====================================================

    use_subject_preference: bool = True
    use_day_preference: bool = True
    use_time_preference: bool = True
    use_gap_preference: bool = False
    use_lecture_lab_preference: bool = False


    # =====================================================
    # CONVERSION HELPERS
    # =====================================================

    def to_dict(self) -> dict:
        return asdict(self)


    @classmethod
    def from_dict(
        cls,
        data: dict
    ) -> "FacultyPreference":

        return cls(
            faculty_code=data["faculty_code"],

            faculty_priority=data.get(
                "faculty_priority",
                1
            ),

            preferred_subjects=data.get(
                "preferred_subjects",
                []
            ),

            subject_importance=data.get(
                "subject_importance",
                3
            ),

            preferred_days=data.get(
                "preferred_days",
                []
            ),

            day_importance=data.get(
                "day_importance",
                3
            ),

            preferred_start_time=data.get(
                "preferred_start_time"
            ),

            preferred_end_time=data.get(
                "preferred_end_time"
            ),

            time_importance=data.get(
                "time_importance",
                3
            ),

            gap_preference=data.get(
                "gap_preference",
                "No Preference"
            ),

            gap_importance=data.get(
                "gap_importance",
                0
            ),

            lecture_lab_preference=data.get(
                "lecture_lab_preference",
                "No Preference"
            ),

            lecture_lab_importance=data.get(
                "lecture_lab_importance",
                0
            ),

            use_subject_preference=data.get(
                "use_subject_preference",
                True
            ),

            use_day_preference=data.get(
                "use_day_preference",
                True
            ),

            use_time_preference=data.get(
                "use_time_preference",
                True
            ),

            use_gap_preference=data.get(
                "use_gap_preference",
                False
            ),

            use_lecture_lab_preference=data.get(
                "use_lecture_lab_preference",
                False
            ),
        )