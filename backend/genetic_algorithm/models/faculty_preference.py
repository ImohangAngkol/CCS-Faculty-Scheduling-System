from dataclasses import dataclass, field, asdict


@dataclass
class FacultyPreference:
    faculty_code: int

    # 1 = highest priority
    faculty_priority: int = 1

    preferred_subjects: list[str] = field(
        default_factory=list
    )

    preferred_days: list[str] = field(
        default_factory=list
    )

    preferred_start_time: str | None = None
    preferred_end_time: str | None = None

    # Future use:
    # Compact / Scattered / No Preference
    gap_preference: str = "No Preference"

    # Faculty/admin can decide which preferences
    # the GA should consider.
    use_subject_preference: bool = True
    use_day_preference: bool = True
    use_time_preference: bool = True
    use_gap_preference: bool = False

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            faculty_code=int(data["faculty_code"]),
            faculty_priority=int(
                data.get("faculty_priority", 1)
            ),
            preferred_subjects=list(
                data.get("preferred_subjects", [])
            ),
            preferred_days=list(
                data.get("preferred_days", [])
            ),
            preferred_start_time=data.get(
                "preferred_start_time"
            ),
            preferred_end_time=data.get(
                "preferred_end_time"
            ),
            gap_preference=data.get(
                "gap_preference",
                "No Preference"
            ),
            use_subject_preference=bool(
                data.get(
                    "use_subject_preference",
                    True
                )
            ),
            use_day_preference=bool(
                data.get(
                    "use_day_preference",
                    True
                )
            ),
            use_time_preference=bool(
                data.get(
                    "use_time_preference",
                    True
                )
            ),
            use_gap_preference=bool(
                data.get(
                    "use_gap_preference",
                    False
                )
            ),
        )