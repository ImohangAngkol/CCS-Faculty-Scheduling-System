"""FICTIONAL independent directory/verifier/catalog; no production activation."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from uuid import uuid4
import pytest
from sqlalchemy.engine import Engine
from services.ga_run_authority import Context,RunError,digest,verify
from services.ga_qualification_authority import ScopedAuthority,OptimizationMandate,Attestation,ACTIONS
from services.ga_qualified_capture import CaptureAdapter,PreparedSnapshot,identity
from services.ga_input_bundle import InputBundle,canonical,digest as byte_digest
from services.ga_trusted_runs import Coordinator,configured_service
from services.ga_owned_store import Store
from services.ga_storage_qualification import inspect,DeploymentEvidence,REQUIRED
from tests.trusted_run_support import ACTOR,OTHER,DEPT,OTHER_DEPT,PRINCIPAL,CATALOG,FictionalSource

TEMPLATE='00000000-0000-4000-8000-000000000951'

class FictionalDirectory:
    def __init__(self,records):self.records=records;self.lock=threading.RLock()
    @contextmanager
    def guard(self):
        with self.lock:yield
    def records_for(self,actor,department):return tuple(r for r in self.records if (r.actor_id,r.department_id)==(actor,department))

class FictionalVerifier:
    def __init__(self,clock):self.clock=clock;self.approved={};self.revoked=False;self.lock=threading.RLock()
    @contextmanager
    def guard(self):
        with self.lock:yield
    def verify(self,kind,binding,source):
        if self.revoked or self.approved.get((kind,binding))!=source:return None
        return Attestation(binding,source,'f'*64,self.clock()-1,self.clock()+60)

class FictionalCatalog:
    def __init__(self,record):self.record=record;self.lock=threading.RLock();self.calls=0
    @contextmanager
    def guard(self):
        with self.lock:yield
    def snapshot(self,department,reference):
        self.calls+=1
        return self.record if (department,reference)==(self.record.department_id,self.record.reference) else None

@pytest.fixture(autouse=True)
def no_institution(monkeypatch):
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Institutional database access forbidden'))
    from services import ga_checkpoint_service,chromosome_service
    def forbidden(*_a,**_k):pytest.fail('Application GA persistence forbidden')
    monkeypatch.setattr(ga_checkpoint_service,'save_checkpoint',forbidden)
    monkeypatch.setattr(chromosome_service,'save_best_if_better',forbidden)

@pytest.fixture
def qualified():
    clock=[100000.0];now=lambda:clock[0]
    record=OptimizationMandate('00000000-0000-4000-8000-000000000952','fictional-revision-1',ACTOR,DEPT,
        'department_optimization_control',tuple(sorted(ACTIONS)),'a'*64,'ACTIVE',99000.0,101000.0)
    directory=FictionalDirectory((record,));verifier=FictionalVerifier(now)
    verifier.approved[('optimization-mandate',digest(asdict(record)))]=record.source_id
    bundle=FictionalSource().capture(TEMPLATE,ACTOR,DEPT,CATALOG).bundle
    prepared=PreparedSnapshot(DEPT,CATALOG,'fictional-source-1','b'*64,bundle,99000.0,101000.0)
    catalog=FictionalCatalog(prepared)
    verifier.approved[('prepared-input-snapshot',byte_digest(canonical(identity(prepared))))]=prepared.source_id
    return ScopedAuthority(directory,verifier,clock=now),CaptureAdapter(catalog,verifier,clock=now),directory,verifier,catalog,clock

def context(action='admit',department=DEPT,actor=ACTOR):return Context(actor,department,action,catalog_reference=CATALOG)
def capture(adapter):
    run=str(uuid4())
    with adapter.guard(ACTOR,DEPT,CATALOG):return adapter.capture(run,ACTOR,DEPT,CATALOG)
def admit(s,key=None):return s.admit(PRINCIPAL,DEPT,key or str(uuid4()),CATALOG)['run_id']
def coordinator(q):
    a,c,_,_,_,clock=q;now=lambda:clock[0]
    store=Store.create(clock=now);return Coordinator(store,a,c,clock=now),store

def test_valid_independent_authority_and_audit(qualified):
    a,_,d,v,_,clock=qualified;c=context()
    with a.guard(c):
        grant=verify(a,c,lambda:clock[0]);audit=a.audit(c)
        assert audit['mandate_digest']==digest(asdict(d.records[0]))
        assert audit['context_digest']==grant.context_digest and audit['source_id']=='a'*64
        assert audit['publication_authority'] is False
    with pytest.raises(RunError,match='GUARD_REQUIRED'):a.authorize(c)

@pytest.mark.parametrize('change',[{'state':'REVOKED'},{'effective_until':99999.0},{'effective_from':100001.0},
    {'effective_until':float('nan')},{'capability':'department_chair_review'},{'actions':('status',)},
    {'actions':('admit','admit')},{'actions':('unrecognized',)},{'revision':''},{'source_id':'bad'}])
def test_invalid_mandates_never_gain_optimization(qualified,change):
    a,_,d,*_=qualified;d.records=(replace(d.records[0],**change),);c=context()
    with a.guard(c):
        with pytest.raises(RunError,match='MANDATE_REQUIRED'):a.authorize(c)

@pytest.mark.parametrize('count',[0,2])
def test_missing_or_ambiguous_records_fail_closed(qualified,count):
    a,_,d,*_=qualified;d.records=d.records*count;c=context()
    with a.guard(c):
        with pytest.raises(RunError,match='MANDATE_REQUIRED'):a.authorize(c)

@pytest.mark.parametrize('actor,department',[(OTHER,DEPT),(ACTOR,OTHER_DEPT)])
def test_cross_actor_or_department_cannot_select_another_mandate(qualified,actor,department):
    a,*_=qualified;c=context(actor=actor,department=department)
    with a.guard(c):
        with pytest.raises(RunError,match='MANDATE_REQUIRED'):a.authorize(c)

@pytest.mark.parametrize('change',[{'binding_digest':'0'*64},{'source_id':'0'*64},{'expires_at':1},{'evidence_digest':'bad'}])
def test_attestation_mismatch_is_not_a_verified_claim(qualified,change):
    a,_,_,v,_,_=qualified;original=v.verify
    v.verify=lambda *args:replace(original(*args),**change)
    with a.guard(context()):
        with pytest.raises(RunError,match='MANDATE_REQUIRED'):a.authorize(context())

def test_independent_verifier_missing_or_revoked(qualified):
    a,_,_,v,_,_=qualified;v.revoked=True
    with a.guard(context()):
        with pytest.raises(RunError,match='MANDATE_REQUIRED'):a.authorize(context())
    a.verifier=None
    with pytest.raises(RunError,match='DIRECTORY_UNAVAILABLE'):
        with a.guard(context()):pass

def test_run_bound_prepared_capture_preserves_actual_model_graph(qualified):
    _,adapter,_,_,catalog,_=qualified;prepared=catalog.record.prepared_bundle
    received=capture(adapter).bundle;doc=json.loads(received._raw)
    assert received.run_id!=prepared.run_id and received.fingerprint!=prepared.fingerprint
    assert doc['graph']==json.loads(prepared._raw)['graph']
    assert doc['source_identities']['prepared']==prepared.fingerprint
    assert doc['source_identities']['sourceattestation']=='f'*64
    assert doc['configuration']==json.loads(prepared._raw)['configuration']
    assert doc['verification_status']=='UNVERIFIED' and not received.qualification(received.run_id)['eligible_for_current']

def test_guard_required_and_scope_binding(qualified):
    _,a,*_=qualified
    with pytest.raises(RunError,match='GUARD_REQUIRED'):a.capture(str(uuid4()),ACTOR,DEPT,CATALOG)
    with a.guard(ACTOR,DEPT,CATALOG):
        with pytest.raises(RunError,match='GUARD_REQUIRED'):a.capture(str(uuid4()),OTHER,DEPT,CATALOG)
    with pytest.raises(RunError,match='UNQUALIFIED'):
        with a.guard(ACTOR,OTHER_DEPT,CATALOG):pass

@pytest.mark.parametrize('change',[{'department_id':OTHER_DEPT},{'reference':'another-catalog'},
    {'revision':''},{'effective_until':1},{'source_id':'bad'},{'prepared_bundle':None}])
def test_bad_source_snapshot_rejects_before_admission(qualified,change):
    _,a,_,_,catalog,_=qualified;catalog.record=replace(catalog.record,**change)
    with pytest.raises(RunError,match='UNQUALIFIED'):capture(a)

@pytest.mark.parametrize('at',[2,3])
def test_source_revision_drift_before_or_after_materialization_rejected(qualified,at):
    _,a,_,_,catalog,_=qualified;original=catalog.snapshot
    def drift(*args):
        value=original(*args)
        return replace(value,revision='changed-without-approval') if catalog.calls>=at else value
    catalog.snapshot=drift
    with pytest.raises(RunError,match='CHANGED_OR_INVALID'):capture(a)

def test_malformed_raw_bundle_never_falls_back_to_globals(qualified):
    _,a,_,_,catalog,_=qualified;old=catalog.record.prepared_bundle
    bad=InputBundle(old.run_id,old.fingerprint,b'malformed')
    catalog.record=replace(catalog.record,prepared_bundle=bad)
    with pytest.raises(RunError,match='UNQUALIFIED'):capture(a)

def test_unverified_source_fingerprints_do_not_supply_trust(qualified):
    _,a,_,v,catalog,_=qualified;v.approved.clear()
    assert catalog.record.prepared_bundle.fingerprint
    with pytest.raises(RunError,match='UNQUALIFIED'):capture(a)

def test_source_runtime_engine_mismatch_fails_full_preflight(qualified):
    _,a,_,v,catalog,_=qualified;old=catalog.record.prepared_bundle;doc=json.loads(old._raw)
    doc['source_identities']['engine']='0'*64;raw=canonical(doc)
    bad=InputBundle.from_bytes(raw,old.run_id,byte_digest(raw));catalog.record=replace(catalog.record,prepared_bundle=bad)
    v.approved[('prepared-input-snapshot',byte_digest(canonical(identity(catalog.record))))]=catalog.record.source_id
    with pytest.raises(RunError,match='CHANGED_OR_INVALID'):capture(a)

def test_cached_globals_are_not_prepared_capture_inputs(qualified,monkeypatch):
    from genetic_algorithm.utils import Functions
    monkeypatch.setattr(Functions,'list_faculty',[]);monkeypatch.setattr(Functions,'list_subjects',[])
    _,a,*_=qualified;bundle=capture(a).bundle
    assert len(bundle.materialize(bundle.run_id)['templates'][1])==2

def test_capture_keeps_source_bytes_and_global_rng_unchanged(qualified):
    import random
    _,adapter,_,_,catalog,_=qualified
    raw=catalog.record.prepared_bundle._raw;before=random.getstate()
    capture(adapter)
    assert random.getstate()==before and catalog.record.prepared_bundle._raw==raw

def test_simultaneous_admissions_and_revocation_use_new_adapters(qualified):
    s,store=coordinator(qualified);key=str(uuid4());a,c,_,v,_,_=qualified
    other=Coordinator(store,a,c,clock=s.clock)
    with ThreadPoolExecutor(2) as pool:ids=list(pool.map(lambda service:admit(service,key),[s,other]))
    assert len(set(ids))==1
    v.revoked=True
    with pytest.raises(RunError,match='AUTHORITY_REQUIRED'):s.status(PRINCIPAL,ids[0])
    assert configured_service() is None

def test_policy_revision_cannot_resume_an_earlier_mandate(qualified):
    s,store=coordinator(qualified);run=admit(s);s.command(PRINCIPAL,run,'pause');s.execute(PRINCIPAL,run)
    _,_,d,v,_,_=qualified;d.records=(replace(d.records[0],revision='new-authority-revision'),)
    v.approved[('optimization-mandate',digest(asdict(d.records[0])))]=d.records[0].source_id
    with pytest.raises(RunError,match='POLICY_CHANGED'):s.execute(PRINCIPAL,run,resume=True)
    with store.connection() as db:assert store.row(db,run)['state']=='PAUSED'

def test_prepared_capture_to_actual_optimizer_and_restart(qualified):
    s,store=coordinator(qualified);run=admit(s);s.command(PRINCIPAL,run,'pause')
    assert s.execute(PRINCIPAL,run)['state']=='PAUSED'
    a,c,*_=qualified;again=Coordinator(Store(store.root,store.store_id,clock=s.clock),a,c,clock=s.clock)
    assert again.execute(PRINCIPAL,run,resume=True)['receipt']['verification_status']=='VERIFIED'
    result=again.result(PRINCIPAL,run)
    assert result['best_fitness']==0 and not result['saved_best_updated']
    assert again.status(PRINCIPAL,run)['eligible_for_current'] is False

def test_storage_qualification_and_offline_backup_restore(qualified):
    s,store=coordinator(qualified);run=admit(s);s.command(PRINCIPAL,run,'pause');s.execute(PRINCIPAL,run)
    # Entirely fictional, private, separate target. No source database is reset,
    # rewritten, deleted or activated as a second running execution instance.
    dest=Store.create(clock=s.clock)
    source_uri=(store.root/'records.sqlite3').as_uri()+'?mode=ro'
    source=sqlite3.connect(source_uri,uri=True);target=sqlite3.connect(dest.root/'records.sqlite3')
    try:source.backup(target)
    finally:source.close();target.close()
    restored=inspect(dest)
    assert restored['technical_integrity']=='PASS' and restored['run_count']==1 and restored['checkpoint_count']==1
    assert restored['production_ready'] is False and not restored['cleanup_performed']
    with dest.connection() as db:
        row=dest.row(db,run);raw=dest.load_checkpoint(db,row)
        assert s._session(row,raw).run_id==run
    assert s.status(PRINCIPAL,run)['state']=='PAUSED'  # original remains retained

def test_storage_corruption_is_not_a_ready_state(qualified):
    s,store=coordinator(qualified);run=admit(s);s.command(PRINCIPAL,run,'pause');s.execute(PRINCIPAL,run)
    with store.transaction() as db:db.execute('UPDATE checkpoints SET raw=? WHERE run=?',(b'fictional-corruption',run))
    with pytest.raises(RunError,match='INTEGRITY'):inspect(store)

def test_retention_boundary_preserves_integrity_but_denies_access(qualified):
    s,store=coordinator(qualified);run=admit(s);s.command(PRINCIPAL,run,'pause');s.execute(PRINCIPAL,run)
    qualified[-1][0]+=7*86400
    with pytest.raises(RunError,match='RETENTION_EXPIRED'):s.status(PRINCIPAL,run)
    assert inspect(store)['checkpoint_count']==1

def test_space_and_self_asserted_evidence_cannot_activate_storage():
    store=Store.create();result=inspect(store,DeploymentEvidence(tuple((k,'fictional-policy-reference') for k in REQUIRED)),minimum_free_bytes=2**80)
    assert not result['minimum_free_space_observed'] and not result['production_ready']
    assert all(r['status']=='INDEPENDENT_DEPLOYMENT_EVIDENCE_REQUIRED' for r in result['deployment_requirements'])

def test_permission_failure_precedes_database_creation(monkeypatch):
    import services.ga_owned_store as module
    roots=[]
    def deny(root):roots.append(root);raise RunError('GA_STORE_ACL_UNVERIFIED',503)
    monkeypatch.setattr(module,'secure',deny)
    with pytest.raises(RunError,match='ACL_UNVERIFIED'):Store.create()
    assert len(roots)==1 and not (roots[0]/'records.sqlite3').exists()

def test_missing_storage_never_recreates_user_records():
    store=Store.create();(store.root/'records.sqlite3').rename(store.root/'retained-fictional.sqlite3')
    with pytest.raises(RunError):inspect(store)
    assert not (store.root/'records.sqlite3').exists()

@pytest.mark.parametrize('target',['directory','authority_verifier','catalog','source_verifier'])
def test_missing_server_dependencies_stay_blocked(qualified,target):
    a,c,*_=qualified
    if target in {'directory','authority_verifier'}:
        setattr(a,'directory' if target=='directory' else 'verifier',None)
        with pytest.raises(RunError,match='UNAVAILABLE'):
            with a.guard(context()):pass
    else:
        setattr(c,'catalog' if target=='catalog' else 'verifier',None)
        with pytest.raises(RunError,match='UNAVAILABLE'):capture(c)

def test_read_only_permission_failure_cannot_be_ignored(monkeypatch):
    import services.ga_storage_qualification as module
    store=Store.create()
    def fail(_):raise RunError('GA_STORAGE_PERMISSIONS_UNVERIFIED')
    monkeypatch.setattr(module,'permissions',fail)
    with pytest.raises(RunError,match='PERMISSIONS_UNVERIFIED'):inspect(store)
