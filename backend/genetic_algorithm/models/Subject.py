
class Subject:
    def __init__(self,
                number: str,
                title: str = None,
                credit_units: int = 0,
                lec_hours: int = 0,
                lab_hours: int = 0,
                section: str = None,
                year_level:int = 0):

        
        self.number = number
        self.title = title
        self.scheduled_time_blocks = None
        # A subject may use different rooms for its lecture and laboratory.
        self.assigned_room = None
        self.lecture_room = None
        self.laboratory_room = None
        self.lecture_time_blocks = []
        self.laboratory_time_blocks = []
        self.lecture_room_time_blocks = []
        self.laboratory_room_time_blocks = []
        self.credit_units = credit_units
        self.assigned_faculty = None
        self.lec_hours = lec_hours
        self.lab_hours = lab_hours
        self.section = section
        self.year_level = year_level


    
    def __repr__(self):
        return (
            f"Subject(number={self.number}, "
            f"credit_units={self.credit_units}, "
            f"assigned_room={self.assigned_room}, "
            f"assigned_faculty={self.assigned_faculty}, "
            f"time_blocks={self.scheduled_time_blocks},"
            f"lec_hours={self.lec_hours},"
            f"lab_hours={self.lab_hours},"
            f"section={self.section.code},"
    
        )