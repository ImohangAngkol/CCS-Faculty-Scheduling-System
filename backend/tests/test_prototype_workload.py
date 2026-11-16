"""Owned fictional source only; real session/SQLite acceptance, no GA worker."""
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Requires an owned empty-data snapshot', allow_module_level=True)

from services.prototype_workload import Change, Scope, Store, WorkloadService, PolicyError
from services.preference_authorization import PreferencePrincipal

ACTOR = '00000000-0000-4000-8000-000000007501'
VIEWER = '00000000-0000-4000-8000-000000007502'
OTHER = '00000000-0000-4000-8000-000000007503'
DEPT = '00000000-0000-4000-8000-000000007510'
PRINCIPAL = PreferencePrincipal('admin', user_id=ACTOR)


class FictionalGrants:
    """Explicit test grants, never installed as institutional authority."""
    def allows(self, actor, scope, action):
        return (scope.department_id == DEPT and scope.academic_year == 'FICTIONAL-YEAR'
                and scope.term == 'FICTIONAL-TERM' and scope.catalog_revision == 'FICTIONAL-CATALOG-1'
                and (actor == ACTOR or actor == VIEWER and action == 'read'))


def bundle_for(count=4):
    from genetic_algorithm.models.Faculty import Faculty
    from genetic_algorithm.models.Subject import Subject
    from genetic_algorithm.models.Room import Room
    from genetic_algorithm.models.Section import Section
    from genetic_algorithm.models.ga_setting import GASetting
    from genetic_algorithm.utils.FrozenInputs import capture_inputs
    from services.ga_input_bundle import capture
    from services.ga_checkpoint_service import engine_fingerprint, input_fingerprint
    from tests.d10.support import preferences
    subjects = [Subject('SYN-WA' if i % 2 == 0 else 'SYN-WB', 'Fictional prototype', 3, 3, 0,
                        Section('SYN-P-'+str(i))) for i in range(count)]
    faculty = [Faculty(i, 1, eligible_subjects={'SYN-WA', 'SYN-WB'}) for i in [1, 2]]
    values = subjects, faculty, [Room('Fictional prototype room', 'Lecture')]
    scoring = capture_inputs()
    scoring.update(system_faculty=copy.deepcopy(faculty), preferences={}, settings=GASetting().to_dict())
    parameters = dict(population_size=2, generations=1, fresh_chromosomes=0,
                      baseline_mode='fresh', mutation_attempts=1, max_restarts=2)
    bundle = capture(run_id='00000000-0000-4000-8000-000000007520', templates=values,
        fallback_templates=values, legacy_preferences=preferences(), scoring_context=scoring,
        configuration=parameters, source_identities=dict(dataset=input_fingerprint(), engine=engine_fingerprint(),
        loader=hashlib.sha256(b'FICTIONAL-LOADER').hexdigest(), transformation=hashlib.sha256(b'FICTIONAL-TRANSFORM').hexdigest()))
    return bundle, values


def service_for(count=4):
    bundle, values = bundle_for(count)
    scope = Scope(department_id=DEPT, academic_year='FICTIONAL-YEAR', term='FICTIONAL-TERM',
                  catalog_revision='FICTIONAL-CATALOG-1')
    return WorkloadService(scope, bundle, FictionalGrants()), values


def change(revision=0, **minima):
    return Change(expected_revision=revision, minimums=[dict(faculty_code=int(c), minimum_teaching_units=v)
                                                        for c, v in minima.items()])


@pytest.fixture
def configured():
    return service_for()


@pytest.mark.parametrize('value', [-1, 41, 24.5, True, '24'])
def test_strict_integer_range(value):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        change(**{'2': value})


def test_sparse_minimum_and_preflight(configured):
    service, values = configured
    before = service.bundle._raw
    first = service.view(PRINCIPAL)
    assert all(x['minimum_teaching_units'] is None for x in first['faculty'])
    view = service.save(PRINCIPAL, change(**{'2': 24}))
    assert view['preflight'] == 'MINIMUM_WORKLOAD_INFEASIBLE' and not view['optimizer_executed']
    assert [(x['faculty_code'], x['minimum_teaching_units'], x['proven_shortfall']) for x in view['faculty']] == [(1, None, None), (2, 24, 12)]
    assert service.bundle._raw == before and values[1][1].required_teaching_load == 24
    assert view['input_capture_verification'] == 'UNVERIFIED' and view['optimizer_consumption'] == 'NOT_ESTABLISHED'


def test_independent_zero_and_clear(configured):
    service, _ = configured
    view = service.save(PRINCIPAL, change(**{'1': 3, '2': 0}))
    assert [x['minimum_teaching_units'] for x in view['faculty']] == [3, 0]
    view = service.save(PRINCIPAL, change(1))
    assert all(x['minimum_teaching_units'] is None for x in view['faculty'])


def test_duplicate_unknown_extra_scope_rejected(configured):
    service, _ = configured
    with pytest.raises(PolicyError):
        service.save(PRINCIPAL, Change(expected_revision=0, minimums=[{'faculty_code': 2, 'minimum_teaching_units': 24}] * 2))
    with pytest.raises(PolicyError):
        service.save(PRINCIPAL, change(**{'99': 24}))
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Change(expected_revision=0, minimums=[], department_id=DEPT)


@pytest.mark.parametrize('actor', [OTHER, None])
def test_scoped_read_denies_role_claim(configured, actor):
    service, _ = configured
    with pytest.raises(PolicyError):
        service.view(PreferencePrincipal('admin', user_id=actor))


def test_read_grant_does_not_allow_configure(configured):
    service, _ = configured
    viewer = PreferencePrincipal('faculty', user_id=VIEWER)
    assert not service.view(viewer)['can_configure']
    with pytest.raises(PolicyError):
        service.save(viewer, change(**{'2': 24}))
    service.authority = None
    with pytest.raises(PolicyError):
        service.save(PRINCIPAL, change(**{'2': 24}))


def test_term_or_catalog_change_does_not_reuse_authority(configured):
    service, _ = configured
    for field in ['term', 'catalog_revision']:
        scope = Scope.model_validate(service.scope.model_dump() | {field: 'FICTIONAL-OTHER'})
        other = WorkloadService(scope, service.bundle, FictionalGrants())
        with pytest.raises(PolicyError):
            other.view(PRINCIPAL)


def test_persistence_restart_stale_write_and_immutable_history(configured):
    service, _ = configured
    first = service.save(PRINCIPAL, change(**{'2': 24}))
    restored = WorkloadService(service.scope, service.bundle, FictionalGrants(),
                              Store(service.store.root, service.binding))
    assert restored.view(PRINCIPAL) == first
    with pytest.raises(PolicyError, match='STALE'):
        restored.save(PRINCIPAL, change(**{'2': 12}))
    with sqlite3.connect(service.store.root/'policy.sqlite3') as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM revisions')
    assert restored.view(PRINCIPAL) == first


def test_concurrent_compare_and_swap(configured):
    service, _ = configured
    def attempt(value):
        try:
            service.save(PRINCIPAL, change(**{'2': value}))
            return 'saved'
        except PolicyError as exc:
            return exc.code
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt, [12, 24]))
    assert sorted(results) == ['PROTOTYPE_POLICY_STALE', 'saved']
    assert service.store.current()['revision'] == 1


def test_store_context_and_corruption_reject(configured):
    service, _ = configured
    service.save(PRINCIPAL, change(**{'2': 24}))
    with pytest.raises(PolicyError):
        Store(service.store.root, 'x'*64)
    with sqlite3.connect(service.store.root/'policy.sqlite3') as db:
        db.execute('DROP TRIGGER immutable_update')
        db.execute("UPDATE revisions SET doc='{}'")
    with pytest.raises(PolicyError):
        service.view(PRINCIPAL)


def arranged(values, owner):
    from genetic_algorithm.utils.Functions import assign_schedule_to_faculty
    subjects, faculty, rooms = copy.deepcopy(values)
    for i, subject in enumerate(subjects):
        assert assign_schedule_to_faculty(faculty[owner], subject,
            ('7:30 - 10:30' if i % 2 == 0 else '10:30 - 13:30', ['M', 'T', 'W', 'TH'][i//2]),
            'Lecture', room_list=rooms, list_subjects=subjects)
    return subjects


def test_sufficient_units_zero_and_valid24_are_distinguished():
    from services.ga_publication_service import validate_publication
    service, values = service_for(8)
    view = service.save(PRINCIPAL, change(**{'2': 24}))
    assert view['preflight'] == 'NOT_PROVEN_INFEASIBLE'
    for owner, status, deficit in [(0, 'MINIMUM_WORKLOAD_VIOLATION', 24), (1, 'EXPLICIT_MINIMA_SATISFIED', 0)]:
        candidate = arranged(values, owner)
        validate_publication(candidate, *values)
        assessment = service.assess(PRINCIPAL, candidate, view['policy']['digest'])
        assert assessment['minimum_status'] == status and assessment['faculty'][0]['deficit'] == deficit
        assert assessment['full_academic_validation'] == 'SEPARATE_ORIGINAL_VALIDATION_REQUIRED'
    with pytest.raises(PolicyError, match='STALE'):
        service.assess(PRINCIPAL, candidate, '0'*64)


def test_assessment_never_accepts_missing_or_changed_eligibility(configured):
    service, values = configured
    view = service.save(PRINCIPAL, change(**{'2': 24}))
    candidate = arranged(values, 0)
    with pytest.raises(PolicyError):
        service.assess(PRINCIPAL, candidate[:-1], view['policy']['digest'])
    candidate[0].assigned_faculty.code = 99
    with pytest.raises(PolicyError):
        service.assess(PRINCIPAL, candidate, view['policy']['digest'])


def test_real_sessions_CSRF_scope_and_persisted_HTTP(configured, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from identity_models import Base, User
    from services import auth_service as auth
    from routers.prototype_workload import create_app
    service, _ = configured
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS', 'http://localhost:5173')
    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'false')
    engine = create_engine('sqlite:///'+str(tmp_path/'auth.sqlite3'), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    password = secrets.token_urlsafe(24)
    with Session(engine) as db, db.begin():
        db.add_all([User(id=UUID(actor), username=label+'@fictional.invalid', role='admin',
                         password_hash=auth.hash_password(password)) for actor, label in [(ACTOR, 'editor'), (OTHER, 'unscoped')]])
    def identity_db():
        with Session(engine) as db:
            yield db
    with TestClient(create_app(service, identity_db)) as client:
        assert client.get('/api/prototype/workload').status_code == 401
        login = client.post('/api/auth/login', json={'username': 'editor@fictional.invalid', 'password': password}, headers={'Origin': 'http://localhost:5173'})
        assert login.status_code == 200
        csrf = login.json()['csrf_token']
        payload = change(**{'2': 24}).model_dump()
        assert client.put('/api/prototype/workload', json=payload).status_code == 403
        response = client.put('/api/prototype/workload', json=payload, headers={'Origin': 'http://localhost:5173', 'X-CSRF-Token': csrf})
        assert response.status_code == 200 and response.json()['preflight'] == 'MINIMUM_WORKLOAD_INFEASIBLE'
        assert response.headers['Cache-Control'] == 'no-store'
        assert client.get('/api/prototype/workload').json()['policy']['revision'] == 1
        assert client.get('/prototype/workload').status_code == 200
        assert client.get('/prototype/workload/console.mjs?name=../../data/faculty_preferences.json').status_code == 200
        assert b'import {changeFor' in client.get('/prototype/workload/console.mjs').content
        client.post('/api/auth/login', json={'username': 'unscoped@fictional.invalid', 'password': password}, headers={'Origin': 'http://localhost:5173'})
        assert client.get('/api/prototype/workload').status_code == 403
    with TestClient(create_app()) as client:
        assert client.get('/api/prototype/workload').status_code == 503
        assert client.get('/api/auth/me').status_code == 503
    engine.dispose()
