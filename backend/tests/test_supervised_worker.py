"""Actual Windows/SQLite fictional acceptance plus explicit fault injection."""
from dataclasses import replace
import json
import hashlib
import os
from pathlib import Path
import random
import sqlite3
import stat
import subprocess
import sys
import time
from uuid import uuid4
import pytest
from services.ga_supervised_worker import Worker
from services.ga_supervised_storage import StorageLimits
from services.ga_windows_supervisor import Resources,alive
from services.ga_owned_store import Store
from services.ga_trusted_runs import Coordinator
from services.ga_worker_contract import Limits,fictional_source
from services.ga_run_authority import RunError,canonical
from tests.bounded_worker_support import dependencies
from tests.trusted_run_support import ACTOR,DEPT,CATALOG,PRINCIPAL
from tests.test_bounded_worker import until
from tests import test_bounded_worker as checks

@pytest.fixture
def fixture(monkeypatch,request):
    fictional_source()
    from sqlalchemy.engine import Engine
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Institutional database forbidden'))
    made=[]
    def make(generations=0,limits=None,prepared=None,resources=Resources(),storage=StorageLimits()):
        authority,source,verifier=dependencies(generations,prepared)
        w=Worker(Coordinator(Store.create(max_runs=4),authority,source),initialize=True,resources=resources,storage=storage);made.append(w)
        run=w.admit(PRINCIPAL,DEPT,str(uuid4()),CATALOG,limits or Limits())['run_id']
        return w,run,verifier
    yield make
    observations=[]
    for w in made:
        assert w.close(PRINCIPAL,timeout=130)['quiescent']
        with w.storage.connection() as db:
            observations.extend(json.loads(p[0]) for p in db.execute('SELECT observation FROM l_processes WHERE observation IS NOT NULL'))
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        p=Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/('U5L-'+request.node.name+'.json')
        with p.open('x',encoding='utf-8') as f:json.dump(dict(scope='Fictional owned Windows optimizer processes; no institutional acceptance',observations=observations),f,indent=2)

# Reuse the original assertions with this module's physically supervised fixture.
test_start_zero_original_behavior=checks.test_actual_process_initialization_completion_zero_and_cleanup
test_nonzero_original_fixed_ga_parity=checks.test_nonzero_fitness_original_fixed_engine_parity
test_stop_idempotent_preserves_best=checks.test_stop_at_boundary_preserves_best_and_idempotent_commands
test_invalid_transitions=checks.test_illegal_transition_and_created_stop_without_fabricated_best
test_generation_and_active_limits=checks.test_generation_ceiling_and_active_worker_cap
test_owner_authorization=checks.test_unauthorized_owner_never_retrieves_or_advances
test_revoked_cross_department=checks.test_revoked_and_cross_department_authority
test_partial_checkpoint_transaction_rollback=checks.test_partial_checkpoint_transaction_rolls_back_tip_and_best
test_write_failure_old_checkpoint=checks.test_storage_write_failure_keeps_previous_checkpoint
test_checkpoint_retention_and_corruption=checks.test_retention_cap_and_corruption_fail_closed
test_cross_run_checkpoint_rejected=checks.test_cross_run_checkpoint_cannot_restore_another_bundle
test_expired_lease_stale_writer_fenced=checks.test_expired_owner_is_fenced_and_explicit_recovery_advances
test_missing_checkpoint_never_reinitialized=checks.test_interrupted_run_without_checkpoint_cannot_be_reinitialized
test_metadata_quota_rollback=checks.test_control_metadata_quota_rolls_back_without_false_ack

def paused(fixture,generations=1):
    w,run,v=fixture(generations=generations);w.start(PRINCIPAL,run);w.command(PRINCIPAL,run,'pause')
    assert until(w,run,{'PAUSED','FAILED'})['state']=='PAUSED'
    return w,run,v

def test_restart_recovery_and_two_batches_match_uninterrupted_rng(fixture):
    w,run,_=fixture(generations=2)
    with w.storage.connection() as db:row=w.coordinator.owned(db,ACTOR,run)
    oracle=w.coordinator._session(row);expected=oracle.run();rng=oracle.runtime.random.getstate()
    w.start(PRINCIPAL,run);w.command(PRINCIPAL,run,'pause');assert until(w,run,{'PAUSED','FAILED'})['state']=='PAUSED'
    a,c,_=dependencies(2);again=Worker(Coordinator(Store(w.storage.root,w.storage.store_id,max_runs=4),a,c))
    again.resume(PRINCIPAL,run);done=until(again,run,{'COMPLETED','FAILED'});assert done['state']=='COMPLETED',done
    result=again.result(PRINCIPAL,run)
    for k in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']:assert result[k]==expected[k]
    with again.storage.connection() as db:r=again.store.row(db,ACTOR,run);doc,raw=again.store.checkpoint(db,r)
    assert again._validate(r,doc,raw).resume_state['random_state']==rng
    assert done['checkpoint_sequence']==3 and again.close(PRINCIPAL)['quiescent']

def blocking_arguments(backend):
    return [getattr(sys,'_base_executable',sys.executable),'-I','-B','-c','import sys,ctypes;sys.stdin.buffer.readline();ctypes.windll.kernel32.Sleep(60000)']

def test_forced_native_termination_recovers_pinned_best(fixture,monkeypatch):
    import services.ga_supervised_worker as module
    w,run,_=paused(fixture);old=w.checkpoint(PRINCIPAL,run);best=w.result(PRINCIPAL,run);original=module.arguments
    monkeypatch.setattr(module,'arguments',blocking_arguments);w.resume(PRINCIPAL,run)
    end=time.monotonic()+15
    while time.monotonic()<end:
        p=w.processes.get(run)
        if p and p.handle and p.poll() is None:break
        time.sleep(.02)
    else:pytest.fail('No owned native child observed')
    p.terminate();s=until(w,run,{'FAILED'});assert s['reason']=='GA_SUPERVISION_CHILD_CRASH'
    assert w.checkpoint(PRINCIPAL,run)==old and w.result(PRINCIPAL,run)==best
    monkeypatch.setattr(module,'arguments',original)
    with pytest.raises(RunError,match='RECOVERY_STALE'):w.recover(PRINCIPAL,run,expected_tip='0'*64,expected_fence=s['fence'])
    w.recover(PRINCIPAL,run,expected_tip=hashlib.sha256(canonical(old)).hexdigest(),expected_fence=s['fence'])
    assert until(w,run,{'COMPLETED','FAILED'})['state']=='COMPLETED'

def test_native_wall_timeout_stops_owned_computation(fixture,monkeypatch):
    import services.ga_supervised_worker as module
    w,run,_=fixture(limits=Limits(wall_seconds=5));monkeypatch.setattr(module,'arguments',blocking_arguments)
    w.start(PRINCIPAL,run);s=until(w,run,{'FAILED'},timeout=20)
    assert s['reason']=='GA_WORKER_TIME_BUDGET' and w.cleanup[run]
    with w.storage.connection() as db:
        p=db.execute('SELECT * FROM l_processes WHERE run=?',(run,)).fetchone()
    assert p['status']=='EXIT_VERIFIED' and not alive(p['pid'],p['created'])

def test_crash_during_initialization_has_no_fabricated_checkpoint(fixture,monkeypatch):
    import services.ga_supervised_worker as module
    w,run,_=fixture();monkeypatch.setattr(module,'arguments',lambda _: [getattr(sys,'_base_executable',sys.executable),'-I','-B','-c','import os;os._exit(87)'])
    w.start(PRINCIPAL,run);s=until(w,run,{'FAILED'})
    assert s['checkpoint_sequence']==0 and s['best_fitness'] is None
    with pytest.raises(RunError,match='CHECKPOINT_MISSING'):w.recover(PRINCIPAL,run,expected_tip=None,expected_fence=s['fence'])

def test_sqlite_page_quota_real_full_rollback(fixture):
    w,run,_=paused(fixture);old=w.checkpoint(PRINCIPAL,run)
    with pytest.raises(RunError,match='TRANSACTION_FAILED'):
        with w.storage.transaction() as db:
            db.execute('CREATE TABLE fictional_pressure(payload BLOB)')
            db.execute('INSERT INTO fictional_pressure VALUES(zeroblob(?))',(w.storage.limits.database_bytes,))
    assert w.checkpoint(PRINCIPAL,run)==old
    with w.storage.connection() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='fictional_pressure'").fetchone()
    assert (w.storage.root/'records.sqlite3').stat().st_size<=w.storage.limits.database_bytes

def test_parent_interruption_real_checkpoint_and_explicit_fresh_recovery(fixture):
    w,run,_=paused(fixture);old=w.checkpoint(PRINCIPAL,run);best=w.result(PRINCIPAL,run)
    code='''import sys,os,time
wire=sys.stdout
class Discard:
 def write(self,s):return len(s)
 def flush(self):pass
sys.stdout=Discard()
from services.ga_supervised_worker import Worker
from services.ga_trusted_runs import Coordinator
from services.ga_owned_store import Store
from tests.bounded_worker_support import dependencies
from tests.trusted_run_support import PRINCIPAL
from tests.test_supervised_worker import blocking_arguments
import services.ga_supervised_worker as module
a,c,_=dependencies(1)
w=Worker(Coordinator(Store(sys.argv[1],sys.argv[2],max_runs=4),a,c))
module.arguments=blocking_arguments
w.resume(PRINCIPAL,sys.argv[3])
end=time.monotonic()+20
while time.monotonic()<end:
 p=w.processes.get(sys.argv[3])
 with w.storage.connection() as db:
  registered=db.execute("SELECT pid FROM l_processes WHERE run=? AND status='ACTIVE'",(sys.argv[3],)).fetchone()
 if p and p.handle and p.poll() is None and registered and registered[0]==p.pid:break
 time.sleep(.01)
else:raise RuntimeError('Owned process not observed')
wire.write('SUPERVISED_READY\\n');wire.flush()
sys.stdin.readline()
os._exit(23)
'''
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}}
    parent=subprocess.Popen([sys.executable,'-B','-c',code,str(w.storage.root),w.storage.store_id,run],env=env,
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    try:
        assert parent.stdout.readline().strip()=='SUPERVISED_READY'
        parent.stdin.write('simulate supervisor crash\n');parent.stdin.flush();assert parent.wait(10)==23
    finally:
        if parent.poll() is None:parent.terminate();parent.wait(5)
        parent.stdin.close();parent.stdout.close()
    end=time.monotonic()+12
    while time.monotonic()<end and not w.status(PRINCIPAL,run)['recovery_required']:time.sleep(.05)
    assert w.status(PRINCIPAL,run)['recovery_required'] and w.checkpoint(PRINCIPAL,run)==old and w.result(PRINCIPAL,run)==best
    with w.storage.connection() as db:
        row=w.store.row(db,ACTOR,run);p=db.execute('SELECT * FROM l_processes WHERE run=? ORDER BY heartbeat DESC LIMIT 1',(run,)).fetchone()
    assert not alive(p['pid'],p['created'])
    a,c,_=dependencies(1);again=Worker(Coordinator(Store(w.storage.root,w.storage.store_id,max_runs=4),a,c))
    again.recover(PRINCIPAL,run,expected_tip=row['tip'],expected_fence=row['fence'])
    assert until(again,run,{'COMPLETED','FAILED'})['state']=='COMPLETED' and again.close(PRINCIPAL)['quiescent']

def test_changed_physical_policy_reopen_fails_closed(fixture):
    w,run,_=fixture();a,c,_=dependencies()
    with pytest.raises(RunError,match='POLICY_CHANGED'):
        Worker(Coordinator(Store(w.storage.root,w.storage.store_id,max_runs=4),a,c),resources=Resources(process_user_cpu_seconds=2))

def test_actual_readonly_storage_denies_write_without_data_loss(fixture):
    w,run,_=fixture();p=w.storage.root/'records.sqlite3';p.chmod(stat.S_IREAD)
    try:
        with pytest.raises(RunError,match='TRANSACTION_FAILED'):
            with w.storage.transaction() as db:db.execute('UPDATE workers SET reason=? WHERE run=?',('FICTIONAL',run))
    finally:p.chmod(stat.S_IWRITE|stat.S_IREAD)
    assert w.status(PRINCIPAL,run)['state']=='CREATED'

def test_backup_inspection_staleness_and_no_restore_activation(fixture):
    w,run,_=paused(fixture);result=w.storage.backup(w.coordinator,PRINCIPAL,run)
    assert result['integrity']=='PASS' and not result['restore_enabled']
    with pytest.raises(RunError,match='RETENTION_LIMIT'):w.storage.backup(w.coordinator,PRINCIPAL,run)
    w.resume(PRINCIPAL,run);assert until(w,run,{'COMPLETED','FAILED'})['state']=='COMPLETED'
    with pytest.raises(RunError,match='BACKUP_STALE'):w.storage.inspect_backup(w.coordinator,PRINCIPAL,run)

def test_retention_plan_fences_but_never_deletes(fixture):
    w,run,_=fixture();w.start(PRINCIPAL,run);s=until(w,run,{'COMPLETED','FAILED'});assert s['state']=='COMPLETED'
    with w.storage.connection() as db:row=w.store.row(db,ACTOR,run)
    with pytest.raises(RunError,match='RETENTION_STALE'):w.retention_plan(PRINCIPAL,run,expected_tip=row['tip'],expected_fence=row['fence']-1)
    assert not w.retention_plan(PRINCIPAL,run,expected_tip=row['tip'],expected_fence=row['fence'])['cleanup_enabled']
    assert w.checkpoint(PRINCIPAL,run)['sequence']==1

def test_grace_bounded_shutdown_and_cross_owner_rejection(fixture,monkeypatch):
    import services.ga_supervised_worker as module
    from services.preference_authorization import PreferencePrincipal
    from tests.trusted_run_support import OTHER
    w,run,_=fixture();monkeypatch.setattr(module,'arguments',blocking_arguments);w.start(PRINCIPAL,run)
    with pytest.raises(RunError,match='NOT_FOUND'):w.shutdown(PreferencePrincipal('admin',user_id=OTHER),grace=1)
    end=time.monotonic()+15
    while time.monotonic()<end and not w.processes.get(run):time.sleep(.02)
    assert w.processes.get(run)
    assert w.shutdown(PRINCIPAL,grace=1)['quiescent']
    assert w.status(PRINCIPAL,run)['state']=='FAILED'

def test_idle_shutdown_preserves_paused_checkpoint(fixture):
    w,run,_=paused(fixture);before=w.checkpoint(PRINCIPAL,run)
    assert w.shutdown(PRINCIPAL)['quiescent'] and w.status(PRINCIPAL,run)['state']=='PAUSED'
    assert w.checkpoint(PRINCIPAL,run)==before

def test_bound_physical_checkpoint_pin_cannot_be_changed(fixture):
    w,run,_=paused(fixture)
    with w.storage.connection() as db:db.execute('UPDATE l_pins SET policy=? WHERE run=?',('0'*64,run))
    with pytest.raises(RunError,match='CHECKPOINT_POLICY_MISMATCH'):w.resume(PRINCIPAL,run)

def test_l_metadata_counts_toward_per_run_quota(fixture):
    w,run,_=fixture()
    with w.storage.connection() as db:size=w.store.size(db,run)
    with pytest.raises(RunError,match='SUPERVISION_STORED_BYTES_LIMIT'):
        fixture(limits=Limits(run_bytes=size+2048))

@pytest.mark.parametrize('field',['contract','bundle'])
def test_backup_manifest_binding_tampering_rejected(fixture,field):
    w,run,_=fixture();w.command(PRINCIPAL,run,'stop');w.storage.backup(w.coordinator,PRINCIPAL,run)
    p=w.storage.root/'backups/manifest.json';d=json.loads(p.read_bytes());d[field]='FICTIONAL-TAMPERING';p.write_bytes(canonical(d))
    with pytest.raises(RunError,match='BACKUP_BINDING_INVALID'):w.storage.inspect_backup(w.coordinator,PRINCIPAL,run)

def test_insufficient_disk_headroom_rejects_before_write(fixture,monkeypatch):
    import services.ga_supervised_storage as module
    from types import SimpleNamespace
    w,run,_=fixture();original=module.shutil.disk_usage
    monkeypatch.setattr(module.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
    try:
        with pytest.raises(RunError,match='FREE_SPACE_INSUFFICIENT'):w.start(PRINCIPAL,run)
    finally:monkeypatch.setattr(module.shutil,'disk_usage',original)
    assert w.status(PRINCIPAL,run)['state']=='CREATED'

@pytest.mark.parametrize('field,value',[('database_bytes',0),('database_bytes',131073),('filesystem_bytes',1024),('backup_count',2)])
def test_unqualified_storage_modes_rejected(field,value):
    with pytest.raises(RunError):replace(StorageLimits(),**{field:value}).validate()
