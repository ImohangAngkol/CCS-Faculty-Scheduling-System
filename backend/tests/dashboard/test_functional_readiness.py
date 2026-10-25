"""D16 isolated reload/restart and negative journeys; real services, fictional authority."""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from uuid import uuid4

from fastapi.testclient import TestClient
from main import app
from tests.dashboard.test_my_schedule import ORIGIN
from tests.dashboard.test_system_acceptance import (
    system, application, chair, setup, fixture, isolate, approved_generated,
    generate, own_proposal, session, publisher, counts, store, create, command,
)


def apply(f, request):
    publisher(f)
    reply=f.client.get('/api/schedule-applications/'+request['id']+'/preview')
    assert reply.status_code==200 and reply.json()['can_apply']
    return f.client.post('/api/schedule-applications/'+request['id']+'/apply', headers=f.apply_headers,
                         json={**reply.json()['command'],'operation_id':str(uuid4())})


def test_published_journey_survives_pool_restart_fresh_process_and_login(system):
    f=system
    run,result,elapsed,request=approved_generated(f)
    generated=store.path_for(run).read_bytes()
    rng=random.getstate()
    assert apply(f,request).status_code==200
    session(f,0)
    before=f.client.get('/api/schedules/me').json()
    assert before['source']['sequence']==2
    f.engine.dispose()  # Owned file-backed SQLite only; no service/database reset.
    with TestClient(app) as client:
        reply=client.post('/api/auth/login',headers={'Origin':ORIGIN},
                          json={'username':'faculty0@example.invalid','password':f.password})
        assert reply.status_code==200
        assert client.get('/api/schedules/me').json()==before
        detail=client.get('/api/adjustment-requests/'+request['id']).json()
        assert detail['status']=='APPLIED' and len(detail['history'])==2
    database=Path(f.engine.url.database).resolve()
    assert database.is_relative_to(Path(os.environ['TEMP']).resolve())
    script="""import sqlite3,json,sys
with sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True) as db:
 db.execute('PRAGMA query_only=ON')
 assert db.execute('PRAGMA query_only').fetchone()[0]==1
 print(json.dumps({t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('published_schedule_versions','published_schedule_heads','schedule_adjustment_applications','faculty_adjustment_decisions')}))
"""
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','TEMP','TMP'}}
    result=subprocess.run([sys.executable,'-B','-c',script,str(database)],env=env,capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)=={'published_schedule_versions':2,'published_schedule_heads':1,'schedule_adjustment_applications':1,'faculty_adjustment_decisions':1}
    assert store.path_for(run).read_bytes()==generated and random.getstate()==rng
    assert counts(f)==[2,1,1]


def test_generated_request_rejects_conflict_duplicate_and_stale_replay(system):
    f=system
    run,result,elapsed=generate(f)
    body=own_proposal(f)
    # A time interval with reversed bounds must not become a valid proposal.
    invalid={**body,'proposal':{**body['proposal'],'start':'18:00','end':'07:30'}}
    response=f.client.post('/api/adjustment-requests/preview',headers=f.headers,json=invalid)
    assert response.status_code==422
    record=create(f,{**body,'operation_id':str(uuid4())})
    duplicate=f.client.post('/api/adjustment-requests',headers=f.headers,json={**body,'operation_id':str(uuid4())})
    assert duplicate.status_code==409
    assert command(f,record,'submit').status_code==200
    stale=command(f,record,'submit')
    assert stale.status_code==409
    assert f.client.get('/api/adjustment-requests/'+record['id']).json()['status']=='SUBMITTED'


def test_independent_authorities_can_be_revoked_without_enabling_fallback(system):
    f=system
    run,result,elapsed,record=approved_generated(f)
    f.apply_enabled=False
    publisher(f)
    assert f.client.get('/api/schedule-applications/access').status_code==403
    assert f.client.get('/api/schedule-applications/'+record['id']+'/preview').status_code==403
    assert counts(f)==[0,0,0]
    f.apply_enabled=True
    assert apply(f,record).status_code==200
