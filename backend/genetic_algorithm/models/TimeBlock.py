class TimeBlock:
    def __init__(
        self,
        start_time,
        end_time,
        is_available=True,
        preferred=False,
        room = None
    ):
        self.start_time = start_time
        self.end_time = end_time
        self.is_available = is_available
        self.preferred = preferred
        self.room = room
        self.subject = None
        self.instructor = None
        self.type = None

    def __repr__(self):
        return (
            f"TimeBlock("
            f"{self.start_time}-{self.end_time}, "
            f"available={self.is_available}, "
            f"subject={self.subject}, "

            f"type={self.type}, "
            f"preferred={self.preferred})"
        )

    