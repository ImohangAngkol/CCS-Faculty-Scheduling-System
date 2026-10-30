"""Explicit fictional GA inputs. No CSV import, authority provider or database."""
from dataclasses import asdict, dataclass
import hashlib
import json


@dataclass(frozen=True)
class Dimensions:
    faculty: int
    offerings: int
    sections: int
    lecture_rooms: int
    laboratory_rooms: int
    unqualified_last_member: bool = False


SCENARIOS = {
    'small': Dimensions(6, 12, 3, 2, 2, True),
    'medium': Dimensions(12, 24, 6, 3, 3),
    'large': Dimensions(24, 48, 12, 5, 5),
}
VERSION = 'fictional-scaled-fixtures.1'


def build(name):
    from genetic_algorithm.models.Faculty import Faculty
    from genetic_algorithm.models.Room import Room
    from genetic_algorithm.models.Section import Section
    from genetic_algorithm.models.Subject import Subject
    from genetic_algorithm.models.ga_setting import GASetting
    import pandas as pd

    d = SCENARIOS[name]
    sections = [Section(f'BENCH-SEC-{i:02}') for i in range(d.sections)]
    subjects = [Subject(f'BENCH{i:03}', f'Fictional benchmark course {i:03}', 3,
                        2 if i % 2 else 3, 3 if i % 2 else 0,
                        sections[i // 4]) for i in range(d.offerings)]
    eligible = [set() for _ in range(d.faculty)]
    qualified = d.faculty - int(d.unqualified_last_member)
    for i, subject in enumerate(subjects):
        for index in {i % qualified, (i + 1) % qualified, (i + qualified // 2) % qualified}:
            eligible[index].add(subject.number)
    faculty = []
    rows = []
    targets = (12, 15, 18, 21, 24, 9)
    for i, codes in enumerate(eligible):
        # All three non-teaching inputs are hypothetical and fixed, not outputs.
        release = 24 - targets[i % len(targets)]
        admin = release // 2
        research = (release - admin) // 2
        member = Faculty(990100 + i, 1 + i % 3, admin_load=admin,
                         research_load=research, extension_load=release-admin-research,
                         eligible_subjects=codes)
        faculty.append(member)
        rows.append({'faculty_code': member.code, 'faculty_priority': 1 + i % 3,
                     'preferred_subjects': sorted(codes)[i % 2:i % 2 + 2],
                     'use_subject_preference': True, 'subject_importance': 1 + i % 5,
                     'preferred_days': [['M', 'W'], ['T', 'TH'], ['F', 'S']][i % 3],
                     'use_day_preference': True, 'day_importance': 1 + i % 4,
                     'preferred_start_time': '08:00' if i % 2 == 0 else '13:00',
                     'preferred_end_time': '12:00' if i % 2 == 0 else '17:00',
                     'use_time_preference': True, 'time_importance': 1 + i % 3,
                     'gap_preference': 'Compact' if i % 2 == 0 else 'Scattered',
                     'use_gap_preference': True, 'gap_importance': 2 + i % 3})
    rooms = [Room(f'BENCH-LEC-{i:02}', 'Lecture') for i in range(d.lecture_rooms)]
    rooms += [Room(f'BENCH-LAB-{i:02}', 'Laboratory') for i in range(d.laboratory_rooms)]
    legacy = pd.DataFrame({'Faculty_Code': [f.code for f in faculty],
                           'Faculty_Prio': [1 + i % 3 for i in range(d.faculty)],
                           'Preferred Subjects': [None] * d.faculty,
                           'Preferred Day(s)': [None] * d.faculty})
    settings = GASetting().to_dict()  # Source defaults, never user's settings JSON.
    metadata = {'version': VERSION, 'scenario': name, 'dimensions': asdict(d),
                'scope': 'Fictional kernel benchmark; no institutional approval or publication',
                'subjects': [{'code': s.number, 'section': s.section.code, 'units': s.credit_units,
                              'lec_hours': s.lec_hours, 'lab_hours': s.lab_hours} for s in subjects],
                'faculty': [{'code': f.code, 'admin': f.admin_load, 'research': f.research_load,
                             'extension': f.extension_load, 'target': f.required_teaching_load,
                             'eligible': sorted(f.eligible_subjects)} for f in faculty],
                'preferences': rows, 'settings': settings,
                'weekly_calendar': 'Original 07:30-22:00 Monday-Saturday',
                'total_offered_units': sum(s.credit_units for s in subjects),
                'total_target_units': sum(f.required_teaching_load for f in faculty)}
    metadata['synthetic_input_sha256'] = hashlib.sha256(
        json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return (subjects, faculty, rooms), legacy, rows, settings, metadata


def snapshot(values, metadata):
    """Static unit-fixture snapshot, like D10 tests, NOT a trusted deployment.

    Direct kernel use is intentionally outside APIs, D8/D9 providers and durable
    confirmation/publication. No provider or authority flag is installed.
    """
    from services.ga_v2_constraints import Catalog, Commitment, Head, Snapshot, template_fingerprint
    from services.ga_progress_service import input_fingerprint
    catalog = Catalog(academic_year='2026-2027', term='Fictional benchmark term',
                      effective_start='2026-08-03', effective_end='2026-12-18',
                      revision='benchmark-only-NOT-INSTITUTIONAL.1',
                      input_fingerprint=input_fingerprint(), template_digest=template_fingerprint(values),
                      sections=tuple((f'bench-section-{i}', f'BENCH-SEC-{i:02}')
                                     for i in range(metadata['dimensions']['sections'])),
                      faculty=tuple((f'bench-faculty-{i}', str(f.code)) for i, f in enumerate(values[1])),
                      rooms=tuple((f'bench-room-{i}', r.name) for i, r in enumerate(values[2])))
    source = metadata['synthetic_input_sha256']
    head = Head(record_id='benchmark-static-record', revision_id='benchmark-static-revision',
                event_id='benchmark-static-event', version=1, content_digest=source,
                evidence_digest=source, source_sha256=source)
    commitments = tuple(Commitment(record_id=head.record_id, revision_id=head.revision_id,
                                  source_row=i+1, source_sha256=source, subject='BENCH-EXTERNAL',
                                  day='M', start=540, end=600, sections=(id,),
                                  faculty='bench-faculty-0' if i == 0 else None,
                                  room='bench-room-0' if i == 0 else None)
                        for i, (id, _) in enumerate(catalog.sections))
    return Snapshot(catalog=catalog, heads=(head,), commitments=commitments)
