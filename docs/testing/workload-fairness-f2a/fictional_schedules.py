"""Small, exhaustive fixed-geometry allocation controls using original GA rules.

No replacement scorer is injected into the GA; all candidate scores are computed
after original admission, and all original non-workload components must be zero.
"""
import copy
from dataclasses import dataclass
import itertools
import random

from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import scaled_python as bench
from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.models.Room import Room
from genetic_algorithm.models.Subject import Subject
from genetic_algorithm.models.Section import Section
from services import ga_v2_constraints as constraints
from services.ga_progress_service import input_fingerprint
from tests.audit.test_thesis_correctness import independent_conflicts
from fairness_models import FUNCTIONS,metrics,original_workload,serial

engine,fitness,scoring_inputs,Setting,*_=runtime()
DAYS=('M','T','W','TH','F','S')


@dataclass(frozen=True)
class Scenario:
    name: str
    targets: tuple
    offerings: int
    eligibility: tuple | None = None
    allowances: tuple | None = None


SCENARIOS=(
    Scenario('equal_shortage',(24,24),2),
    Scenario('unequal_shortage',(12,24),6),
    Scenario('allowance_shortage',(4,8),3,allowances=((8,8,4),(8,4,4))),
    Scenario('above_combined_targets',(4,8),8),
    Scenario('no_eligible_member',(12,24,6),6,eligibility=(tuple(range(6)),tuple(range(6)),())),
    Scenario('limited_eligibility',(12,24),6,eligibility=(tuple(range(6)),(4,5))),
    Scenario('indivisible_zero_assignment',(12,24),1),
    Scenario('targets_exactly_reachable',(4,8),6),
    Scenario('zero_target_member',(0,4),2),
)


def templates(scenario):
    subjects=[Subject('SYN-F2A','Fictional IT offering',2,2,0,Section('F2A-'+str(i+1))) for i in range(scenario.offerings)]
    # Separate course codes only where different explicit per-offering eligibility
    # is needed. Preparation thresholds are not changed; valid rows remain <=3
    # distinct preparations per faculty by using two course groups in that case.
    if scenario.name=='limited_eligibility':
        for i,s in enumerate(subjects):s.number='SYN-ONLY-A' if i<4 else 'SYN-SHARED'
    members=[]
    for i,t in enumerate(scenario.targets):
        a,r,e=scenario.allowances[i] if scenario.allowances else (24-t,0,0)
        codes={s.number for j,s in enumerate(subjects) if scenario.eligibility is None or j in scenario.eligibility[i]}
        member=Faculty(990101+i,1,admin_load=a,research_load=r,extension_load=e,eligible_subjects=codes)
        assert member.required_teaching_load==t
        members.append(member)
    rooms=[Room('Fictional F2A lecture room','Lecture')]
    for resource in [*members,*rooms,*(s.section for s in subjects)]:
        for name in ('monday','tuesday','wednesday','thursday','friday','saturday'):
            setattr(resource,'time_blocks_'+name,getattr(resource,'time_blocks_'+name)[:8])
    return subjects,members,rooms


def snapshot(values):
    subjects,members,rooms=values
    catalog=constraints.Catalog(academic_year='2026-2027',term='Fictional IT test term',effective_start='2026-08-03',effective_end='2026-12-18',
        revision='fictional-f2a.1',input_fingerprint=input_fingerprint(),template_digest=constraints.template_fingerprint(values),
        sections=tuple(('fictional-section-'+str(i),s.section.code) for i,s in enumerate(subjects)),
        faculty=tuple(('fictional-faculty-'+str(i),str(f.code)) for i,f in enumerate(members)),rooms=(('fictional-room',rooms[0].name),))
    head=constraints.Head(record_id='fictional-record',revision_id='fictional-revision',event_id='fictional-event',version=1,
        content_digest='b'*64,evidence_digest='c'*64,source_sha256='a'*64)
    commitment=constraints.Commitment(record_id=head.record_id,revision_id=head.revision_id,source_row=1,source_sha256='a'*64,
        subject='SYN-FIXED',day='M',start=570,end=630,sections=('fictional-section-0',),faculty=None,room=None)
    return constraints.Snapshot(catalog=catalog,heads=(head,),commitments=(commitment,))


def arrange(values,assignment):
    subjects,members,rooms=copy.deepcopy(values)
    for i,(subject,index) in enumerate(zip(subjects,assignment)):
        period='7:30 - 9:30' if i%2==0 else '9:30 - 11:30'
        if not engine.schedule.assign_schedule_to_faculty(members[index],subject,(period,DAYS[i//2]),'Lecture',room_list=rooms,list_subjects=subjects):
            raise ValueError('FICTIONAL_ASSIGNMENT_REJECTED')
    return subjects


def evaluate(scenario):
    before=random.getstate()
    try:
        random.seed(6200)
        values=templates(scenario);pinned=snapshot(values);reduced=constraints.reduced_templates(pinned,values)
        choices=[tuple(i for i,m in enumerate(values[1]) if engine.schedule.faculty_is_explicitly_eligible_for_subject(m,s)) for s in values[0]]
        rows={};checked=0
        with bench.synthetic_scoring(values,[],Setting().to_dict()),data_guard(),bench.no_io():
            token=scoring_inputs.set(engine.freeze(values))
            try:
                for assignment in itertools.product(*choices):
                    candidate=arrange(reduced,assignment);engine.admit(candidate,pinned,reduced)
                    assert independent_conflicts(candidate)==dict(faculty=0,room=0,section=0)
                    total,breakdown=fitness.faculty_preference_fitness(candidate,return_breakdown=True)
                    assert all(v==0 for k,v in breakdown.items() if k!='teaching_load_balance')
                    actual=[sum(s.credit_units for s in candidate if s.assigned_faculty.code==m.code) for m in values[1]]
                    assert total==breakdown['teaching_load_balance']==original_workload(actual,scenario.targets)
                    checked+=1
                    key=tuple(actual)
                    if key not in rows:
                        rows[key]=dict(actual=actual,original_total=total,original_components=breakdown,
                            scores={k:fn(actual,scenario.targets) for k,fn in FUNCTIONS.items()},
                            metrics=metrics(actual,scenario.targets,[bool(m.eligible_subjects) for m in values[1]]),
                            original_hard_admitted=True,unassigned_offerings=0,hard_conflicts=dict(faculty=0,room=0,section=0))
            finally:scoring_inputs.reset(token)
        winners={name:[row['actual'] for row in rows.values() if row['scores'][name]==min(r['scores'][name] for r in rows.values())] for name in FUNCTIONS}
        return dict(scenario=scenario.name,targets=list(scenario.targets),allowances=[dict(admin=f.admin_load,research=f.research_load,extension=f.extension_load) for f in values[1]],
            offered_teaching_units=2*scenario.offerings,combined_targets=sum(scenario.targets),
            faculty_count=len(values[1]),faculty_with_no_eligible_offerings=sum(not m.eligible_subjects for m in values[1]),
            fixed_geometry_assignment_space=len(values[1])**scenario.offerings,
            explicitly_eligible_assignments_checked=checked,unique_workload_vectors=len(rows),
            exhaustive_boundary='All explicit eligible assignments on fixed fictional geometry, not all possible timetables or a GA-quality campaign',
            all_original_hard_valid=True,all_seven_other_components_zero=True,winners=winners,rows=list(rows.values()))
    finally:random.setstate(before)
