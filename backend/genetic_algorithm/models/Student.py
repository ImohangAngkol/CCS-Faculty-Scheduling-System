from genetic_algorithm.models.TimeBlock import TimeBlock
class Student:
    def __init__(self, name: str):

        self.name = name
        self.time_blocks_monday = []
        self.time_blocks_tuesday = []
        self.time_blocks_wednesday = []
        self.time_blocks_thursday = []
        self.time_blocks_friday = []
        self.time_blocks_saturday = []
        start1 = 7
        end1 = 8
        start2 = 8
        end2 = 8
        for i in range(0,23):
            if i % 2 == 0:
                self.time_blocks_monday.append(TimeBlock(str(start1) + ':30', str(end1) + ':00'))
                self.time_blocks_tuesday.append(TimeBlock(str(start1) + ':30', str(end1) + ':00'))
                self.time_blocks_wednesday.append(TimeBlock(str(start1) + ':30', str(end1) + ':00'))
                self.time_blocks_thursday.append(TimeBlock(str(start1) + ':30', str(end1) + ':00'))
                self.time_blocks_friday.append(TimeBlock(str(start1) + ':30', str(end1) + ':00'))
                self.time_blocks_saturday.append(TimeBlock(str(start1) + ':30', str(end1) + ':00'))
                start1 += 1
                end1 += 1
            else:
                self.time_blocks_monday.append(TimeBlock(str(start2) + ':00', str(end2) + ':30')) 
                self.time_blocks_tuesday.append(TimeBlock(str(start2) + ':00', str(end2) + ':30',))
                self.time_blocks_wednesday.append(TimeBlock(str(start2) + ':00', str(end2) + ':30'))
                self.time_blocks_thursday.append(TimeBlock(str(start2) + ':00', str(end2) + ':30'))
                self.time_blocks_friday.append(TimeBlock(str(start2) + ':00', str(end2) + ':30'))
                self.time_blocks_saturday.append(TimeBlock(str(start2) + ':00', str(end2) + ':30'))
                start2 += 1
                end2 += 1

    def __repr__(self):
        return (
              f"name={self.name}"

        )