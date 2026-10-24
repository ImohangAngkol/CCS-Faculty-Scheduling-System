"""Read a fictional D13 application through a fresh Python process, no source writes."""
from contextlib import redirect_stdout, redirect_stderr
import json
import os
import sys

config=json.load(sys.stdin)  # Private session transfer; never argv or evidence.
with open(os.devnull,'w') as sink, redirect_stdout(sink), redirect_stderr(sink):
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from adjustment_models import AdjustmentRequest
    from services.adjustment_service import verify
    from fastapi.testclient import TestClient
    from main import app
    from database import get_identity_db
    from services import auth_service as auth, identity_service, metadata_service
    from services.identity_service import FacultyIdentity
    from genetic_algorithm.models.Faculty import Faculty
    from tests.dashboard.test_my_schedule import IDS
    engine=create_engine('sqlite:///'+sys.argv[1])
    with Session(engine) as db:
        rows=db.scalars(select(AdjustmentRequest)).all()
        result=[{'status':r.status,'version':r.version,'events':len(verify(db,r))} for r in rows]
    identities=tuple(FacultyIdentity(str(id),i,f'Synthetic Faculty {i}',f'Synthetic Lecturer {i}') for i,id in enumerate(IDS))
    identity_service.load_faculty_identities=lambda:identities
    members=[Faculty(i,1) for i in range(3)]
    for member,identity in zip(members,identities):member.stable_id=identity.faculty_id
    metadata_service.scheduling.list_faculty=members
    def session():
        with Session(engine) as db:yield db
    app.dependency_overrides={get_identity_db:session,auth.authenticated_db:session}
    with TestClient(app,base_url='http://localhost') as client:
        client.cookies.set(auth.COOKIE_NAME,config['private_session'])
        reply=client.get('/api/adjustment-requests/'+config['request_id'])
        assert reply.status_code==200
        own=reply.json()
        assert own['status']==config['expected_status'] and len(own['history'])==2 and own['schedule_changed'] is True
        assert own['application']['payload_digest']==config['expected_digest']
    engine.dispose()
print(json.dumps({'fresh_process':True,'requests':result,'fresh_authenticated_API_read':True}))
