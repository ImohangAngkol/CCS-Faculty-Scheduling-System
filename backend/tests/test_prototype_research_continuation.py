"""Original GA in-process only; no native worker, browser or institution data."""
from contextlib import closing
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
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

from services.prototype_workload import PolicyError, digest
from services.prototype_recovery_bootstrap import capture, reopen
from services.prototype_continuation_supervisor import Supervisor, checkpoint_audit, storage_report
from tests.test_prototype_cycle import create, admit, WorkflowDirectory
from tests.test_prototype_inputs import Directory, CHAIR, FACULTY, weights, preference
from tests.test_prototype_workload import PRINCIPAL, FictionalGrants, change, OTHER
from services.preference_authorization import PreferencePrincipal


def rebuild(pin, **overrides):
    values = dict(workload_authority=FictionalGrants(), input_directory=Directory(),
                  workflow_directory=WorkflowDirectory(), offline_qualification=True)
    values.update(overrides)
    return reopen(pin, PRINCIPAL, **values)


@pytest.fixture(scope='module')
def continued():
    cycle = create()
    cycle.inputs.workload.save(PRINCIPAL, change(**{'2': 3}))
    cycle.inputs.approve_weights(CHAIR, weights(day_penalty=17))
    cycle.inputs.save_preference(FACULTY, 2, preference(preferred_subjects=['SYN-WB'],
        preferred_days=['S'], use_day_preference=True, day_importance=5))
    view, command = admit(cycle)
    run = view['run_id']
    bundle = cycle.inputs.prepared(PRINCIPAL, command.preparation_id, internal_bundle=True)
    from services.ga_bundle_optimizer import Session
    oracle = Session(bundle, run_id=bundle.run_id, random_state=random.Random(710).getstate())
    before = random.getstate()
    expected = oracle.run()
    pin = capture(cycle, PRINCIPAL, run)
    supervisor = Supervisor(cycle, offline_qualification=True)
    nonce = str(uuid4())
    first = supervisor.step_offline(PRINCIPAL, run, nonce)
    assert first['checkpoint']['generation'] == 0
    assert supervisor.step_offline(PRINCIPAL, run, nonce) == first
    # Rebuild ALL source/policy/input/cycle/witness objects, not just listener.
    rebuilt = rebuild(pin)
    assert rebuilt.inputs is not cycle.inputs
    assert rebuilt.inputs.workload is not cycle.inputs.workload
    successor = Supervisor(rebuilt, root=supervisor.storage.root, offline_qualification=True)
    result = successor.step_offline(PRINCIPAL, run, str(uuid4()))
    assert result['cycle_state'] == 'COMPLETED'
    assert random.getstate() == before
    yield successor, pin, run, oracle, expected


def test_full_bootstrap_exact_original_GA_and_RNG_parity(continued):
    sup, pin, run, oracle, expected = continued
    actual = sup.cycle.inspect(PRINCIPAL, run)['result']
    for key in ['schedule', 'best_fitness', 'history', 'fitness_breakdown', 'faculty_analysis']:
        assert actual['original_result'][key] == expected[key]
    assert actual['qualification']['fully_feasible_under_captured_policy']
    assert actual['provenance']['weights_policy']['body']['day_penalty'] == 17
    assert actual['qualification']['faculty'][1]['assigned_units'] == 3
    from services.ga_checkpoint_service import rng_to_json
    proof = checkpoint_audit(sup.cycle, PRINCIPAL, run)
    assert proof['RNG_fingerprint'] == digest(rng_to_json(oracle.runtime.random.getstate()))
    assert proof['population'] > 0 and proof['best_ever_present'] and proof['history_points'] == 2
    assert proof['next_generation'] == 2 and proof['generation'] == 1
    assert proof['original_codec_verified'] and not proof['native_verified']
    status = sup.status(PRINCIPAL, run)
    assert status['physical_termination'] == 'NOT_VERIFIED' and status['seven_day'] == 'NO_GO'
    target = os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
    if target:
        with (Path(target)/'genuine-continuation.json').open('x', encoding='utf-8') as stream:
            json.dump(dict(checkpoint=proof, original_fitness=expected['best_fitness'],
                history=expected['history'], result=actual, segmented_vs_uninterrupted='EXACT_MATCH',
                source_objects_rebuilt=True, OS_process_restart=False, native_workers=0, browsers=0), stream, indent=2)


def test_measured_storage_and_explicit_seven_day_scenario(continued):
    sup, _pin, run, _oracle, _expected = continued
    report = storage_report(sup.cycle, PRINCIPAL, run)
    assert len(report['checkpoint_bytes']) == report['segments'] == 2
    assert all(0 < n <= 8*1024*1024 for n in report['checkpoint_bytes'])
    assert report['hypothetical_7day_checkpoint_count'] == 1008
    assert report['existing_lifetime_seconds'] == 600 and report['checkpoint_count_cap'] == 8
    assert report['future_generations'] is None and report['seven_day'] == 'NO_GO'
    assert report['hypothetical_constant_size_checkpoint_bytes'] == 1008*max(report['checkpoint_bytes'])
    assert set(report['current_export_bytes']) == {'json', 'csv', 'txt'}
    target = os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
    if target:
        with (Path(target)/'storage-measurement.json').open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)


@pytest.mark.parametrize('field', ['document_sha256', 'cycle_binding', 'storage_binding', 'witness_key_fingerprint', 'run_id'])
def test_external_pin_mismatch_rejected(continued, field):
    _sup, pin, _run, _oracle, _expected = continued
    with pytest.raises((PolicyError, ValueError)):
        rebuild(replace(pin, **{field: '0'*64}))


def test_no_authority_or_client_roles_reconstructed_from_stored_labels(continued):
    _sup, pin, _run, _oracle, _expected = continued
    with pytest.raises(PolicyError, match='FRESH_AUTHORITY'):
        reopen(pin, PRINCIPAL)
    class Denied:
        def grant(self, *args):
            return None
    with pytest.raises(PolicyError, match='SCOPED_GRANT'):
        rebuild(pin, input_directory=Denied())
    directory = WorkflowDirectory(); directory.revoked = True
    with pytest.raises(PolicyError, match='SCOPED_AUTHORITY'):
        rebuild(pin, workflow_directory=directory)
    other = PreferencePrincipal('admin', user_id=OTHER)
    with pytest.raises(PolicyError):
        reopen(pin, other, workload_authority=FictionalGrants(), input_directory=Directory(), workflow_directory=WorkflowDirectory())


def test_bootstrap_defaults_cannot_execute_or_recover(continued):
    _sup, pin, run, _oracle, _expected = continued
    cycle = rebuild(pin, offline_qualification=False)
    assert not cycle.offline_qualification
    with pytest.raises(PolicyError, match='NATIVE_EXECUTION_UNQUALIFIED'):
        cycle.step_offline(PRINCIPAL, run)
    supervisor = Supervisor(cycle)
    with pytest.raises(PolicyError, match='NATIVE_TRANSPORT_UNQUALIFIED'):
        supervisor.step_offline(PRINCIPAL, run, str(uuid4()))
    with pytest.raises(PolicyError, match='NATIVE_RECOVERY_UNQUALIFIED'):
        supervisor.reconcile_offline(PRINCIPAL, run)


def test_descriptor_tamper_and_missing_file_fail_closed(continued):
    sup, _pin, run, _oracle, _expected = continued
    pin = capture(sup.cycle, PRINCIPAL, run)
    path = Path(pin.root)/'bootstrap.json'
    raw = path.read_bytes(); path.write_bytes(raw+b' ')
    with pytest.raises(PolicyError, match='PIN_MISMATCH'):
        rebuild(pin)
    path.unlink()  # Only this test's NEW private descriptor, not historical data.
    with pytest.raises(PolicyError, match='FILE_INVALID'):
        rebuild(pin)


def test_readonly_full_reopen_changes_no_private_store_bytes(continued):
    sup, pin, run, _oracle, _expected = continued
    roots = [sup.cycle.storage.root, sup.cycle.inputs.storage.root, sup.cycle.inputs.workload.store.root,
             sup.cycle.witness.storage.root, sup.storage.root, Path(pin.root)]
    def snapshot():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for root in roots for p in root.iterdir() if p.is_file()}
    before = snapshot()
    cycle = rebuild(pin)
    checkpoint_audit(cycle, PRINCIPAL, run)
    assert snapshot() == before


def test_fresh_process_readonly_bootstrap_decodes_exact_checkpoint_without_GA(continued):
    sup, pin, run, _oracle, _expected = continued
    roots = [sup.cycle.storage.root, sup.cycle.inputs.storage.root, sup.cycle.inputs.workload.store.root,
             sup.cycle.witness.storage.root, Path(pin.root)]
    def snapshot():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for root in roots for p in root.iterdir() if p.is_file()}
    before = snapshot()
    nonce = str(uuid4())
    probe = Path(__file__).resolve().parents[2]/'docs/testing/scheduling-first-accelerated-3/cold_metadata_probe.py'
    child = subprocess.run([sys.executable, '-B', str(probe)], input=json.dumps(dict(pin=asdict(pin), nonce=nonce)),
        text=True, encoding='utf-8', capture_output=True, timeout=30)
    assert child.returncode == 0, 'Fresh metadata probe failed; no worker was launched'
    result = json.loads(child.stdout)
    assert result['nonce'] == nonce and result['checkpoint'] == checkpoint_audit(sup.cycle, PRINCIPAL, run)
    assert result['native_workers'] == result['GA_executions'] == result['Session_run_calls'] == 0
    assert snapshot() == before
    target = os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
    if target:
        with (Path(target)/'cold-process-metadata.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)


def test_lost_ack_reconciliation_does_not_repeat_generation(monkeypatch):
    cycle = create(); view, _command = admit(cycle); run = view['run_id']
    supervisor = Supervisor(cycle, offline_qualification=True)
    real_ack = supervisor._ack
    def fail_ack(*args):
        raise PolicyError('ACKNOWLEDGEMENT_INTERRUPTED')
    monkeypatch.setattr(supervisor, '_ack', fail_ack)
    nonce = str(uuid4())
    with pytest.raises(PolicyError, match='ACKNOWLEDGEMENT_INTERRUPTED'):
        supervisor.step_offline(PRINCIPAL, run, nonce)
    assert cycle.inspect(PRINCIPAL, run)['sequence'] == 1
    with pytest.raises(PolicyError, match='RECOVERY_REQUIRED'):
        supervisor.step_offline(PRINCIPAL, run, str(uuid4()))
    monkeypatch.setattr(supervisor, '_ack', real_ack)
    monkeypatch.setattr(supervisor, 'clock', lambda: time.time()+61)
    recovered = supervisor.reconcile_offline(PRINCIPAL, run)
    assert recovered['checkpoint']['generation'] == 0
    assert recovered['history'][-1]['event'] == 'RECOVERED_COMMITTED_SEGMENT'
    assert supervisor.step_offline(PRINCIPAL, run, nonce) == recovered
    assert cycle.inspect(PRINCIPAL, run)['sequence'] == 1


def test_duplicate_concurrent_dispatch_rejected_and_no_fresh_run_recovery(monkeypatch):
    cycle = create(); view, _ = admit(cycle); run = view['run_id']
    sup = Supervisor(cycle, offline_qualification=True)
    entered, release = threading.Event(), threading.Event()
    def hold(*args):
        entered.set(); assert release.wait(5)
        raise PolicyError('INJECTED_BEFORE_EXECUTION')
    monkeypatch.setattr(cycle, 'step_offline', hold)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(sup.step_offline, PRINCIPAL, run, str(uuid4()))
        assert entered.wait(5)
        try:
            with pytest.raises(PolicyError, match='RECOVERY_REQUIRED'):
                sup.step_offline(PRINCIPAL, run, str(uuid4()))
        finally:
            release.set()
        with pytest.raises(PolicyError, match='INJECTED_BEFORE_EXECUTION'):
            future.result(timeout=5)
    assert cycle.inspect(PRINCIPAL, run)['sequence'] == 0
    monkeypatch.setattr(sup, 'clock', lambda: time.time()+61)
    with pytest.raises(PolicyError, match='NO_RECOVERABLE_COMMITTED_SEGMENT'):
        sup.reconcile_offline(PRINCIPAL, run)


def test_stop_is_durable_idempotent_and_not_worker_termination():
    cycle = create(); view, _ = admit(cycle); run = view['run_id']
    sup = Supervisor(cycle, offline_qualification=True)
    nonce = str(uuid4())
    first = sup.request_stop(PRINCIPAL, run, nonce)
    assert sup.request_stop(PRINCIPAL, run, nonce) == first
    assert first['worker_termination_verified'] is False
    result = sup.step_offline(PRINCIPAL, run, str(uuid4()))
    assert result['cycle_state'] == 'STOPPED' and not result['checkpoint']['present']
    assert len([e for e in result['history'] if e['event'] == 'STOP_REQUEST_RECORDED']) == 1


def test_storage_exhaustion_rejects_before_dispatch(monkeypatch):
    import services.prototype_continuation_supervisor as module
    cycle = create(); view, _ = admit(cycle); run = view['run_id']
    sup = Supervisor(cycle, offline_qualification=True)
    monkeypatch.setattr(module, 'MAX_LOGICAL_BYTES', 1)
    with pytest.raises(PolicyError, match='STORAGE_CAPACITY'):
        sup.step_offline(PRINCIPAL, run, str(uuid4()))
    assert cycle.inspect(PRINCIPAL, run)['sequence'] == 0
    assert sup.status(PRINCIPAL, run)['history'] == []


def test_checkpoint_corruption_and_missing_checkpoint_rejected(continued):
    sup, _pin, run, _oracle, _expected = continued
    from services.prototype_cycle import Cycle
    cloned = Path(tempfile.mkdtemp(prefix='ccs-prototype-workload-'))
    shutil.copytree(sup.cycle.storage.root, cloned, dirs_exist_ok=True)
    cycle = Cycle(sup.cycle.inputs, WorkflowDirectory(), sup.cycle.witness, root=cloned)
    with closing(cycle.db()) as db, db:
        db.execute('DROP TRIGGER immutable_segments_update')
        db.execute('UPDATE segments SET checkpoint=? WHERE run=? AND sequence=2', (b'corrupt', run))
    with pytest.raises(PolicyError, match='SEGMENT_CORRUPT'):
        checkpoint_audit(cycle, PRINCIPAL, run)
    with closing(cycle.db()) as db, db:
        db.execute('DROP TRIGGER immutable_segments_delete')
        db.execute('DELETE FROM segments WHERE run=?', (run,))
    with pytest.raises(PolicyError, match='TIP_CORRUPT'):
        checkpoint_audit(cycle, PRINCIPAL, run)


def test_journal_events_immutable_and_corruption_detected(continued):
    sup, _pin, run, _oracle, _expected = continued
    fresh = Supervisor(sup.cycle)
    with closing(fresh.db()) as db, db:
        fresh._append(db, run, 'SYNTHETIC_JOURNAL_FAULT_FIXTURE')
    with closing(fresh.db()) as db:
        with pytest.raises(sqlite3.IntegrityError, match='immutable'):
            db.execute("UPDATE events SET hash='broken'")
    with closing(fresh.db()) as db, db:
        db.execute('DROP TRIGGER immutable_events_update')
        db.execute("UPDATE events SET hash='broken'")
    with pytest.raises(PolicyError, match='EVENT_CORRUPT'):
        fresh.status(PRINCIPAL, run)


@pytest.mark.parametrize('field,value', [('nonce', 'tampered'), ('owner', 'tampered'), ('fence', 999),
    ('before_sequence', 999), ('before_tip', 'tampered'), ('observed_sequence', 999),
    ('lease', 999), ('state', 'ACTIVE')])
def test_mutable_claim_cannot_disagree_with_immutable_dispatch_journal(continued, field, value):
    sup, _pin, run, _oracle, _expected = continued
    root = Path(tempfile.mkdtemp(prefix='ccs-prototype-workload-'))
    shutil.copytree(sup.storage.root, root, dirs_exist_ok=True)
    clone = Supervisor(sup.cycle, root=root)
    with closing(clone.db()) as db, db:
        db.execute('UPDATE claims SET '+field+'=? WHERE run=?', (value, run))
    with pytest.raises(PolicyError, match='CLAIM_JOURNAL_MISMATCH'):
        clone.status(PRINCIPAL, run)
