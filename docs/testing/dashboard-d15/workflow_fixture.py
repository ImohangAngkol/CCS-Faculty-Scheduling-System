"""D15 fictional resource providers, real auth/services and migrated PG engine.

Adapted from the committed D2/D11/D14 fixtures. No create_all, SQLite trigger
substitution, protected-path writes or production authority installation.
"""
from contextlib import contextmanager
from dataclasses import replace
import copy
import json
import random
import secrets
import threading
import time
from types import SimpleNamespace
from uuid import UUID

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_identity_db
from identity_models import FacultyIdentityRecord, User
from main import app
from routers import genetic_algorithm as ga_router
from services import auth_service as auth, ga_service, metadata_service, identity_service
from services.identity_service import FacultyIdentity
from services import adjustment_schedule_service as schedules, published_schedule_source as published
from services import ga_v2_service as ga, ga_v2_constraints as constraints, ga_v2_store as store
from services import chair_review_service
from genetic_algorithm.models.Faculty import Faculty
from genetic_algorithm.models.Subject import Subject
from genetic_algorithm.models.Section import Section
from genetic_algorithm.models.Room import Room
from tests.dashboard.test_my_schedule import IDS, ORIGIN
from tests.dashboard.test_chair_reviews import chair
from tests.dashboard.test_schedule_applications import application
from tests.dashboard.test_external_confirmations import permit, proposal, decision
from tests.dashboard.test_external_readiness import isolate
from tests.dashboard.evidence_support import install_fictional
from tests.dashboard.test_chair_trust import REAL_TRUST
from tests.dashboard.test_adjustments import session
from tests.d10.test_v2_engine import catalog_for


@contextmanager
def resources(engine, monkeypatch, root):
    identities = tuple(FacultyIdentity(str(id), i, f'Synthetic Faculty {i}', f'Synthetic Lecturer {i}') for i, id in enumerate(IDS))
    monkeypatch.setattr(identity_service, 'load_faculty_identities', lambda: identities)
    members = [Faculty(i, 1, admin_load=24, eligible_subjects={'SYN101'} if i == 0 else {'SYN202'} if i == 1 else set()) for i in range(3)]
    for member, identity in zip(members, identities):
        member.stable_id, member.display_code, member.name = identity.faculty_id, identity.display_code, identity.name
    courses = [Subject('SYN101', 'Fictional Programming', 4, 3, 3, Section('SYN-A')),
               Subject('SYN202', 'Fictional Design', 3, 3, 0, Section('SYN-B'))]
    rooms = [Room('SYN LEC', 'Lecture'), Room('SYN LAB', 'Laboratory')]
    for key, value in [('list_faculty', members), ('list_subjects', courses), ('lst_rooms', rooms)]:
        monkeypatch.setattr(ga_service, key, value)
    monkeypatch.setattr(metadata_service.scheduling, 'list_faculty', members)
    monkeypatch.setattr(metadata_service.scheduling, 'list_subjects', courses)
    path = root/'fictional-original.json'
    path.write_text(json.dumps({'status': 'COMPLETED', 'schedule': []}), encoding='utf-8')
    original = path.read_bytes()
    monkeypatch.setattr(ga_router, 'LATEST_RESULT_FILE', path)
    password = secrets.token_urlsafe(24)
    hashed = auth.hash_password(password)
    with Session(engine) as db, db.begin():
        db.add_all([FacultyIdentityRecord(id=IDS[i], display_code=identity.display_code, name=identity.name) for i, identity in enumerate(identities)])
        db.flush()
        db.add_all([User(username=f'faculty{i}@example.invalid', password_hash=hashed, role='faculty', faculty_id=IDS[i], is_active=True) for i in range(3)])
        db.add(User(username='admin@example.invalid', password_hash=hashed, role='admin', is_active=True))

    def db_session():
        with Session(engine) as db:
            yield db
    monkeypatch.setattr(app, 'dependency_overrides', {get_identity_db: db_session, auth.authenticated_db: db_session})
    monkeypatch.setattr(auth, 'LOGIN_LIMITER', auth.LoginLimiter())
    monkeypatch.setenv('AUTH_COOKIE_SECURE', 'false')
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS', ORIGIN)
    # Existing test-only intake context. Runtime receipts stay in memory.
    isolate.__wrapped__(monkeypatch)
    install_fictional(monkeypatch)
    permit(monkeypatch)
    with TestClient(app, base_url='http://localhost') as client:
        f = SimpleNamespace(client=client, engine=engine, password=password, path=path, members=members,
                            courses=courses, rooms=(schedules.Room('lec','SYN LEC','Lecture'), schedules.Room('lab','SYN LAB','Laboratory')),
                            guard=threading.RLock(), snapshot=None)
        f.windows = tuple((kind, key, day, '07:30', '22:00') for kind, keys in
            [('faculty', map(str, IDS)), ('section', ['section-a','section-b']), ('room', ['lec','lab'])]
            for key in keys for day in ['M','T','W','TH','F','S'])
        # These two provider fixtures contain no DDL and reuse the real services.
        # Their temporary trusted_snapshot stub is immediately replaced below.
        chair_generator = chair.__wrapped__(f, monkeypatch)
        next(chair_generator)
        application.__wrapped__(f, monkeypatch)
        monkeypatch.setattr(chair_review_service, 'trusted_snapshot', REAL_TRUST)
        values = copy.deepcopy((courses, members, rooms))
        catalog = catalog_for(values).model_copy(update={
            'sections': (('synthetic-section-a','SYN-A'), ('synthetic-section-b','SYN-B')),
            'faculty': tuple((str(id), str(i)) for i, id in enumerate(IDS)),
            'rooms': (('SYN LEC','SYN LEC'), ('SYN LAB','SYN LAB'))})
        preferences = pd.DataFrame({'Faculty_Code':[0,1,2], 'Faculty_Prio':[1,1,1], 'Preferred Subjects':[None]*3, 'Preferred Day(s)':[None]*3})
        deployment = ga.Deployment(catalog, constraints.LedgerAuthority(lambda: Session(engine), catalog, values), values, preferences)
        f.deployment = deployment
        monkeypatch.setattr(ga, 'institutional_deployment', lambda year, term: deployment)
        monkeypatch.setattr(store, 'STORE', root/'v2')
        monkeypatch.setattr(ga, 'JOBS', {})
        f.publish_file = root/'explicit-fictional-publication.json'
        cached = {}
        from routers import preferences as preference_router
        from genetic_algorithm.operators import FitnessFunction
        preference_file, settings_file = root/'fictional-preferences.json', root/'fictional-settings.json'
        preference_file.write_text('[]', encoding='utf-8')
        settings_file.write_text(json.dumps(preference_router.GASetting().to_dict()), encoding='utf-8')
        for module, key, value in ((preference_router,'PREFERENCE_FILE',preference_file), (preference_router,'GA_SETTINGS_FILE',settings_file),
            (ga_service,'FACULTY_PREFERENCES_FILE',preference_file), (ga_service,'GA_SETTINGS_FILE',settings_file),
            (FitnessFunction,'PREFERENCE_FILE',preference_file), (FitnessFunction,'GA_SETTINGS_FILE',settings_file)):
            monkeypatch.setattr(module, key, value)

        @contextmanager
        def publication():
            id = str(UUID(json.loads(f.publish_file.read_text(encoding='utf-8'))['run_id']))
            raw = store.path_for(id).read_bytes()
            if id not in cached:
                cached[id] = raw, copy.deepcopy(ga.inspect(id)['result'])
            recorded, result = cached[id]
            assert raw == recorded and result['status'] == 'COMPLETED'
            with Session(engine) as db:
                snapshot = constraints._read_snapshot(db, catalog, values)
            with f.guard:
                assert result['constraint_digest'] == snapshot.digest
                room_ids = {'SYN LEC':'lec', 'SYN LAB':'lab'}
                meetings = tuple(schedules.Meeting(schedules.digest(row), str(IDS[int(row['faculty'])]),
                    {'SYN101':'subject-a','SYN202':'subject-b'}[row['subject']], {'SYN-A':'section-a','SYN-B':'section-b'}[row['section']],
                    row['subject'], row.get('title',''), row['section'], row['type'], row['day'], row['start'], row['end'], room_ids[row['room']]) for row in result['schedule'])
                fixed = tuple(c.model_copy(update={'sections':tuple({'synthetic-section-a':'section-a','synthetic-section-b':'section-b'}[s] for s in c.sections),
                    'room': room_ids[dict(catalog.rooms)[c.room]] if c.room else None}) for c in snapshot.commitments)
                def unchanged():
                    assert store.path_for(id).read_bytes() == recorded
                    assert json.loads(f.publish_file.read_text(encoding='utf-8'))['run_id'] == id
                source = schedules.ReviewSchedule('fictional-published-v2-'+id, schedules.digest(result), catalog.academic_year, catalog.term,
                    snapshot.digest, meetings, f.rooms, f.windows, fixed, unchanged, lambda *args: None)
                yield published.PublicationContext(source, 'fictional-explicit-publisher:'+id, 'fictional-full-policy.1', lambda:Session(engine),
                    values, tuple((str(v),str(i)) for i,v in enumerate(IDS)), (('subject-a','SYN101'),('subject-b','SYN202')),
                    (('section-a','SYN-A'),('section-b','SYN-B')), 'required', 'fictional-capacity.1', (('section-a',20),('section-b',15)), (('lec',40),('lab',30)))
        monkeypatch.setattr(published, 'institutional_publication_source', publication)
        f.publication_provider = publication
        f.headers = session(f, 'admin')
        f.confirmation = proposal(f, f.headers)
        assert decision(f, f.headers, f.confirmation).status_code == 200
        with Session(engine) as db:
            f.snapshot = constraints._read_snapshot(db, catalog, values)
        saved_rng = random.getstate()
        try:
            yield f
        finally:
            deadline = time.monotonic()+30
            while any(j.active for j in ga.JOBS.values()) and time.monotonic() < deadline:
                time.sleep(.01)
            assert not any(j.active for j in ga.JOBS.values())
            assert path.read_bytes() == original
            assert random.getstate() == saved_rng
            try:
                next(chair_generator)
            except StopIteration:
                pass
