
from genetic_algorithm.models.TimeBlock import TimeBlock
class Faculty:
    def __init__(
        self,
        code: int,
        seniority_level: int,
        subjects_assigned: list = None,
        preferred_subjects: list = None,
        preferred_time=None,
        preferred_day=None,
        admin_load=0,
        extension_load=0,
        research_load=0,
        max_teaching_load=0
    ):
        self.code = code
        self.seniority_level = seniority_level
        self.current_teaching_load = 0
        self.max_teaching_load = 18
        self.min_teaching_load =  6
        self.max_load = 30
        self.admin_load = admin_load
        self.extension_load = extension_load
        self.research_load = research_load

        self.subjects_assigned = (
            subjects_assigned
            if subjects_assigned is not None
            else []
        )

        self.preferred_subjects = (
            preferred_subjects
            if preferred_subjects is not None
            else []
        )

        self.preferred_time = (
            preferred_time
            if preferred_time is not None
            else []
        )

        self.preferred_day = (
            preferred_day
            if preferred_day is not None
            else []
        )

        self.num_preparations = 0

        self.time_blocks_monday = []
        self.time_blocks_tuesday = []
        self.time_blocks_wednesday = []
        self.time_blocks_thursday = []
        self.time_blocks_friday = []
        self.time_blocks_saturday = []

        self._create_time_blocks()
    @staticmethod
    def _normalize_days(day_value):
        """
        Convert a day value into a list of valid lowercase day names.

        Examples:
            "Tuesday" -> ["tuesday"]
            "Tuesday, Friday" -> ["tuesday", "friday"]
            "Tuesday/Friday" -> ["tuesday", "friday"]
            "Tuesday and Friday" -> ["tuesday", "friday"]
            ["Tuesday", "Friday"] -> ["tuesday", "friday"]
        """

        valid_days = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday"
        }

        if day_value is None:
            return []

        # Handle an existing list, tuple, or set
        if isinstance(day_value, (list, tuple, set)):
            results = []

            for item in day_value:
                results.extend(
                    Faculty._normalize_days(item)
                )

            # Remove duplicates while preserving order
            return list(dict.fromkeys(results))

        day_text = str(day_value).strip().lower()

        # Convert common separators into commas
        replacements = [
            " and ",
            "&",
            "/",
            "\\",
            ";",
            "|"
        ]

        for separator in replacements:
            day_text = day_text.replace(separator, ",")

        day_parts = [
            part.strip()
            for part in day_text.split(",")
            if part.strip()
        ]

        normalized_days = []

        for day in day_parts:
            if day in valid_days:
                normalized_days.append(day)
            else:
                # print(f"Skipped invalid preferred day: {day}")
                pass

        return list(dict.fromkeys(normalized_days))

    def _create_time_blocks(self):
        """
        Create 30-minute time blocks from 07:30 to 19:00.
        """

        day_lists = [
            self.time_blocks_monday,
            self.time_blocks_tuesday,
            self.time_blocks_wednesday,
            self.time_blocks_thursday,
            self.time_blocks_friday,
            self.time_blocks_saturday
        ]

        start_minutes = self._time_to_minutes("07:30")
        end_minutes = self._time_to_minutes("22:00")

        current_start = start_minutes

        while current_start < end_minutes:
            current_end = current_start + 30

            start_text = self._minutes_to_time(current_start)
            end_text = self._minutes_to_time(current_end)

            for blocks in day_lists:
                blocks.append(
                    TimeBlock(
                        start_time=start_text,
                        end_time=end_text,
                        is_available=True,
                        preferred=False
                    )
                )

            current_start = current_end

    @staticmethod
    def _time_to_minutes(time_value):
        """
        Convert HH:MM into total minutes after midnight.

        Examples:
            07:30 -> 450
            14:00 -> 840
        """

        time_value = str(time_value).strip()

        hour, minute = map(int, time_value.split(":"))

        if not 0 <= hour <= 23:
            raise ValueError(
                f"Invalid hour in time: {time_value}"
            )

        if not 0 <= minute <= 59:
            raise ValueError(
                f"Invalid minute in time: {time_value}"
            )

        return hour * 60 + minute

    @staticmethod
    def _minutes_to_time(total_minutes):
        """
        Convert total minutes into HH:MM.
        """

        hour = total_minutes // 60
        minute = total_minutes % 60

        return f"{hour:02d}:{minute:02d}"

    def get_day_map(self):
        """
        Return the time-block list associated with each day.
        """

        return {
            "monday": self.time_blocks_monday,
            "tuesday": self.time_blocks_tuesday,
            "wednesday": self.time_blocks_wednesday,
            "thursday": self.time_blocks_thursday,
            "friday": self.time_blocks_friday,
            "saturday": self.time_blocks_saturday
        }

    def reset_preferred_time_blocks(self):
        """
        Set all faculty time blocks to preferred=False.
        """

        for blocks in self.get_day_map().values():
            for block in blocks:
                block.preferred = False

    def set_preferred_time_blocks(
        self,
        preferred_days=None,
        preferred_times=None,
        day_schedule_pairs=None,
        reset=True
    ):
        """
        Mark matching time blocks as preferred.

        Supports combined day formats such as:

            ("Tuesday, Friday", "09:30-11:30")
            ("Tuesday/Friday", "09:30-11:30")
            ("Tuesday and Friday", "09:30-11:30")

        The same schedule will be applied to every listed day.
        """

        if reset:
            self.reset_preferred_time_blocks()

        day_map = self.get_day_map()

        if day_schedule_pairs is not None:
            pairs = day_schedule_pairs

        else:
            preferred_days = (
                preferred_days
                if preferred_days is not None
                else self.preferred_day
            )

            preferred_times = (
                preferred_times
                if preferred_times is not None
                else self.preferred_time
            )

            if len(preferred_days) != len(preferred_times):
                raise ValueError(
                    "preferred_days and preferred_times must "
                    "have the same number of elements. "
                    f"Received {len(preferred_days)} days and "
                    f"{len(preferred_times)} schedules."
                )

            pairs = zip(
                preferred_days,
                preferred_times
            )

        valid_pairs = []

        for day_value, schedule in pairs:
            if day_value is None or schedule is None:
                continue

            # Convert "Tuesday, Friday" into
            # ["tuesday", "friday"]
            normalized_days = self._normalize_days(
                day_value
            )

            if not normalized_days:
                continue

            schedule = str(schedule).strip()

            try:
                start_text, end_text = [
                    value.strip()
                    for value in schedule.split(
                        "-",
                        maxsplit=1
                    )
                ]

                preferred_start = self._time_to_minutes(
                    start_text
                )

                preferred_end = self._time_to_minutes(
                    end_text
                )

            except (
                ValueError,
                AttributeError,
                TypeError
            ):
                # print(
                #     "Skipped invalid preferred schedule: "
                #     f"{schedule}"
                # )
                continue

            if preferred_end <= preferred_start:
                # print(
                #     f"Skipped invalid time range: {schedule}"
                # )
                continue

            # Apply the same schedule to every normalized day
            for normalized_day in normalized_days:
                valid_pairs.append(
                    (
                        normalized_day,
                        preferred_start,
                        preferred_end
                    )
                )

        for day, preferred_start, preferred_end in valid_pairs:
            for block in day_map[day]:
                block_start = self._time_to_minutes(
                    block.start_time
                )

                block_end = self._time_to_minutes(
                    block.end_time
                )

                if (
                    block_start >= preferred_start
                    and block_end <= preferred_end
                ):
                    block.preferred = True


    def get_preferred_blocks(self):
        """
        Return all preferred blocks grouped by day.
        """

        result = {}

        for day, blocks in self.get_day_map().items():
            preferred_blocks = [
                f"{block.start_time}-{block.end_time}"
                for block in blocks
                if block.preferred
            ]

            if preferred_blocks:
                result[day.capitalize()] = preferred_blocks

        return result

    def display_preferred_blocks(self):
        """
        Print preferred blocks grouped by day.
        """

        preferred_blocks = self.get_preferred_blocks()

        print(f"Faculty code: {self.code}")

        if not preferred_blocks:
            print("No preferred time blocks.")
            return

        for day, schedules in preferred_blocks.items():
            print(f"\n{day}")

            for schedule in schedules:
                print(f"  {schedule}")

    def __repr__(self):
        return (
            f"Faculty("
            f"code={self.code}, "
            f"seniority_level={self.seniority_level}, "
            f"subjects_assigned={self.subjects_assigned}, "
            f"preferred_subjects={self.preferred_subjects}, "
            f"preferred_time={self.preferred_time}, "
            f"preferred_day={self.preferred_day})"
        )
