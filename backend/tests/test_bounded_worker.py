"""Actual process/SQLite worker acceptance; exclusively fictional owned sources."""
from dataclasses import replace
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from uuid import uuid4
import pytest
from services.ga_worker_contract import Limits,Job,VERSION,fictional_source
from services.ga_bounded_worker import Worker
from services.ga_trusted_runs import Coordinator,Capture,configured_service
from services.ga_owned_store import Store
from services.ga_run_authority import RunError
from services.preference_authorization import PreferencePrincipal
from tests.trusted_run_support import ACTOR,OTHER,DEPT,OTHER_DEPT,CATALOG,PRINCIPAL,FictionalSource,FictionalAuthority
from tests.bounded_worker_support import dependencies
from services.chromosome_service import save_best_if_better as ORIGINAL_SAVE_BEST

@pytest.fixture
def fixture(monkeypatch):
    fictional_source()
    from sqlalchemy.engine import Engine
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Institutional database forbidden'))
    from services import chromosome_service,ga_checkpoint_service
    def no_write(*_a,**_k):pytest.fail('Application persistence forbidden')
    monkeypatch.setattr(chromosome_service,'save_best_if_better',no_write)
    monkeypatch.setattr(ga_checkpoint_service,'save_checkpoint',no_write)
    made=[]
    def make(generations=0,limits=None,prepared=None):
        authority,source,verifier=dependencies(generations,prepared)
        store=Store.create(max_runs=4);coordinator=Coordinator(store,authority,source)
        worker=Worker(coordinator,initialize=True);made.append(worker)
        run=worker.admit(PRINCIPAL,DEPT,str(uuid4()),CATALOG,limits or Limits())['run_id']
        return worker,run,verifier
    yield make
    for worker in made:assert worker.close(PRINCIPAL,timeout=130)['quiescent']

def until(worker,run,states,timeout=130):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        status=worker.wait(PRINCIPAL,run,.1)
        if status['state'] in states:return status
    pytest.fail('Owned worker did not reach expected durable state: '+str(status))

def test_actual_process_initialization_completion_zero_and_cleanup(fixture):
    w,run,_=fixture();before=random.getstate()
    assert w.start(PRINCIPAL,run)['state'] in {'RUNNING','COMPLETED'}
    s=until(w,run,{'COMPLETED','FAILED'});assert s['state']=='COMPLETED',json.dumps(s)
    assert s['best_fitness']==0 and s['checkpoint_sequence']==1 and s['initialized']
    assert not s['publication'] and not s['saved_best_promotion'] and configured_service() is None
    assert random.getstate()==before and w.cleanup[run]

def test_pause_resume_exact_saved_population_and_rng(fixture):
    w,run,_=fixture(generations=1)
    with w.store.base.connection() as db:row=w.coordinator.owned(db,ACTOR,run)
    oracle=w.coordinator._session(row);expected=oracle.run();rng=oracle.runtime.random.getstate()
    w.start(PRINCIPAL,run);w.command(PRINCIPAL,run,'pause')
    paused=until(w,run,{'PAUSED','FAILED','COMPLETED'});assert paused['state']=='PAUSED',paused
    doc=w.checkpoint(PRINCIPAL,run)
    assert doc['owner']==ACTOR and doc['department']==DEPT and doc['fence']==paused['fence']
    again=Worker(Coordinator(Store(w.store.base.root,w.store.base.store_id,max_runs=4),w.coordinator.authority,w.coordinator.source))
    again.resume(PRINCIPAL,run)
    done=until(again,run,{'COMPLETED','FAILED'});assert done['state']=='COMPLETED',done
    actual=again.result(PRINCIPAL,run)
    for key in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']:assert actual[key]==expected[key]
    with again.store.base.connection() as db:
        row=again.store.row(db,ACTOR,run);doc,raw=again.store.checkpoint(db,row)
    assert again._validate(row,doc,raw).resume_state['random_state']==rng
    assert again.close(PRINCIPAL)['quiescent']

def test_stop_at_boundary_preserves_best_and_idempotent_commands(fixture):
    w,run,_=fixture(generations=1);w.start(PRINCIPAL,run)
    first=w.command(PRINCIPAL,run,'stop');assert first['state'] in {'STOPPING','STOPPED'}
    w.command(PRINCIPAL,run,'stop')
    s=until(w,run,{'STOPPED','FAILED'});assert s['state']=='STOPPED',s
    assert s['checkpoint_sequence']>=1 and s['best_fitness'] is not None
    assert w.command(PRINCIPAL,run,'stop')['best_chromosome_id']==s['best_chromosome_id']
    with pytest.raises(RunError,match='TERMINAL'):w.resume(PRINCIPAL,run)

def test_illegal_transition_and_created_stop_without_fabricated_best(fixture):
    w,run,_=fixture()
    with pytest.raises(RunError,match='TRANSITION_INVALID'):w.command(PRINCIPAL,run,'pause')
    with pytest.raises(RunError,match='TRANSITION_INVALID'):w.resume(PRINCIPAL,run)
    assert w.command(PRINCIPAL,run,'stop')['state']=='STOPPED'
    assert w.status(PRINCIPAL,run)['best_fitness'] is None
    with pytest.raises(RunError,match='TERMINAL'):w.start(PRINCIPAL,run)

@pytest.mark.parametrize('field,value',[('batch_generations',0),('total_generations',21),('wall_seconds',0),('memory_bytes',512*1024*1024),('cpu_seconds',1)])
def test_unsupported_or_invalid_limits_reject(field,value):
    with pytest.raises(RunError):replace(Limits(),**{field:value}).validate()

def test_generation_ceiling_and_active_worker_cap(fixture):
    with pytest.raises(RunError,match='FIXTURE_LIMIT_EXCEEDED'):fixture(generations=2,limits=Limits(total_generations=1))
    w,run,_=fixture(generations=1)
    second=w.admit(PRINCIPAL,DEPT,str(uuid4()),CATALOG)['run_id'];w.start(PRINCIPAL,run)
    with pytest.raises(RunError,match='ACTIVE_LIMIT'):w.start(PRINCIPAL,second)
    # Repeated start is an observation, not a second ownership claim/thread.
    fence=w.status(PRINCIPAL,run)['fence'];w.start(PRINCIPAL,run)
    assert w.status(PRINCIPAL,run)['fence']==fence
    w.command(PRINCIPAL,run,'stop');assert until(w,run,{'STOPPED','FAILED'})['state']=='STOPPED'

@pytest.mark.parametrize('action',['status','start','resume','checkpoint','result','pause','stop'])
def test_unauthorized_owner_never_retrieves_or_advances(fixture,action):
    w,run,_=fixture();other=PreferencePrincipal('admin',user_id=OTHER)
    with pytest.raises(RunError,match='NOT_FOUND'):
        if action in {'pause','stop'}:w.command(other,run,action)
        else:getattr(w,action)(other,run)

def test_revoked_and_cross_department_authority(fixture):
    w,run,a=fixture();a.revoked=True
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):w.start(PRINCIPAL,run)
    a.revoked=False
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):w.admit(PRINCIPAL,OTHER_DEPT,str(uuid4()),CATALOG)

def test_checkpoint_size_and_stored_bytes_limits(fixture):
    w,run,_=fixture(limits=Limits(checkpoint_bytes=1));w.start(PRINCIPAL,run)
    s=until(w,run,{'FAILED'});assert s['reason']=='GA_WORKER_CHECKPOINT_SIZE_LIMIT'
    assert s['checkpoint_sequence']==0
    with pytest.raises(RunError,match='STORED_BYTES_LIMIT'):fixture(limits=Limits(run_bytes=1))

def test_native_blocking_child_is_killed_at_wall_deadline(fixture,monkeypatch):
    import services.ga_bounded_worker as module
    w,run,_=fixture(limits=Limits(wall_seconds=5));original=module.subprocess.Popen;children=[]
    def blocked(command,**kw):
        child=original([getattr(sys,'_base_executable',sys.executable),'-I','-B','-c','import sys,ctypes;sys.stdin.buffer.readline();ctypes.windll.kernel32.Sleep(60000)'],**kw)
        children.append(child);return child
    monkeypatch.setattr(module.subprocess,'Popen',blocked)
    start=time.monotonic();w.start(PRINCIPAL,run);s=until(w,run,{'FAILED'},timeout=15)
    assert s['reason']=='GA_WORKER_TIME_BUDGET' and time.monotonic()-start<15
    assert children and all(c.poll() is not None for c in children) and w.cleanup[run]

def test_broken_job_protection_blocks_computation(fixture,monkeypatch):
    import services.ga_bounded_worker as module
    w,run,_=fixture()
    def no_job(*_a,**_kw):raise RunError('GA_WORKER_JOB_UNAVAILABLE',503)
    monkeypatch.setattr(module,'Job',no_job);w.start(PRINCIPAL,run)
    assert until(w,run,{'FAILED'})['reason']=='GA_WORKER_JOB_UNAVAILABLE'

def test_storage_write_failure_keeps_previous_checkpoint(fixture,monkeypatch):
    w,run,_=fixture(generations=1);w.start(PRINCIPAL,run);w.command(PRINCIPAL,run,'pause')
    paused=until(w,run,{'PAUSED','FAILED'});assert paused['state']=='PAUSED',paused
    old=w.checkpoint(PRINCIPAL,run)
    def fail(*_a,**_kw):raise RunError('FICTIONAL_STORAGE_WRITE_FAILED')
    monkeypatch.setattr(w.store,'save',fail);w.resume(PRINCIPAL,run)
    assert until(w,run,{'FAILED'})['reason']=='FICTIONAL_STORAGE_WRITE_FAILED'
    assert w.checkpoint(PRINCIPAL,run)==old

def test_retention_cap_and_corruption_fail_closed(fixture):
    w,run,_=fixture(generations=1,limits=Limits(retained_checkpoints=1));w.start(PRINCIPAL,run)
    s=until(w,run,{'FAILED'});assert s['reason']=='GA_WORKER_CHECKPOINT_RETENTION_LIMIT',s
    assert s['checkpoint_sequence']==1 and s['best_fitness'] is not None
    with w.store.base.transaction() as db:db.execute('UPDATE worker_checkpoints SET raw=? WHERE run=?',(b'corrupt',run))
    with pytest.raises(RunError,match='CORRUPT'):w.checkpoint(PRINCIPAL,run)

def test_fresh_process_observes_retained_pause_and_validated_checkpoint(fixture):
    w,run,_=fixture(generations=1);w.start(PRINCIPAL,run);w.command(PRINCIPAL,run,'pause')
    assert until(w,run,{'PAUSED','FAILED'})['state']=='PAUSED'
    code='''from services.ga_bounded_worker import Worker
from services.ga_owned_store import Store
from services.ga_trusted_runs import Coordinator
from tests.trusted_run_support import *
from tests.bounded_worker_support import dependencies
import sys
a,c,_=dependencies(1)
w=Worker(Coordinator(Store(sys.argv[1],sys.argv[2],max_runs=4),a,c))
assert w.status(PRINCIPAL,sys.argv[3])['state']=='PAUSED'
assert w.checkpoint(PRINCIPAL,sys.argv[3])['run']==sys.argv[3]
w.resume(PRINCIPAL,sys.argv[3])
import time
end=time.monotonic()+120
while time.monotonic()<end and w.wait(PRINCIPAL,sys.argv[3],.1)['state'] not in {'COMPLETED','FAILED'}:pass
assert w.status(PRINCIPAL,sys.argv[3])['state']=='COMPLETED'
assert w.close(PRINCIPAL)['quiescent']
print('FRESH_PROCESS_CHECKPOINT_VERIFIED')
'''
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    result=subprocess.run([sys.executable,'-B','-c',code,str(w.store.base.root),w.store.base.store_id,run],
        env={k:v for k,v in os.environ.items() if k.upper() in allowed},capture_output=True,text=True,timeout=130)
    assert result.returncode==0,result.stderr
    assert 'FRESH_PROCESS_CHECKPOINT_VERIFIED' in result.stdout

def test_expired_owner_is_fenced_and_explicit_recovery_advances(fixture):
    w,run,_=fixture(generations=1);w.start(PRINCIPAL,run);w.command(PRINCIPAL,run,'pause')
    assert until(w,run,{'PAUSED','FAILED'})['state']=='PAUSED'
    with w.store.base.connection() as db:row=w.store.row(db,ACTOR,run);doc,inner=w.store.checkpoint(db,row)
    old_owner='FICTIONAL-CRASHED-SUPERVISOR'
    _,old_fence=w.store.claim(PRINCIPAL,run,old_owner,resume=True,expected_tip=row['tip'])
    with w.store.base.transaction() as db:db.execute('UPDATE runs SET lease=? WHERE id=?',(time.time()-1,run))
    assert w.status(PRINCIPAL,run)['recovery_required']
    with pytest.raises(RunError,match='RECOVERY_DECISION_REQUIRED'):w.resume(PRINCIPAL,run)
    w.resume(PRINCIPAL,run,recover=True)
    with pytest.raises(RunError,match='OWNERSHIP_LOST'):
        w.store.save(PRINCIPAL,run,old_owner,old_fence,inner,w.result(PRINCIPAL,run),0,doc['inner_parent'])
    w._fail(PRINCIPAL,run,old_owner,old_fence,'STALE_FAILURE_MUST_NOT_WIN')
    s=until(w,run,{'COMPLETED','FAILED'});assert s['state']=='COMPLETED',json.dumps(s)
    assert s['fence']>old_fence

def test_interrupted_run_without_checkpoint_cannot_be_reinitialized(fixture):
    w,run,_=fixture();w.store.claim(PRINCIPAL,run,'FICTIONAL-CRASH',expected_tip=None)
    with w.store.base.transaction() as db:db.execute('UPDATE runs SET lease=? WHERE id=?',(time.time()-1,run))
    with pytest.raises(RunError,match='CHECKPOINT_MISSING'):w.resume(PRINCIPAL,run,recover=True)

def test_partial_checkpoint_transaction_rolls_back_tip_and_best(fixture,monkeypatch):
    w,run,_=fixture(generations=1);w.start(PRINCIPAL,run);w.command(PRINCIPAL,run,'pause')
    assert until(w,run,{'PAUSED','FAILED'})['state']=='PAUSED'
    old=w.checkpoint(PRINCIPAL,run);best=w.result(PRINCIPAL,run);event=w.store.event;once=[]
    def fail_after_update(db,row,state,reason=None):
        event(db,row,state,reason)
        if not once and reason in {'BATCH_CHECKPOINT','GENERATION_CEILING'}:
            once.append(True);raise RunError('FICTIONAL_TRANSACTION_ABORT')
    monkeypatch.setattr(w.store,'event',fail_after_update);w.resume(PRINCIPAL,run)
    s=until(w,run,{'FAILED'});assert s['reason']=='FICTIONAL_TRANSACTION_ABORT'
    assert w.checkpoint(PRINCIPAL,run)==old and w.result(PRINCIPAL,run)==best

def test_cross_run_checkpoint_cannot_restore_another_bundle(fixture):
    w,first,_=fixture();w.start(PRINCIPAL,first);assert until(w,first,{'COMPLETED','FAILED'})['state']=='COMPLETED'
    second=w.admit(PRINCIPAL,DEPT,str(uuid4()),CATALOG)['run_id']
    with w.store.base.connection() as db:
        a=w.store.row(db,ACTOR,first);b=w.store.row(db,ACTOR,second);doc,inner=w.store.checkpoint(db,a)
    with pytest.raises(ValueError):w._validate(b,doc,inner)

def test_windows_job_kills_owned_native_child_when_supervisor_process_dies(tmp_path):
    """Actual process-exit test, not a timeout/GC/thread-level claim."""
    import ctypes
    from ctypes import wintypes
    code='''import sys,subprocess,os
from services.ga_worker_contract import Job,fictional_source
fictional_source()
p=subprocess.Popen([getattr(sys,'_base_executable',sys.executable),'-I','-B','-c','import ctypes;ctypes.windll.kernel32.Sleep(60000)'],creationflags=subprocess.CREATE_NO_WINDOW)
job=Job(p)
print(p.pid,flush=True)
sys.stdin.readline()
os._exit(23)
'''
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    parent=subprocess.Popen([sys.executable,'-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        env={k:v for k,v in os.environ.items() if k.upper() in allowed},text=True)
    handle=None;kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    try:
        line=parent.stdout.readline();assert line.strip().isdigit()
        handle=kernel.OpenProcess(0x100000,False,int(line));assert handle
        parent.stdin.write('terminate supervisor\n');parent.stdin.flush();assert parent.wait(10)==23
        assert kernel.WaitForSingleObject(handle,5000)==0
    finally:
        if parent.poll() is None:parent.terminate();parent.wait(5)
        if handle:kernel.CloseHandle(handle)
        for stream in [parent.stdin,parent.stdout,parent.stderr]:stream.close()

def test_control_metadata_quota_rolls_back_without_false_ack(fixture,monkeypatch):
    w,run,_=fixture()
    with w.store.base.connection() as db:
        before=db.execute('SELECT COUNT(*) FROM worker_events').fetchone()[0]
    original=w.store.size
    monkeypatch.setattr(w.store,'size',lambda db,run=None:w.store.base.max_bytes)
    with pytest.raises(RunError,match='STORED_BYTES_LIMIT'):w.command(PRINCIPAL,run,'stop')
    monkeypatch.setattr(w.store,'size',original)
    assert w.status(PRINCIPAL,run)['state']=='CREATED'
    with w.store.base.connection() as db:
        assert db.execute('SELECT COUNT(*) FROM worker_events').fetchone()[0]==before


def test_named_jobs_enforce_cross_supervisor_process_cap():
    from services.ga_worker_contract import Job
    # Actual OS process admission, independent of the SQLite lease count.
    processes=[];jobs=[];store=uuid4().hex;run=uuid4().hex
    try:
        for _ in range(2):
            processes.append(subprocess.Popen([getattr(sys,'_base_executable',sys.executable),'-I','-B','-c',
                'import ctypes;ctypes.windll.kernel32.Sleep(60000)'],creationflags=subprocess.CREATE_NO_WINDOW))
        jobs.append(Job(processes[0],store_id=store,run_id=run,max_workers=1))
        with pytest.raises(RunError,match='GA_WORKER_JOB_UNAVAILABLE'):
            Job(processes[1],store_id=store,run_id=run,max_workers=1)
        assert processes[0].poll() is None
    finally:
        for job in jobs:job.close()
        for process in processes:
            if process.poll() is None:process.terminate()
            process.wait(5)


def test_nonzero_fitness_original_fixed_engine_parity(fixture,monkeypatch,tmp_path):
    from services import ga_service as engine,ga_checkpoint_service as cp,chromosome_service,ga_trusted_runs
    from genetic_algorithm.utils import Functions
    from genetic_algorithm.utils.FrozenInputs import capture_inputs
    from genetic_algorithm.operators import FitnessFunction
    from services.ga_input_bundle import capture
    from tests.d10.support import templates,preferences
    models=templates(compact=True);frame=preferences()
    pref=tmp_path/'FICTIONAL-preferences.json';settings=tmp_path/'FICTIONAL-settings.json'
    pref.write_text(json.dumps([{'faculty_code':f.code,'faculty_priority':1,'use_subject_preference':True,'subject_importance':5,
        'preferred_subjects':['SYN101'],'use_day_preference':False,'use_time_preference':False,'use_gap_preference':False} for f in models[1]]))
    settings.write_text(json.dumps({'subject_penalty':91,'day_penalty':37,'time_penalty':41}))
    for owner,name,value in [(engine,'FACULTY_PREFERENCES_FILE',pref),(engine,'GA_SETTINGS_FILE',settings),
        (FitnessFunction,'PREFERENCE_FILE',pref),(FitnessFunction,'GA_SETTINGS_FILE',settings),
        (chromosome_service,'BEST_CHROMOSOME_PATH',tmp_path/'FICTIONAL-oracle-best.json')]:monkeypatch.setattr(owner,name,value)
    monkeypatch.setattr(engine,'save_best_if_better',ORIGINAL_SAVE_BEST)
    for name,value in zip(['list_subjects','list_faculty','lst_rooms'],models):monkeypatch.setattr(engine,name,value)
    monkeypatch.setattr(Functions,'list_faculty',models[1]);monkeypatch.setattr(engine,'df_faculty_pref',frame)
    configuration=dict(population_size=2,generations=1,fresh_chromosomes=0,baseline_mode='fresh',mutation_attempts=1,max_restarts=5)
    prepared=capture(run_id='00000000-0000-4000-8000-000000000973',templates=models,fallback_templates=models,
        legacy_preferences=frame,scoring_context=capture_inputs(),configuration=configuration,
        source_identities=dict(dataset=cp.input_fingerprint(),engine=cp.engine_fingerprint(),loader='c'*64,transformation='d'*64))
    prior=random.getstate()
    try:
        random.seed(710);expected=engine.run_genetic_algorithm(**configuration);expected_rng=random.getstate()
        assert expected['best_fitness']>0
        random.setstate(prior);monkeypatch.setattr(ga_trusted_runs.secrets,'randbits',lambda _:710)
        w,run,_=fixture(generations=1,prepared=prepared);w.start(PRINCIPAL,run)
        status=until(w,run,{'COMPLETED','FAILED'});assert status['state']=='COMPLETED',json.dumps(status)
        actual=w.result(PRINCIPAL,run)
        for key in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']:assert actual[key]==expected[key]
        history=[r.get('best_ever_fitness',r.get('best_fitness')) for r in actual['history']]
        assert history==sorted(history,reverse=True) and random.getstate()==prior
        with w.store.base.connection() as db:row=w.store.row(db,ACTOR,run);doc,raw=w.store.checkpoint(db,row)
        assert w._validate(row,doc,raw).resume_state['random_state']==expected_rng
        if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
            target=Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/'U5K-nonzero-worker-parity.json'
            with target.open('x',encoding='utf-8') as f:json.dump({'scope':'Fictional original fixed engine versus process-batched worker; not institutional acceptance',
                'original_fitness':expected['best_fitness'],'worker_fitness':actual['best_fitness'],
                'fitness_breakdown':actual['fitness_breakdown'],'history':actual['history'],
                'schedule_fitness_history_breakdown_faculty_and_rng_equal':True,'global_rng_unchanged':True,
                'saved_best_promotion':False,'checkpoint_sequence':status['checkpoint_sequence']},f,indent=2)
    finally:random.setstate(prior)
