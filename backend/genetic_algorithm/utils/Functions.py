from pathlib import Path

import pandas as pd

from genetic_algorithm.models.Room import Room
from genetic_algorithm.models.Subject import Subject
from genetic_algorithm.models.TimeBlock import TimeBlock
from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.models.Section import Section
from genetic_algorithm.models.Student import Student


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


df_subjects = pd.read_csv(
    DATA_DIR / "first_sem_bsit_subjects.csv"
)

df_section_schedules = pd.read_csv(
    DATA_DIR / "BSIT_Consolidated_Subject_Schedules.csv"
)

df_preferences = pd.read_csv(
    DATA_DIR / "Faculty Preferences V2.csv"
)

df_faculty_loads = pd.read_csv(
    DATA_DIR / "Faculty Admin, Research and Extension.csv"
)
def _parse_fixed_section_days(day_string):
    """Parse schedule day codes from the consolidated section CSV.

    Examples: MTH -> M, TH; TF -> T, F; TTH -> T, TH; SAT -> S.
    """
    text = str(day_string).strip().upper()
    if text == 'SAT':
        return ['S']

    result = []
    i = 0
    while i < len(text):
        if text[i:i + 2] == 'TH':
            result.append('TH')
            i += 2
        elif text[i] in {'M', 'T', 'W', 'F', 'S'}:
            result.append(text[i])
            i += 1
        else:
            raise ValueError(f"Invalid day code in fixed section schedule: {day_string}")

    # Avoid reserving the same day twice if a source value repeats a code.
    return list(dict.fromkeys(result))


def _parse_12_hour_time_to_minutes(value):
    from datetime import datetime
    parsed = datetime.strptime(str(value).strip().upper(), '%I:%M%p')
    return parsed.hour * 60 + parsed.minute


def apply_fixed_section_schedules(section_list, schedule_df):
    """Mark Section TimeBlocks unavailable using the consolidated schedule CSV.

    Returns a list of rows that could not be applied, instead of silently
    converting malformed or out-of-range schedules.
    """
    section_lookup = {str(section.code).strip().upper(): section for section in section_list}
    skipped = []

    for _, row in schedule_df.iterrows():
        section_code = str(row['Section']).strip().upper()
        course_number = str(row['Course Number']).strip()
        schedule_text = str(row['Schedule']).strip()
        section = section_lookup.get(section_code)

        if section is None:
            skipped.append((section_code, course_number, schedule_text, 'section not found'))
            continue

        try:
            time_range, day_text = schedule_text.rsplit(None, 1)
            start_text, end_text = [x.strip() for x in time_range.split('-', 1)]
            start_min = _parse_12_hour_time_to_minutes(start_text)
            end_min = _parse_12_hour_time_to_minutes(end_text)
            days = _parse_fixed_section_days(day_text)
        except Exception as exc:
            skipped.append((section_code, course_number, schedule_text, str(exc)))
            continue

        if end_min <= start_min:
            skipped.append((
                section_code, course_number, schedule_text,
                'end time is not later than start time; please verify AM/PM'
            ))
            continue

        expected_per_day = (end_min - start_min) // 30
        if (end_min - start_min) % 30 != 0:
            skipped.append((section_code, course_number, schedule_text, 'duration is not a multiple of 30 minutes'))
            continue

        for day_code in days:
            blocks = section.get_day_map().get(day_code, [])
            matching = []
            for block in blocks:
                block_start = Section._time_to_minutes(block.start_time)
                block_end = Section._time_to_minutes(block.end_time)
                if block_start >= start_min and block_end <= end_min:
                    matching.append(block)

            if len(matching) != expected_per_day:
                skipped.append((
                    section_code, course_number, schedule_text,
                    f'only {len(matching)}/{expected_per_day} time blocks exist for {day_code}'
                ))
                continue

            for block in matching:
                block.is_available = False
                block.fixed_schedule = True
                block.fixed_course = course_number
                block.subject = course_number
                block.section = section
                block.day_code = day_code

    return skipped


def set_priority(x):


    if x =='SALA':
        return 1
    elif x == 'IBRAHIM':
        return 2
    elif x =='TINAM-ISAN':
        return 3
    elif x =='NAGA':
        return 4
    elif x =='LUA':
        return 5
    elif x =='BOKINGKITO':
        return 6
    elif x =='LLAMAS':
        return 7
    elif x =='CONOL':
        return 8
    elif x =='RARUGAL':
        return 9
    elif x =='BALAGA':
        return 10
    else:
        return 11
    

# df_preferences = pd.read_csv('Faculty Preferences V2.csv')

# # Faculty administrative, research, extension, and teaching loads
# df_faculty_loads = pd.read_csv('Faculty Admin, Research and Extension.csv')

# Remove accidental index columns such as 'Unnamed: 0'
df_faculty_loads = df_faculty_loads.loc[
    :, ~df_faculty_loads.columns.astype(str).str.startswith('Unnamed')
].copy()

# Normalize faculty names for reliable matching
df_faculty_loads['Faculty'] = (
    df_faculty_loads['Faculty']
    .astype(str)
    .str.strip()
    .str.upper()
)

# Faculty name -> load information
dct_fac_loads = {
    row['Faculty']: {
        'admin_load': int(row['Admin Load']),
        'research_load': int(row['Research Load']),
        'extension_load': int(row['Extension Load']),
        'max_teaching_load': int(row['Teaching Load'])
    }
    for _, row in df_faculty_loads.iterrows()
}
df_preferences['Faculty_Prio'] = df_preferences['Faculty'].apply(lambda x: set_priority(x))


tmp = df_preferences.groupby('Faculty').count().reset_index().reset_index()
dct_fac_code = {}

for i,u in zip(tmp['index'],tmp['Faculty']):
    dct_fac_code[u] = i

# Reverse lookup: faculty code -> normalized faculty name
dct_fac_name = {
    code: str(name).strip().upper()
    for name, code in dct_fac_code.items()
}
# for i,u in zip(tmp['Faculty'],tmp['Faculty']):
#     dct_fac_code[u] = i
def get_code(x):
    return int(dct_fac_code[x])
df_preferences['Faculty_Code'] = df_preferences['Faculty'].apply(lambda x: get_code(x))


rooms_names = ['NETWORK LAB','DATABASE LAB','MULTIMEDIA LAB']
lst_rooms = []
for room in rooms_names:
        room1 = Room(room,'Laboratory')
        lst_rooms.append(room1)


rooms_names = ['ICT 3B','ICT 3A','ICT 3C']

for room in rooms_names:
        room1 = Room(room,'Lecture')
        lst_rooms.append(room1)

dct_fac_days = {}
for fac, sub in zip(df_preferences['Faculty_Code'], df_preferences['Day(s)']):
    if fac in dct_fac_days.keys():

        tmp = dct_fac_days[fac]
        if sub not in tmp:
            tmp.append(sub)
        dct_fac_days[fac] = tmp
       
    else:
        tmp = []
        tmp.append(sub)
        dct_fac_days[fac] = tmp

dct_fac_prio = {}
for fac, pri in zip(df_preferences['Faculty_Code'], df_preferences['Faculty_Prio']):

    dct_fac_prio[fac] = pri

dct_fac_subj = {}
for fac, sub in zip(df_preferences['Faculty_Code'], df_preferences['Subject']):
    if fac in dct_fac_subj.keys():

        tmp = dct_fac_subj[fac]
        if sub not in tmp:
            tmp.append(sub)
        dct_fac_subj[fac] = tmp
       
    else:
        tmp = []
        tmp.append(sub)
        dct_fac_subj[fac] = tmp
dct_fac_sched = {}
for fac, sched in zip(df_preferences['Faculty_Code'], df_preferences['New Schedule']):
    if fac in dct_fac_sched.keys():

        tmp = dct_fac_sched[fac]
        if sched not in tmp:
            tmp.append(sched)
        dct_fac_sched[fac] = tmp
       
    else:
        tmp = []
        tmp.append(sched)
        dct_fac_sched[fac] = tmp
dct_fac_room = {}
for fac, room in zip(df_preferences['Faculty_Code'], df_preferences['Room Assignment']):
    if fac in dct_fac_room.keys():

        tmp = dct_fac_room[fac]
        if room not in tmp:
            tmp.append(room)
        dct_fac_room[fac] = tmp
       
    else:
        tmp = []
        tmp.append(room)
        dct_fac_room[fac] = tmp




dct_fac_preferences = {}

for _, row in df_preferences.iterrows():
    faculty_code = row["Faculty_Code"]
    preferred_day = row["Day(s)"]
    preferred_schedule = row["New Schedule"]

    if (
        pd.isna(faculty_code)
        or pd.isna(preferred_day)
        or pd.isna(preferred_schedule)
    ):
        continue

    faculty_code = int(faculty_code)
    preferred_day = str(preferred_day).strip()
    preferred_schedule = str(
        preferred_schedule
    ).strip()

    pair = (
        preferred_day,
        preferred_schedule
    )

    if faculty_code not in dct_fac_preferences:
        dct_fac_preferences[faculty_code] = []

    # Avoid duplicate day-schedule pairs
    if pair not in dct_fac_preferences[faculty_code]:
        dct_fac_preferences[faculty_code].append(pair)


list_faculty = []

for faculty_code in dct_fac_subj.keys():
    preferences = dct_fac_preferences.get(
        faculty_code,
        []
    )

    preferred_days = [
        day
        for day, schedule in preferences
    ]

    preferred_times = [
        schedule
        for day, schedule in preferences
    ]

    # Get faculty loads from Faculty Admin, Research and Extension.csv
    faculty_name = dct_fac_name.get(faculty_code, '')
    faculty_loads = dct_fac_loads.get(
        faculty_name,
        {
            'admin_load': 0,
            'research_load': 0,
            'extension_load': 0,
            'max_teaching_load': 0
        }
    )

    faculty = Faculty(
        code=faculty_code,
        seniority_level=dct_fac_prio.get(
            faculty_code,
            0
        ),
        subjects_assigned=[],
        preferred_subjects=dct_fac_subj.get(
            faculty_code,
            []
        ),
        preferred_time=preferred_times,
        preferred_day=preferred_days,
        admin_load=faculty_loads['admin_load'],
        extension_load=faculty_loads['extension_load'],
        research_load=faculty_loads['research_load'],
        max_teaching_load=faculty_loads['max_teaching_load']
    )

    faculty.set_preferred_time_blocks(
        day_schedule_pairs=preferences
    )

    list_faculty.append(faculty)


lst_sections = []
for yr_lvl in [1,2,3,4]:
    for sct in ['A','B']:

        lst_students = []
        for stud in range(0,40):
            stud = str(stud)
            student = Student(stud)
            lst_students.append(student)
        section = str(yr_lvl) + sct
        sect = Section(section, lst_students,yr_lvl)
        lst_sections.append(sect)


# Reserve all section time blocks occupied by the consolidated/fixed schedules.
fixed_section_schedule_warnings = apply_fixed_section_schedules(
    lst_sections,
    df_section_schedules
)

if fixed_section_schedule_warnings:
    print('\nWARNING: Some fixed section schedules could not be applied:')
    for warning in fixed_section_schedule_warnings:
        print('  ', warning)


list_subjects = []
for section in lst_sections:
    for i,o,u,p,l,n in zip(df_subjects['course no.'], df_subjects['course title'],df_subjects['units'], df_subjects['num of lec hours/week'],df_subjects['num of lab hours/week'], df_subjects['year_level']):
        # print(section.code)
        if str(section.year_level) == str(n):
            if i in ['ITN101','ITN102','ITN103','ITN111']:
                if str(section.code) == '4B':
                    list_subjects.append(Subject(i,o,u,p,l,section,n))
                elif str(section.code) == '3B':
                    list_subjects.append(Subject(i,o,u,p,l,section,n))
                else:
                    pass
            elif i in ['ITD100','ITD103','ITD104','ITD105']:
                if str(section.code) == '4A':
                    list_subjects.append(Subject(i,o,u,p,l,section,n))
                elif str(section.code) == '3A':
                    list_subjects.append(Subject(i,o,u,p,l,section,n))
                else:
                    pass
            else:
                list_subjects.append(Subject(i,o,u,p,l,section,n))


tmp = []
for i in list_subjects:
    if i.lab_hours not in tmp:
        tmp.append(i.lab_hours)

defined_two_lec_hours = [
('7:30 - 9:30','M'), 
('9:30 - 11:30','M'), 
('11:30 - 13:30','M'), 
('13:30 - 15:30','M'), 
('15:30 - 17:30','M'), 
('17:30 - 19:30','M'), 


('7:30 - 9:30','T'), 
('9:30 - 11:30','T'), 
('11:30 - 13:30','T'), 
('13:30 - 15:30','T'), 
('15:30 - 17:30','T'), 
('17:30 - 19:30','T'), 
 

('7:30 - 9:30','W'), 
('9:30 - 11:30','W'), 
('11:30 - 13:30','W'), 
('13:30 - 15:30','W'), 
('15:30 - 17:30','W'), 
('17:30 - 19:30','W'), 


('7:30 - 9:30','TH'), 
('9:30 - 11:30','TH'), 
('11:30 - 13:30','TH'), 
('13:30 - 15:30','TH'), 
('15:30 - 17:30','TH'), 
('17:30 - 19:30','TH'), 


('7:30 - 9:30','F'), 
('9:30 - 11:30','F'), 
('11:30 - 13:30','F'), 
('13:30 - 15:30','F'), 
('15:30 - 17:30','F'), 
('17:30 - 19:30','F'), 


('7:30 - 9:30','S'), 
('9:30 - 11:30','S'), 
('11:30 - 13:30','S'),
('13:30 - 15:30','S'), 
('15:30 - 17:30','S'), 
('17:30 - 19:30','S'), 

]


defined_three_lec_hours = [
('7:30 - 10:30','M'), 
('10:30 - 13:30','M'), 
('13:30 - 16:30','M'), 
('16:30 - 19:30','M'), 
('16:30 - 19:30','T'), 
('16:30 - 19:30','W'), 
('16:30 - 19:30','TH'), 
('16:30 - 19:30','F'), 
('16:30 - 19:30','S'), 

('7:30 - 10:30','T'), 
('10:30 - 13:30','T'), 
('13:30 - 16:30','T'), 

('7:30 - 10:30','W'), 
('10:30 - 13:30','W'), 
('13:30 - 16:30','W'),  

('7:30 - 10:30','TH'), 
('10:30 - 13:30','TH'), 
('13:30 - 16:30','TH'), 

('7:30 - 10:30','F'), 
('10:30 - 13:30','F'), 
('13:30 - 16:30','F'), 

('7:30 - 10:30','S'), 
('10:30 - 13:30','S'), 
('13:30 - 16:30','S'), 


('7:30 - 9:00','MTH'),
('9:00 - 10:30','MTH'),
('10:30 - 12:00','MTH'),
('12:00 - 13:30','MTH'),
('13:30 - 15:00','MTH'),
('15:00 - 16:30','MTH'),
('16:30 - 18:00','MTH'),
('18:00 - 19:30','MTH'),

('7:30 - 9:00','TF'),
('9:00 - 10:30','TF'),
('10:30 - 12:00','TF'),
('12:00 - 13:30','TF'),
('13:30 - 15:00','TF'),
('15:00 - 16:30','TF'),
('16:30 - 18:00','TF'),
('18:00 - 19:30','TF'),

('7:30 - 9:00','WS'),
('9:00 - 10:30','WS'),
('10:30 - 12:00','WS'),
('12:00 - 13:30','WS'),
('13:30 - 15:00','WS'),
('15:00 - 16:30','WS'),
('16:30 - 18:00','WS'),
('18:00 - 19:30','WS')


    
]


defined_three_lab_hours = [
('7:30 - 10:30','M'), 
('10:30 - 13:30','M'), 
('13:30 - 16:30','M'), 
('16:30 - 19:30','M'), 
('16:30 - 19:30','T'), 
('16:30 - 19:30','W'), 
('16:30 - 19:30','TH'), 
('16:30 - 19:30','F'), 
('16:30 - 19:30','S'), 

('7:30 - 10:30','T'), 
('10:30 - 13:30','T'), 
('13:30 - 16:30','T'), 

('7:30 - 10:30','W'), 
('10:30 - 13:30','W'), 
('13:30 - 16:30','W'),  

('7:30 - 10:30','TH'), 
('10:30 - 13:30','TH'), 
('13:30 - 16:30','TH'), 

('7:30 - 10:30','F'), 
('10:30 - 13:30','F'), 
('13:30 - 16:30','F'), 

('7:30 - 10:30','S'), 
('10:30 - 13:30','S'), 
('13:30 - 16:30','S'), 


('7:30 - 9:00','MTH'),
('9:00 - 10:30','MTH'),
('10:30 - 12:00','MTH'),
('12:00 - 13:30','MTH'),
('13:30 - 15:00','MTH'),
('15:00 - 16:30','MTH'),
('16:30 - 18:00','MTH'),
('18:00 - 19:30','MTH'),

('7:30 - 9:00','TF'),
('9:00 - 10:30','TF'),
('10:30 - 12:00','TF'),
('12:00 - 13:30','TF'),
('13:30 - 15:00','TF'),
('15:00 - 16:30','TF'),
('16:30 - 18:00','TF'),
('18:00 - 19:30','TF'),

('7:30 - 9:00','WS'),
('9:00 - 10:30','WS'),
('10:30 - 12:00','WS'),
('12:00 - 13:30','WS'),
('13:30 - 15:00','WS'),
('15:00 - 16:30','WS'),
('16:30 - 18:00','WS'),
('18:00 - 19:30','WS')

    
]

import random
from datetime import datetime


def parse_day_codes(day_string):
    """Convert M, TH, MTH, TF, WS, etc. into individual day codes."""
    day_string = day_string.strip().upper()
    if day_string == "SAT":
        return ["S"]
    parsed_days = []
    index = 0

    while index < len(day_string):
        if day_string[index:index + 2] == "TH":
            parsed_days.append("TH")
            index += 2
        elif day_string[index] in ["M", "T", "W", "F", "S"]:
            parsed_days.append(day_string[index])
            index += 1
        else:
            raise ValueError(
                f"Invalid day code '{day_string}' at position {index}"
            )
    return parsed_days


def convert_time_to_minutes(time_string):
    """Convert HH:MM into minutes after midnight."""
    parsed_time = datetime.strptime(time_string.strip(), "%H:%M")
    return (parsed_time.hour * 60) + parsed_time.minute


def get_faculty_day_blocks(faculty):
    return {
        "M": faculty.time_blocks_monday,
        "T": faculty.time_blocks_tuesday,
        "W": faculty.time_blocks_wednesday,
        "TH": faculty.time_blocks_thursday,
        "F": faculty.time_blocks_friday,
        "S": faculty.time_blocks_saturday,
    }


def get_room_day_blocks(room):
    """Return a room's time-block lists using the same day codes."""
    return {
        "M": room.time_blocks_monday,
        "T": room.time_blocks_tuesday,
        "W": room.time_blocks_wednesday,
        "TH": room.time_blocks_thursday,
        "F": room.time_blocks_friday,
        "S": room.time_blocks_saturday,
    }


def get_section_day_blocks(section):
    """Return a section's TimeBlock lists using the standard day codes."""
    if hasattr(section, "get_day_map"):
        return section.get_day_map()
    return {}


def _get_matching_blocks(day_blocks, day_string, time_range):
    """Generic helper used by faculty and room availability checks."""
    selected_days = parse_day_codes(day_string)
    start_text, end_text = [v.strip() for v in time_range.split("-")]
    selected_start = convert_time_to_minutes(start_text)
    selected_end = convert_time_to_minutes(end_text)

    matching_blocks = []
    for day_code in selected_days:
        if day_code not in day_blocks:
            return []
        for block in day_blocks[day_code]:
            block_start = convert_time_to_minutes(block.start_time)
            block_end = convert_time_to_minutes(block.end_time)
            if block_start >= selected_start and block_end <= selected_end:
                matching_blocks.append((day_code, block))
    return matching_blocks


def _expected_block_count(day_string, time_range):
    selected_days = parse_day_codes(day_string)
    start_text, end_text = [v.strip() for v in time_range.split("-")]
    duration = (
        convert_time_to_minutes(end_text)
        - convert_time_to_minutes(start_text)
    )
    if duration <= 0 or duration % 30 != 0:
        return 0
    return (duration // 30) * len(selected_days)


def get_matching_timeblocks(faculty, day_string, time_range):
    return _get_matching_blocks(
        get_faculty_day_blocks(faculty), day_string, time_range
    )


def get_matching_room_timeblocks(room, day_string, time_range):
    return _get_matching_blocks(
        get_room_day_blocks(room), day_string, time_range
    )


def get_matching_section_timeblocks(section, day_string, time_range):
    return _get_matching_blocks(
        get_section_day_blocks(section), day_string, time_range
    )


def schedule_is_available(faculty, day_string, time_range):
    matching_blocks = get_matching_timeblocks(
        faculty, day_string, time_range
    )
    expected = _expected_block_count(day_string, time_range)
    return (
        expected > 0
        and len(matching_blocks) == expected
        and all(block.is_available for _, block in matching_blocks)
    )


def room_schedule_is_available(room, day_string, time_range):
    """True only if every 30-minute room block is still unused."""
    matching_blocks = get_matching_room_timeblocks(
        room, day_string, time_range
    )
    expected = _expected_block_count(day_string, time_range)
    return (
        expected > 0
        and len(matching_blocks) == expected
        and all(block.is_available for _, block in matching_blocks)
    )


def get_available_rooms(schedule_type, day_string, time_range, room_list=None):
    """
    Return rooms of the required type that are free for the complete schedule.

    Lecture    -> ICT 3B, ICT 3A, ICT 3C
    Laboratory -> NETWORK LAB, DATABASE LAB, MULTIMEDIA LAB
    """
    if room_list is None:
        room_list = lst_rooms

    candidates = [
        room for room in room_list
        if str(room.type).strip().lower() == schedule_type.strip().lower()
        and room_schedule_is_available(room, day_string, time_range)
    ]
    random.shuffle(candidates)
    return candidates


def reserve_room(room, faculty, subject, day_string, time_range, schedule_type):
    """Reserve every room block covered by one class component."""
    matching_blocks = get_matching_room_timeblocks(
        room, day_string, time_range
    )
    expected = _expected_block_count(day_string, time_range)

    if (
        len(matching_blocks) != expected
        or not all(block.is_available for _, block in matching_blocks)
    ):
        return None

    for day_code, block in matching_blocks:
        block.is_available = False
        block.subject = subject
        block.instructor = faculty
        block.faculty = faculty
        block.section = subject.section
        block.type = schedule_type
        block.day_code = day_code
        block.room = room.name

    return matching_blocks


def release_room_blocks(room_blocks):
    for _, block in room_blocks:
        block.is_available = True
        block.subject = None
        block.instructor = None
        block.faculty = None
        block.section = None
        block.type = None
        block.day_code = None
        # Keep the room identity on Room-owned TimeBlocks.


def section_schedule_is_available(subject, day_string, time_range, list_subjects=None):
    """Return True only when the subject's section is free for the whole slot.

    This prevents different subjects belonging to the same section from
    overlapping, even when they use different faculty members and rooms.
    """
    if list_subjects is None:
        list_subjects = globals().get("list_subjects", globals().get("lst_subjects", []))

    # First honor fixed section schedules loaded from the consolidated CSV.
    this_section = getattr(subject, "section", None)
    if this_section is None:
        return False

    fixed_blocks = get_matching_section_timeblocks(
        this_section, day_string, time_range
    )
    expected_fixed_blocks = _expected_block_count(day_string, time_range)

    if (
        expected_fixed_blocks <= 0
        or len(fixed_blocks) != expected_fixed_blocks
        or not all(block.is_available for _, block in fixed_blocks)
    ):
        return False

    requested_days = set(parse_day_codes(day_string))
    start_text, end_text = [v.strip() for v in time_range.split("-")]
    requested_start = convert_time_to_minutes(start_text)
    requested_end = convert_time_to_minutes(end_text)

    if requested_end <= requested_start:
        return False

    for other_subject in list_subjects:
        if other_subject is subject:
            continue

        other_section = getattr(other_subject, "section", None)
        this_section = getattr(subject, "section", None)
        if other_section is None or this_section is None:
            continue
        if other_section.code != this_section.code:
            continue

        existing_blocks = (
            getattr(other_subject, "lecture_time_blocks", [])
            + getattr(other_subject, "laboratory_time_blocks", [])
        )

        for day_code, block in existing_blocks:
            if day_code not in requested_days:
                continue

            existing_start = convert_time_to_minutes(block.start_time)
            existing_end = convert_time_to_minutes(block.end_time)

            # Half-open interval overlap: [start, end). Adjacent classes are OK.
            if requested_start < existing_end and requested_end > existing_start:
                return False

    return True


def validate_fixed_section_conflicts(list_subjects, raise_error=True):
    """Validate GA subjects against section-owned fixed schedules.

    Fixed schedules loaded from BSIT_Consolidated_Subject_Schedules.csv are
    represented by section TimeBlocks with ``fixed_schedule=True``.  This
    check provides a final safety net in addition to the availability check
    performed before every assignment.  It therefore protects fixed GEC,
    MAT/MATH, ENT, PED, FRE, ISY, and any other consolidated schedules.
    """
    conflicts = []

    for subject in list_subjects:
        section = getattr(subject, "section", None)
        if section is None:
            continue

        section_day_map = get_section_day_blocks(section)
        scheduled_blocks = (
            getattr(subject, "lecture_time_blocks", [])
            + getattr(subject, "laboratory_time_blocks", [])
        )

        for item in scheduled_blocks:
            if isinstance(item, tuple) and len(item) == 2:
                day_code, block = item
            else:
                block = item
                day_code = getattr(block, "day_code", getattr(block, "day", None))

            if day_code is None:
                continue

            ga_start = convert_time_to_minutes(block.start_time)
            ga_end = convert_time_to_minutes(block.end_time)

            for fixed_block in section_day_map.get(day_code, []):
                if not getattr(fixed_block, "fixed_schedule", False):
                    continue

                fixed_start = convert_time_to_minutes(fixed_block.start_time)
                fixed_end = convert_time_to_minutes(fixed_block.end_time)

                if ga_start < fixed_end and ga_end > fixed_start:
                    conflicts.append({
                        "section": section.code,
                        "ga_subject": subject.number,
                        "fixed_subject": getattr(fixed_block, "fixed_course", None),
                        "day": day_code,
                        "ga_time": f"{block.start_time}-{block.end_time}",
                        "fixed_time": f"{fixed_block.start_time}-{fixed_block.end_time}",
                    })

    if conflicts and raise_error:
        raise ValueError(
            "Generated schedule conflicts with fixed section schedules: "
            f"{conflicts}"
        )

    return len(conflicts) == 0


def assign_schedule_to_faculty(
    faculty,
    subject,
    selected_schedule,
    schedule_type,
    room_list=None,
    list_subjects=None
):
    """
    Atomically assign BOTH faculty time and a compatible room.

    A class is accepted only when:
      * the faculty is free for every required block;
      * a room of the correct type is free for every required block;
      * the subject's section is free for every required block;
      * the faculty remains within max_teaching_load.

    This prevents faculty, room, and same-section schedule conflicts.
    """
    time_range, day_string = selected_schedule

    # A section cannot attend two overlapping subjects, regardless of faculty/room.
    if not section_schedule_is_available(
        subject=subject,
        day_string=day_string,
        time_range=time_range,
        list_subjects=list_subjects
    ):
        return False

    if subject.assigned_faculty is not None and subject.assigned_faculty is not faculty:
        return False

    if schedule_type == "Lecture" and subject.lecture_time_blocks:
        return False
    if schedule_type == "Laboratory" and subject.laboratory_time_blocks:
        return False

    is_new_subject_assignment = subject.assigned_faculty is None
    if is_new_subject_assignment:
        projected_load = faculty.current_teaching_load + subject.credit_units
        if projected_load > faculty.max_teaching_load:
            return False

    if not schedule_is_available(faculty, day_string, time_range):
        return False

    # Find a room BEFORE changing the faculty schedule.
    available_rooms = get_available_rooms(
        schedule_type, day_string, time_range, room_list
    )
    if not available_rooms:
        return False

    faculty_blocks = get_matching_timeblocks(
        faculty, day_string, time_range
    )

    # Try available rooms; reservation is atomic at this point.
    selected_room = None
    room_blocks = None
    for room in available_rooms:
        reserved = reserve_room(
            room, faculty, subject, day_string, time_range, schedule_type
        )
        if reserved is not None:
            selected_room = room
            room_blocks = reserved
            break

    if selected_room is None:
        return False

    # Room is reserved, so now reserve faculty blocks.
    for day_code, block in faculty_blocks:
        block.is_available = False
        block.section = subject.section
        block.subject = subject
        block.faculty = faculty
        block.instructor = faculty
        block.day_code = day_code
        block.type = schedule_type
        block.room = selected_room.name

    if is_new_subject_assignment:
        faculty.current_teaching_load += subject.credit_units
        faculty.subjects_assigned.append(subject)
        subject.assigned_faculty = faculty

    if schedule_type == "Lecture":
        subject.lecture_time_blocks = faculty_blocks
        subject.lecture_room_time_blocks = room_blocks
        subject.lecture_room = selected_room
    else:
        subject.laboratory_time_blocks = faculty_blocks
        subject.laboratory_room_time_blocks = room_blocks
        subject.laboratory_room = selected_room

    # Preserve a convenient combined room representation.
    subject.assigned_room = {
        "Lecture": getattr(subject.lecture_room, "name", None),
        "Laboratory": getattr(subject.laboratory_room, "name", None),
    }
    subject.scheduled_time_blocks = (
        subject.lecture_time_blocks + subject.laboratory_time_blocks
    )
    return True


def _assign_random_component(
    subject,
    faculty,
    schedules,
    schedule_type,
    maximum_attempts=100,
    room_list=None
):
    if not schedules:
        return False

    available_schedules = schedules.copy()
    random.shuffle(available_schedules)

    for selected_schedule in available_schedules[:maximum_attempts]:
        if assign_schedule_to_faculty(
            faculty=faculty,
            subject=subject,
            selected_schedule=selected_schedule,
            schedule_type=schedule_type,
            room_list=room_list
        ):
            time_range, day_string = selected_schedule
            room = (
                subject.lecture_room
                if schedule_type == "Lecture"
                else subject.laboratory_room
            )
            print(
                f"Assigned {subject.number}-{subject.section.code}: "
                f"{schedule_type}, {day_string} {time_range}, "
                f"Room={room.name}, Faculty={faculty.code}"
            )
            return True
    return False


def assign_random_three_hour_schedule(
    subject, faculty, defined_three_lec_hours,
    maximum_attempts=100, room_list=None
):
    if subject.lec_hours != 3:
        return False
    return _assign_random_component(
        subject, faculty, defined_three_lec_hours,
        "Lecture", maximum_attempts, room_list
    )


def assign_random_two_hour_schedule(
    subject, faculty, defined_two_lec_hours,
    maximum_attempts=100, room_list=None
):
    """Assign a lecture that is exactly 2 hours per scheduled day.

    The extra duration validation prevents an accidentally malformed entry in
    ``defined_two_lec_hours`` (for example 16:30-17:30) from ever being used
    for a subject whose lecture requirement is two hours.
    """
    if subject.lec_hours != 2:
        return False

    valid_two_hour_schedules = []
    for time_range, day_string in defined_two_lec_hours:
        start_text, end_text = [v.strip() for v in time_range.split("-")]
        duration_minutes = (
            convert_time_to_minutes(end_text)
            - convert_time_to_minutes(start_text)
        )
        if duration_minutes == 120:
            valid_two_hour_schedules.append((time_range, day_string))

    return _assign_random_component(
        subject, faculty, valid_two_hour_schedules,
        "Lecture", maximum_attempts, room_list
    )


def assign_random_three_hour_lab_schedule(
    subject, faculty, defined_three_lab_hours,
    maximum_attempts=100, room_list=None
):
    if subject.lab_hours != 3:
        return False
    return _assign_random_component(
        subject, faculty, defined_three_lab_hours,
        "Laboratory", maximum_attempts, room_list
    )


import random

MAX_RESTARTS = 2000


def reset_room_schedules(room_list):
    """Clear all room reservations while keeping each room's identity."""
    for room in room_list:
        for blocks in get_room_day_blocks(room).values():
            for block in blocks:
                block.is_available = True
                block.subject = None
                block.instructor = None
                block.faculty = None
                block.section = None
                block.day_code = None
                block.type = None
                block.room = room.name


def reset_complete_schedule(list_faculty, list_subjects, room_list=None):
    """Clear faculty, subject, and room assignments for a clean restart."""
    if room_list is None:
        room_list = lst_rooms

    for faculty in list_faculty:
        faculty.current_teaching_load = 0
        faculty.subjects_assigned.clear()

        for blocks in get_faculty_day_blocks(faculty).values():
            for block in blocks:
                block.is_available = True
                block.section = None
                block.subject = None
                block.faculty = None
                block.instructor = None
                block.day_code = None
                block.type = None
                block.room = None

    reset_room_schedules(room_list)

    for subject in list_subjects:
        subject.assigned_faculty = None
        subject.scheduled_time_blocks = None
        subject.assigned_room = None
        subject.lecture_room = None
        subject.laboratory_room = None
        subject.lecture_time_blocks = []
        subject.laboratory_time_blocks = []
        subject.lecture_room_time_blocks = []
        subject.laboratory_room_time_blocks = []


def rollback_subject_assignment(subject):
    """Undo partial faculty AND room reservations for one subject."""
    faculty = subject.assigned_faculty

    for _, block in (
        getattr(subject, "lecture_time_blocks", [])
        + getattr(subject, "laboratory_time_blocks", [])
    ):
        block.is_available = True
        block.section = None
        block.subject = None
        block.faculty = None
        block.instructor = None
        block.day_code = None
        block.type = None
        block.room = None

    release_room_blocks(
        getattr(subject, "lecture_room_time_blocks", [])
    )
    release_room_blocks(
        getattr(subject, "laboratory_room_time_blocks", [])
    )

    if faculty is not None:
        faculty.current_teaching_load -= subject.credit_units
        faculty.current_teaching_load = max(0, faculty.current_teaching_load)
        if subject in faculty.subjects_assigned:
            faculty.subjects_assigned.remove(subject)

    subject.assigned_faculty = None
    subject.scheduled_time_blocks = None
    subject.assigned_room = None
    subject.lecture_room = None
    subject.laboratory_room = None
    subject.lecture_time_blocks = []
    subject.laboratory_time_blocks = []
    subject.lecture_room_time_blocks = []
    subject.laboratory_room_time_blocks = []


def faculty_subject_preference_score(faculty, subject):
    subject_number = str(subject.number).strip().lower()
    preferred = {
        str(item).strip().lower()
        for item in faculty.preferred_subjects
    }
    return int(subject_number in preferred)


def get_ranked_faculty_candidates(subject, list_faculty):
    """Prioritize faculty members who have not yet reached minimum load."""
    candidates = [
        faculty
        for faculty in list_faculty
        if faculty.current_teaching_load + subject.credit_units
        <= faculty.max_teaching_load
    ]

    random.shuffle(candidates)
    candidates.sort(
        key=lambda faculty: (
            faculty.current_teaching_load < faculty.min_teaching_load,
            max(0, faculty.min_teaching_load - faculty.current_teaching_load),
            faculty_subject_preference_score(faculty, subject),
            -faculty.current_teaching_load,
            faculty.seniority_level,
        ),
        reverse=True
    )
    return candidates


def try_assign_complete_subject(subject, faculty, room_list=None):
    """Assign all lecture/lab components, including conflict-free rooms."""
    lecture_assigned = subject.lec_hours == 0
    laboratory_assigned = subject.lab_hours == 0

    if subject.lec_hours == 2:
        lecture_assigned = assign_random_two_hour_schedule(
            subject, faculty, defined_two_lec_hours,
            room_list=room_list
        )
    elif subject.lec_hours == 3:
        lecture_assigned = assign_random_three_hour_schedule(
            subject, faculty, defined_three_lec_hours,
            room_list=room_list
        )

    if not lecture_assigned:
        rollback_subject_assignment(subject)
        return False

    if subject.lab_hours == 3:
        laboratory_assigned = assign_random_three_hour_lab_schedule(
            subject, faculty, defined_three_lab_hours,
            room_list=room_list
        )

    if not laboratory_assigned:
        rollback_subject_assignment(subject)
        return False

    return True


def validate_minimum_teaching_load(list_faculty, raise_error=True):
    violations = []
    for faculty in list_faculty:
        if not (
            faculty.min_teaching_load
            <= faculty.current_teaching_load
            <= faculty.max_teaching_load
        ):
            violations.append((
                faculty.code,
                faculty.current_teaching_load,
                faculty.min_teaching_load,
                faculty.max_teaching_load,
            ))

    if violations and raise_error:
        details = ", ".join(
            f"Faculty {code}: {load} units (required {minimum}-{maximum})"
            for code, load, minimum, maximum in violations
        )
        raise RuntimeError(
            "Teaching-load constraint was not satisfied. " + details
        )
    return not violations


def validate_room_conflicts(room_list, raise_error=True):
    """
    Validate room ownership block-by-block.

    Because each Room has one availability calendar, a block can hold only one
    subject. This additional validator catches corrupted/manual assignments.
    """
    problems = []
    for room in room_list:
        for day_code, blocks in get_room_day_blocks(room).items():
            for block in blocks:
                if not block.is_available and block.subject is None:
                    problems.append(
                        f"{room.name} {day_code} {block.start_time}-{block.end_time}: "
                        "reserved without a subject"
                    )

    if problems and raise_error:
        raise RuntimeError("Invalid room schedule: " + "; ".join(problems))
    return not problems


def validate_section_conflicts(list_subjects, raise_error=True):
    """Validate that subjects in the same section never overlap."""
    problems = []
    by_section = {}

    for subject in list_subjects:
        section = getattr(subject, "section", None)
        if section is None:
            continue
        by_section.setdefault(section.code, []).append(subject)

    for section_code, subjects in by_section.items():
        occupied = {}
        for subject in subjects:
            blocks = (
                getattr(subject, "lecture_time_blocks", [])
                + getattr(subject, "laboratory_time_blocks", [])
            )
            for day_code, block in blocks:
                key = (day_code, block.start_time, block.end_time)
                previous = occupied.get(key)
                if previous is not None and previous is not subject:
                    problems.append(
                        f"Section {section_code} {day_code} "
                        f"{block.start_time}-{block.end_time}: "
                        f"{getattr(previous, 'number', previous)} conflicts with "
                        f"{getattr(subject, 'number', subject)}"
                    )
                else:
                    occupied[key] = subject

    if problems and raise_error:
        raise RuntimeError("Section schedule conflict(s): " + "; ".join(problems))
    return not problems


def check_minimum_load_feasibility(list_faculty, list_subjects):
    total_available_units = sum(subject.credit_units for subject in list_subjects)
    total_minimum_units = sum(f.min_teaching_load for f in list_faculty)
    total_maximum_units = sum(f.max_teaching_load for f in list_faculty)

    if total_available_units < total_minimum_units:
        raise ValueError(
            f"Impossible minimum-load requirement: only {total_available_units} "
            f"subject units are available, but {total_minimum_units} are required."
        )
    if total_available_units > total_maximum_units:
        raise ValueError(
            f"Impossible maximum-load requirement: {total_available_units} units "
            f"must be assigned, but faculty can carry only {total_maximum_units}."
        )


def print_final_schedule(list_faculty):
    """Compact final report including lecture/lab room assignments."""
    print("\nFINAL FACULTY TEACHING LOADS AND ROOMS")
    for faculty in sorted(list_faculty, key=lambda item: str(item.code)):
        print(
            f"\nFaculty {faculty.code}: {faculty.current_teaching_load} units "
            f"(minimum={faculty.min_teaching_load}, maximum={faculty.max_teaching_load})"
        )
        for subject in faculty.subjects_assigned:
            lec_room = getattr(getattr(subject, "lecture_room", None), "name", "-")
            lab_room = getattr(getattr(subject, "laboratory_room", None), "name", "-")
            print(
                f"  {subject.number}-{subject.section.code}: "
                f"Lecture Room={lec_room}, Lab Room={lab_room}"
            )


def create_schedule_with_minimum_load(
    list_faculty,
    list_subjects,
    room_list=None,
    max_restarts=MAX_RESTARTS
):
    """
    Build a complete schedule satisfying faculty-load, room, AND section constraints.

    Room rules:
      * Lecture -> ICT 3B, ICT 3A, ICT 3C
      * Laboratory -> NETWORK LAB, DATABASE LAB, MULTIMEDIA LAB
      * A room cannot be assigned to overlapping subjects.
    """
    if room_list is None:
        room_list = lst_rooms

    check_minimum_load_feasibility(list_faculty, list_subjects)

    for restart in range(1, max_restarts + 1):
        reset_complete_schedule(list_faculty, list_subjects, room_list)

        subjects = list_subjects.copy()
        random.shuffle(subjects)
        subjects.sort(
            key=lambda subject: (subject.credit_units, subject.lab_hours),
            reverse=True
        )

        complete = True
        for subject in subjects:
            assigned = False
            for faculty in get_ranked_faculty_candidates(subject, list_faculty):
                if try_assign_complete_subject(subject, faculty, room_list):
                    assigned = True
                    break
            if not assigned:
                complete = False
                break

        if (
            complete
            and validate_minimum_teaching_load(list_faculty, raise_error=False)
            and validate_room_conflicts(room_list, raise_error=False)
            and validate_section_conflicts(list_subjects, raise_error=False)
            and validate_fixed_section_conflicts(list_subjects, raise_error=False)
        ):
            print(f"Valid conflict-free schedule found after {restart} restart(s).")
            print_final_schedule(list_faculty)
            return True

    reset_complete_schedule(list_faculty, list_subjects, room_list)
    raise RuntimeError(
        f"No valid schedule satisfying faculty-load, room, and section constraints was "
        f"found after {max_restarts} full restarts. Consider increasing "
        f"max_restarts or adding room/time capacity."
    )


# Run the scheduler with faculty, room, and same-section conflict checking.
# create_schedule_with_minimum_load(
#     list_faculty=list_faculty,
#     list_subjects=list_subjects,
#     room_list=lst_rooms,
#     max_restarts=2000
# )
import matplotlib.pyplot as plt
import matplotlib.patches as patches


DAY_ORDER = ["M", "T", "W", "TH", "F", "S"]

DAY_NAMES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "TH": "Thursday",
    "F": "Friday",
    "S": "Saturday",
}


def time_to_decimal(time_string):
    """
    Convert HH:MM to decimal hour.

    Example:
        09:30 -> 9.5
        13:00 -> 13.0
    """
    hour, minute = map(int, str(time_string).split(":"))
    return hour + minute / 60




def get_fixed_section_schedule_entries(section):
    """
    Get fixed/non-GA schedules stored inside a Section.

    Consecutive 30-minute blocks belonging to the same fixed course
    are combined into one schedule entry.
    """
    if section is None:
        return []

    entries = []

    for day_code, blocks in section.get_day_map().items():
        fixed_blocks = [
            block
            for block in blocks
            if getattr(block, "fixed_schedule", False)
            and getattr(block, "fixed_course", None) is not None
        ]

        if not fixed_blocks:
            continue

        courses = {}
        for block in fixed_blocks:
            course = str(getattr(block, "fixed_course", "Fixed Course"))
            courses.setdefault(course, []).append(block)

        for course, course_blocks in courses.items():
            course_blocks = sorted(
                course_blocks,
                key=lambda block: time_to_decimal(block.start_time)
            )

            current_start = course_blocks[0].start_time
            current_end = course_blocks[0].end_time

            for block in course_blocks[1:]:
                if block.start_time == current_end:
                    current_end = block.end_time
                else:
                    entries.append({
                        "day": day_code,
                        "start": current_start,
                        "end": current_end,
                        "subject": course,
                        "title": "",
                        "type": "Fixed",
                        "room": "-",
                        "faculty": "-",
                        "section": str(section.code),
                    })
                    current_start = block.start_time
                    current_end = block.end_time

            entries.append({
                "day": day_code,
                "start": current_start,
                "end": current_end,
                "subject": course,
                "title": "",
                "type": "Fixed",
                "room": "-",
                "faculty": "-",
                "section": str(section.code),
            })

    return entries

def collect_schedule_entries(
    view_type,
    target,
    list_subjects,
):
    """
    Collect schedule entries for:

        view_type = "section"
        view_type = "faculty"
        view_type = "room"

    target examples:

        "BSIT-1A"
        faculty object
        faculty.code
        "ICT 3A"
        room object
    """

    view_type = view_type.lower().strip()

    if view_type not in {
        "section",
        "faculty",
        "room"
    }:
        raise ValueError(
            "view_type must be either "
            "'section', 'faculty', or 'room'."
        )

    # -----------------------------------------------------
    # Convert target object into a comparable value
    # -----------------------------------------------------

    if view_type == "section":

        if hasattr(target, "code"):
            target_value = str(target.code)
        else:
            target_value = str(target)

    elif view_type == "faculty":

        if hasattr(target, "code"):
            target_value = str(target.code)
        else:
            target_value = str(target)

    else:

        if hasattr(target, "name"):
            target_value = str(target.name)
        else:
            target_value = str(target)

    entries = []

    # -----------------------------------------------------
    # Examine every scheduled subject
    # -----------------------------------------------------

    for subject in list_subjects:

        section = getattr(
            subject,
            "section",
            None
        )

        faculty = getattr(
            subject,
            "assigned_faculty",
            None
        )

        section_code = (
            str(section.code)
            if section is not None
            else None
        )

        faculty_code = (
            str(faculty.code)
            if faculty is not None
            else None
        )

        # =================================================
        # LECTURE
        # =================================================

        lecture_room = getattr(
            subject,
            "lecture_room",
            None
        )

        lecture_room_name = (
            str(lecture_room.name)
            if lecture_room is not None
            else None
        )

        include_lecture = False

        if view_type == "section":
            include_lecture = (
                section_code == target_value
            )

        elif view_type == "faculty":
            include_lecture = (
                faculty_code == target_value
            )

        elif view_type == "room":
            include_lecture = (
                lecture_room_name == target_value
            )

        if include_lecture:

            lecture_blocks = getattr(
                subject,
                "lecture_time_blocks",
                []
            )

            entries.extend(
                collapse_subject_blocks(
                    subject=subject,
                    blocks=lecture_blocks,
                    schedule_type="Lecture",
                    room_name=lecture_room_name,
                    faculty_code=faculty_code,
                    section_code=section_code,
                )
            )

        # =================================================
        # LABORATORY
        # =================================================

        laboratory_room = getattr(
            subject,
            "laboratory_room",
            None
        )

        laboratory_room_name = (
            str(laboratory_room.name)
            if laboratory_room is not None
            else None
        )

        include_lab = False

        if view_type == "section":
            include_lab = (
                section_code == target_value
            )

        elif view_type == "faculty":
            include_lab = (
                faculty_code == target_value
            )

        elif view_type == "room":
            include_lab = (
                laboratory_room_name == target_value
            )

        if include_lab:

            laboratory_blocks = getattr(
                subject,
                "laboratory_time_blocks",
                []
            )

            entries.extend(
                collapse_subject_blocks(
                    subject=subject,
                    blocks=laboratory_blocks,
                    schedule_type="Laboratory",
                    room_name=laboratory_room_name,
                    faculty_code=faculty_code,
                    section_code=section_code,
                )
            )

    # Include fixed/non-GA courses only in the section view.
    # These schedules are stored in Section TimeBlocks and are not
    # added to the chromosome itself.
    if view_type == "section":
        target_section = None

        for subject in list_subjects:
            section = getattr(subject, "section", None)
            if section is not None and str(section.code) == str(target_value):
                target_section = section
                break

        if target_section is None and hasattr(target, "get_day_map"):
            target_section = target

        if target_section is not None:
            entries.extend(
                get_fixed_section_schedule_entries(target_section)
            )

    return entries


def collapse_subject_blocks(
    subject,
    blocks,
    schedule_type,
    room_name,
    faculty_code,
    section_code,
):
    """
    Combine consecutive 30-minute TimeBlocks into one
    continuous class period.

    Example:

        09:30-10:00
        10:00-10:30
        10:30-11:00
        11:00-11:30

    becomes:

        09:30-11:30
    """

    if not blocks:
        return []

    grouped_by_day = {}

    for day_code, block in blocks:

        grouped_by_day.setdefault(
            day_code,
            []
        ).append(block)

    entries = []

    for day_code, day_blocks in grouped_by_day.items():

        day_blocks = sorted(
            day_blocks,
            key=lambda b: time_to_decimal(
                b.start_time
            )
        )

        current_start = day_blocks[0].start_time
        current_end = day_blocks[0].end_time

        for block in day_blocks[1:]:

            if block.start_time == current_end:

                # Consecutive block
                current_end = block.end_time

            else:

                entries.append(
                    create_schedule_entry(
                        subject,
                        day_code,
                        current_start,
                        current_end,
                        schedule_type,
                        room_name,
                        faculty_code,
                        section_code,
                    )
                )

                current_start = block.start_time
                current_end = block.end_time

        # Final block
        entries.append(
            create_schedule_entry(
                subject,
                day_code,
                current_start,
                current_end,
                schedule_type,
                room_name,
                faculty_code,
                section_code,
            )
        )

    return entries


def create_schedule_entry(
    subject,
    day_code,
    start_time,
    end_time,
    schedule_type,
    room_name,
    faculty_code,
    section_code,
):

    return {
        "day": day_code,

        "start": start_time,

        "end": end_time,

        "subject": str(
            getattr(
                subject,
                "number",
                "Unknown"
            )
        ),

        "title": str(
            getattr(
                subject,
                "title",
                ""
            )
            or ""
        ),

        "type": schedule_type,

        "room": (
            room_name
            if room_name is not None
            else "-"
        ),

        "faculty": (
            faculty_code
            if faculty_code is not None
            else "-"
        ),

        "section": (
            section_code
            if section_code is not None
            else "-"
        ),
    }


def plot_schedule(
    view_type,
    target,
    list_subjects,
    start_hour=7.5,
    end_hour=22,
    figsize=(14, 9),
):
    """
    Plot a weekly timetable.

    Parameters
    ----------
    view_type : str
        "section", "faculty", or "room"

    target :
        Section code / Section object
        Faculty code / Faculty object
        Room name / Room object

    list_subjects :
        Your existing list_subjects

    Example
    -------
    plot_schedule(
        "section",
        "BSIT-1A",
        list_subjects
    )
    """

    entries = collect_schedule_entries(
        view_type=view_type,
        target=target,
        list_subjects=list_subjects,
    )

    if not entries:

        print(
            f"No scheduled classes found for "
            f"{view_type}: {target}"
        )

        return

    # -----------------------------------------------------
    # Determine target name
    # -----------------------------------------------------

    if view_type.lower() == "room":

        target_name = (
            target.name
            if hasattr(target, "name")
            else target
        )

    else:

        target_name = (
            target.code
            if hasattr(target, "code")
            else target
        )

    # -----------------------------------------------------
    # Figure
    # -----------------------------------------------------

    fig, ax = plt.subplots(
        figsize=figsize
    )

    # -----------------------------------------------------
    # Day columns
    # -----------------------------------------------------

    for i, day_code in enumerate(DAY_ORDER):

        ax.axvline(
            i,
            linewidth=0.8,
            alpha=0.3
        )

        ax.axvline(
            i + 1,
            linewidth=0.8,
            alpha=0.3
        )

    # -----------------------------------------------------
    # Time rows
    # -----------------------------------------------------

    current = start_hour

    while current <= end_hour:

        ax.axhline(
            current,
            linewidth=0.5,
            alpha=0.2
        )

        current += 0.5

    # -----------------------------------------------------
    # Draw subjects
    # -----------------------------------------------------

    for entry in entries:

        if entry["day"] not in DAY_ORDER:
            continue

        day_index = DAY_ORDER.index(
            entry["day"]
        )

        start = time_to_decimal(
            entry["start"]
        )

        end = time_to_decimal(
            entry["end"]
        )

        duration = end - start

        # Lecture and laboratory are visually
        # distinguished using hatch patterns.
        if entry["type"] == "Laboratory":

            rectangle = patches.Rectangle(
                (
                    day_index + 0.05,
                    start
                ),
                0.90,
                duration,
                linewidth=1.5,
                edgecolor="black",
                facecolor="lightgray",
                hatch="//",
            )

        elif entry["type"] == "Fixed":

            rectangle = patches.Rectangle(
                (
                    day_index + 0.05,
                    start
                ),
                0.90,
                duration,
                linewidth=1.5,
                edgecolor="black",
                facecolor="lightgray",
                hatch="..",
            )

        else:

            rectangle = patches.Rectangle(
                (
                    day_index + 0.05,
                    start
                ),
                0.90,
                duration,
                linewidth=1.5,
                edgecolor="black",
                facecolor="white",
            )

        ax.add_patch(rectangle)

        # -------------------------------------------------
        # Label depending on selected visualization
        # -------------------------------------------------

        if view_type.lower() == "section":

            if entry["type"] == "Fixed":
                label = (
                    f"{entry['subject']}\n"
                    f"Fixed Schedule"
                )
            else:
                label = (
                    f"{entry['subject']}\n"
                    f"{entry['type']}\n"
                    f"Faculty: {entry['faculty']}\n"
                    f"Room: {entry['room']}"
                )

        elif view_type.lower() == "faculty":

            label = (
                f"{entry['subject']}\n"
                f"{entry['section']}\n"
                f"{entry['type']}\n"
                f"Room: {entry['room']}"
            )

        else:

            label = (
                f"{entry['subject']}\n"
                f"{entry['section']}\n"
                f"{entry['type']}\n"
                f"Faculty: {entry['faculty']}"
            )

        ax.text(
            day_index + 0.5,
            start + duration / 2,
            label,
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=8,
        )

    # -----------------------------------------------------
    # X axis
    # -----------------------------------------------------

    ax.set_xlim(
        0,
        len(DAY_ORDER)
    )

    ax.set_xticks(
        [
            i + 0.5
            for i in range(len(DAY_ORDER))
        ]
    )

    ax.set_xticklabels(
        [
            DAY_NAMES[day]
            for day in DAY_ORDER
        ]
    )

    # -----------------------------------------------------
    # Y axis
    # -----------------------------------------------------

    tick_values = []

    current = start_hour

    while current <= end_hour:

        tick_values.append(current)
        current += 0.5

    tick_labels = []

    for value in tick_values:

        hour = int(value)

        minute = (
            30
            if value % 1
            else 0
        )

        tick_labels.append(
            f"{hour:02d}:{minute:02d}"
        )

    ax.set_yticks(tick_values)

    ax.set_yticklabels(
        tick_labels
    )

    # Reverse the time axis so morning appears at top.
    ax.set_ylim(
        end_hour,
        start_hour
    )

    # -----------------------------------------------------
    # Titles
    # -----------------------------------------------------

    readable_type = (
        view_type
        .strip()
        .capitalize()
    )

    ax.set_title(
        f"{readable_type} Schedule: "
        f"{target_name}",
        fontsize=16,
        pad=20,
    )

    ax.set_xlabel(
        "Day"
    )

    ax.set_ylabel(
        "Time"
    )

    plt.tight_layout()

    plt.show()


from collections import defaultdict


DAY_NAMES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "TH": "Thursday",
    "F": "Friday",
    "S": "Saturday"
}


def time_to_minutes(time_string):
    """
    Convert HH:MM into minutes.

    Example:
        09:30 -> 570
        13:00 -> 780
    """
    hour, minute = map(int, str(time_string).split(":"))
    return (hour * 60) + minute


def get_subject_schedule_entries(subject):
    """
    Extract all Lecture and Laboratory schedules
    of one Subject.

    Returns one entry per day/class period.
    """

    entries = []

    section = getattr(subject, "section", None)
    faculty = getattr(subject, "assigned_faculty", None)

    section_code = (
        str(section.code)
        if section is not None
        else "Unknown"
    )

    faculty_code = (
        str(faculty.code)
        if faculty is not None
        else "Unknown"
    )

    subject_number = str(
        getattr(subject, "number", "Unknown")
    )

    subject_title = str(
        getattr(subject, "title", "")
        or ""
    )

    # =====================================================
    # LECTURE
    # =====================================================

    lecture_blocks = getattr(
        subject,
        "lecture_time_blocks",
        []
    )

    lecture_room = getattr(
        subject,
        "lecture_room",
        None
    )

    lecture_room_name = (
        str(lecture_room.name)
        if lecture_room is not None
        else None
    )

    entries.extend(
        collapse_blocks_for_conflict_check(
            blocks=lecture_blocks,
            subject_number=subject_number,
            subject_title=subject_title,
            schedule_type="Lecture",
            section_code=section_code,
            faculty_code=faculty_code,
            room_name=lecture_room_name
        )
    )

    # =====================================================
    # LABORATORY
    # =====================================================

    laboratory_blocks = getattr(
        subject,
        "laboratory_time_blocks",
        []
    )

    laboratory_room = getattr(
        subject,
        "laboratory_room",
        None
    )

    laboratory_room_name = (
        str(laboratory_room.name)
        if laboratory_room is not None
        else None
    )

    entries.extend(
        collapse_blocks_for_conflict_check(
            blocks=laboratory_blocks,
            subject_number=subject_number,
            subject_title=subject_title,
            schedule_type="Laboratory",
            section_code=section_code,
            faculty_code=faculty_code,
            room_name=laboratory_room_name
        )
    )

    return entries


def collapse_blocks_for_conflict_check(
    blocks,
    subject_number,
    subject_title,
    schedule_type,
    section_code,
    faculty_code,
    room_name
):
    """
    Combine consecutive TimeBlocks.

    Example:

        M 09:30-10:00
        M 10:00-10:30
        M 10:30-11:00
        M 11:00-11:30

    becomes:

        M 09:30-11:30
    """

    if not blocks:
        return []

    blocks_by_day = defaultdict(list)

    for day_code, block in blocks:
        blocks_by_day[day_code].append(block)

    results = []

    for day_code, day_blocks in blocks_by_day.items():

        day_blocks = sorted(
            day_blocks,
            key=lambda block:
                time_to_minutes(block.start_time)
        )

        current_start = day_blocks[0].start_time
        current_end = day_blocks[0].end_time

        for block in day_blocks[1:]:

            # Continuous block
            if block.start_time == current_end:
                current_end = block.end_time

            else:
                results.append({
                    "subject": subject_number,
                    "title": subject_title,
                    "type": schedule_type,
                    "day": day_code,
                    "start": current_start,
                    "end": current_end,
                    "section": section_code,
                    "faculty": faculty_code,
                    "room": room_name
                })

                current_start = block.start_time
                current_end = block.end_time

        # Add last continuous period
        results.append({
            "subject": subject_number,
            "title": subject_title,
            "type": schedule_type,
            "day": day_code,
            "start": current_start,
            "end": current_end,
            "section": section_code,
            "faculty": faculty_code,
            "room": room_name
        })

    return results


def schedules_overlap(schedule1, schedule2):
    """
    Return True when two schedules overlap.

    Adjacent schedules are allowed.

    Example:

        09:30-11:30
        11:30-13:30

    is NOT a conflict.
    """

    if schedule1["day"] != schedule2["day"]:
        return False

    start1 = time_to_minutes(schedule1["start"])
    end1 = time_to_minutes(schedule1["end"])

    start2 = time_to_minutes(schedule2["start"])
    end2 = time_to_minutes(schedule2["end"])

    return (
        start1 < end2
        and
        start2 < end1
    )


def find_resource_conflicts(entries, resource):
    """
    Find conflicts for one resource:

        resource = "section"
        resource = "faculty"
        resource = "room"
    """

    grouped = defaultdict(list)

    for entry in entries:

        resource_value = entry.get(resource)

        # Ignore missing/unassigned resources
        if resource_value in [
            None,
            "",
            "Unknown"
        ]:
            continue

        grouped[str(resource_value)].append(entry)

    conflicts = []

    for resource_value, schedules in grouped.items():

        for i in range(len(schedules)):

            for j in range(i + 1, len(schedules)):

                schedule1 = schedules[i]
                schedule2 = schedules[j]

                # -------------------------------------------------
                # Same exact subject/type entry should not be
                # compared against itself.
                # -------------------------------------------------

                same_class = (
                    schedule1["subject"]
                    == schedule2["subject"]
                    and
                    schedule1["type"]
                    == schedule2["type"]
                    and
                    schedule1["day"]
                    == schedule2["day"]
                    and
                    schedule1["start"]
                    == schedule2["start"]
                    and
                    schedule1["end"]
                    == schedule2["end"]
                )

                if same_class:
                    continue

                if schedules_overlap(
                    schedule1,
                    schedule2
                ):
                    conflicts.append({
                        "resource_type": resource,
                        "resource": resource_value,
                        "schedule1": schedule1,
                        "schedule2": schedule2
                    })

    return conflicts


def print_conflicts(
    conflicts,
    title
):
    """
    Nicely print conflict information.
    """

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    if not conflicts:

        print("✓ NO CONFLICTS FOUND")

        return

    print(
        f"✗ {len(conflicts)} CONFLICT(S) FOUND"
    )

    print()

    for number, conflict in enumerate(
        conflicts,
        start=1
    ):

        schedule1 = conflict["schedule1"]
        schedule2 = conflict["schedule2"]

        day = DAY_NAMES.get(
            schedule1["day"],
            schedule1["day"]
        )

        print("-" * 80)

        print(
            f"Conflict #{number}"
        )

        print(
            f"{conflict['resource_type'].capitalize()}: "
            f"{conflict['resource']}"
        )

        print(
            f"Day: {day}"
        )

        print()

        print(
            "CLASS 1:"
        )

        print(
            f"   Subject : "
            f"{schedule1['subject']}"
        )

        if schedule1["title"]:
            print(
                f"   Title   : "
                f"{schedule1['title']}"
            )

        print(
            f"   Type    : "
            f"{schedule1['type']}"
        )

        print(
            f"   Time    : "
            f"{schedule1['start']}"
            f"-"
            f"{schedule1['end']}"
        )

        print(
            f"   Section : "
            f"{schedule1['section']}"
        )

        print(
            f"   Faculty : "
            f"{schedule1['faculty']}"
        )

        print(
            f"   Room    : "
            f"{schedule1['room']}"
        )

        print()

        print(
            "CLASS 2:"
        )

        print(
            f"   Subject : "
            f"{schedule2['subject']}"
        )

        if schedule2["title"]:
            print(
                f"   Title   : "
                f"{schedule2['title']}"
            )

        print(
            f"   Type    : "
            f"{schedule2['type']}"
        )

        print(
            f"   Time    : "
            f"{schedule2['start']}"
            f"-"
            f"{schedule2['end']}"
        )

        print(
            f"   Section : "
            f"{schedule2['section']}"
        )

        print(
            f"   Faculty : "
            f"{schedule2['faculty']}"
        )

        print(
            f"   Room    : "
            f"{schedule2['room']}"
        )

    print("-" * 80)


def check_all_schedule_conflicts(
    lst_subjects
):
    """
    Check the COMPLETE generated schedule.

    Checks:

        1. Section conflicts
        2. Faculty conflicts
        3. Room conflicts

    Returns True if schedule is conflict-free.
    """

    print()
    print("#" * 80)
    print("SCHEDULE CONFLICT VALIDATION")
    print("#" * 80)

    # =====================================================
    # Extract every scheduled class
    # =====================================================

    all_entries = []

    for subject in lst_subjects:
        all_entries.extend(
            get_subject_schedule_entries(subject)
        )

    print(
        f"\nTotal scheduled class periods checked: "
        f"{len(all_entries)}"
    )

    # =====================================================
    # SECTION
    # =====================================================

    section_conflicts = (
        find_resource_conflicts(
            all_entries,
            "section"
        )
    )

    # =====================================================
    # FACULTY
    # =====================================================

    faculty_conflicts = (
        find_resource_conflicts(
            all_entries,
            "faculty"
        )
    )

    # =====================================================
    # ROOM
    # =====================================================

    room_conflicts = (
        find_resource_conflicts(
            all_entries,
            "room"
        )
    )

    # =====================================================
    # Display results
    # =====================================================

    print_conflicts(
        section_conflicts,
        "SECTION CONFLICT CHECK"
    )

    print_conflicts(
        faculty_conflicts,
        "FACULTY CONFLICT CHECK"
    )

    print_conflicts(
        room_conflicts,
        "ROOM CONFLICT CHECK"
    )

    # =====================================================
    # Final summary
    # =====================================================

    total_conflicts = (
        len(section_conflicts)
        +
        len(faculty_conflicts)
        +
        len(room_conflicts)
    )

    print()
    print("=" * 80)
    print("FINAL VALIDATION RESULT")
    print("=" * 80)

    print(
        f"Section conflicts : "
        f"{len(section_conflicts)}"
    )

    print(
        f"Faculty conflicts : "
        f"{len(faculty_conflicts)}"
    )

    print(
        f"Room conflicts    : "
        f"{len(room_conflicts)}"
    )

    print(
        f"Total conflicts   : "
        f"{total_conflicts}"
    )

    print()

    if total_conflicts == 0:

        print(
            "✓ SCHEDULE IS VALID."
        )

        print(
            "✓ No section conflicts."
        )

        print(
            "✓ No faculty conflicts."
        )

        print(
            "✓ No room conflicts."
        )

        return True

    else:

        print(
            "✗ SCHEDULE IS NOT VALID."
        )

        print(
            "✗ Please resolve the conflicts "
            "listed above."
        )

        return False

df_faculty_pref = df_preferences[['Faculty_Code','Faculty_Prio','New Schedule','Subject','Day(s)']]



df_faculty_pref.columns = ['Faculty_Code','Faculty_Prio' ,'PreferredSchedule','Preferred Subjects','Preferred Day(s)']

def faculty_preference_fitness(
    chromosome,
    df_faculty_pref,
    subject_penalty=10,
    day_penalty=6,
    time_penalty=8
):
    """
    Calculate faculty-preference penalty for one chromosome.

    LOWER FITNESS = BETTER

    Assumptions:
    - chromosome is a list of Subject objects
    - subject.assigned_faculty contains the assigned Faculty object
    - subject.number contains the subject/course number
    - faculty.code identifies the faculty
    - faculty.seniority_level / Faculty_Prio:
          smaller value = higher priority
    - scheduled time blocks contain the actual assigned schedule

    This function evaluates ONLY faculty preferences.
    Hard constraints such as:
        - faculty conflicts
        - room conflicts
        - section/student conflicts
    should already be prevented elsewhere.
    """

    total_penalty = 0

    # Fix the double-level columns created by:
    # df_faculty_pref.columns = [[...]]
    prefs = df_faculty_pref.copy()

    if isinstance(prefs.columns, pd.MultiIndex):
        prefs.columns = prefs.columns.get_level_values(0)

    # Highest numeric priority is used to construct
    # an inverse priority weight.
    max_priority = prefs["Faculty_Prio"].max()

    for subject in chromosome:

        faculty = subject.assigned_faculty

        if faculty is None:
            continue

        # -------------------------------------------------
        # Get this faculty member's preference records
        # -------------------------------------------------
        faculty_pref = prefs[
            prefs["Faculty_Code"] == faculty.code
        ]

        if faculty_pref.empty:
            continue

        faculty_priority = faculty_pref[
            "Faculty_Prio"
        ].iloc[0]

        # Example:
        #
        # priorities 1,2,3,4,5
        #
        # priority 1 -> weight 5
        # priority 2 -> weight 4
        # priority 3 -> weight 3
        # priority 4 -> weight 2
        # priority 5 -> weight 1

        priority_weight = (
            max_priority - faculty_priority + 1
        )

        # =================================================
        # 1. SUBJECT PREFERENCE
        # =================================================

        preferred_subjects = (
            faculty_pref["Preferred Subjects"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .tolist()
        )

        actual_subject = str(
            subject.number
        ).strip().upper()

        if (
            preferred_subjects
            and actual_subject not in preferred_subjects
        ):
            total_penalty += (
                subject_penalty * priority_weight
            )

        # =================================================
        # Get actual schedule
        # =================================================

        actual_blocks = []

        if getattr(subject, "lecture_time_blocks", None):
            actual_blocks.extend(
                subject.lecture_time_blocks
            )

        if getattr(subject, "laboratory_time_blocks", None):
            actual_blocks.extend(
                subject.laboratory_time_blocks
            )

        # Fall back to scheduled_time_blocks
        if not actual_blocks:
            scheduled = getattr(
                subject,
                "scheduled_time_blocks",
                None
            )

            if scheduled:
                if isinstance(scheduled, list):
                    actual_blocks.extend(scheduled)
                else:
                    actual_blocks.append(scheduled)

        # =================================================
        # 2. DAY PREFERENCE
        # =================================================

        preferred_days = set()

        for value in (
            faculty_pref["Preferred Day(s)"]
            .dropna()
            .tolist()
        ):
            preferred_days.update(
                Faculty._normalize_days(value)
            )

        actual_days = set()

        for block in actual_blocks:

            day = getattr(block, "day", None)

            if day is not None:
                actual_days.add(
                    str(day).strip().lower()
                )

        if preferred_days and actual_days:

            if not actual_days.issubset(preferred_days):

                total_penalty += (
                    day_penalty * priority_weight
                )

        # =================================================
        # 3. TIME PREFERENCE
        # =================================================

        #
        # Your Faculty class already marks preferred
        # TimeBlocks using:
        #
        #     block.preferred = True
        #
        # Therefore, we can evaluate whether the actual
        # scheduled blocks fall inside preferred blocks.
        #

        faculty_day_map = faculty.get_day_map()

        nonpreferred_blocks = 0

        for block in actual_blocks:

            actual_day = getattr(
                block,
                "day",
                None
            )

            actual_start = getattr(
                block,
                "start_time",
                None
            )

            actual_end = getattr(
                block,
                "end_time",
                None
            )

            if actual_day is None:
                continue

            day_name = str(
                actual_day
            ).strip().lower()

            if day_name not in faculty_day_map:
                continue

            matching_preferred = False

            for pref_block in faculty_day_map[day_name]:

                if (
                    pref_block.start_time == actual_start
                    and
                    pref_block.end_time == actual_end
                    and
                    pref_block.preferred
                ):
                    matching_preferred = True
                    break

            if not matching_preferred:
                nonpreferred_blocks += 1

        if nonpreferred_blocks > 0:

            total_penalty += (
                time_penalty
                * nonpreferred_blocks
                * priority_weight
            )

    return total_penalty


# rooms_names = ['ICT 3B','ICT 3A','ICT 3C']
# lst_rooms = []
# for room in rooms_names:
#         room1 = Room(room,'Lecture')
#         lst_rooms.append(room1)

# rooms_names = ['NETWORK LAB','DATABASE LAB','MULTIMEDIA LAB']

# for room in rooms_names:
#         room1 = Room(room,'Laboratory')
#         lst_rooms.append(room1)


rooms_names = ['NETWORK LAB','DATABASE LAB','MULTIMEDIA LAB']
lst_rooms = []
for room in rooms_names:
        room1 = Room(room,'Laboratory')
        lst_rooms.append(room1)


rooms_names = ['ICT 3B','ICT 3A','ICT 3C']

for room in rooms_names:
        room1 = Room(room,'Lecture')
        lst_rooms.append(room1)

