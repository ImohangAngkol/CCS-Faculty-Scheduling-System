"""Fictional minimum gate and diagnostic candidates; no native worker in this file."""
from contextlib import closing
import copy
import json
import secrets
import sqlite3
from uuid import UUID, uuid4
import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Owned fictional snapshot required', allow_module_level=True)
from services.prototype_workload import WorkloadService, Scope, PolicyError, Store as PolicyStore
from services.prototype_scheduling import MinimumRuns, Submission, assess_snapshot
from services.ga_run_authority import RunError
from services.preference_authorization import PreferencePrincipal
from tests.test_prototype_workload import bundle_for, arranged, change
from tests.trusted_run_support import ACTOR, DEPT, CATALOG, PRINCIPAL, OTHER


class Grants:
    def allows(self, actor, scope, action):
        return actor == ACTOR and scope.department_id == DEPT and scope.academic_year == 'FICTIONAL-YEAR' and scope.term == 'FICTIONAL-TERM' and scope.catalog_revision == CATALOG and action in {'read', 'configure', 'execute'}


def setup(count=4):
    from tests.bounded_worker_support import dependencies
    from services.ga_owned_store import Store
    from services.ga_trusted_runs import Coordinator
    from services.ga_research_bridge import ResearchBridge, ResearchWorker
    from services.ga_research_context import ResearchPermit
    from services.ga_research_operator import Operator
    bundle, values = bundle_for(count)
    authority, capture, _ = dependencies(prepared=bundle)
    worker = ResearchWorker(Coordinator(Store.create(max_runs=4), authority, capture), initialize=True)
    bridge = ResearchBridge(worker, ResearchPermit(ACTOR, DEPT, CATALOG, bundle.fingerprint,
        'FICTIONAL-YEAR', 'FICTIONAL-TERM', 'FICTIONAL-DATASET'), initialize=True)
    operator = Operator(bridge, initialize=True)
    scope = Scope(department_id=DEPT, academic_year='FICTIONAL-YEAR', term='FICTIONAL-TERM', catalog_revision=CATALOG)
    workload = WorkloadService(scope, bundle, Grants())
    service = MinimumRuns(workload, operator, initialize=True)
    return service, values


def selected(service, nonce=None):
    view = service.context(PRINCIPAL)
    w = view['workload']
    return Submission(request_id=nonce or str(uuid4()), academic_year=w['scope']['academic_year'], term=w['scope']['term'],
        catalog_revision=w['scope']['catalog_revision'], minimum_revision=w['policy']['revision'], minimum_digest=w['policy']['digest'],
        prepared_bundle_fingerprint=w['bundle_fingerprint'], configuration_fingerprint=view['configuration_fingerprint'])


def no_launch(service, monkeypatch):
    def denied(*_a, **_k):
        pytest.fail('Unexpected native dispatch in offline gate test')
    monkeypatch.setattr(service.operator, 'control', denied)


def test_A_infeasible24_eligible12_before_dispatch_and_durable_restart(monkeypatch):
    s, _ = setup()
    no_launch(s, monkeypatch)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    req = selected(s)
    result = s.submit(PRINCIPAL, req)
    assert result['state'] == 'INPUT_INFEASIBLE' and not result['worker_admitted']
    row = result['details']['shortages'][0]
    assert (row['faculty_code'], row['eligible_units'], row['minimum_teaching_units'], row['proven_shortfall']) == (2, 12, 24, 12)
    assert not result['fully_feasible'] and not s.operator.bridge.worker.threads
    with s.operator.bridge.worker.storage.connection() as db:
        assert db.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM l_processes').fetchone()[0] == 0
    restored = MinimumRuns(s.workload, s.operator)
    assert restored.submit(PRINCIPAL, req) == result
    assert restored.lookup(PRINCIPAL, req.request_id) == result


@pytest.mark.parametrize('owner,status,deficit', [(0, 'MINIMUM_WORKLOAD_VIOLATION', 24), (1, 'EXPLICIT_MINIMA_SATISFIED', 0)])
def test_B_C_original_hard_valid_diagnostic_candidates(owner, status, deficit):
    s, values = setup(8)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    snapshot = s.snapshot(PRINCIPAL, selected(s))
    assert snapshot['preflight'] == 'NOT_PROVEN_INFEASIBLE'
    candidate = arranged(values, owner)
    result = assess_snapshot(s.workload, snapshot, candidate)
    row = next(x for x in result['faculty'] if x['faculty_code'] == 2)
    assert row['assigned_units'] == (0 if owner == 0 else 24) and row['minimum_deficit'] == deficit
    assert result['minimum_status'] == status and result['original_hard_constraints'] == 'VALIDATED'
    assert result['fully_feasible_under_captured_policy'] == (owner == 1)


def test_D_no_minimum_does_not_reinterpret_soft_target():
    s, values = setup()
    result = assess_snapshot(s.workload, s.snapshot(PRINCIPAL, selected(s)), arranged(values, 0))
    assert result['fully_feasible_under_captured_policy']
    assert all(x['minimum_teaching_units'] is None and x['minimum_deficit'] is None for x in result['faculty'])
    assert next(x for x in result['faculty'] if x['faculty_code'] == 2)['assigned_units'] == 0


def test_E_F_capture_survives_new_head_and_separate_term_has_no_inherited_policy():
    s, values = setup(8)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    request = selected(s)
    snapshot = s.snapshot(PRINCIPAL, request)
    record, _ = s.store.create(ACTOR, request.model_dump(), snapshot)
    s.workload.save(PRINCIPAL, change(1, **{'1': 12, '2': 0}))
    s._verify_record(record)
    result = assess_snapshot(s.workload, snapshot, arranged(values, 0))
    assert result['minimum_revision'] == 1 and result['faculty'][1]['minimum_deficit'] == 24
    with pytest.raises(PolicyError, match='STALE'):
        s.snapshot(PRINCIPAL, request)
    class OtherTerm:
        def allows(self, actor, scope, action):
            return actor == ACTOR and scope.term == 'FICTIONAL-TERM-2'
    scope = Scope.model_validate(s.workload.scope.model_dump() | {'term': 'FICTIONAL-TERM-2'})
    other = WorkloadService(scope, s.workload.bundle, OtherTerm())
    assert other.view(PRINCIPAL)['policy']['revision'] == 0 and other.binding != s.workload.binding
    with pytest.raises(PolicyError):
        PolicyStore(s.workload.store.root, other.binding)


@pytest.mark.parametrize('field,value', [('term', 'FICTIONAL-WRONG'), ('minimum_digest', '0'*64), ('configuration_fingerprint', '0'*64), ('prepared_bundle_fingerprint', '0'*64)])
def test_reject_stale_or_cross_input_selection(field, value, monkeypatch):
    s, _ = setup()
    no_launch(s, monkeypatch)
    request = Submission.model_validate(selected(s).model_dump() | {field: value})
    with pytest.raises(PolicyError):
        s.submit(PRINCIPAL, request)
    with closing(s.store.connection()) as db:
        assert db.execute('SELECT COUNT(*) FROM requests').fetchone()[0] == 0


def test_resource_gate_fail_closed_no_mock_native_result(monkeypatch):
    s, _ = setup()
    no_launch(s, monkeypatch)
    s.resources = lambda: {'passed': True, 'available_bytes': 2*2**30}
    result = s.submit(PRINCIPAL, selected(s))
    assert result['state'] == 'RESOURCE_BLOCKED' and result['result'] is None
    assert not result['worker_admitted'] and not result['fully_feasible']


def test_H_cross_owner_read_and_execute_denied(monkeypatch):
    s, _ = setup()
    no_launch(s, monkeypatch)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    request = selected(s)
    result = s.submit(PRINCIPAL, request)
    other = PreferencePrincipal('admin', user_id=OTHER)
    for operation in [lambda: s.submit(other, request), lambda: s.inspect(other, result['run_id']), lambda: s.lookup(other, request.request_id)]:
        with pytest.raises((PolicyError, RunError)):
            operation()


def test_idempotency_snapshot_and_event_corruption(monkeypatch):
    s, _ = setup()
    no_launch(s, monkeypatch)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    request = selected(s)
    result = s.submit(PRINCIPAL, request)
    with pytest.raises(PolicyError, match='REUSE'):
        s.submit(PRINCIPAL, Submission.model_validate(request.model_dump() | {'minimum_revision': 0}))
    with sqlite3.connect(s.store.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM events')
        db.execute('DROP TRIGGER no_event_update')
        db.execute("UPDATE events SET raw='{}'")
    with pytest.raises((PolicyError, KeyError)):
        s.inspect(PRINCIPAL, result['run_id'])


def test_invalid_candidate_never_minimum_qualified():
    s, values = setup(8)
    snapshot = s.snapshot(PRINCIPAL, selected(s))
    candidate = arranged(values, 1)
    with pytest.raises(ValueError):
        assess_snapshot(s.workload, snapshot, candidate[:-1])
    candidate[0].assigned_faculty.code = 999
    with pytest.raises((ValueError, RuntimeError)):
        assess_snapshot(s.workload, snapshot, candidate)


@pytest.mark.parametrize('state', ['FAILED', 'INTERRUPTED', 'RECOVERY_REQUIRED'])
def test_diagnostic_lifecycle_failure_is_durable_not_a_candidate(monkeypatch, state):
    # Real admission/captured-input binding, synthetic lifecycle state only.
    # No child, optimizer execution or genuine termination proof is claimed.
    s, _ = setup()
    request = selected(s)
    record, _ = s.store.create(ACTOR, request.model_dump(), s.snapshot(PRINCIPAL, request))
    worker_run = s.operator.bridge.admit(PRINCIPAL, request.request_id, s.operator.limits)['run_id']
    s._link(PRINCIPAL, record, worker_run)
    monkeypatch.setattr(s.operator, 'runtime', lambda *_: dict(recorded_state=state, terminal_cleanup_recorded=True))
    result = s.inspect(PRINCIPAL, record['id'])
    assert result['state'] == ('RUN_FAILED' if state == 'FAILED' else 'INTERRUPTED')
    assert result['terminal'] and result['result'] is None and not result['fully_feasible']
    assert result['physical_execution'] == 'NOT_ESTABLISHED_BY_THIS_RECORD'
    assert MinimumRuns(s.workload, s.operator).inspect(PRINCIPAL, record['id']) == result


@pytest.mark.parametrize('owner', [0, 1])
def test_diagnostic_qualification_storage_zero_and_old_revision(monkeypatch, owner):
    # This is an explicitly mocked proof boundary around hard-valid diagnostic
    # candidates, NOT genuine optimizer/child-consumption acceptance.
    from services.chromosome_service import chromosome_to_payload
    s, values = setup(8)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    request = selected(s)
    record, _ = s.store.create(ACTOR, request.model_dump(), s.snapshot(PRINCIPAL, request))
    worker_run = s.operator.bridge.admit(PRINCIPAL, request.request_id, s.operator.limits)['run_id']
    s._link(PRINCIPAL, record, worker_run)
    candidate = arranged(values, owner)
    payload = chromosome_to_payload(candidate, 0)
    original = copy.deepcopy(payload)
    result = dict(best_fitness=0, schedule=payload['schedule'], history=[{'generation': 0, 'best_fitness': 0}],
                  generations_completed=0, fitness_breakdown={})
    monkeypatch.setattr(s.operator.bridge, 'qualified_result', lambda *_: ({'test_only': 'MOCK_PROOF_BOUNDARY'}, result))
    monkeypatch.setattr(s.operator.bridge, 'candidate', lambda *_: payload)
    monkeypatch.setattr(s.operator, 'runtime', lambda *_: dict(recorded_state='COMPLETED', terminal_cleanup_recorded=True))
    s.workload.save(PRINCIPAL, change(1, **{'2': 0}))
    response = s.inspect(PRINCIPAL, record['id'])
    assert response['state'] == ('CANDIDATE_FULLY_FEASIBLE' if owner == 1 else 'CANDIDATE_CONSTRAINT_VIOLATING')
    assert response['minimum_revision'] == 1 and response['result']['original_GA_fitness'] == 0
    assert response['result']['schedule'] == original['schedule'] and payload == original
    assert response['worker']['admitted_bundle_fingerprint'] != response['prepared_bundle_fingerprint']
    restored = MinimumRuns(s.workload, s.operator)
    assert restored.inspect(PRINCIPAL, record['id']) == response


def test_real_HTTP_cookie_auth_CSRF_scope_and_durable_rejection(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base, User
    from services import auth_service as auth
    from routers.prototype_scheduling import create_app
    s, _ = setup()
    no_launch(s, monkeypatch)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS', 'http://localhost:5173')
    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'false')
    engine = create_engine('sqlite:///'+str(tmp_path/'identity.sqlite3'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db, db.begin():
        db.add_all([User(id=UUID(actor), username=label+'@fictional.invalid', role='admin', password_hash=auth.hash_password(password))
                    for actor, label in [(ACTOR, 'editor'), (OTHER, 'unscoped')]])
    def identity_db():
        with Session(engine) as db:
            yield db
    with TestClient(create_app(s, identity_db)) as client:
        assert client.get('/api/prototype/scheduling/context').status_code == 401
        response = client.post('/api/auth/login', json={'username': 'editor@fictional.invalid', 'password': password}, headers={'Origin': 'http://localhost:5173'})
        headers = {'Origin': 'http://localhost:5173', 'X-CSRF-Token': response.json()['csrf_token']}
        body = selected(s).model_dump()
        assert client.post('/api/prototype/scheduling/runs', json=body).status_code == 403
        response = client.post('/api/prototype/scheduling/runs', json=body, headers=headers)
        assert response.status_code == 409 and response.json()['state'] == 'INPUT_INFEASIBLE'
        run = response.json()['run_id']
        assert client.get('/api/prototype/scheduling/runs/'+run).json() == response.json()
        assert response.headers['Cache-Control'] == 'no-store'
        assert client.get('/prototype/scheduling').status_code == 200
        assert client.get('/prototype/scheduling/model.mjs').status_code == 200
        assert client.post('/api/prototype/scheduling/runs', json=body | {'role': 'admin'}, headers=headers).status_code == 422
        client.post('/api/auth/login', json={'username': 'unscoped@fictional.invalid', 'password': password}, headers={'Origin': 'http://localhost:5173'})
        assert client.get('/api/prototype/scheduling/runs/'+run).status_code == 403
    with TestClient(create_app()) as client:
        assert client.get('/api/prototype/scheduling/context').status_code == 503
    engine.dispose()
