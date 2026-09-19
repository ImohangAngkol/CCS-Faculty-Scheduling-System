from genetic_algorithm.models.TimeBlock import TimeBlock


class Section:
    def __init__(self,
                 code: str,
                 students: list = None,
                 year_level: int = 0):

        self.code = code
        self.students = students if students else []
        self.year_level = year_level

        # Section-owned time blocks are used to represent fixed schedules
        # (e.g., GEC/MAT/PED/other subjects already scheduled outside the GA).
        self.time_blocks_monday = []
        self.time_blocks_tuesday = []
        self.time_blocks_wednesday = []
        self.time_blocks_thursday = []
        self.time_blocks_friday = []
        self.time_blocks_saturday = []

        self._create_time_blocks()

    def _create_time_blocks(self):
        """Create 30-minute section blocks from 07:30 through 20:00."""
        day_lists = [
            self.time_blocks_monday,
            self.time_blocks_tuesday,
            self.time_blocks_wednesday,
            self.time_blocks_thursday,
            self.time_blocks_friday,
            self.time_blocks_saturday,
        ]

        current_start = self._time_to_minutes("07:30")
        end_minutes = self._time_to_minutes("22:00")

        while current_start < end_minutes:
            current_end = current_start + 30
            start_text = self._minutes_to_time(current_start)
            end_text = self._minutes_to_time(current_end)

            for blocks in day_lists:
                block = TimeBlock(
                    start_time=start_text,
                    end_time=end_text,
                    is_available=True,
                    preferred=False,
                )
                block.fixed_schedule = False
                block.fixed_course = None
                blocks.append(block)

            current_start = current_end

    @staticmethod
    def _time_to_minutes(time_value):
        hour, minute = map(int, str(time_value).strip().split(":"))
        return hour * 60 + minute

    @staticmethod
    def _minutes_to_time(total_minutes):
        hour = total_minutes // 60
        minute = total_minutes % 60
        return f"{hour:02d}:{minute:02d}"

    def get_day_map(self):
        return {
            "M": self.time_blocks_monday,
            "T": self.time_blocks_tuesday,
            "W": self.time_blocks_wednesday,
            "TH": self.time_blocks_thursday,
            "F": self.time_blocks_friday,
            "S": self.time_blocks_saturday,
        }

    @property
    def num_students(self):
        return len(self.students)

    def add_student(self, student):
        self.students.append(student)

    def __str__(self):
        return f"name={self.code}"
