"""Genuine GA protocol in-process, NOT Windows/native worker acceptance."""
import copy
from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Owned empty-import snapshot required', allow_module_level=True)

from services.prototype_native_adapter import NativeAdapter
from services.prototype_native_transport import WindowsTransport, InProcessQualification, PreservationFinding, ExchangeError
from services.prototype_workload import PolicyError, digest
from services.prototype_cycle import Decision
from services.prototype_recovery_bootstrap import capture, reopen
from services.prototype_continuation_supervisor import checkpoint_audit
from tests.test_prototype_cycle import create, admit, WorkflowDirectory
from tests.test_prototype_inputs import CHAIR, FACULTY, Directory, weights, preference
from tests.test_prototype_workload import PRINCIPAL, FictionalGrants, change


def setup():
    cycle=create();cycle.offline_qualification=False
    cycle.inputs.workload.save(PRINCIPAL,change(**{'2':3}))
    cycle.inputs.approve_weights(CHAIR,weights(day_penalty=17))
    cycle.inputs.save_preference(FACULTY,2,preference(preferred_subjects=['SYN-WB'],preferred_days=['S'],
        use_day_preference=True,day_importance=5))
    view,command=admit(cycle)
    return cycle,view['run_id'],command


def adapter_for(cycle):
    return NativeAdapter(cycle,transport=InProcessQualification())


@pytest.fixture(scope='module')
def completed():
    cycle,run,command=setup();adapter=adapter_for(cycle)
    bundle=cycle.inputs.prepared(PRINCIPAL,command.preparation_id,internal_bundle=True)
    from services.ga_bundle_optimizer import Session
    oracle=Session(bundle,run_id=bundle.run_id,random_state=random.Random(710).getstate())
    before=random.getstate();expected=oracle.run()
    nonce=str(uuid4());first=adapter.step(PRINCIPAL,run,nonce)
    assert first['run']['sequence']==1
    assert adapter.step(PRINCIPAL,run,nonce)==first
    # Cold object graph reconstruction. No process restart is implied.
    pin=capture(cycle,PRINCIPAL,run)
    rebuilt=reopen(pin,PRINCIPAL,workload_authority=FictionalGrants(),input_directory=Directory(),workflow_directory=WorkflowDirectory())
    successor=NativeAdapter(rebuilt,transport=InProcessQualification(),root=adapter.journal.storage.root)
    final=successor.step(PRINCIPAL,run,str(uuid4()))
    assert random.getstate()==before
    yield successor,run,oracle,expected,final


def test_exact_frozen_protocol_output_rng_and_existing_review(completed):
    adapter,run,oracle,expected,final=completed
    actual=final['run']['result']
    assert actual['original_result']==expected
    assert final['run']['state']=='COMPLETED' and final['attempt_count']==2
    assert actual['qualification']['fully_feasible_under_captured_policy']
    assert actual['qualification']['faculty'][1]['assigned_units']==3
    assert actual['provenance']['weights_policy']['body']['day_penalty']==17
    from services.ga_checkpoint_service import rng_to_json
    assert checkpoint_audit(adapter.cycle,PRINCIPAL,run)['RNG_fingerprint']==digest(rng_to_json(oracle.runtime.random.getstate()))
    assert not final['physical_exit_verified'] and not final['native_result_verified']
    assert all(p['no_process_created'] and p['exit_verified'] is False for p in final['observations'])
    view=adapter.cycle.inspect(CHAIR,run)
    decision=Decision(request_id=str(uuid4()),expected_review=0,candidate_fingerprint=view['latest_candidate_fingerprint'],
        decision='APPROVE',explanation='Fictional protocol and workload reviewed')
    adapter.cycle.decide(CHAIR,run,decision)
    assert adapter.cycle.versions(CHAIR)[0]['version']==1
    timetable=adapter.cycle.timetable(FACULTY,2)
    assert timetable['version']==1
    for kind in ['json','csv','txt']:
        assert adapter.cycle.export_run(PRINCIPAL,run,kind)
        assert adapter.cycle.export_version(CHAIR,1,kind)
    target=os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
    if target:
        with (Path(target)/'genuine-protocol-result.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(classification='GA_WORKER_PROTOCOL_EXECUTED_IN_PROCESS_NOT_NATIVE',result=actual,
                checkpoint=checkpoint_audit(adapter.cycle,PRINCIPAL,run),original_parity='EXACT',
                native_workers=0,Edge=0,physical_exit_verified=False),stream,indent=2)


def test_native_gate_absent_before_intent_and_no_process_creation(monkeypatch):
    import services.prototype_native_transport as module
    cycle,run,_=setup();adapter=NativeAdapter(cycle)
    def forbidden(*args,**kwargs):
        pytest.fail('A worker must not be created when preservation is blocked')
    monkeypatch.setattr(module,'Process',forbidden)
    with pytest.raises(PolicyError,match='PRESERVATION_PROVIDER_UNCONFIGURED'):
        adapter.step(PRINCIPAL,run,str(uuid4()))
    assert adapter.status(PRINCIPAL,run)['attempt_count']==0
    assert cycle.inspect(PRINCIPAL,run)['sequence']==0


@pytest.mark.parametrize('kind',['unqualified','expired','future','bad_reference','client_dict'])
def test_server_preservation_findings_fail_closed_before_windows_process(kind,monkeypatch):
    import services.prototype_native_transport as module
    finding=PreservationFinding('a'*64,'FICTIONAL-OPERATOR-PROSPECTIVE-TEST',time.time(),time.time()+10,False,'UNRESOLVED')
    if kind=='expired':finding=replace(finding,current_preservation_qualified=True,expires_at=time.time()-1)
    elif kind=='future':finding=replace(finding,current_preservation_qualified=True,verified_at=time.time()+5)
    elif kind=='bad_reference':finding=replace(finding,current_preservation_qualified=True,approval_reference='CLIENT-ADMIN')
    elif kind=='client_dict':finding=vars(finding)
    class Provider:
        def current(self):return finding
    def forbidden(*a,**k):pytest.fail('No native process allowed in guard tests')
    monkeypatch.setattr(module,'Process',forbidden)
    with pytest.raises(PolicyError,match='PRESERVATION_NOT_QUALIFIED'):
        WindowsTransport(preservation_provider=Provider()).validate()


@pytest.mark.parametrize('field',['run','inner_hash','sequence','inner_parent','rng_hash','receipt','projection'])
def test_real_protocol_output_tampering_rejected_without_persisting_candidate(monkeypatch,field):
    cycle,run,_=setup();adapter=adapter_for(cycle);real=adapter.transport.execute
    def tampered(*args,**kwargs):
        result=real(*args,**kwargs)
        if field=='sequence':result[field]+=1
        elif field=='receipt':result[field]['configuration_fingerprint']='0'*64
        elif field=='projection':result[field]['best_fitness']+=1
        else:result[field]='0'*64
        return result
    monkeypatch.setattr(adapter.transport,'execute',tampered)
    with pytest.raises((PolicyError,ValueError)):
        adapter.step(PRINCIPAL,run,str(uuid4()))
    assert cycle.inspect(PRINCIPAL,run)['result'] is None
    assert not adapter.status(PRINCIPAL,run)['native_result_verified']


def test_infeasible24_versus12_rejected_before_protocol(monkeypatch):
    cycle=create(4,False);cycle.inputs.workload.save(PRINCIPAL,change(**{'2':24}))
    view,_=admit(cycle);assert view['state']=='INPUT_INFEASIBLE'
    adapter=adapter_for(cycle)
    def forbidden(*a,**k):pytest.fail('No GA execution for input-infeasible minimum')
    monkeypatch.setattr(adapter.transport,'execute',forbidden)
    with pytest.raises(PolicyError,match='INFEASIBLE'):
        adapter.step(PRINCIPAL,view['run_id'],str(uuid4()))
    assert adapter.status(PRINCIPAL,view['run_id'])['attempt_count']==0


def test_actual_protocol_minimum_violation_cannot_be_approved():
    cycle=create(2,False);cycle.inputs.workload.save(PRINCIPAL,change(**{'1':6,'2':6}))
    view,_=admit(cycle);run=view['run_id'];adapter=adapter_for(cycle)
    adapter.step(PRINCIPAL,run,str(uuid4()));result=adapter.step(PRINCIPAL,run,str(uuid4()))
    assert result['run']['result']['generated']
    assert not result['run']['result']['qualification']['fully_feasible_under_captured_policy']
    with pytest.raises(PolicyError):
        cycle.decide(CHAIR,run,Decision(request_id=str(uuid4()),expected_review=0,
            candidate_fingerprint=result['run']['latest_candidate_fingerprint'],decision='APPROVE',
            explanation='Should reject actual generated workload deficit'))


def test_initial_population_protocol_minimum_violation_cannot_be_approved():
    # Separate bounded counterexample, NOT a pass for the retained one-generation
    # case above which exceeded60seconds. Captured generations0 before admission.
    cycle=create(2,False)
    from services.ga_input_bundle import capture as bundle_capture
    from services.prototype_inputs import Inputs
    from services.prototype_tip_witness import TipWitness
    from services.prototype_cycle import Cycle
    from services.prototype_workload import WorkloadService
    data=cycle.inputs.workload.bundle.materialize(cycle.inputs.workload.bundle.run_id)
    data['configuration']['generations']=0
    bundle=bundle_capture(run_id=cycle.inputs.workload.bundle.run_id,templates=data['templates'],
        fallback_templates=data['fallback_templates'],legacy_preferences=data['legacy_preferences'],
        scoring_context=data['scoring_context'],configuration=data['configuration'],
        source_identities=json.loads(cycle.inputs.workload.bundle._raw)['source_identities'])
    workload=WorkloadService(cycle.inputs.workload.scope,bundle,FictionalGrants())
    workload.save(PRINCIPAL,change(**{'1':6,'2':6}))
    cycle=Cycle(Inputs(workload,Directory()),WorkflowDirectory(),TipWitness(),state_factory=lambda:random.Random(710).getstate())
    view,_=admit(cycle);adapter=adapter_for(cycle)
    result=adapter.step(PRINCIPAL,view['run_id'],str(uuid4()))
    assert result['run']['state']=='COMPLETED' and result['run']['result']['original_result']['generations_completed']==0
    assert not result['run']['result']['qualification']['fully_feasible_under_captured_policy']
    with pytest.raises(PolicyError,match='CONSTRAINT_VIOLATION'):
        cycle.decide(CHAIR,view['run_id'],Decision(request_id=str(uuid4()),expected_review=0,
            candidate_fingerprint=result['run']['latest_candidate_fingerprint'],decision='APPROVE',
            explanation='Genuine initialization deficit must not be approved'))


def test_actual_24_unit_minimum_through_real_protocol_in_process():
    from tests.fictional_deadline_support import minimum24_case
    from tests.test_prototype_workload import service_for
    from services.ga_input_bundle import capture as bundle_capture
    from services.prototype_workload import WorkloadService
    from services.prototype_inputs import Inputs
    from services.prototype_tip_witness import TipWitness
    from services.prototype_cycle import Cycle
    source,_=minimum24_case();data=source.materialize(source.run_id)
    data['legacy_preferences'].loc[:,'Faculty_Code']=[1,2]
    bundle=bundle_capture(run_id=source.run_id,templates=data['templates'],fallback_templates=data['fallback_templates'],
        legacy_preferences=data['legacy_preferences'],scoring_context=data['scoring_context'],
        configuration=data['configuration'],source_identities=json.loads(source._raw)['source_identities'])
    base,_=service_for();workload=WorkloadService(base.scope,bundle,FictionalGrants())
    workload.save(PRINCIPAL,change(**{'1':12,'2':24}))
    cycle=Cycle(Inputs(workload,Directory()),WorkflowDirectory(),TipWitness(),state_factory=lambda:random.Random(710).getstate())
    view,_=admit(cycle);adapter=adapter_for(cycle);run=view['run_id']
    adapter.step(PRINCIPAL,run,str(uuid4()));result=adapter.step(PRINCIPAL,run,str(uuid4()))
    assert [r['assigned_units'] for r in result['run']['result']['qualification']['faculty']]==[12,24]
    assert result['run']['result']['qualification']['fully_feasible_under_captured_policy']
    assert not result['native_result_verified']
    target=os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
    if target:
        with (Path(target)/'genuine-minimum24-protocol.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(classification='REAL_GA_PROTOCOL_IN_PROCESS_NOT_NATIVE',result=result['run']['result'],
                native_workers=0,Edge=0),stream,indent=2)


def test_stop_before_dispatch_creates_no_process_or_candidate():
    cycle,run,_=setup();adapter=adapter_for(cycle)
    assert adapter.request_stop(PRINCIPAL,run,str(uuid4()))['worker_termination_verified'] is False
    result=adapter.step(PRINCIPAL,run,str(uuid4()))
    assert result['run']['state']=='STOPPED' and not result['run']['generated']
    assert result['observations']==[] and not result['physical_exit_verified']


def test_duplicate_concurrent_ownership_is_excluded(monkeypatch):
    cycle,run,_=setup();adapter=adapter_for(cycle);real=adapter.transport.execute
    entered,release=threading.Event(),threading.Event()
    def hold(*a,**kw):
        entered.set();assert release.wait(5);return real(*a,**kw)
    monkeypatch.setattr(adapter.transport,'execute',hold)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(adapter.step,PRINCIPAL,run,str(uuid4()));assert entered.wait(5)
        try:
            with pytest.raises(PolicyError,match='RECOVERY_REQUIRED'):
                adapter.step(PRINCIPAL,run,str(uuid4()))
            other=adapter_for(cycle)
            with pytest.raises(PolicyError,match='OWNERSHIP_CONTEXT_DIFFERENT'):
                other.step(PRINCIPAL,run,str(uuid4()))
        finally:release.set()
        assert future.result(timeout=40)['run']['sequence']==1


def test_lost_ack_recovery_preserves_committed_generation_and_cold_graph(monkeypatch):
    cycle,run,_=setup();adapter=adapter_for(cycle);nonce=str(uuid4())
    def lost(*a,**kw):raise PolicyError('INJECTED_ACK_LOSS')
    monkeypatch.setattr(adapter,'_ack',lost)
    with pytest.raises(PolicyError,match='ACK_LOSS'):
        adapter.step(PRINCIPAL,run,nonce)
    assert cycle.inspect(PRINCIPAL,run)['sequence']==1
    pin=capture(cycle,PRINCIPAL,run)
    clock=lambda:time.time()+61
    reopened=reopen(pin,PRINCIPAL,workload_authority=FictionalGrants(),input_directory=Directory(),
        workflow_directory=WorkflowDirectory(clock),clock=clock)
    successor=NativeAdapter(reopened,transport=InProcessQualification(),root=adapter.journal.storage.root)
    proof=checkpoint_audit(reopened,PRINCIPAL,run)
    recovered=successor.recover(PRINCIPAL,run)
    assert recovered['supervision']['checkpoint']==proof
    assert successor.step(PRINCIPAL,run,nonce)['run']['sequence']==1
    assert successor.step(PRINCIPAL,run,str(uuid4()))['run']['state']=='COMPLETED'


def test_lost_response_after_durable_ack_does_not_poison_success(monkeypatch):
    cycle,run,_=setup();adapter=adapter_for(cycle);real=adapter._ack;nonce=str(uuid4())
    def lost(*a,**kw):real(*a,**kw);raise PolicyError('RESPONSE_LOST_AFTER_ACK')
    monkeypatch.setattr(adapter,'_ack',lost)
    with pytest.raises(PolicyError,match='RESPONSE_LOST'):
        adapter.step(PRINCIPAL,run,nonce)
    result=adapter.step(PRINCIPAL,run,nonce)
    assert result['run']['state']=='BETWEEN_SEGMENTS'
    assert result['supervision']['controller_state']=='ACKNOWLEDGED' and result['run']['sequence']==1


def test_failed_second_attempt_recovers_prior_checkpoint_without_reseeding(monkeypatch):
    cycle,run,_=setup();adapter=adapter_for(cycle)
    adapter.step(PRINCIPAL,run,str(uuid4()));before=checkpoint_audit(cycle,PRINCIPAL,run)
    real=adapter.transport.execute
    def fail(*a,**kw):raise ExchangeError('INJECTED_SEGMENT_FAILURE','INJECTED_CLEANUP_UNCERTAINTY')
    monkeypatch.setattr(adapter.transport,'execute',fail)
    with pytest.raises(ExchangeError):adapter.step(PRINCIPAL,run,str(uuid4()))
    monkeypatch.setattr(adapter.transport,'execute',real)
    monkeypatch.setattr(cycle,'clock',lambda:time.time()+61)
    cycle.directory=WorkflowDirectory(cycle.clock)
    result=adapter.recover(PRINCIPAL,run)
    assert result['supervision']['checkpoint']==before
    assert result['supervision']['history'][-1]['recovery_kind']=='RETRY_PRIOR_VERIFIED_BOUNDARY_NO_NEW_WORK'
    assert any(e.get('cleanup_code')=='INJECTED_CLEANUP_UNCERTAINTY' for e in result['supervision']['history'])
    assert adapter.step(PRINCIPAL,run,str(uuid4()))['run']['state']=='COMPLETED'


def test_simulated_exit_cannot_be_promoted_to_native_proof(completed):
    adapter,run,*_=completed
    with pytest.raises(PolicyError,match='SIMULATED_EXIT'):
        adapter._exited(run,str(uuid4()),dict(kind=adapter.transport.kind,pid=1,created_100ns=2,exit_verified=True))


@pytest.mark.parametrize('still_alive',[True,False])
def test_pid_creation_identity_probe_contract_is_readonly_simulation(monkeypatch,still_alive):
    import services.prototype_native_transport as module
    calls=[]
    def probe(pid,created):calls.append((pid,created));return still_alive
    monkeypatch.setattr(module,'alive',probe)
    assert WindowsTransport().prove_dead(123456,987654321)==(not still_alive)
    assert calls==[(123456,987654321)]  # No real PID query, kill or process creation.


@pytest.mark.parametrize('pid,created',[(None,None),(0,1),(True,1),(1,None),(1,False)])
def test_missing_or_ambiguous_process_identity_fails_before_any_OS_probe(monkeypatch,pid,created):
    import services.prototype_native_transport as module
    def forbidden(*a):pytest.fail('Invalid identity must not query or terminate an OS process')
    monkeypatch.setattr(module,'alive',forbidden)
    with pytest.raises(PolicyError,match='PROCESS_IDENTITY_REQUIRED'):
        WindowsTransport().prove_dead(pid,created)


def test_adapter_release_and_exit_record_corruption_fail_closed():
    cycle,run,_=setup();adapter=adapter_for(cycle)
    adapter.step(PRINCIPAL,run,str(uuid4()))
    import shutil,tempfile
    root=Path(tempfile.mkdtemp(prefix='ccs-prototype-workload-'))
    shutil.copytree(adapter.journal.storage.root,root,dirs_exist_ok=True)
    with pytest.raises(PolicyError,match='RELEASE_CHANGED'):
        NativeAdapter(adapter.cycle,transport=InProcessQualification(),root=root)
    with closing(adapter.journal.db()) as db,db:db.execute("UPDATE native_attempts SET raw='{}'")
    with pytest.raises(PolicyError,match='EXIT_RECORD_CORRUPT'):adapter.status(PRINCIPAL,run)
    adapter.marker.write_text('{}')
    with pytest.raises(PolicyError,match='RELEASE_CHANGED'):adapter.status(PRINCIPAL,run)
