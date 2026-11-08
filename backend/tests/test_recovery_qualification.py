"""Fictional U5N authority, actual SQLite quarantine and H checkpoint tests."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict,replace
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
from uuid import uuid4
import pytest
from services.ga_recovery_qualification import RecoveryAuthority,RecoveryMandate,RecoveryContext
from services.ga_recovery_vault import PrivateRoot,Anchor,Vault,Package
from services.ga_run_authority import RunError,digest
from services.ga_bundle_optimizer import Session
from services.ga_input_bundle import InputBundle
from services.ga_worker_contract import fictional_source
from services.preference_authorization import PreferencePrincipal
from tests.test_qualified_execution import FictionalDirectory,FictionalVerifier
from tests.trusted_run_support import ACTOR,OTHER,DEPT,OTHER_DEPT,CATALOG,PRINCIPAL,FictionalSource

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    fictional_source()
    from sqlalchemy.engine import Engine
    from services import chromosome_service,ga_checkpoint_service
    def forbidden(*a,**k):pytest.fail('Non-quarantine persistence forbidden')
    monkeypatch.setattr(Engine,'connect',forbidden);monkeypatch.setattr(chromosome_service,'save_best_if_better',forbidden);monkeypatch.setattr(ga_checkpoint_service,'save_checkpoint',forbidden)

@pytest.fixture(scope='module')
def package():
    fictional_source();run=str(uuid4());bundle=FictionalSource(1).capture(run,ACTOR,DEPT,CATALOG).bundle
    session=Session(bundle,run_id=run,random_state=random.Random(17514).getstate())
    def pause(kind,data):
        if data['generation']==0:session.control.request_pause()
    assert session.run(pause) is None
    return Package(run,ACTOR,DEPT,bundle._raw,(session.checkpoint,))

@pytest.fixture
def setup(package):
    now=[100000.0];clock=lambda:now[0]
    record=RecoveryMandate(str(uuid4()),'FICTIONAL-RECOVERY-v1',ACTOR,DEPT,package.run_id,'a'*64,'ACTIVE',now[0]-10,now[0]+300)
    directory=FictionalDirectory((record,));verifier=FictionalVerifier(clock)
    verifier.approved[('recovery-mandate',digest(asdict(record)))]=record.source_id
    authority=RecoveryAuthority(directory,verifier,clock=clock)
    anchor=Anchor(PrivateRoot.create(),initialize=True);epoch=anchor.pin(package,expected_epoch=0)
    vault=Vault(PrivateRoot.create(),anchor,authority,initialize=True,clock=clock)
    return vault,epoch,directory,verifier,now

def count(vault):
    with vault.root.transaction() as db:return db.execute('SELECT COUNT(*) FROM n_restores').fetchone()[0]

def test_actual_writable_quarantine_and_exact_continuation(package,setup):
    v,e,*_=setup;before=random.getstate();result=v.restore(PRINCIPAL,package,str(uuid4()),e)
    assert result['state']=='VALIDATED_QUARANTINE' and not result['worker_resume_enabled'] and not result['institutional_restore_enabled']
    with v.root.transaction() as db:stored=bytes(db.execute('SELECT raw FROM n_restores').fetchone()[0]);audit=[json.loads(r[0]) for r in db.execute('SELECT body FROM n_audit')]
    assert stored==package.raw() and audit[0]['authority']['authorized_role']=='RECOVERY_OPERATOR'
    restored=Package.decode(stored);bundle=InputBundle.from_bytes(restored.bundle,restored.run_id,hashlib.sha256(restored.bundle).hexdigest())
    def continuation(p):return Session.restore(bundle,p.chain[-1],run_id=p.run_id,expected_fingerprint=hashlib.sha256(p.chain[-1]).hexdigest(),expected_sequence=1,expected_parent=None)
    oracle=continuation(package);actual=continuation(restored);expected=oracle.run();out=actual.run()
    for key in ['schedule','best_fitness','fitness_breakdown','history','faculty_analysis']:assert out[key]==expected[key]
    assert actual.runtime.random.getstate()==oracle.runtime.random.getstate() and random.getstate()==before

@pytest.mark.parametrize('mode',['missing_provider','admin_only','chair_only','revoked','expired','scope_changed','wrong_run','unverified','wrong_capability'])
def test_independent_authority_fail_closed(package,setup,mode):
    v,e,d,verifier,now=setup
    if mode=='missing_provider':v.authority=None
    elif mode in {'admin_only','chair_only'}:d.records=()
    elif mode=='revoked':verifier.revoked=True
    elif mode=='expired':now[0]+=1000
    elif mode=='unverified':verifier.approved.clear()
    else:
        changes={'scope_changed':{'department_id':OTHER_DEPT},'wrong_run':{'run_id':str(uuid4())},'wrong_capability':{'capability':'department_optimization_control'}}
        d.records=(replace(d.records[0],**changes[mode]),)
    with pytest.raises(RunError):v.restore(PRINCIPAL,package,str(uuid4()),e)
    assert count(v)==0

@pytest.mark.parametrize('kind',['actor','department','run'])
def test_cross_scope_and_owner_rejected(package,setup,kind):
    v,e,*_=setup;p=package;principal=PRINCIPAL
    if kind=='actor':principal=PreferencePrincipal('admin',user_id=OTHER)
    if kind=='department':p=replace(p,department_id=OTHER_DEPT)
    if kind=='run':p=replace(p,run_id=str(uuid4()))
    with pytest.raises(RunError):v.restore(principal,p,str(uuid4()),e)
    assert count(v)==0

@pytest.mark.parametrize('kind',['checkpoint','bundle','optimizer','configuration','rng','lineage','missing_chain'])
def test_invalid_backup_never_writes(package,setup,kind):
    v,e,*_=setup;p=package
    if kind=='bundle':p=replace(p,bundle=package.bundle+b' ')
    elif kind=='missing_chain':p=replace(p,chain=())
    elif kind=='checkpoint':p=replace(p,chain=(b'FICTIONAL-CORRUPT',))
    else:
        doc=json.loads(package.chain[0]);field={'optimizer':'optimizer_fingerprint','configuration':'configuration_fingerprint','rng':'graph','lineage':'sequence'}[kind]
        doc[field]=2 if kind=='lineage' else ({} if kind=='rng' else '0'*64)
        from services.ga_run_authority import canonical
        p=replace(p,chain=(canonical(doc),))
    with pytest.raises(RunError):v.restore(PRINCIPAL,p,str(uuid4()),e)
    assert count(v)==0

def test_stale_anchor_and_nonadvancing_repin(package,setup):
    v,e,*_=setup
    with pytest.raises(RunError,match='ANCHOR_STALE'):v.restore(PRINCIPAL,package,str(uuid4()),e+1)
    with pytest.raises(RunError,match='NONADVANCING'):v.anchor.pin(package,expected_epoch=e)
    assert count(v)==0

def test_replay_and_existing_run_never_overwrite(package,setup):
    v,e,*_=setup;request=str(uuid4());v.restore(PRINCIPAL,package,request,e)
    with v.root.transaction() as db:before=bytes(db.execute('SELECT raw FROM n_restores').fetchone()[0])
    for key in [request,str(uuid4())]:
        with pytest.raises(RunError,match='REPLAY'):v.restore(PRINCIPAL,package,key,e)
    with v.root.transaction() as db:assert bytes(db.execute('SELECT raw FROM n_restores').fetchone()[0])==before
    assert count(v)==1

def test_simultaneous_restores_one_durable_winner(package,setup):
    v,e,*_=setup;barrier=threading.Barrier(2)
    def attempt(_):
        barrier.wait(timeout=10)
        try:v.restore(PRINCIPAL,package,str(uuid4()),e);return 'OK'
        except RunError as exc:return exc.code
    with ThreadPoolExecutor(2) as pool:out=list(pool.map(attempt,[0,1]))
    assert sorted(out)==['GA_RECOVERY_REPLAY_REJECTED','OK'] and count(v)==1

@pytest.mark.parametrize('stage',['BEFORE_VAULT_COMMIT','AFTER_VAULT_COMMIT'])
def test_interruption_preserves_uncertain_evidence_without_activation(package,setup,stage):
    v,e,*_=setup
    def interrupt(where):
        if where==stage:raise RuntimeError('FICTIONAL interruption')
    v.fault=interrupt
    with pytest.raises(RunError,match='INTERRUPTED_REVIEW'):v.restore(PRINCIPAL,package,str(uuid4()),e)
    assert count(v)==int(stage=='AFTER_VAULT_COMMIT')
    if stage=='AFTER_VAULT_COMMIT':
        with pytest.raises(RunError,match='ANCHOR_INCOMPLETE'):v.inspect(PRINCIPAL,package.run_id)
        v.fault=lambda _:None
        with pytest.raises(RunError,match='EXISTING_RUN'):v.restore(PRINCIPAL,package,str(uuid4()),e)
    else:
        v.fault=lambda _:None;assert v.restore(PRINCIPAL,package,str(uuid4()),e)['state']=='VALIDATED_QUARANTINE'

def test_authority_expiry_before_commit_rolls_back(package,setup):
    v,e,d,verifier,now=setup
    v.fault=lambda where:now.__setitem__(0,now[0]+1000) if where=='BEFORE_VAULT_COMMIT' else None
    with pytest.raises(RunError,match='EXPIRED'):v.restore(PRINCIPAL,package,str(uuid4()),e)
    assert count(v)==0

@pytest.mark.parametrize('kind',['per_package','global'])
def test_payload_quotas(package,setup,kind):
    v,e,*_=setup
    if kind=='per_package':v.maximum_package_bytes=1
    else:v.maximum_total_bytes=1
    with pytest.raises(RunError,match='QUOTA'):v.restore(PRINCIPAL,package,str(uuid4()),e)
    assert count(v)==0

def test_unapproved_roots_and_shared_anchor_fail_closed(setup):
    v,*_=setup
    with pytest.raises(RunError,match='UNAPPROVED'):PrivateRoot(object())
    with pytest.raises(RunError,match='INDEPENDENT_ROOTS'):Vault(v.anchor.root,v.anchor,v.authority)

@pytest.mark.parametrize('kind',['root','database_identity','marker'])
def test_filesystem_substitution_fails_closed(setup,monkeypatch,tmp_path,kind):
    v,*_=setup
    if kind=='root':monkeypatch.setattr(v.root.store,'root',tmp_path/'FICTIONAL-UNAPPROVED')
    elif kind=='database_identity':
        original=v.root.identity
        monkeypatch.setattr(v.root,'identity',lambda p:(0,0) if p.name=='records.sqlite3' else original(p))
    else:
        path=v.root.store.root/'OWNER.json';d=json.loads(path.read_bytes());d['store_id']=str(uuid4());path.write_text(json.dumps(d))
    with pytest.raises(RunError,match='ROOT_IDENTITY_CHANGED'):v.root.guard()

def test_real_junction_substitution_rejected(setup):
    v,*_=setup;root=v.root.store.root;link=root/'junction-probe';target=v.anchor.root.store.root
    result=subprocess.run(['cmd','/d','/c','mklink','/J',str(link),str(target)],capture_output=True)
    assert result.returncode==0
    with pytest.raises(RunError,match='REPARSE'):PrivateRoot.identity(link)

def test_reopened_vault_uses_retained_anchor_and_current_authority(package,setup):
    v,e,d,verifier,_=setup;v.restore(PRINCIPAL,package,str(uuid4()),e)
    again=Vault(v.root,Anchor(v.anchor.root),v.authority)
    assert again.inspect(PRINCIPAL,package.run_id)['checkpoint_tip']==hashlib.sha256(package.chain[-1]).hexdigest()
    verifier.revoked=True
    with pytest.raises(RunError):again.inspect(PRINCIPAL,package.run_id)

def test_recorded_scope_and_no_worker_restore_provider(setup):
    from services.ga_trusted_runs import configured_service
    assert configured_service() is None
    v,*_=setup
    assert not hasattr(v,'resume') and not hasattr(v,'publish') and not hasattr(v,'delete')

def test_reopen_never_reapproves_current_filesystem_identity(setup):
    from services.ga_recovery_vault import RootApproval
    v,*_=setup
    with pytest.raises(RunError,match='UNAPPROVED'):PrivateRoot(v.root.store)
    pins=list(v.root.approval.pins);pins[1]=(pins[1][0],(0,0))
    bad=replace(v.root.approval,pins=tuple(pins))
    with pytest.raises(RunError,match='ROOT_IDENTITY_CHANGED'):PrivateRoot(v.root.store,bad)

def test_real_sqlite_page_quota_rolls_back_without_schema_or_payload_loss(package,setup):
    v,e,*_=setup;v.restore(PRINCIPAL,package,str(uuid4()),e)
    with pytest.raises(RunError,match='TRANSACTION_FAILED'):
        with v.root.transaction() as db:
            db.execute('CREATE TABLE n_pressure(value BLOB)')
            db.execute('INSERT INTO n_pressure VALUES(zeroblob(?))',(34*1024*1024,))
    with v.root.transaction() as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='n_pressure'").fetchone()
    assert v.inspect(PRINCIPAL,package.run_id)['state']=='VALIDATED_QUARANTINE'

def test_disk_headroom_and_permission_change_fail_closed(setup,monkeypatch):
    import services.ga_recovery_vault as module
    from types import SimpleNamespace
    v,*_=setup
    with monkeypatch.context() as patch:
        patch.setattr(module.shutil,'disk_usage',lambda _:SimpleNamespace(free=0))
        with pytest.raises(RunError,match='DISK_HEADROOM'):
            with v.root.transaction():pytest.fail('No transaction permitted')
    def denied(_):raise RunError('FICTIONAL_PERMISSION_CHANGE')
    monkeypatch.setattr(module,'permissions',denied)
    with pytest.raises(RunError,match='ROOT_IDENTITY_CHANGED'):v.root.guard()

def test_rejected_action_has_bounded_safe_audit_fields(package,setup):
    v,e,d,verifier,_=setup;verifier.revoked=True
    with pytest.raises(RunError):v.restore(PRINCIPAL,package,str(uuid4()),e)
    with v.root.transaction() as db:row=json.loads(db.execute('SELECT body FROM n_audit ORDER BY id DESC').fetchone()[0])
    assert row['actor_id']==ACTOR and row['department_id']==DEPT and row['target_run']==package.run_id
    assert row['decision']=='REJECTED' and row['authority'] is None and row['action']=='restore_quarantine'
    assert not {'password','cookie','csrf_token'}&set(row)

def test_fresh_process_validates_quarantine_with_external_root_approvals(package,setup):
    v,e,d,verifier,_=setup;v.restore(PRINCIPAL,package,str(uuid4()),e)
    def approval(root):
        a=root.approval;return dict(root=a.root,store_id=a.store_id,pins=[(str(p),list(pin)) for p,pin in a.pins])
    data=dict(vault=approval(v.root),anchor=approval(v.anchor.root),mandate=asdict(d.records[0]),run=package.run_id)
    code='''import sys,json
from pathlib import Path
from dataclasses import asdict
from services.ga_owned_store import Store
from services.ga_recovery_vault import PrivateRoot,RootApproval,Anchor,Vault
from services.ga_recovery_qualification import RecoveryAuthority,RecoveryMandate
from services.ga_run_authority import digest
from tests.test_qualified_execution import FictionalDirectory,FictionalVerifier
from tests.trusted_run_support import PRINCIPAL
d=json.loads(sys.argv[1]);clock=lambda:100000.0
def root(value):
 a=RootApproval(value['root'],value['store_id'],tuple((Path(p),tuple(pin)) for p,pin in value['pins']))
 return PrivateRoot(Store(a.root,a.store_id,max_runs=4),a)
r=d['mandate'];r['actions']=tuple(r['actions']);record=RecoveryMandate(**r)
verifier=FictionalVerifier(clock);verifier.approved[('recovery-mandate',digest(asdict(record)))]=record.source_id
authority=RecoveryAuthority(FictionalDirectory((record,)),verifier,clock=clock)
vault=Vault(root(d['vault']),Anchor(root(d['anchor'])),authority,clock=clock)
assert vault.inspect(PRINCIPAL,d['run'])['state']=='VALIDATED_QUARANTINE'
print('FICTIONAL_FRESH_PROCESS_QUARANTINE_VERIFIED')
'''
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    result=subprocess.run([sys.executable,'-B','-c',code,json.dumps(data)],env={k:v for k,v in os.environ.items() if k.upper() in allowed},capture_output=True,text=True,timeout=90)
    if result.returncode:pytest.fail('Owned fresh-process quarantine check failed; provider/approval payload withheld')
    assert 'FICTIONAL_FRESH_PROCESS_QUARANTINE_VERIFIED' in result.stdout
