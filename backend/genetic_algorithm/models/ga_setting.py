from dataclasses import dataclass, asdict


@dataclass
class GASetting:

    subject_penalty: int = 70
    time_penalty: int = 10
    day_penalty: int = 5

    preparation_penalty: int = 10
    load_balance_penalty: int = 10
    daily_load_penalty: int = 10

    max_preparations: int = 3

    # KEEP current model behavior for now.
    # We will redesign this around admin/research
    # adjusted faculty load later.
    target_teaching_load: int = 12

    load_tolerance: int = 3

    max_daily_teaching_minutes: int = 360
    daily_load_step_minutes: int = 60

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):

        defaults = cls()

        return cls(
            subject_penalty=int(
                data.get(
                    "subject_penalty",
                    defaults.subject_penalty
                )
            ),

            time_penalty=int(
                data.get(
                    "time_penalty",
                    defaults.time_penalty
                )
            ),

            day_penalty=int(
                data.get(
                    "day_penalty",
                    defaults.day_penalty
                )
            ),

            preparation_penalty=int(
                data.get(
                    "preparation_penalty",
                    defaults.preparation_penalty
                )
            ),

            load_balance_penalty=int(
                data.get(
                    "load_balance_penalty",
                    defaults.load_balance_penalty
                )
            ),

            daily_load_penalty=int(
                data.get(
                    "daily_load_penalty",
                    defaults.daily_load_penalty
                )
            ),

            max_preparations=int(
                data.get(
                    "max_preparations",
                    defaults.max_preparations
                )
            ),

            target_teaching_load=int(
                data.get(
                    "target_teaching_load",
                    defaults.target_teaching_load
                )
            ),

            load_tolerance=int(
                data.get(
                    "load_tolerance",
                    defaults.load_tolerance
                )
            ),

            max_daily_teaching_minutes=int(
                data.get(
                    "max_daily_teaching_minutes",
                    defaults.max_daily_teaching_minutes
                )
            ),

            daily_load_step_minutes=int(
                data.get(
                    "daily_load_step_minutes",
                    defaults.daily_load_step_minutes
                )
            ),
        )