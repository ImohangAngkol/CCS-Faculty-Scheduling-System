"""Offline real SQLite/API/scorer checks. No worker, browser or GA search."""
from contextlib import closing
from dataclasses import replace
import copy
import json
import random
import secrets
import sqlite3
import time
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Owned fictional snapshot required', allow_module_level=True)
from services.prototype_inputs import Inputs, Grant, Weights, Preference, Freeze, PENALTIES
from services.prototype_workload import PolicyError, digest
from services.preference_authorization import PreferencePrincipal
from tests.test_prototype_workload import service_for, arranged, change, PRINCIPAL, ACTOR, VIEWER, OTHER

CHAIR_ID = '00000000-0000-4000-8000-000000007561'
CHAIR = PreferencePrincipal('admin', user_id=CHAIR_ID)
FACULTY_ID = '00000000-0000-4000-8000-000000007562'
FACULTY = PreferencePrincipal('faculty', faculty_id='00000000-0000-4000-8000-000000007563', user_id=FACULTY_ID)
UNSCOPED = PreferencePrincipal('admin', user_id=OTHER)


class Directory:
    """Explicit fictional grants; account role alone never grants Chair power."""
    denied = False
    def grant(self, actor, scope, action, code):
        capacity = None
        if not self.denied:
            if actor == CHAIR_ID and action in {'weights.approve', 'weights.read'} and code is None:
                capacity = 'DEPARTMENT_CHAIR'
            elif actor == FACULTY_ID and (action in {'preferences.read', 'preferences.write'} and code == 2 or action == 'weights.read' and code is None):
                capacity = 'FACULTY_SELF'
            elif actor == ACTOR and action in {'prepare', 'prepared.read', 'weights.read'} and code is None:
                capacity = 'SCHEDULER'
        return Grant(actor, digest(scope.model_dump()), action, code, capacity, 'FICTIONAL-INPUT-GRANT', time.time()+120)


def configured():
    workload, values = service_for(8)
    return Inputs(workload, Directory()), values


def weights(revision=0, **penalties):
    return Weights(request_id=str(uuid4()), expected_revision=revision, penalties=penalties or {'subject_penalty': 140})


def preference(revision=0, **values):
    return Preference.model_validate(dict(request_id=str(uuid4()), expected_revision=revision,
        preference=dict(preferred_subjects=['SYN-WA'], use_subject_preference=True, subject_importance=5,
                        use_day_preference=False, use_time_preference=False) | values))


def selection(inputs):
    current = inputs.selection(PRINCIPAL)
    return Freeze(request_id=str(uuid4()), **{k: current[k] for k in ['minimum_revision', 'minimum_digest',
        'weights_revision', 'weights_digest', 'preferences_digest']})


def test_chair_coefficients_are_versioned_and_other_settings_untouched():
    s, _ = configured()
    original = copy.deepcopy(s.data['scoring_context']['settings'])
    cmd = weights()
    saved = s.approve_weights(CHAIR, cmd)
    assert saved['body'] == original | {'subject_penalty': 140}
    assert saved['revision'] == 1 and saved['approval'].startswith('FICTIONAL_DEPARTMENT_CHAIR')
    assert s.approve_weights(CHAIR, cmd) == saved
    assert set(s.weights(FACULTY)['configurable_penalties']) == PENALTIES
    assert not s.weights(FACULTY)['non_penalty_settings_editable']
    assert Inputs(s.workload, Directory(), root=s.storage.root).weights(CHAIR)['policy'] == saved


@pytest.mark.parametrize('key,value', [('absolute_max_teaching_load', 99), ('total_workload_target', 12),
    ('workload_step_units', 1), ('faculty_code', 2), ('specialization_penalty', 5), ('day_penalty', -1), ('time_penalty', 100001)])
def test_reject_policy_math_eligibility_or_unbounded_changes(key, value):
    s, _ = configured()
    with pytest.raises(PolicyError):
        s.approve_weights(CHAIR, weights(**{key: value}))
    assert s.weights(CHAIR)['policy']['revision'] == 0


@pytest.mark.parametrize('actor', [PRINCIPAL, FACULTY, UNSCOPED])
def test_admin_scheduler_or_faculty_does_not_imply_chair(actor):
    s, _ = configured()
    with pytest.raises(PolicyError):
        s.approve_weights(actor, weights())


def test_own_preferences_persist_and_other_faculty_denied():
    s, _ = configured()
    assert s.preference(FACULTY, 2)['preference']['body'] is None
    cmd = preference(preferred_days=['M', 'W'], use_day_preference=True)
    saved = s.save_preference(FACULTY, 2, cmd)
    assert saved['body']['faculty_code'] == 2 and saved['revision'] == 1
    assert s.save_preference(FACULTY, 2, cmd) == saved
    assert Inputs(s.workload, Directory(), root=s.storage.root).preference(FACULTY, 2)['preference'] == saved
    for actor, code in [(FACULTY, 1), (CHAIR, 2), (PRINCIPAL, 2), (UNSCOPED, 2)]:
        with pytest.raises(PolicyError):
            s.save_preference(actor, code, preference())
    with pytest.raises(PolicyError):
        s.preference(FACULTY, 1)


@pytest.mark.parametrize('values', [{'preferred_subjects': ['SYN-INELIGIBLE']}, {'preferred_subjects': ['SYN-WA', 'SYN-WA']},
    {'preferred_days': ['M', 'M']}, {'preferred_days': ['SUN']}, {'preferred_start_time': '22:00', 'preferred_end_time': '07:30'},
    {'preferred_start_time': '7:30', 'preferred_end_time': '09:00'}, {'faculty_priority': 99},
    {'preferred_schedule_blocks': [{'id': 'fictional', 'kind': 'general', 'day': 'M', 'start_time': '07:30', 'end_time': '09:00'}]}])
def test_reject_invalid_or_not_yet_qualified_preference_features(values):
    s, _ = configured()
    with pytest.raises(PolicyError):
        s.save_preference(FACULTY, 2, preference(**values))
    assert s.preference(FACULTY, 2)['preference']['revision'] == 0


def test_concurrent_CAS_and_immutable_rows():
    s, _ = configured()
    commands = [weights(subject_penalty=100), weights(subject_penalty=101)]
    def call(command):
        try:
            return s.approve_weights(CHAIR, command)['revision']
        except PolicyError:
            return 'stale'
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(call, commands))
    assert results.count(1) == results.count('stale') == 1
    with closing(s.connection()) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM revisions')


def test_expired_absent_or_wrong_department_authority_fails_closed():
    s, _ = configured()
    original = s.directory.grant
    class Invalid:
        def grant(self, *args):
            return replace(original(*args), scope_digest='0'*64)
    s.directory = Invalid()
    with pytest.raises(PolicyError):
        s.approve_weights(CHAIR, weights())
    class Expired:
        def grant(self, *args):
            return replace(original(*args), expires_at=time.time()-1)
    s.directory = Expired()
    with pytest.raises(PolicyError):
        s.approve_weights(CHAIR, weights())
    s.directory = None
    with pytest.raises(PolicyError):
        s.weights(CHAIR)


def test_revoked_before_commit_rolls_back(monkeypatch):
    s, _ = configured()
    monkeypatch.setattr(s, '_recheck', lambda *_: (_ for _ in ()).throw(PolicyError('FICTIONAL_REVOKED', 403)))
    with pytest.raises(PolicyError):
        s.approve_weights(CHAIR, weights())
    assert s.weights(CHAIR)['policy']['revision'] == 0


def test_freeze_consumes_correct_integer_preference_keys_and_preserves_graph():
    from services.ga_bundle_optimizer import Session
    from services.ga_bundle_runtime import profile_fingerprint
    s, _ = configured()
    source = s.workload.bundle._raw
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    s.approve_weights(CHAIR, weights())
    s.save_preference(FACULTY, 2, preference())
    req = selection(s)
    prepared = s.prepare(PRINCIPAL, req)
    bundle = s.prepared(PRINCIPAL, prepared['preparation_id'], internal_bundle=True)
    data = bundle.materialize(bundle.run_id)
    assert set(data['scoring_context']['preferences']) == {2}  # String keys would silently miss the scorer's faculty lookup.
    assert data['scoring_context']['preferences'][2]['preferred_subjects'] == ['SYN-WA']
    assert data['scoring_context']['settings']['subject_penalty'] == 140
    assert len(data['templates'][1]) == 2 and data['templates'][1][0].code == 1  # Missing submission never removes a member.
    assert profile_fingerprint(data['templates']) == profile_fingerprint(s.data['templates'])
    assert data['configuration'] == s.data['configuration'] and s.workload.bundle._raw == source
    rng = random.getstate()
    session = Session(bundle, run_id=bundle.run_id, random_state=random.Random(123).getstate())
    assert session.config_fingerprint == prepared['configuration_fingerprint'] and random.getstate() == rng
    assert session.receipt()['verification_status'] == 'UNVERIFIED'  # Constructor is not execution proof.
    assert not prepared['optimizer_executed'] and prepared['optimizer_consumption'] == 'NOT_ESTABLISHED'
    assert prepared['provenance']['minimum_policy']['revision'] == 1
    assert s.prepare(PRINCIPAL, req) == prepared
    assert Inputs(s.workload, Directory(), root=s.storage.root).prepared(PRINCIPAL, prepared['preparation_id']) == prepared


def test_real_original_scorer_uses_frozen_weights_without_mutating_candidate():
    from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
    from genetic_algorithm.utils.FrozenInputs import scoring_inputs
    from services.ga_publication_service import validate_publication
    s, values = configured()
    s.save_preference(FACULTY, 2, preference())
    p1 = s.prepare(PRINCIPAL, selection(s))
    s.approve_weights(CHAIR, weights())
    p2 = s.prepare(PRINCIPAL, selection(s))
    candidate = arranged(values, 1)
    validate_publication(candidate, *values)
    def score(p):
        b = s.prepared(PRINCIPAL, p['preparation_id'], internal_bundle=True)
        data = b.materialize(b.run_id)
        token = scoring_inputs.set(data['scoring_context'])
        try:
            return faculty_preference_fitness(candidate, data['legacy_preferences'], return_breakdown=True)
        finally:
            scoring_inputs.reset(token)
    rng = random.getstate()
    a, b = score(p1), score(p2)
    assert a[1]['subject_preference'] > 0 and b[1]['subject_preference'] == 2*a[1]['subject_preference']
    assert all(a[1][k] == b[1][k] for k in a[1] if k != 'subject_preference')
    assert b[0]-a[0] == b[1]['subject_preference']-a[1]['subject_preference']
    assert random.getstate() == rng
    validate_publication(candidate, *values)


def test_stale_revision_and_nonce_mismatch_rejected_but_old_preparation_unchanged():
    s, _ = configured()
    req = selection(s)
    s.save_preference(FACULTY, 2, preference())
    with pytest.raises(PolicyError, match='STALE'):
        s.prepare(PRINCIPAL, req)
    req = selection(s)
    old = s.prepare(PRINCIPAL, req)
    s.approve_weights(CHAIR, weights())
    assert s.prepared(PRINCIPAL, old['preparation_id']) == old
    assert s.prepare(PRINCIPAL, req) == old  # Explicit replay returns the captured old bundle, never the latest revision.
    with pytest.raises(PolicyError, match='NONCE'):
        s.prepare(PRINCIPAL, Freeze.model_validate(selection(s).model_dump() | {'request_id': req.request_id}))


def test_frozen_bytes_corruption_and_cross_owner_access_fail():
    s, _ = configured()
    record = s.prepare(PRINCIPAL, selection(s))
    with pytest.raises(PolicyError):
        s.prepared(UNSCOPED, record['preparation_id'])
    with closing(s.connection()) as db, db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM frozen')
        db.execute('DROP TRIGGER immutable_frozen_update')
        db.execute("UPDATE frozen SET bundle=X'00'")
    with pytest.raises(ValueError):
        s.prepared(PRINCIPAL, record['preparation_id'])


def test_existing_capture_adapter_accepts_prepared_bundle_without_executing():
    from services.ga_qualified_capture import CaptureAdapter, PreparedSnapshot, identity
    from services.ga_input_bundle import canonical, digest as byte_digest
    from tests.test_qualified_execution import FictionalCatalog, FictionalVerifier
    s, _ = configured()
    s.approve_weights(CHAIR, weights())
    prepared = s.prepare(PRINCIPAL, selection(s))
    bundle = s.prepared(PRINCIPAL, prepared['preparation_id'], internal_bundle=True)
    record = PreparedSnapshot(s.workload.scope.department_id, s.workload.scope.catalog_revision,
        'FICTIONAL-PREPARED-INPUTS', 'c'*64, bundle, 0.0, float(2**40))
    verifier = FictionalVerifier(time.time)
    verifier.approved[('prepared-input-snapshot', byte_digest(canonical(identity(record))))] = record.source_id
    adapter = CaptureAdapter(FictionalCatalog(record), verifier)
    with adapter.guard(ACTOR, record.department_id, record.reference):
        captured = adapter.capture(str(uuid4()), ACTOR, record.department_id, record.reference).bundle
    assert json.loads(captured._raw)['source_identities']['prepared'] == bundle.fingerprint
    assert captured.materialize(captured.run_id)['scoring_context']['settings']['subject_penalty'] == 140
    assert captured.qualification(captured.run_id)['optimizer_consumption'] == 'NOT_ESTABLISHED'


def test_real_cookie_HTTP_faculty_self_and_chair_approval(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base, User, FacultyIdentityRecord
    from services import auth_service as auth
    from routers.prototype_inputs import create_app
    s, _ = configured()
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS', 'http://localhost:5173')
    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'false')
    engine = create_engine('sqlite:///'+str(tmp_path/'identity.sqlite3'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db, db.begin():
        db.add(FacultyIdentityRecord(id=UUID(FACULTY.faculty_id), display_code='SYN-F2', name='Fictional Faculty 2'))
        for actor, label, role, faculty in [(ACTOR, 'scheduler', 'admin', None), (CHAIR_ID, 'chair', 'admin', None),
            (FACULTY_ID, 'faculty', 'faculty', UUID(FACULTY.faculty_id)), (OTHER, 'unscoped', 'admin', None)]:
            db.add(User(id=UUID(actor), username=label+'@fictional.invalid', role=role, faculty_id=faculty, password_hash=auth.hash_password(password)))
    def database():
        with Session(engine) as db:
            yield db
    def login(client, label):
        response = client.post('/api/auth/login', json={'username': label+'@fictional.invalid', 'password': password}, headers={'Origin': 'http://localhost:5173'})
        assert response.status_code == 200
        return {'Origin': 'http://localhost:5173', 'X-CSRF-Token': response.json()['csrf_token']}
    with TestClient(create_app(s, database)) as client:
        assert client.get('/prototype/inputs').status_code == 200
        assert client.get('/prototype/inputs/console.mjs').status_code == 200
        assert client.get('/prototype/inputs/model.mjs').status_code == 200
        assert client.get('/api/prototype/inputs/weights').status_code == 401
        header = login(client, 'faculty')
        command = preference().model_dump()
        assert client.put('/api/prototype/inputs/preferences/2', json=command).status_code == 403
        assert client.put('/api/prototype/inputs/preferences/2', json=command, headers=header).status_code == 200
        assert client.get('/api/prototype/inputs/preferences/1').status_code == 403
        assert client.post('/api/prototype/inputs/weights/approve', json=weights().model_dump(), headers=header).status_code == 403
        header = login(client, 'chair')
        assert client.post('/api/prototype/inputs/weights/approve', json=weights().model_dump(), headers=header).status_code == 200
        assert client.get('/api/prototype/inputs/selection').status_code == 403
        header = login(client, 'scheduler')
        response = client.get('/api/prototype/inputs/selection')
        assert response.headers['Cache-Control'] == 'no-store'
        selected = response.json()
        body = {k: selected[k] for k in ['minimum_revision', 'minimum_digest', 'weights_revision', 'weights_digest', 'preferences_digest']} | {'request_id': str(uuid4())}
        prepared = client.post('/api/prototype/inputs/prepare', json=body, headers=header)
        assert prepared.status_code == 200 and prepared.json()['optimizer_consumption'] == 'NOT_ESTABLISHED'
        assert client.get('/api/prototype/inputs/prepared/'+prepared.json()['preparation_id']).json() == prepared.json()
        assert client.post('/api/prototype/inputs/prepare', json=body | {'role': 'chair'}, headers=header).status_code == 422
        header = login(client, 'unscoped')
        assert client.get('/api/prototype/inputs/weights').status_code == 403
    with TestClient(create_app()) as client:
        assert client.get('/api/prototype/inputs/weights').status_code == 503
    engine.dispose()


def test_explicit_fictional_demonstration_has_24_eligible_units_and_hard_valid_witness():
    from tests.fictional_deadline_support import minimum24_case
    from tests.test_prototype_workload import FictionalGrants, service_for
    from services.prototype_workload import WorkloadService
    from services.prototype_scheduling import assess_snapshot
    from genetic_algorithm.utils.Functions import assign_schedule_to_faculty
    bundle, values = minimum24_case()
    baseline, _ = service_for()
    workload = WorkloadService(baseline.scope, bundle, FictionalGrants())
    view = workload.save(PRINCIPAL, change(**{'1': 12, '2': 24}))
    assert [(r['eligible_units'], r['minimum_teaching_units']) for r in view['faculty']] == [(12, 12), (24, 24)]
    assert view['preflight'] == 'NOT_PROVEN_INFEASIBLE'
    subjects, faculty, rooms = values
    for i, subject in enumerate(subjects):
        owner = faculty[0] if i < 4 else faculty[1]
        assert assign_schedule_to_faculty(owner, subject,
            ('7:30 - 10:30' if i % 2 == 0 else '10:30 - 13:30', ['M', 'T', 'W', 'TH', 'F', 'S'][i//2]),
            'Lecture', room_list=rooms, list_subjects=subjects)
    result = assess_snapshot(workload, {'policy': view['policy']}, subjects)
    assert result['fully_feasible_under_captured_policy']
    assert [r['assigned_units'] for r in result['faculty']] == [12, 24]
    # Constructed feasibility witness only, NEVER a claimed generated schedule.
