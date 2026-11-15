"""Genuine synchronous original GA + private SQLite, never a native worker."""
from contextlib import closing
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import random
import sqlite3
import time
from uuid import uuid4
import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Owned empty-import snapshot required', allow_module_level=True)
from services.prototype_cycle import Cycle, Admission, Decision
from services.prototype_tip_witness import TipWitness
from services.prototype_inputs import Inputs, Grant
from services.prototype_workload import WorkloadService, PolicyError, digest
from tests.test_prototype_inputs import Directory, weights, preference, selection, CHAIR, CHAIR_ID, FACULTY, UNSCOPED
from tests.test_prototype_workload import bundle_for, service_for, FictionalGrants, PRINCIPAL, ACTOR, change


class WorkflowDirectory:
    """Separate initial-prototype-review mandate, not coefficient authority."""
    def __init__(self, clock=time.time):
        self.clock, self.revoked = clock, False
    def grant(self, actor, scope, action, code):
        capacity = None
        if not self.revoked:
            if actor == ACTOR and action in {'run.create', 'run.read', 'run.segment', 'run.stop', 'run.recover', 'schedule.read', 'schedule.export'}:
                capacity = 'SCHEDULER'
            if actor == CHAIR_ID and action in {'run.read', 'review.decide', 'schedule.read', 'schedule.export'}:
                capacity = 'DEPARTMENT_CHAIR'
            if actor == FACULTY.user_id and action == 'faculty.timetable' and code == 2:
                capacity = 'FACULTY_SELF'
        return Grant(actor, digest(scope.model_dump()), action, code, capacity, 'FICTIONAL-INITIAL-PROTOTYPE-SCHEDULE-MANDATE', self.clock()+120)


def make_inputs(count=2, forced=True):
    source, _ = bundle_for(count)
    from services.ga_input_bundle import capture
    data = source.materialize(source.run_id)
    if forced:
        data['templates'][1][0].eligible_subjects = {'SYN-WA'}
        data['templates'][1][1].eligible_subjects = {'SYN-WB'}
        data['scoring_context']['system_faculty'] = copy.deepcopy(data['templates'][1])
    # Correct this NEW fictional fixture before capture. Never repair a frozen
    # input or alter the original analysis/priority equation after admission.
    data['legacy_preferences'].loc[:, 'Faculty_Code'] = [1, 2]
    base, _ = service_for()
    bundle = capture(run_id=source.run_id, templates=data['templates'], fallback_templates=data['fallback_templates'],
        legacy_preferences=data['legacy_preferences'], scoring_context=data['scoring_context'],
        configuration=data['configuration'], source_identities=json.loads(source._raw)['source_identities'])
    workload = WorkloadService(base.scope, bundle, FictionalGrants())
    return Inputs(workload, Directory())


def create(count=2, forced=True):
    inputs = make_inputs(count, forced)
    witness = TipWitness()
    service = Cycle(inputs, WorkflowDirectory(), witness, offline_qualification=True,
                    state_factory=lambda: random.Random(710).getstate())
    return service


def admit(s):
    p = s.inputs.prepare(PRINCIPAL, selection(s.inputs))
    request = Admission(request_id=str(uuid4()), preparation_id=p['preparation_id'])
    return s.admit(PRINCIPAL, request), request


def finish(s, run):
    for _ in range(3):
        view = s.inspect(PRINCIPAL, run)
        if view['state'] in {'COMPLETED', 'STOPPED'}:
            return view
        s.step_offline(PRINCIPAL, run)
    pytest.fail('Finite two-generation test did not complete')


@pytest.fixture(scope='module')
def generated():
    s = create()
    s.inputs.workload.save(PRINCIPAL, change(**{'2': 3}))
    s.inputs.approve_weights(CHAIR, weights(day_penalty=17))
    s.inputs.save_preference(FACULTY, 2, preference(preferred_subjects=['SYN-WB'], preferred_days=['S'], use_day_preference=True, day_importance=5))
    admitted, command = admit(s)
    bundle = s.inputs.prepared(PRINCIPAL, command.preparation_id, internal_bundle=True)
    from services.ga_bundle_optimizer import Session
    before = random.getstate()
    oracle = Session(bundle, run_id=bundle.run_id, random_state=random.Random(710).getstate())
    expected = oracle.run()  # Genuine original algorithm, not a constructed witness.
    first = s.step_offline(PRINCIPAL, admitted['run_id'])
    assert first['sequence'] == 1 and first['state'] == 'BETWEEN_SEGMENTS'
    # Reconstruct BOTH durable services from their actual private SQLite files.
    witness = TipWitness(root=s.witness.storage.root, key_fingerprint=s.witness.key_fingerprint)
    s = Cycle(s.inputs, WorkflowDirectory(), witness, root=s.storage.root, offline_qualification=True)
    final = finish(s, admitted['run_id'])
    assert random.getstate() == before
    yield s, command, final, oracle, expected


def test_genuine_frozen_consumption_qualification_and_resume_parity(generated):
    s, command, actual, oracle, expected = generated
    result = actual['result']['original_result']
    for key in ['schedule', 'best_fitness', 'history', 'fitness_breakdown', 'faculty_analysis']:
        assert result[key] == expected[key]
    assert len({(r['subject'], r['section']) for r in result['schedule']}) == 2 and result['generations_completed'] == 1
    assert actual['result']['qualification']['fully_feasible_under_captured_policy']
    assert actual['result']['qualification']['faculty'][1]['assigned_units'] == 3
    assert actual['result']['provenance']['weights_policy']['body']['day_penalty'] == 17
    assert actual['result']['receipt']['verification_status'] == 'VERIFIED'
    assert actual['generated'] and not actual['native_verified'] and not actual['browser_verified']
    assert result['saved_best_updated'] is False
    with closing(s.db()) as db:
        admission, row, control, segments = s._read(db, actual['run_id'])
        restored = s._session(admission, row, segments)
        matches = restored.resume_state['random_state'] == oracle.runtime.random.getstate()
        assert matches, 'Checkpoint must retain the exact uninterrupted RNG state'
        restored.control.request_stop()
        restored.run()  # Runtime applies restored RNG when execution begins.
        matches = restored.runtime.random.getstate() == oracle.runtime.random.getstate()
        assert matches, 'Restored finalization must not advance RNG'
    folder = os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
    if folder:
        (Path(folder)/'genuine-inprocess-result.json').write_text(json.dumps(dict(scope='GENUINE_ORIGINAL_GA_OFFLINE_NOT_NATIVE_OR_BROWSER',
            schedule_fitness_history_rng_parity=True, service_and_SQLite_reconstruction=True, OS_process_restart=False,
            result=actual), indent=2)+'\n', encoding='utf-8')


def test_source_revision_changes_do_not_replace_captured_input(generated):
    s = create(); record, command = admit(s); result = finish(s, record['run_id'])
    s.inputs.approve_weights(CHAIR, weights(day_penalty=21))
    assert s.inspect(PRINCIPAL, result['run_id'])['result'] == result['result']
    assert s.admit(PRINCIPAL, command)['result'] == result['result']
    with pytest.raises(PolicyError, match='CURRENT_REVIEW_INPUTS_CHANGED'):
        s.decide(CHAIR, result['run_id'], Decision(request_id=str(uuid4()), expected_review=0,
            candidate_fingerprint=result['latest_candidate_fingerprint'], decision='APPROVE', explanation='A changed input policy requires a new generated candidate.'))
    assert s.versions(CHAIR) == []


def test_approval_requires_separate_chair_grant_and_creates_immutable_version(generated):
    s, _command, result, _oracle, _expected = generated
    command = Decision(request_id=str(uuid4()), expected_review=0, candidate_fingerprint=result['latest_candidate_fingerprint'],
        decision='APPROVE', explanation='Fictional generated candidate and workload were reviewed.')
    with pytest.raises(PolicyError):
        s.decide(PRINCIPAL, result['run_id'], command)
    approved = s.decide(CHAIR, result['run_id'], command)
    assert s.decide(CHAIR, result['run_id'], command) == approved
    versions = s.versions(CHAIR)
    assert len(versions) == 1 and versions[0]['candidate'] == result['result']
    assert not versions[0]['institutional_publication']
    faculty_view = s.timetable(FACULTY, 2)
    assert faculty_view['version'] == 1 and faculty_view['workload']['assigned_units'] == 3
    assert all(row['faculty'] == '2' for row in faculty_view['schedule'])
    with pytest.raises(PolicyError):
        s.timetable(FACULTY, 1)
    with closing(s.db()) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM versions')
    for kind in ['json', 'csv', 'txt']:
        exported = s.export_version(CHAIR, 1, kind)
        assert result['run_id'] in exported
    with pytest.raises(PolicyError):
        s.decide(CHAIR, result['run_id'], Decision.model_validate(command.model_dump() | {'request_id': str(uuid4()), 'expected_review': 1, 'decision': 'REJECT'}))


def test_input_infeasible24_versus12_is_durable_before_any_GA():
    s = create(4, forced=False)
    s.inputs.workload.save(PRINCIPAL, change(**{'2': 24}))
    result, _ = admit(s)
    assert result['state'] == 'INPUT_INFEASIBLE' and not result['generated']
    assert result['shortages'] == [dict(faculty_code=2, minimum=24, eligible_units=12, shortage=12)]
    with pytest.raises(PolicyError):
        s.step_offline(PRINCIPAL, result['run_id'])
    with closing(s.db()) as db:
        assert db.execute('SELECT COUNT(*) FROM segments').fetchone()[0] == 0


def test_legacy_priority_cohort_mismatch_is_rejected_before_execution():
    workload, _ = service_for()
    inputs = Inputs(workload, Directory())  # Original characterization fixture has unrelated legacy codes.
    s = Cycle(inputs, WorkflowDirectory(), TipWitness(), offline_qualification=True)
    with pytest.raises(PolicyError, match='COHORT_PRIORITY'):
        admit(s)
    with closing(s.db()) as db:
        assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0


def test_unqualified_execution_and_missing_witness_fail_closed():
    inputs = make_inputs()
    s = Cycle(inputs, WorkflowDirectory())
    with pytest.raises(PolicyError):
        admit(s)
    with closing(s.db()) as db:
        assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0
    s = Cycle(inputs, WorkflowDirectory(), TipWitness())
    result, _ = admit(s)
    with pytest.raises(PolicyError, match='NATIVE_EXECUTION_UNQUALIFIED'):
        s.step_offline(PRINCIPAL, result['run_id'])


def test_stop_before_execution_never_generates_and_no_termination_claim():
    s = create()
    result, _ = admit(s)
    acknowledgement = s.request_stop(PRINCIPAL, result['run_id'])
    assert not acknowledgement['termination_verified']
    stopped = s.step_offline(PRINCIPAL, result['run_id'])
    assert stopped['state'] == 'STOPPED' and not stopped['generated']


def test_corrupted_checkpoint_and_witness_rollback_are_rejected(generated):
    s, _command, result, _oracle, _expected = generated
    # Copy only OUR new database, never a repository/historical store.
    import shutil
    clone = create()
    with closing(s.db()) as source, closing(clone.db()) as destination:
        source.backup(destination)
    # Different store/binding/witness cannot reinterpret the copied records.
    with pytest.raises(PolicyError):
        clone.inspect(PRINCIPAL, result['run_id'])
    with pytest.raises(PolicyError):
        clone.versions(CHAIR)
    assert s.inspect(PRINCIPAL, result['run_id'])['generated']


def test_cross_owner_and_unscoped_review_denied(generated):
    s, _command, result, _oracle, _expected = generated
    for operation in [lambda: s.inspect(UNSCOPED, result['run_id']), lambda: s.request_stop(CHAIR, result['run_id']),
                      lambda: s.export_version(UNSCOPED, 1, 'json')]:
        with pytest.raises(PolicyError):
            operation()


@pytest.mark.parametrize('decision', ['REJECT', 'REQUEST_REVISION'])
def test_generated_candidate_rejection_or_revision_request_is_immutable(decision):
    s = create()
    result, _ = admit(s)
    result = finish(s, result['run_id'])
    record = s.decide(CHAIR, result['run_id'], Decision(request_id=str(uuid4()), expected_review=0,
        candidate_fingerprint=result['latest_candidate_fingerprint'], decision=decision,
        explanation='Fictional reviewer requests a separately generated revision.'))
    assert record['decision'] == decision and s.versions(CHAIR) == []


def test_different_weight_contexts_are_incomparable_without_Saved_Best_writes():
    s = create()
    first, _ = admit(s); first = finish(s, first['run_id'])
    s.inputs.approve_weights(CHAIR, weights(day_penalty=99))
    second, _ = admit(s); second = finish(s, second['run_id'])
    comparison = s.compare(PRINCIPAL, first['run_id'], second['run_id'])
    assert comparison['classification'] == 'INCOMPARABLE' and comparison['fitness_difference'] is None and not comparison['best_saved']


def test_actual_24_unit_generated_demo_uses_original_engine():
    from tests.fictional_deadline_support import minimum24_case
    from services.ga_input_bundle import capture
    source, _ = minimum24_case()
    data = source.materialize(source.run_id)
    data['legacy_preferences'].loc[:, 'Faculty_Code'] = [1, 2]
    bundle = capture(run_id=source.run_id, templates=data['templates'], fallback_templates=data['fallback_templates'],
        legacy_preferences=data['legacy_preferences'], scoring_context=data['scoring_context'],
        configuration=data['configuration'], source_identities=json.loads(source._raw)['source_identities'])
    base, _ = service_for()
    workload = WorkloadService(base.scope, bundle, FictionalGrants())
    workload.save(PRINCIPAL, change(**{'1': 12, '2': 24}))
    inputs = Inputs(workload, Directory())
    s = Cycle(inputs, WorkflowDirectory(), TipWitness(), offline_qualification=True, state_factory=lambda: random.Random(710).getstate())
    record, _ = admit(s)
    final = finish(s, record['run_id'])
    assert [r['assigned_units'] for r in final['result']['qualification']['faculty']] == [12, 24]
    assert final['result']['qualification']['fully_feasible_under_captured_policy']
    folder = os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
    if folder:
        (Path(folder)/'genuine-minimum24-result.json').write_text(json.dumps(dict(scope='GENUINELY_GENERATED_ORIGINAL_GA_IN_PROCESS_NOT_CONSTRUCTED_NOT_NATIVE', result=final), indent=2)+'\n', encoding='utf-8')


def test_actual_generated_minimum_violation_cannot_be_approved():
    s = create(2, forced=False)
    # Individual capacity6 each is only an upper bound, not joint feasibility.
    s.inputs.workload.save(PRINCIPAL, change(**{'1': 6, '2': 6}))
    record, _ = admit(s)
    final = finish(s, record['run_id'])
    assert not final['result']['qualification']['fully_feasible_under_captured_policy']
    assert any(r['minimum_deficit'] > 0 for r in final['result']['qualification']['faculty'])
    with pytest.raises(PolicyError, match='CONSTRAINT_VIOLATION'):
        s.decide(CHAIR, record['run_id'], Decision(request_id=str(uuid4()), expected_review=0,
            candidate_fingerprint=final['latest_candidate_fingerprint'], decision='APPROVE', explanation='This must be denied due to the generated workload deficit.'))
    assert s.versions(CHAIR) == []


def test_logical_interruption_recovery_fences_old_owner_without_new_rng():
    s = create()
    record, _ = admit(s)
    partial = s.step_offline(PRINCIPAL, record['run_id'])
    with closing(s.db()) as db, db:
        db.execute("UPDATE control SET owner=?,lease=0,state='QUALIFICATION_RUNNING',fence=fence+1 WHERE run=?", (str(uuid4()), record['run_id']))
    resumed = Cycle(s.inputs, WorkflowDirectory(), TipWitness(root=s.witness.storage.root, key_fingerprint=s.witness.key_fingerprint),
        root=s.storage.root, offline_qualification=True)
    recovered = resumed.recover(PRINCIPAL, record['run_id'])
    assert recovered['tip'] == partial['tip'] and recovered['state'] == 'BETWEEN_SEGMENTS'
    assert finish(resumed, record['run_id'])['state'] == 'COMPLETED'


def test_checkpoint_bytes_and_separate_witness_reject_corruption_and_rollback():
    s = create(); record, _ = admit(s); run = record['run_id']
    first = s.step_offline(PRINCIPAL, run)
    backup_path = s.storage.root/'qualification-first-tip.sqlite3'
    with closing(s.db()) as source, closing(sqlite3.connect(backup_path)) as destination:
        source.backup(destination)
    final = finish(s, run)
    assert final['sequence'] > first['sequence']
    # Simulated restore of ONLY this newly created disposable primary store.
    # The separate witness retains the final tip and must reject rollback.
    with closing(sqlite3.connect(backup_path)) as source, closing(s.db()) as destination:
        source.backup(destination)
    with pytest.raises(PolicyError, match='WITNESS_MISMATCH'):
        s.inspect(PRINCIPAL, run)
    t = create(); record, _ = admit(t); t.step_offline(PRINCIPAL, record['run_id'])
    with closing(t.db()) as db, db:
        db.execute('DROP TRIGGER immutable_segments_UPDATE')
        db.execute("UPDATE segments SET checkpoint=X'00'")
    with pytest.raises(PolicyError, match='SEGMENT_CORRUPT'):
        t.inspect(PRINCIPAL, record['run_id'])


def test_cross_run_checkpoint_graft_rejected_before_resume():
    s = create(); first, _ = admit(s); s.step_offline(PRINCIPAL, first['run_id'])
    second, _ = admit(s)
    with closing(s.db()) as db, db:
        row = db.execute('SELECT * FROM segments WHERE run=?', (first['run_id'],)).fetchone()
        db.execute('INSERT INTO segments VALUES(?,?,?,?,?,?)', (second['run_id'], row['sequence'], row['raw'], row['hash'], row['checkpoint'], row['result']))
        db.execute('UPDATE control SET sequence=?,tip=? WHERE run=?', (row['sequence'], row['hash'], second['run_id']))
    with pytest.raises(PolicyError, match='SEGMENT_CORRUPT'):
        s.inspect(PRINCIPAL, second['run_id'])


def test_execution_failure_is_durable_and_preserves_primary_error(monkeypatch):
    s = create(); record, _ = admit(s)
    def fail(*_args):
        raise PolicyError('FICTIONAL_EXECUTION_FAILURE')
    monkeypatch.setattr(s, '_session', fail)
    with pytest.raises(PolicyError, match='FICTIONAL_EXECUTION_FAILURE'):
        s.step_offline(PRINCIPAL, record['run_id'])
    result = s.inspect(PRINCIPAL, record['run_id'])
    assert result['state'] == 'FAILED_NO_CHECKPOINT' and not result['generated']
    assert result['commands'][-1]['code'] == 'FICTIONAL_EXECUTION_FAILURE'


def test_witness_commit_uncertainty_retains_checkpoint_and_blocks_recovery(monkeypatch):
    s = create(); record, _ = admit(s)
    def unavailable(*_args):
        raise PolicyError('FICTIONAL_WITNESS_COMMIT_FAILURE')
    monkeypatch.setattr(s.witness, 'advance', unavailable)
    with pytest.raises(PolicyError, match='FICTIONAL_WITNESS_COMMIT_FAILURE'):
        s.step_offline(PRINCIPAL, record['run_id'])
    with closing(s.db()) as db:
        assert db.execute('SELECT COUNT(*) FROM segments').fetchone()[0] == 1
        assert db.execute('SELECT state FROM control WHERE run=?', (record['run_id'],)).fetchone()[0] == 'QUARANTINED_COMMIT_UNCERTAINTY'
    with pytest.raises(PolicyError, match='WITNESS_MISMATCH'):
        s.recover(PRINCIPAL, record['run_id'])


def test_quota_check_rejects_before_writes_and_does_not_delete_history():
    from services.prototype_cycle import MAX_STORED_BYTES
    s = create(); record, _ = admit(s)
    with closing(s.db()) as db:
        before = db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
        with pytest.raises(PolicyError, match='DURABLE_STORAGE_CAPACITY'):
            s.capacity(db, MAX_STORED_BYTES)
        assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == before
    assert s.inspect(PRINCIPAL, record['run_id'])['state'] == 'ADMITTED_NATIVE_BLOCKED'


def test_new_frozen_revision_creates_version2_without_mutating_version1():
    s = create(); first, _ = admit(s); first = finish(s, first['run_id'])
    s.decide(CHAIR, first['run_id'], Decision(request_id=str(uuid4()), expected_review=0,
        candidate_fingerprint=first['latest_candidate_fingerprint'], decision='APPROVE',
        explanation='First fictional generated schedule approved after validation.'))
    original = copy.deepcopy(s.versions(CHAIR)[0])
    s.inputs.approve_weights(CHAIR, weights(day_penalty=99))
    second, _ = admit(s); second = finish(s, second['run_id'])
    s.decide(CHAIR, second['run_id'], Decision(request_id=str(uuid4()), expected_review=0,
        candidate_fingerprint=second['latest_candidate_fingerprint'], decision='APPROVE',
        explanation='New frozen coefficient revision and generated schedule reviewed.'))
    versions = s.versions(CHAIR)
    assert len(versions) == 2 and versions[0] == original
    assert versions[1]['previous'] == versions[0]['fingerprint'] and versions[1]['run_id'] == second['run_id']
    assert s.timetable(FACULTY, 2)['version'] == 2
    assert s.compare(PRINCIPAL, first['run_id'], second['run_id'])['classification'] == 'INCOMPARABLE'
