"""U5M bounded instrumentation of the actual guard in owned source fixtures."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import threading
import time
from uuid import UUID
import pytest
from services import ga_input_receipt as receipt
from services.ga_worker_contract import fictional_source
from tests.test_ga_input_receipt import isolated

@pytest.fixture(autouse=True)
def owned_snapshot_only():fictional_source()

def replay(monkeypatch,tmp_path):
    root=tmp_path/'regular-root';root.mkdir();run='00000000-0000-4000-8000-000000001751';target=root/run
    original=Path.resolve
    # Both are actual supported spellings of this same regular Windows folder.
    extended=Path('\\\\?\\'+str(root));assert root.samefile(extended)
    def resolve(path,*args,**kwargs):
        if path==root:return extended
        if path==target:return target
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',resolve);monkeypatch.setattr(receipt,'RECEIPTS_DIR',root)
    return root,target,run

def test_frozen_original_rejects_observed_equivalent_namespace(monkeypatch,tmp_path):
    from tests import u5m_frozen_guard as frozen
    root,target,run=replay(monkeypatch,tmp_path);monkeypatch.setattr(frozen,'RECEIPTS_DIR',root)
    with pytest.raises(receipt.HistoryError):frozen.directory(run)

def test_current_guard_accepts_observed_equivalent_namespace(monkeypatch,tmp_path):
    root,target,run=replay(monkeypatch,tmp_path)
    assert receipt.directory(run)==target

def test_resolved_outside_parent_still_rejected(monkeypatch,tmp_path):
    root=tmp_path/'root';other=tmp_path/'other';root.mkdir();other.mkdir();run='00000000-0000-4000-8000-000000001751'
    original=Path.resolve
    def resolve(path,*a,**k):
        if path==root/run:return other/run
        return original(path,*a,**k)
    monkeypatch.setattr(receipt,'RECEIPTS_DIR',root);monkeypatch.setattr(Path,'resolve',resolve)
    with pytest.raises(receipt.HistoryError):receipt.directory(run)

@pytest.mark.parametrize('exception',[PermissionError,FileNotFoundError])
def test_samefile_uncertainty_fails_closed(monkeypatch,tmp_path,exception):
    _,_,run=replay(monkeypatch,tmp_path)
    def unavailable(*args):raise exception('FICTIONAL identity unavailable')
    monkeypatch.setattr(Path,'samefile',unavailable)
    with pytest.raises(receipt.HistoryError):receipt.directory(run)

@pytest.mark.parametrize('kind',['root','target'])
def test_actual_junctions_remain_rejected(monkeypatch,tmp_path,kind):
    root=tmp_path/'root';outside=tmp_path/'outside';outside.mkdir();run='00000000-0000-4000-8000-000000001751'
    if kind=='target':root.mkdir()
    link=root if kind=='root' else root/run
    result=subprocess.run(['cmd','/d','/c','mklink','/J',str(link),str(outside)],capture_output=True,text=True)
    assert result.returncode==0 and link.is_junction()
    monkeypatch.setattr(receipt,'RECEIPTS_DIR',root)
    with pytest.raises(receipt.HistoryError):receipt.directory(run)

def test_reparse_change_after_resolution_is_rejected(monkeypatch,tmp_path):
    root,target,run=replay(monkeypatch,tmp_path);original=Path.is_junction;seen=[]
    def changed(path):
        if path==root:
            seen.append(True);return len(seen)>1
        return original(path)
    monkeypatch.setattr(Path,'is_junction',changed)
    with pytest.raises(receipt.HistoryError):receipt.directory(run)

def test_missing_store_read_does_not_create_anything(monkeypatch,tmp_path):
    root=tmp_path/'absent';monkeypatch.setattr(receipt,'RECEIPTS_DIR',root)
    assert receipt.read('00000000-0000-4000-8000-000000001751')['record_state']=='MISSING'
    assert not root.exists()

@pytest.mark.parametrize('run',['../escape','NOT-A-UUID','00000000000040008000000000001751',None])
def test_invalid_writer_identity_creates_no_store(monkeypatch,tmp_path,run):
    root=tmp_path/'absent';monkeypatch.setattr(receipt,'RECEIPTS_DIR',root)
    with pytest.raises(receipt.HistoryError):receipt.write(run,'start.json',None)
    assert not root.exists()

def test_repeated_full_observers_keep_context_and_immutable_records():
    from tests.test_ga_input_receipt import test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim as original_case
    for _ in range(100):original_case()
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        with (Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/'U5M-full-observer-stress.json').open('x',encoding='utf-8') as f:
            json.dump(dict(scope='Actual begin/progress/finish/read with distinct context-local fictional preferences, not concurrent GA engines',pairs=100,completed_observers=200,all_recorded=True),f,indent=2)

def test_legacy_observer_source_record_remains_readable_and_unverified():
    from tests.test_ga_input_receipt import control,PARAMETERS
    observer=receipt.begin(control(),PARAMETERS);run='00000000-0000-4000-8000-000000001752'
    legacy=observer.start.model_copy(update={'run_id':run,'observer_source_fingerprint':'2b418773be9ba119ff39fc87157e28d364462d139eb46b4c12f4a99f18fb5c5e'})
    receipt.write(run,'start.json',legacy);path=receipt.directory(run)/'start.json';raw=path.read_bytes();result=receipt.read(run)
    assert result['verification_status']=='UNVERIFIED' and not result['eligible_for_current']
    assert result['start']['observer_source_fingerprint']==legacy.observer_source_fingerprint and path.read_bytes()==raw

def test_same_run_concurrent_writes_have_one_immutable_winner():
    from tests.test_ga_input_receipt import control,PARAMETERS
    observer=receipt.begin(control(),PARAMETERS);run='00000000-0000-4000-8000-000000001753'
    value=observer.start.model_copy(update={'run_id':run});barrier=threading.Barrier(2)
    def write(_):
        barrier.wait(timeout=5)
        try:receipt.write(run,'start.json',value);return 200
        except receipt.HistoryError as exc:return exc.status
    with ThreadPoolExecutor(2) as pool:statuses=list(pool.map(write,[0,1]))
    assert sorted(statuses)==[200,409]
    assert receipt.load(run,'start.json',receipt.Start)==value

@pytest.mark.parametrize('kind',['root','target'])
def test_symlink_checks_not_bypassed_by_identity_fallback(monkeypatch,tmp_path,kind):
    root,target,run=replay(monkeypatch,tmp_path);original=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda path:True if path==(root if kind=='root' else target) else original(path))
    with pytest.raises(receipt.HistoryError):receipt.directory(run)

def test_instrumented_writer_directory_guard(monkeypatch,tmp_path):
    fictional_source();seed=17501;rng=random.Random(seed);logs={};lock=threading.Lock();local=threading.local()
    originals={name:getattr(Path,name) for name in ['is_symlink','is_junction','resolve','samefile','mkdir']}
    def wrapper(name):
        original=originals[name]
        def call(path,*args,**kwargs):
            try:result=original(path,*args,**kwargs)
            except OSError as exc:
                if getattr(local,'active',False):
                    with lock:logs.setdefault(threading.get_ident(),[]).append(dict(operation=name,path=str(path),exception=type(exc).__name__,winerror=getattr(exc,'winerror',None),at_ns=time.perf_counter_ns()))
                raise
            if getattr(local,'active',False):
                row=dict(operation=name,path=str(path),result=str(result) if isinstance(result,Path) else result,at_ns=time.perf_counter_ns())
                with lock:logs.setdefault(threading.get_ident(),[]).append(row)
            return result
        return call
    for name in originals:monkeypatch.setattr(Path,name,wrapper(name))
    failures=[];successes=[];total=0;start=time.perf_counter()
    class FictionalValue:
        def model_dump(self):return {'scope':'FICTIONAL_DIRECTORY_GUARD_PROBE_ONLY'}
    with ThreadPoolExecutor(2) as pool:
        for precreated in [False,True]:
            for index in range(1500):
                parent=tmp_path/('existing' if precreated else 'missing')/str(index)/'input_receipts'
                if precreated:parent.mkdir(parents=True)
                monkeypatch.setattr(receipt,'RECEIPTS_DIR',parent)
                ids=[str(UUID(int=rng.getrandbits(128),version=4)) for _ in range(2)];barrier=threading.Barrier(2)
                def observe(run):
                    ident=threading.get_ident()
                    with lock:logs[ident]=[]
                    local.active=True;barrier.wait(timeout=5);error=None
                    target=parent/run
                    try:receipt.write(run,'probe.json',FictionalValue())
                    except Exception as exc:error=type(exc).__name__;target=parent/run
                    finally:local.active=False
                    captured=list(logs[ident]);target.mkdir(parents=True,exist_ok=True)
                    if error:return dict(precreated=precreated,index=index,error=error,trace=captured,
                        root_is_symlink=parent.is_symlink(),root_is_junction=parent.is_junction(),
                        root_after=str(parent.resolve()),target_parent_after=str(target.resolve().parent))
                    if len(successes)<2:successes.append(dict(precreated=precreated,index=index,trace=captured))
                    return None
                rows=list(pool.map(observe,ids));total+=2
                failures.extend(r for r in rows if r)
    result=dict(scope='Instrumented actual receipt.write/directory; fictional tiny probe envelopes only. Path wrappers are test-local; production code is not modified by instrumentation.',
        seed=seed,path_checks=total,failures=len(failures),failures_by_root_state={str(v):sum(r['precreated']==v for r in failures) for v in [False,True]},elapsed_seconds=time.perf_counter()-start,
        source_sha256=hashlib.sha256(Path(receipt.__file__).read_bytes()).hexdigest(),first_failures=failures[:10],sample_successes=successes)
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        with (Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/'U5M-receipt-guard-trace.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    assert not failures,json.dumps(result)
