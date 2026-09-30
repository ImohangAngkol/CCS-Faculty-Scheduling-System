from dataclasses import dataclass, asdict


@dataclass
class GASetting:

    # ============================================================
    # FACULTY PREFERENCE PENALTIES
    # ============================================================

    subject_penalty: int = 70
    time_penalty: int = 10
    day_penalty: int = 5

    preparation_penalty: int = 10
    load_balance_penalty: int = 10
    daily_load_penalty: int = 10

    gap_penalty: int = 10
    lecture_lab_penalty: int = 5

    max_preparations: int = 3

    # ============================================================
    # FACULTY WORKLOAD MODEL
    # ============================================================

    # Regular faculty teaching-load baseline.
    regular_teaching_load: int = 18

    # Absolute hard ceiling. No generated schedule may exceed this.
    absolute_max_teaching_load: int = 40

    # Above this value, the schedule is considered a heavy overload.
    overload_warning_threshold: int = 30

    # Penalties used by the workload fitness model.
    underload_penalty: int = 25
    overload_penalty: int = 10
    heavy_overload_penalty: int = 25

    # Number of teaching units represented by one workload penalty step.
    workload_step_units: int = 3

    # ============================================================
    # LEGACY COMPATIBILITY
    # ============================================================
    #
    # Keep these temporarily so older code paths do not fail while
    # FitnessFunction.py is being migrated in Workload Phase 4.
    #
    # Phase 4 will stop using target_teaching_load and load_tolerance.
    # ============================================================

    target_teaching_load: int = 12
    load_tolerance: int = 3

    # ============================================================
    # DAILY LOAD
    # ============================================================

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

            gap_penalty=int(
                data.get(
                    "gap_penalty",
                    defaults.gap_penalty
                )
            ),

            lecture_lab_penalty=int(
                data.get(
                    "lecture_lab_penalty",
                    defaults.lecture_lab_penalty
                )
            ),

            max_preparations=int(
                data.get(
                    "max_preparations",
                    defaults.max_preparations
                )
            ),

            regular_teaching_load=int(
                data.get(
                    "regular_teaching_load",
                    defaults.regular_teaching_load
                )
            ),

            absolute_max_teaching_load=int(
                data.get(
                    "absolute_max_teaching_load",
                    defaults.absolute_max_teaching_load
                )
            ),

            overload_warning_threshold=int(
                data.get(
                    "overload_warning_threshold",
                    defaults.overload_warning_threshold
                )
            ),

            underload_penalty=int(
                data.get(
                    "underload_penalty",
                    defaults.underload_penalty
                )
            ),

            overload_penalty=int(
                data.get(
                    "overload_penalty",
                    defaults.overload_penalty
                )
            ),

            heavy_overload_penalty=int(
                data.get(
                    "heavy_overload_penalty",
                    defaults.heavy_overload_penalty
                )
            ),

            workload_step_units=int(
                data.get(
                    "workload_step_units",
                    defaults.workload_step_units
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
