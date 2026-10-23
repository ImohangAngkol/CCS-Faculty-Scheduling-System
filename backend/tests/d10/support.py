"""Fictional D10 resources. No production providers or datasets are installed."""
import copy
import pandas as pd

from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.models.Room import Room
from genetic_algorithm.models.Section import Section
from genetic_algorithm.models.Subject import Subject


def templates(compact=False):
    faculty = [Faculty(990001+i, 1, admin_load=22, eligible_subjects={"SYN101", "SYN102"}) for i in range(2)]
    subjects = [Subject("SYN101", "Fictional Systems", 2, 2, 0, Section("SYN-A")),
                Subject("SYN102", "Fictional Design", 2, 2, 0, Section("SYN-B"))]
    rooms = [Room("Fictional Lecture Room", "Lecture")]
    if compact:
        for resource in [*faculty, *rooms, *(s.section for s in subjects)]:
            for index, day in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday")):
                attribute = "time_blocks_" + day
                setattr(resource, attribute, getattr(resource, attribute)[:8] if index < 2 else [])
    return subjects, faculty, rooms


def detached():
    return copy.deepcopy(templates())


def preferences():
    return pd.DataFrame({"Faculty_Code": [990001, 990002], "Faculty_Prio": [1, 1],
                         "Preferred Subjects": [None, None], "Preferred Day(s)": [None, None]})
