"""Fictional V2 engine/constraint/checkpoint tests, not institutional acceptance."""
from contextlib import contextmanager
import copy
import gzip
import hashlib
import json
import random
import os
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from services import ga_v2_constraints as constraints, ga_v2_engine as engine, ga_v2_store as store
from services import ga_checkpoint_service as legacy
from services.ga_progress_service import input_fingerprint
from services.external_confirmation_service import digest
from schemas.ga_constrained import Parameters
from tests.d10.support import templates, preferences


def catalog_for(values):
    return constraints.Catalog(academic_year="2026-2027",term="Fictional first term",effective_start="2026-08-03",effective_end="2026-12-18",
        revision="fictional-catalog.1",input_fingerprint=input_fingerprint(),template_digest=constraints.template_fingerprint(values),
        sections=(("section-a","SYN-A"),("section-b","SYN-B")),faculty=(("faculty-a","990001"),("faculty-b","990002")),
        rooms=(("room-a","Fictional Lecture Room"),))


def snapshot_for(values,**changes):
    item=constraints.Commitment(record_id="fictional-record",revision_id="fictional-revision",source_row=7,source_sha256="a"*64,
        subject="SYN-GEC",day="M",start=540,end=600,sections=("section-a",),faculty="faculty-a",room="room-a")
    item=item.model_copy(update=changes)
    head=constraints.Head(record_id=item.record_id,revision_id=item.revision_id,event_id="fictional-event",version=1,
        content_digest="b"*64,evidence_digest="c"*64,source_sha256="a"*64)
    return constraints.Snapshot(catalog=catalog_for(values),heads=(head,),commitments=(item,))


class FictionalAuthority:
    """Unit boundary ONLY; D8/D9 integration is separately tested against SQLite."""
    def __init__(self,snapshot):self.snapshot=snapshot;self.blocked=False;self.calls=0
    @contextmanager
    def pinned(self,expected=None):
        self.calls+=1
        if self.blocked:constraints.reject("EVIDENCE_NOT_CURRENT","Fictional revocation or authority loss.")
        if expected and expected.digest!=self.snapshot.digest:constraints.reject("CONSTRAINT_SET_CHANGED","Fictional head changed.")
        yield self.snapshot

    def recheck(self,expected):
        with self.pinned(expected):pass


@pytest.fixture
def inputs(monkeypatch,tmp_path):
    monkeypatch.setattr(store,"STORE",tmp_path/"v2")
    return templates(compact=True)


def arranged(values, start="09:30", end="11:30"):
    subjects,faculty,rooms=copy.deepcopy(values)
    assert engine.schedule.assign_schedule_to_faculty(faculty[0],subjects[0],(start+" - "+end,"M"),"Lecture",room_list=rooms,list_subjects=subjects)
    assert engine.schedule.assign_schedule_to_faculty(faculty[1],subjects[1],("7:30 - 9:30","T"),"Lecture",room_list=rooms,list_subjects=subjects)
    return subjects


@pytest.mark.parametrize("kind,changes",[("SECTION",dict(sections=("section-a",),faculty=None,room=None)),
    ("FACULTY",dict(sections=("section-b",),faculty="faculty-a",room=None)),
    ("ROOM",dict(sections=("section-b",),faculty=None,room="room-a"))])
def test_all_resources_and_partial_overlap_are_admitted_before_scoring(inputs,kind,changes):
    snapshot=snapshot_for(inputs,**changes)
    candidate=arranged(inputs)
    with pytest.raises(constraints.ConstraintError) as caught:engine.admit(candidate,snapshot,constraints.reduced_templates(snapshot,inputs))
    assert caught.value.code=="EXTERNAL_"+kind+"_CONFLICT"


def test_adjacent_half_open_interval_is_allowed_and_nonmutating(inputs):
    snapshot=snapshot_for(inputs,start=570,end=630)
    candidate=arranged(constraints.reduced_templates(snapshot,inputs),"7:30","9:30")
    before=legacy.canonical(legacy.encode_graph(candidate));rng=random.getstate()
    engine.admit(candidate,snapshot,constraints.reduced_templates(snapshot,inputs))
    assert legacy.canonical(legacy.encode_graph(candidate))==before and random.getstate()==rng


@pytest.mark.parametrize("change,code",[(dict(start=600,end=540),"INVALID_COMMITMENT"),(dict(start=555),"INVALID_COMMITMENT"),
    (dict(day="SUN"),"INVALID_COMMITMENT"),(dict(end=720),"CALENDAR_CONTAINMENT"),
    (dict(faculty="unknown"),"RESOURCE_MAPPING_REQUIRED"),(dict(sections=()),"INVALID_PROVENANCE"),
    (dict(source_sha256="b"*64),"INVALID_PROVENANCE")])
def test_invalid_constraints_fail_closed(inputs,change,code):
    snapshot=snapshot_for(inputs,**change)
    with pytest.raises(constraints.ConstraintError) as caught:constraints.validate_snapshot(snapshot,inputs)
    assert caught.value.code==code


def test_duplicate_and_internal_fixed_conflicts_are_not_omitted(inputs):
    snapshot=snapshot_for(inputs)
    for second,code in [(snapshot.commitments[0],"DUPLICATE_COMMITMENT"),
        (snapshot.commitments[0].model_copy(update={"subject":"OTHER","source_row":8,"start":570,"end":630}),"FIXED_RESOURCE_CONFLICT")]:
        with pytest.raises(constraints.ConstraintError) as caught:constraints.validate_snapshot(snapshot.model_copy(update={"commitments":(*snapshot.commitments,second)}),inputs)
        assert caught.value.code==code


def test_reset_restarts_preserve_all_external_reservations(inputs):
    snapshot=snapshot_for(inputs);reduced=constraints.reduced_templates(snapshot,inputs)
    for _ in range(3):
        engine.schedule.reset_complete_schedule(reduced[1],reduced[0],reduced[2])
        for member in (reduced[1][0],reduced[2][0]):
            assert not any(constraints.overlap(540,600,constraints.minutes(b.start_time),constraints.minutes(b.end_time)) for b in constraints.calendar(member,"M"))
        assert all(not b.is_available for b in constraints.calendar(reduced[0][0].section,"M") if constraints.overlap(540,600,constraints.minutes(b.start_time),constraints.minutes(b.end_time)))
    assert constraints.calendar(inputs[1][0],"M")[3].is_available


def execute(values,snapshot,params,authority,run_id,*,pause_at=None,state=None,**kwargs):
    def boundary(current):
        status="PAUSED" if current["generation"]==pause_at else "COMPLETED" if current["generation"]==params.generations else "RUNNING"
        from services.ga_v2_service import result_for
        store.write(run_id,current,snapshot,authority,values,status,result_for(current,snapshot,status))
        return "pause" if status=="PAUSED" else None
    return engine.run(values,snapshot,params,preferences(),boundary,state=state,**kwargs)


def test_feasible_actual_operators_checkpoint_and_exact_v2_continuation(inputs):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot)
    params=Parameters(population_size=2,generations=2,fresh_chromosomes=1,mutation_attempts=1,crossover_attempts=1,max_restarts=3,candidate_attempts=3)
    original=random.getstate()
    try:
        plain,paused=str(uuid4()),str(uuid4())
        random.seed(714);assert execute(inputs,snapshot,params,authority,plain)=="complete"
        expected=random.getstate();left,_,_=store.read(plain)
        random.seed(714);assert execute(inputs,snapshot,params,authority,paused,pause_at=1)=="pause"
        before=store.path_for(paused).read_bytes();payload,pinned,state=store.read(paused)
        assert payload["engine_version"]==engine.ENGINE_VERSION and pinned.digest==snapshot.digest
        random.seed(111);assert execute(inputs,snapshot,params,authority,paused,state=state)=="complete"
        assert random.getstate()==expected
        right,_,_=store.read(paused)
        assert left["result"]==right["result"]
        assert before!=store.path_for(paused).read_bytes()
        assert authority.calls>=6
        assert not list(store.STORE.rglob("*.tmp"))
    finally:random.setstate(original)


def test_post_crossover_mutation_and_best_ever_admission(inputs):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot);bad=arranged(inputs)
    params=Parameters(population_size=2,generations=1,fresh_chromosomes=0,max_restarts=3,candidate_attempts=3,crossover_attempts=1,mutation_attempts=1)
    run_id=str(uuid4())
    execute(inputs,snapshot,params,authority,run_id,crossover=lambda **k:copy.deepcopy(bad),mutation=lambda **k:copy.deepcopy(bad))
    payload,_,state=store.read(run_id)
    assert state["diagnostics"]["crossover:EXTERNAL_SECTION_CONFLICT"]==20
    assert state["diagnostics"]["mutation:EXTERNAL_SECTION_CONFLICT"]==1
    assert len(state["population"])==2 and payload["result"]["feasibility"]=="VALIDATED_CANDIDATE"
    for candidate in [*state["population"],state["best"]]:assert constraints.external_conflict(candidate,snapshot) is None


def test_initial_rejection_backfill_and_bounded_exhaustion(inputs):
    snapshot=snapshot_for(inputs);bad=arranged(inputs);calls=[]
    def rejected(*args):calls.append(1);return copy.deepcopy(bad)
    params=Parameters(population_size=2,generations=1,candidate_attempts=2,max_restarts=1)
    with pytest.raises(constraints.ConstraintError) as caught:
        engine.run(inputs,snapshot,params,preferences(),lambda state:pytest.fail("No partial population may publish"),factory=rejected)
    assert caught.value.code=="SEARCH_EXHAUSTED" and len(calls)==4
    assert not store.STORE.exists()


def test_incompatible_seed_is_not_silently_dropped(inputs):
    snapshot=snapshot_for(inputs)
    with pytest.raises(constraints.ConstraintError) as caught:
        engine.run(inputs,snapshot,Parameters(),preferences(),lambda s:None,seed=arranged(inputs))
    assert caught.value.code=="INCOMPATIBLE_REQUESTED_SEED"


def test_authority_loss_prevents_saved_best_history_and_checkpoint_write(inputs):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot);run_id=str(uuid4())
    params=Parameters(population_size=2,generations=1,crossover_attempts=1,max_restarts=2,mutation_attempts=1)
    def boundary(state):
        authority.blocked=True
        store.write(run_id,state,snapshot,authority,inputs,"COMPLETED",{})
    with pytest.raises(constraints.ConstraintError):engine.run(inputs,snapshot,params,preferences(),boundary)
    assert not store.path_for(run_id).exists() and not store.STORE.exists()


@pytest.mark.parametrize("change",["checksum","engine","term","partial","population"])
def test_checkpoint_corruption_or_incompatibility_rejected(inputs,change):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot);run_id=str(uuid4())
    params=Parameters(population_size=2,generations=1,crossover_attempts=1,max_restarts=2,mutation_attempts=1)
    execute(inputs,snapshot,params,authority,run_id,pause_at=0)
    path=store.path_for(run_id);envelope=json.loads(gzip.decompress(path.read_bytes()))
    if change=="partial":path.write_bytes(b"partial");
    else:
        payload=envelope["payload"]
        if change=="checksum":envelope["sha256"]="0"*64
        if change=="engine":payload["engine_fingerprint"]="0"*64
        if change=="term":payload["snapshot"]["catalog"]["term"]="Wrong term"
        if change=="population":
            state=legacy.decode_graph(payload["graph"]);state["population"].pop();payload["graph"]=legacy.encode_graph(state)
        if change!="checksum":envelope["sha256"]=hashlib.sha256(legacy.canonical(payload)).hexdigest()
        path.write_bytes(gzip.compress(legacy.canonical(envelope)))
    with pytest.raises((constraints.ConstraintError,ValueError)):
        payload,pinned,state=store.read(run_id)
        engine.validate_state(state,pinned,inputs)


def test_last_moment_revocation_keeps_previous_checkpoint_atomic(inputs):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot);run_id=str(uuid4())
    params=Parameters(population_size=2,generations=1,crossover_attempts=1,max_restarts=2,mutation_attempts=1)
    execute(inputs,snapshot,params,authority,run_id,pause_at=0)
    before=store.path_for(run_id).read_bytes();_,_,state=store.read(run_id)
    def deny(expected):constraints.reject("EVIDENCE_NOT_CURRENT","Fictional authority lost at the final atomic commit gate.")
    authority.recheck=deny
    with pytest.raises(constraints.ConstraintError):execute(inputs,snapshot,params,authority,run_id,state=state)
    assert store.path_for(run_id).read_bytes()==before and not list(store.STORE.rglob("*.tmp"))


def test_initial_conflict_replacement_produces_exact_valid_population(inputs):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot);bad=arranged(inputs);calls=[];run_id=str(uuid4())
    def sometimes(values,restarts):
        calls.append(1)
        return copy.deepcopy(bad) if len(calls)==1 else engine.construct(values,restarts)
    params=Parameters(population_size=2,generations=1,fresh_chromosomes=0,crossover_attempts=1,max_restarts=2,mutation_attempts=1,candidate_attempts=3)
    execute(inputs,snapshot,params,authority,run_id,factory=sometimes)
    _,_,state=store.read(run_id)
    assert len(calls)==3 and len(state["population"])==2
    assert state["diagnostics"]["construction:EXTERNAL_SECTION_CONFLICT"]==1


def test_candidate_profile_and_frozen_fitness_tampering_rejected(inputs):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot);run_id=str(uuid4())
    params=Parameters(population_size=2,generations=1,crossover_attempts=1,max_restarts=2,mutation_attempts=1)
    execute(inputs,snapshot,params,authority,run_id,pause_at=0)
    _,_,state=store.read(run_id)
    for field,value in [("settings",{}),("preferences",{})]:
        changed=copy.deepcopy(state)
        # Ensure an actual material change, rather than asserting on an already empty fixture.
        changed["scoring_inputs"][field]={"unrecognized_fictional_override":value}
        with pytest.raises(constraints.ConstraintError):engine.validate_state(changed,snapshot,inputs)
    changed=copy.deepcopy(state);changed["population"][0][0].assigned_faculty.eligible_subjects=set()
    with pytest.raises(constraints.ConstraintError):engine.validate_state(changed,snapshot,inputs)


def test_fresh_python_process_restores_v2_checkpoint(inputs,tmp_path):
    snapshot=snapshot_for(inputs);authority=FictionalAuthority(snapshot);run_id=str(uuid4())
    params=Parameters(population_size=2,generations=1,crossover_attempts=1,max_restarts=2,mutation_attempts=1)
    execute(inputs,snapshot,params,authority,run_id,pause_at=0)
    original=store.path_for(run_id).read_bytes();_,_,state=store.read(run_id)
    copied=tmp_path/"private-child-v2"
    shutil.copytree(store.STORE,copied)
    env={k:v for k,v in os.environ.items() if k.upper() in {"PATH","SYSTEMROOT","WINDIR","TEMP","TMP","USERPROFILE","APPDATA","LOCALAPPDATA","COMSPEC","PATHEXT"}}
    env.update(PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",PYTHONIOENCODING="utf-8")
    result=subprocess.run([sys.executable,"-B","-m","tests.d10.resume_v2_child",str(copied),run_id],capture_output=True,text=True,env=env,timeout=30)
    assert result.returncode==0,"Fresh-process V2 continuation failed"
    child=json.loads(result.stdout);assert child["status"]=="COMPLETED"
    assert store.path_for(run_id).read_bytes()==original
    execute(inputs,snapshot,params,authority,run_id,state=state)
    final,_,_=store.read(run_id)
    assert child["result_sha256"]==hashlib.sha256(legacy.canonical(final["result"])).hexdigest()


def test_real_original_crossover_improvement_cannot_bypass_external_admission(inputs):
    from genetic_algorithm.models.Faculty import Faculty
    from genetic_algorithm.utils.FrozenInputs import scoring_inputs
    values=(inputs[0],[Faculty(990001,1,admin_load=20,eligible_subjects={"SYN101","SYN102"}),
                       Faculty(990002,1,admin_load=24,eligible_subjects={"SYN101","SYN102"})],inputs[2])
    snapshot=snapshot_for(values,sections=("section-b",),faculty="faculty-a",room=None)
    working=constraints.reduced_templates(snapshot,values)
    def parent(first):
        subjects,faculty,rooms=copy.deepcopy(working)
        arrangements=[(1,"M","9:30 - 11:30"),(0,"T","7:30 - 9:30")] if first else [(0,"T","7:30 - 9:30"),(1,"T","9:30 - 11:30")]
        for subject,(who,day,period) in zip(subjects,arrangements):
            assert engine.schedule.assign_schedule_to_faculty(faculty[who],subject,(period,day),"Lecture",room_list=rooms,list_subjects=subjects)
        engine.admit(subjects,snapshot,working)
        return subjects
    left,right=parent(True),parent(False)
    original_rng=random.getstate();token=scoring_inputs.set(engine.freeze(values))
    try:
        random.seed(701)
        bad=engine.create_child_by_faculty_swap(parent1=left,parent2=right,df_faculty_pref=preferences(),max_attempts=20)
        assert bad is not None and constraints.external_conflict(bad,snapshot)=="EXTERNAL_FACULTY_CONFLICT"
        bad_score=engine.faculty_preference_fitness(bad,preferences())
    finally:
        scoring_inputs.reset(token);random.setstate(original_rng)
    choices=iter([bad,left,right])
    params=Parameters(population_size=2,generations=1,fresh_chromosomes=0,candidate_attempts=3,crossover_attempts=1,mutation_attempts=1)
    authority=FictionalAuthority(snapshot);run_id=str(uuid4())
    execute(values,snapshot,params,authority,run_id,pause_at=0,factory=lambda *args:copy.deepcopy(next(choices)))
    _,_,state=store.read(run_id)
    assert state["diagnostics"]["construction:EXTERNAL_FACULTY_CONFLICT"]==1
    assert state["best_fitness"]>bad_score
    execute(values,snapshot,params,authority,run_id,state=state)
    _,_,finished=store.read(run_id)
    assert all(constraints.external_conflict(c,snapshot) is None for c in [*finished["population"],finished["best"]])


@pytest.mark.parametrize("case,code",[("capacity","INPUT_CAPACITY_REJECTED"),("pattern","UNSUPPORTED_COMPONENT")])
def test_invalid_input_is_distinct_from_search_exhaustion(inputs,case,code):
    values=copy.deepcopy(inputs)
    if case=="capacity":values[0][0].credit_units=81
    else:values[0][0].lec_hours=1
    snapshot=snapshot_for(values)
    with pytest.raises(constraints.ConstraintError) as caught:
        engine.run(values,snapshot,Parameters(population_size=2,generations=1),preferences(),lambda state:pytest.fail("Invalid inputs cannot publish"))
    assert caught.value.code==code and not store.STORE.exists()
