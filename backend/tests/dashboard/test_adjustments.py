"""D11 real auth/API/persistence with fictional resources and owned SQLite only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
import copy
import hashlib
import json
import random
import threading
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from adjustment_models import AdjustmentBase, AdjustmentRequest, AdjustmentEvent
from services import adjustment_schedule_service as source, adjustment_service as service
from services.ga_v2_constraints import Snapshot, Catalog, Commitment
from services import auth_service as auth
from tests.dashboard.test_my_schedule import fixture, login, IDS, ORIGIN

ENDPOINT = '/api/adjustment-requests'


@pytest.fixture
def setup(fixture, monkeypatch):
    f = fixture
    AdjustmentBase.metadata.create_all(f.engine)
    from tests.dashboard.chair_sqlite import install
    install(f.engine)
    from tests.dashboard.application_sqlite import install as install_application
    install_application(f.engine)
    # SQLite append-only equivalents, fixture-owned schema only. PostgreSQL
    # migration functions are rendered/tested offline separately.
    with f.engine.begin() as db:
        for operation in ('UPDATE', 'DELETE'):
            db.exec_driver_sql(f"CREATE TRIGGER d11_events_{operation} BEFORE {operation} ON faculty_adjustment_events BEGIN SELECT RAISE(ABORT,'immutable history'); END")
        db.exec_driver_sql("CREATE TRIGGER d11_requests_delete BEFORE DELETE ON faculty_adjustment_requests BEGIN SELECT RAISE(ABORT,'immutable history'); END")
    catalog = Catalog(academic_year='2026-2027', term='Fictional first semester', effective_start='2026-08-01', effective_end='2026-12-31',
        revision='fictional-catalog-1', input_fingerprint='a'*64, template_digest='b'*64,
        sections=(('section-a','SYN-A'),('section-b','SYN-B')),
        faculty=tuple((str(IDS[i]),str(i)) for i in range(3)), rooms=(('lec','SYN LEC'),('lab','SYN LAB')))
    f.snapshot = Snapshot(catalog=catalog, heads=(), commitments=())
    f.guard = threading.RLock()
    f.rooms = (source.Room('lec','SYN LEC','Lecture'),source.Room('lab','SYN LAB','Laboratory'))
    f.windows = tuple((kind, key, day, '07:30', '19:00') for kind,keys in [('faculty',map(str,IDS)),('section',['section-a','section-b']),('room',['lec','lab'])] for key in keys for day in ['M','T','W','TH','F','S'])
    f.after_check = lambda: None
    @contextmanager
    def provider():
        with f.guard:
            value=source.legacy_projection(f.path,academic_year=catalog.academic_year,term=catalog.term,
                faculty_ids={str(i):IDS[i] for i in range(3)},subject_ids={'SYN101':'subject-a','SYN202':'subject-b'},
                section_ids={'SYN-A':'section-a','SYN-B':'section-b'},rooms=f.rooms,windows=f.windows,constraint_snapshot=f.snapshot)
            def checked():
                value.check_current();f.after_check()
            yield replace(value,check_current=checked)
    monkeypatch.setattr(source,'institutional_schedule_source',provider)
    f.provider = provider
    f.original = f.path.read_bytes()
    f.headers = session(f)
    yield f
    assert f.path.read_bytes() == f.original, 'D11 changed an original schedule'


def session(f, number=0):
    login(f,number)
    result=f.client.get('/api/auth/me')
    return {'Origin':ORIGIN,'X-CSRF-Token':result.json()['csrf_token']}


def request_for(f, **changes):
    bundle=f.client.get(ENDPOINT+'/assignments').json()
    row=bundle['assignments'][0]
    result={k:bundle[k] for k in ('schedule_id','revision','academic_year','term')}
    result.update(assignment_id=row['id'],proposal={'day':'F','start':'07:30','end':'10:30','room_id':'lec'},
        justification='Fictional faculty proposes a more suitable meeting.',operation_id=str(uuid4()))
    result.update(changes)
    return result


def create(f, body=None):
    r=f.client.post(ENDPOINT,headers=f.headers,json=body or request_for(f))
    assert r.status_code==201, r.status_code
    return r.json()


def command(f,r,action, **changes):
    body={'operation_id':str(uuid4()),'expected_version':r['version'],**changes}
    return f.client.post(f"{ENDPOINT}/{r['id']}/{action}",headers=f.headers,json=body)


def test_create_submit_withdraw_history_and_no_schedule_or_rng_changes(setup):
    f=setup; rng=random.getstate(); row=create(f)
    assert row['status']=='DRAFT' and row['version']==1 and row['freshness']['state']=='CURRENT'
    assert row['content']['review']['validation']['outcome']=='VALID_PROPOSAL'
    reply=command(f,row,'submit');assert reply.status_code==200
    row=reply.json();assert row['status']=='SUBMITTED' and row['submitted_at']
    reply=command(f,row,'withdraw');assert reply.status_code==200
    row=reply.json();assert row['status']=='WITHDRAWN' and row['withdrawn_at']
    assert [h['action'] for h in row['history']]==['CREATED','SUBMITTED','WITHDRAWN']
    assert row['schedule_changed'] is False and row['approval']=='NOT_IMPLEMENTED_D11'
    assert random.getstate()==rng
    assert f.client.get(f"{ENDPOINT}/{row['id']}/status").json()['status']=='WITHDRAWN'
    assert len(f.client.get(f"{ENDPOINT}/{row['id']}/history").json()['history'])==3


@pytest.mark.parametrize('mode',['anonymous','admin','forged','missing_binding'])
def test_authorization_fails_before_source_access(setup,monkeypatch,mode):
    f=setup
    if mode=='anonymous':f.client.cookies.clear()
    if mode=='admin':session(f,'admin')
    if mode=='forged':f.client.cookies.clear();f.client.cookies.set(auth.COOKIE_NAME,'fictional-invalid')
    if mode=='missing_binding':monkeypatch.setattr(source,'institutional_schedule_source',lambda:None);f.members[0].stable_id=str(IDS[1])
    monkeypatch.setattr(source,'current_source',lambda:pytest.fail('Unauthorized source access'))
    assert f.client.get(ENDPOINT+'/assignments').status_code in (401,403)
    assert f.client.get(ENDPOINT).status_code in (401,403)


def test_cross_faculty_private_requests_and_assignment_spoofing(setup):
    f=setup;body=request_for(f);row=create(f,body);headers=session(f,1)
    for path in ['', '/history','/status']:
        assert f.client.get(f"{ENDPOINT}/{row['id']}"+path).status_code==404
    for action in ['submit','withdraw']:
        assert f.client.post(f"{ENDPOINT}/{row['id']}/{action}",headers=headers,json={'operation_id':str(uuid4()),'expected_version':1}).status_code==404
    assert f.client.get(ENDPOINT).json()['items']==[]
    assert f.client.post(ENDPOINT,headers=headers,json=body).status_code==404
    assert f.client.post(ENDPOINT,headers=headers,json={**request_for(f),'faculty_id':str(IDS[0])}).status_code==422


@pytest.mark.parametrize('headers',[{}, {'Origin':'https://evil.invalid'}])
def test_origin_csrf_required_for_all_mutations(setup,headers):
    f=setup
    assert f.client.post(ENDPOINT,headers=headers,json=request_for(f)).status_code==403
    assert f.client.post(ENDPOINT+'/preview',headers=headers,json={}).status_code==403


def test_idempotency_duplicate_active_and_withdrawal_release(setup):
    f=setup;b=request_for(f);a=create(f,b);again=create(f,b)
    assert a['id']==again['id'] and len(again['history'])==1
    assert f.client.post(ENDPOINT,headers=f.headers,json={**b,'justification':'Different operation payload.'}).status_code==409
    assert f.client.post(ENDPOINT,headers=f.headers,json={**b,'operation_id':str(uuid4())}).status_code==409
    transition={'operation_id':str(uuid4()),'expected_version':1}
    for _ in range(2):
        reply=f.client.post(f"{ENDPOINT}/{a['id']}/submit",headers=f.headers,json=transition)
        assert reply.status_code==200 and len(reply.json()['history'])==2
    done=command(f,reply.json(),'withdraw').json()
    assert command(f,done,'withdraw').status_code==409
    assert command(f,done,'approve').status_code==404
    b['operation_id']=str(uuid4());assert create(f,b)['id']!=a['id']


@pytest.mark.parametrize('field,value,code',[('term','Other semester','TERM_MISMATCH'),('academic_year','2030-2031','TERM_MISMATCH'),('revision','f'*64,'STALE_SCHEDULE_REFERENCE'),('assignment_id','a'*64,'ASSIGNMENT_NOT_FOUND')])
def test_invalid_or_stale_schedule_scope(setup,field,value,code):
    f=setup;b=request_for(f,**{field:value});r=f.client.post(ENDPOINT,headers=f.headers,json=b)
    assert r.status_code in (404,409) and r.json()['detail']['code']==code


@pytest.mark.parametrize('change,code',[({'start':'25:00'},'INVALID_TIME_OR_DURATION'),({'end':'07:30'},'INVALID_TIME_OR_DURATION'),({'start':'07:45','end':'10:45'},'INVALID_TIME_OR_DURATION'),({'end':'09:30'},'INVALID_TIME_OR_DURATION'),({'room_id':'unknown'},'MISSING_RESOURCE'),({'room_id':'lab'},'ROOM_COMPONENT_MISMATCH')])
def test_invalid_times_and_room(setup,change,code):
    f=setup;b=request_for(f);b['proposal'].update(change)
    r=f.client.post(ENDPOINT+'/preview',headers=f.headers,json={k:v for k,v in b.items() if k!='operation_id'})
    assert r.status_code==422 and r.json()['detail']['code']==code


@pytest.mark.parametrize('kind',['faculty','room','section'])
def test_conflicting_proposals_are_explicit_not_approved(setup,kind):
    f=setup;b=request_for(f);b['proposal']['day']='T'
    # Existing actual source row belongs to faculty1/sectionB/lecture room.
    # Resource-specific fixture mappings are explicit and never name-derived.
    payload=copy.deepcopy(f.payload)
    if kind=='faculty':payload['schedule'][2]['faculty']='0'
    if kind=='section':payload['schedule'][2]['section']='SYN-A'
    # These changes can invalidate the original full GA source. For validation
    # isolation, use an explicitly fictional detached source after real read.
    with f.provider() as s:
        other=s.meetings[2]
        if kind=='faculty':other=replace(other,faculty_id=str(IDS[0]))
        if kind=='section':other=replace(other,section_id='section-a')
        current=replace(s,meetings=(*s.meetings[:2],other))
        findings=source.validate(current,SimpleNamespace(faculty_id=str(IDS[0])),__import__('schemas.adjustments',fromlist=['Preview']).Preview.model_validate({k:v for k,v in b.items() if k!='operation_id'}))
    assert kind.upper()+'_CONFLICT' in [x['code'] for x in findings['validation']['findings']]
    assert findings['validation']['conflict_free'] is False
    assert create(f,b)['content']['review']['validation']['outcome']=='REQUIRES_REVIEW'


def test_gec_conflict_and_adjacent_interval(setup):
    f=setup
    fixed=Commitment(record_id='fictional-record',revision_id='fictional-revision',source_row=1,source_sha256='d'*64,
        subject='Fictional GEC',day='F',start=450,end=630,sections=('section-a',),faculty=None,room=None)
    f.snapshot=f.snapshot.model_copy(update={'commitments':(fixed,)})
    row=create(f);assert 'CONFIRMED_GEC_CONFLICT' in [x['code'] for x in row['content']['review']['validation']['findings']]
    b=request_for(f);b['proposal'].update(start='10:30',end='13:30')
    assert create(f,b)['content']['review']['validation']['conflict_free'] is True


def test_laboratory_original_duration_cannot_be_shortened(setup):
    f=setup;b=request_for(f);assignments=f.client.get(ENDPOINT+'/assignments').json()['assignments'];b['assignment_id']=assignments[1]['id'];b['proposal'].update(room_id='lab',end='09:30')
    assert f.client.post(ENDPOINT,headers=f.headers,json=b).status_code==422
    b['proposal']['end']='10:30';assert create(f,b)['content']['review']['original']['component']=='Laboratory'


def test_stale_and_missing_source_preserve_history_allow_withdrawal(setup,monkeypatch):
    f=setup;row=create(f)
    f.snapshot=f.snapshot.model_copy(update={'catalog':f.snapshot.catalog.model_copy(update={'revision':'fictional-next'})})
    stale=f.client.get(f"{ENDPOINT}/{row['id']}").json();assert stale['freshness']['state']=='STALE'
    assert command(f,row,'submit').status_code==409
    monkeypatch.setattr(source,'institutional_schedule_source',lambda:None)
    assert f.client.get(ENDPOINT+'/assignments').status_code==503
    unavailable=f.client.get(f"{ENDPOINT}/{row['id']}").json();assert unavailable['freshness']['state']=='UNAVAILABLE'
    assert command(f,row,'withdraw').status_code==200


def test_schedule_revision_changes_are_never_redirected(setup):
    f=setup;row=create(f)
    # Guarded fictional provider changes revision, without modifying source data.
    @contextmanager
    def newer():
        with f.provider() as s:yield replace(s,revision='c'*64)
    from unittest.mock import patch
    with patch.object(source,'institutional_schedule_source',newer):
        detail=f.client.get(f"{ENDPOINT}/{row['id']}").json()
        assert detail['freshness']['state']=='STALE' and detail['content']==row['content']
        assert command(f,row,'submit').status_code==409


def test_transaction_rolls_back_on_source_change(setup):
    f=setup
    def fail():raise source.problem(409,'SOURCE_CHANGED','Fictional source changed before commit.')
    b=request_for(f);f.after_check=fail
    assert f.client.post(ENDPOINT,headers=f.headers,json=b).status_code==409
    with Session(f.engine) as db:
        assert not db.scalar(select(AdjustmentRequest)) and not db.scalar(select(AdjustmentEvent))


def test_concurrent_compare_and_swap_updates_and_durability(setup):
    f=setup;row=create(f)
    with Session(f.engine) as db:user=db.scalar(select(__import__('identity_models').User).where(__import__('identity_models').User.username=='faculty0@example.invalid'));db.expunge(user)
    from schemas.adjustments import Transition
    principal=SimpleNamespace(faculty_id=str(IDS[0]));barrier=threading.Barrier(2)
    def change():
        with Session(f.engine) as db:
            barrier.wait()
            try:return service.transition(db,user,principal,__import__('uuid').UUID(row['id']),'withdraw',Transition(operation_id=uuid4(),expected_version=1))['status']
            except Exception as e:return getattr(e,'status_code',type(e).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:change(),range(2)))
    assert results.count('WITHDRAWN')==1
    with Session(f.engine) as db:
        record=service.owner(db,__import__('uuid').UUID(row['id']),user,principal)
        assert len(service.detail(db,record,principal)['history'])==2


def test_immutable_history_and_tamper_detection(setup):
    f=setup;row=create(f)
    with f.engine.begin() as db:
        with pytest.raises(Exception):db.execute(text("UPDATE faculty_adjustment_events SET action='SUBMITTED'"))
    # Deliberate request-payload corruption in disposable SQLite detects failure.
    with f.engine.begin() as db:db.execute(text("UPDATE faculty_adjustment_requests SET content_json='{}'"))
    assert f.client.get(f"{ENDPOINT}/{row['id']}").status_code==503


def test_request_survives_fresh_python_process(setup):
    import os, subprocess, sys
    f=setup;r=create(f);assert command(f,r,'submit').status_code==200
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT'}}
    private={'request_id':r['id'],'private_session':f.client.cookies.get(auth.COOKIE_NAME)}
    child=subprocess.run([sys.executable,'-B','-m','tests.dashboard.adjustment_restart_child',str(f.engine.url.database)],env=env,input=json.dumps(private),capture_output=True,text=True,timeout=25)
    assert child.returncode==0,'Fresh-process read failed; no private payload emitted'
    assert json.loads(child.stdout)=={'fresh_process':True,'requests':[{'status':'SUBMITTED','version':2,'events':2}],'fresh_authenticated_API_read':True}


def test_schedule_adapter_rejects_cross_faculty_catalog_mapping(setup):
    f=setup
    with pytest.raises(ValueError,match='mapping mismatch'):
        source.legacy_projection(f.path,academic_year='2026-2027',term='Fictional first semester',
            faculty_ids={'0':IDS[1],'1':IDS[0]},subject_ids={'SYN101':'subject-a','SYN202':'subject-b'},
            section_ids={'SYN-A':'section-a','SYN-B':'section-b'},rooms=f.rooms,windows=f.windows,constraint_snapshot=f.snapshot)
