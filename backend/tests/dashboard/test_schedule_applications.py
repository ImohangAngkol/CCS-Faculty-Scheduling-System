"""D13 real authentication/SQL transactions; fictional published source only."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import copy,json,random,threading
from types import SimpleNamespace
from uuid import UUID,uuid4
import pytest
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from fastapi import HTTPException
from identity_models import User
from adjustment_models import AdjustmentRequest,AdjustmentEvent
from chair_models import ChairDecision
from application_models import PublishedHead,PublishedVersion,ScheduleApplication
from services import application_authority_service as authority,published_schedule_source as publication,schedule_application_service as service,schedule_version_store as store
from services import auth_service as auth,ga_service
from services.chair_authority_service import Mandate
from tests.dashboard.test_chair_reviews import chair,setup,fixture,submitted,decide,session,DEPT,OTHER,IDS,ORIGIN,ENDPOINT

BASE='/api/schedule-applications'


@pytest.fixture
def application(chair,monkeypatch):
    f=chair
    with Session(f.engine) as db,db.begin():
        original=db.scalar(select(User).where(User.username=='admin@example.invalid'))
        publisher=User(id=uuid4(),username='scheduler@example.invalid',role='admin',password_hash=original.password_hash,is_active=True);db.add(publisher);f.publisher_id=publisher.id
        second=User(id=uuid4(),username='scheduler2@example.invalid',role='admin',password_hash=original.password_hash,is_active=True);db.add(second);f.publisher2_id=second.id
    f.apply_state='ACTIVE';f.apply_role='schedule_application';f.apply_enabled=True;f.apply_scope=DEPT;f.capacity=100;f.enrollment=10;f.capacity_mode='required';f.publisher_calls=0
    class Directory:
        def application_mandate_for(self,id):
            if not f.apply_enabled or id not in {str(f.publisher_id),str(f.publisher2_id)}:return None
            f.publisher_calls+=1;stamp=datetime.now(timezone.utc)
            return Mandate(actor_id=UUID(id),role=f.apply_role,state=f.apply_state,departments=((DEPT,'Fictional Computing Department'),),reference='fictional-publication-mandate',policy_digest='e'*64,issued_at=stamp,expires_at=stamp+timedelta(seconds=120))
        def department_for(self,*args):
            with f.directory() as directory:
                return directory.department_for(*args).model_copy(update={'department_id':f.apply_scope})
    @contextmanager
    def directory():yield Directory()
    monkeypatch.setattr(authority,'institutional_application_directory',directory)
    f.application_directory=directory
    @contextmanager
    def source():
        with f.provider() as base:
            yield publication.PublicationContext(source=base,publication_reference='fictional-explicit-published-source.1',policy_reference='fictional-complete-policy.1',session_factory=lambda:Session(f.engine),
                templates=(f.courses,f.members,ga_service.lst_rooms),faculty_codes=tuple((str(id),str(i)) for i,id in enumerate(IDS)),subject_codes=(('subject-a','SYN101'),('subject-b','SYN202')),section_codes=(('section-a','SYN-A'),('section-b','SYN-B')),
                capacity_applicability=f.capacity_mode,capacity_reference='fictional-capacity-source.1',section_enrollment=(('section-a',f.enrollment),('section-b',f.enrollment)),room_capacity=(('lec',f.capacity),('lab',f.capacity)))
    monkeypatch.setattr(publication,'institutional_publication_source',source);f.publication_provider=source
    return f


def publisher(f):
    reply=f.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'username':'scheduler@example.invalid','password':f.password});assert reply.status_code==200
    f.apply_headers={'Origin':ORIGIN,'X-CSRF-Token':f.client.get('/api/auth/me').json()['csrf_token']}
    return f.apply_headers


def approved(f,**changes):
    r=submitted(f,**changes);f.chair_headers=session(f,'admin');response=decide(f,r);assert response.status_code==200,response.json();publisher(f);return r


def preview(f,r):return f.client.get(BASE+'/'+r['id']+'/preview')


def apply(f,r,body=None):
    if body is None:
        response=preview(f,r);assert response.status_code==200,response.json();body={**response.json()['command'],'operation_id':str(uuid4())}
    return f.client.post(BASE+'/'+r['id']+'/apply',headers=f.apply_headers,json=body)


def counts(f):
    with Session(f.engine) as db:return [len(db.scalars(select(t)).all()) for t in (PublishedVersion,PublishedHead,ScheduleApplication)]


def test_full_application_versions_own_view_and_immutable_history(application):
    f=application;r=approved(f);before=f.path.read_bytes();rng=random.getstate()
    with Session(f.engine) as db:
        old_request=db.get(AdjustmentRequest,UUID(r['id'])).content_json;old_decision=db.scalar(select(ChairDecision)).payload_json;events=[e.payload_json for e in db.scalars(select(AdjustmentEvent).order_by(AdjustmentEvent.sequence))]
    p=preview(f,r);assert p.status_code==200,p.json();p=p.json();assert p['can_apply'] and p['validation']['outcome']=='VALID';assert counts(f)==[0,0,0]
    body={**p['command'],'operation_id':str(uuid4())};reply=apply(f,r,body);assert reply.status_code==200,reply.json();applied=reply.json();assert applied['status']=='APPLIED' and applied['sequence']==2;assert counts(f)==[2,1,1]
    assert apply(f,r,body).json()==applied
    assert apply(f,r,{**body,'operation_id':str(uuid4())}).status_code==409
    versions=f.client.get(BASE+'/versions').json()['versions'];assert len(versions)==2 and versions[1]['previous_id']==versions[0]['id']
    a,b=versions[0]['meetings'],versions[1]['meetings'];assert sum(x!=y for x,y in zip(a,b))==1
    assert a[0]['day']=='M' and b[0]['day']=='F';assert versions[1]['origin']=='POST_GA_AUTHORIZED_ADJUSTMENT'
    assert f.client.get(BASE+'/versions?version_id='+versions[0]['id']).json()['versions'][0]==versions[0]
    assert f.client.get(BASE).json()=={'items':[]};assert f.client.get(BASE+'?include_applied=true').json()['items'][0]['status']=='APPLIED'
    assert f.client.get(BASE+'/'+r['id']+'/history').json()['applications']==[applied]
    f.headers=session(f);own=f.client.get(ENDPOINT+'/'+r['id']).json();assert own['status']=='APPLIED' and own['decision']['status']=='APPROVED_PENDING_APPLICATION' and own['application']==applied
    timetable=f.client.get('/api/schedules/me').json();assert timetable['schema_version']==2 and timetable['source']['post_ga_changes'] is True;assert timetable['assignments'][0]['day']=='F' and len(timetable['assignments'])==2
    assert 'faculty_id' not in timetable['assignments'][0] and 'SYN202' not in json.dumps(timetable)
    assert f.client.get(ENDPOINT+'/'+r['id']+'/status').json()['application']==applied
    with Session(f.engine) as db:
        assert db.get(AdjustmentRequest,UUID(r['id'])).content_json==old_request
        assert db.scalar(select(ChairDecision)).payload_json==old_decision
        assert [e.payload_json for e in db.scalars(select(AdjustmentEvent).order_by(AdjustmentEvent.sequence))]==events
    assert f.path.read_bytes()==before
    assert random.getstate()==rng


@pytest.mark.parametrize('mode',['anonymous','faculty','chair_only','no_provider','wrong_role','revoked','scope'])
def test_authority_and_scope_fail_closed(application,monkeypatch,mode):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    if mode=='anonymous':f.client.cookies.clear();f.apply_headers={'Origin':ORIGIN}
    if mode=='faculty':f.apply_headers=session(f)
    if mode=='chair_only':f.apply_headers=session(f,'admin')
    if mode=='no_provider':monkeypatch.setattr(authority,'institutional_application_directory',lambda:None)
    if mode=='wrong_role':f.apply_role='department_chair'
    if mode=='revoked':f.apply_state='REVOKED'
    if mode=='scope':f.apply_scope=OTHER
    response=apply(f,r,body);assert response.status_code==(401 if mode=='anonymous' else 503 if mode=='no_provider' else 404 if mode=='scope' else 403)
    assert counts(f)==[0,0,0]


@pytest.mark.parametrize('state',['draft','submitted','rejected','withdrawn'])
def test_approval_required(application,state):
    f=application
    from tests.dashboard.test_adjustments import create,command
    if state=='draft':r=create(f)
    else:r=submitted(f)
    if state=='rejected':f.chair_headers=session(f,'admin');assert decide(f,r,'reject').status_code==200
    if state=='withdrawn':assert command(f,r,'withdraw').status_code==200
    publisher(f);assert preview(f,r).status_code==409;assert counts(f)==[0,0,0]


@pytest.mark.parametrize('field,value',[('decision_id',str(uuid4())),('decision_digest','a'*64),('expected_revision','b'*64),('expected_sequence',9),('constraint_digest','c'*64)])
def test_stale_references_do_not_publish(application,field,value):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4()),field:value};assert apply(f,r,body).status_code==409;assert counts(f)==[0,0,0]


@pytest.mark.parametrize('change',['capacity','missing_capacity','qualification','max_load','availability','GEC','term','assignment','chair_revoked','trust'])
def test_fresh_complete_validation(application,monkeypatch,change):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    if change=='capacity':f.capacity=1
    elif change=='missing_capacity':f.capacity=None
    elif change=='qualification':f.members[0].eligible_subjects=set()
    elif change=='max_load':f.courses[0].credit_units=50
    elif change=='chair_revoked':f.chair_state='REVOKED'
    elif change=='trust':f.trust=False
    else:
        original=f.publication_provider
        @contextmanager
        def changed():
            with original() as c:
                s=c.source
                if change=='availability':s=replace(s,windows=())
                elif change=='term':s=replace(s,term='Wrong term')
                elif change=='assignment':s=replace(s,meetings=tuple(replace(m,id='changed') if i==0 else m for i,m in enumerate(s.meetings)))
                else:
                    from services.ga_v2_constraints import Commitment
                    fixed=Commitment(record_id='fictional',revision_id='fictional',source_row=1,source_sha256='a'*64,subject='Synthetic External',day='F',start=450,end=630,sections=('section-a',),faculty=None,room=None)
                    s=replace(s,commitments=(fixed,))
                yield replace(c,source=s)
        monkeypatch.setattr(publication,'institutional_publication_source',changed)
    reply=apply(f,r,body)
    assert reply.status_code in ((404,) if change=='assignment' else (409,403,503)),reply.json()
    assert counts(f)==[0,0,0]


def test_failure_after_audit_insert_rolls_back_head_and_both_versions(application):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    from sqlalchemy import event
    def failure(mapper,connection,target):raise IntegrityError('fictional storage failure',None,None)
    event.listen(ScheduleApplication,'after_insert',failure)
    try:assert apply(f,r,body).status_code==409
    finally:event.remove(ScheduleApplication,'after_insert',failure)
    assert counts(f)==[0,0,0]
    assert apply(f,r,body).status_code==200


def test_database_guards_and_cross_faculty_reads(application):
    f=application;r=approved(f);assert apply(f,r).status_code==200
    for sql in ['DELETE FROM published_schedule_versions','UPDATE published_schedule_versions SET revision=revision','DELETE FROM schedule_adjustment_applications','UPDATE schedule_adjustment_applications SET payload_digest=payload_digest','DELETE FROM published_schedule_heads','UPDATE published_schedule_heads SET sequence=sequence+1']:
        with pytest.raises(IntegrityError),f.engine.begin() as db:db.exec_driver_sql(sql)
    f.headers=session(f,1);assert f.client.get(ENDPOINT+'/'+r['id']).status_code==404
    reply=f.client.get('/api/schedules/me').json();assert [m['subject'] for m in reply['assignments']]==['SYN202']


def test_two_independent_transactions_publish_once(application,monkeypatch):
    f=application;r=approved(f);body=preview(f,r).json()['command']
    with f.publication_provider() as c:ctx=c
    @contextmanager
    def independent():yield ctx
    monkeypatch.setattr(publication,'institutional_publication_source',independent)
    with f.directory() as d:directory=d
    @contextmanager
    def independent_chair():yield directory
    from services import chair_authority_service as chair_authority
    monkeypatch.setattr(chair_authority,'institutional_chair_directory',independent_chair)
    with Session(f.engine) as db:
        actors=[db.get(User,id) for id in (f.publisher_id,f.publisher2_id)]
        for actor in actors:db.expunge(actor)
    from schemas.schedule_applications import ApplicationCommand
    start=threading.Barrier(2)
    def work(index):
        start.wait(timeout=5)
        try:
            with Session(f.engine) as db:service.apply(db,actors[index],UUID(r['id']),ApplicationCommand.model_validate({**body,'operation_id':str(uuid4())}))
            return 'APPLIED'
        except (HTTPException,SQLAlchemyError):return 'BLOCKED'
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(work,range(2)))
    assert sorted(results)==['APPLIED','BLOCKED'];assert counts(f)==[2,1,1]


def test_subsequent_requests_bind_new_published_version_and_competing_approvals_go_stale(application):
    f=application;first=approved(f)
    second=approved(f,proposal={'day':'TH','start':'07:30','end':'10:30','room_id':'lec'})
    assert apply(f,first).status_code==200
    assert preview(f,second).status_code==409
    third=approved(f,proposal={'day':'TH','start':'07:30','end':'10:30','room_id':'lec'})
    assert third['content']['input']['revision']!=first['content']['input']['revision']
    response=apply(f,third);assert response.status_code==200,response.json();assert response.json()['sequence']==3
    versions=f.client.get(BASE+'/versions').json()['versions'];assert [v['sequence'] for v in versions]==[1,2,3]
    assert [v['meetings'][0]['day'] for v in versions]==['M','F','TH']


@pytest.mark.parametrize('resource',['faculty','room','section'])
def test_current_full_schedule_conflicts_block_application(application,monkeypatch,resource):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())};provider=f.publication_provider
    @contextmanager
    def changed():
        with provider() as ctx:
            m=ctx.source.meetings[0]
            other=replace(m,id='fictional-other-meeting',day='F',faculty_id=m.faculty_id if resource=='faculty' else str(IDS[1]),section_id=m.section_id if resource=='section' else 'section-b',room_id=m.room_id if resource=='room' else 'lab')
            yield replace(ctx,source=replace(ctx.source,meetings=ctx.source.meetings+(other,)))
    monkeypatch.setattr(publication,'institutional_publication_source',changed)
    assert apply(f,r,body).status_code==409;assert counts(f)==[0,0,0]


def test_publication_unavailable_and_extra_client_flags_never_publish(application,monkeypatch):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    for field in ['approved','department_id','bypass','actor_id']:
        assert apply(f,r,{**body,field:True}).status_code==422
    assert f.client.post(BASE+'/'+r['id']+'/apply',json=body,headers={'Origin':ORIGIN}).status_code==403
    monkeypatch.setattr(publication,'institutional_publication_source',lambda:None)
    assert apply(f,r,body).status_code==503;assert counts(f)==[0,0,0]


def test_capacity_findings_are_reviewable_without_persisting_preview(application):
    f=application;r=approved(f);f.capacity=None
    result=preview(f,r);assert result.status_code==200,result.json();p=result.json()
    assert p['status']=='APPLICATION_BLOCKED' and not p['can_apply']
    assert 'CAPACITY_METADATA_UNAVAILABLE' in {v['code'] for v in p['validation']['findings']}
    assert counts(f)==[0,0,0]


def test_application_authority_revocation_after_insert_rolls_back_publication(application):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    from sqlalchemy import event
    def revoke(*args):f.apply_state='REVOKED'
    event.listen(ScheduleApplication,'after_insert',revoke)
    try:assert apply(f,r,body).status_code==403
    finally:event.remove(ScheduleApplication,'after_insert',revoke)
    assert counts(f)==[0,0,0]


def test_changed_owner_binding_cannot_apply_historical_approval(application):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    with Session(f.engine) as db,db.begin():db.scalar(select(User).where(User.username=='faculty0@example.invalid')).is_active=False
    assert apply(f,r,body).status_code==403;assert counts(f)==[0,0,0]


def test_fresh_process_authenticated_application_history(application):
    f=application;r=approved(f);reply=apply(f,r);assert reply.status_code==200
    f.headers=session(f)
    import os,subprocess,sys
    private={'request_id':r['id'],'private_session':f.client.cookies.get(auth.COOKIE_NAME),'expected_status':'APPLIED','expected_digest':reply.json()['payload_digest']}
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT'}}
    result=subprocess.run([sys.executable,'-B','-m','tests.dashboard.application_restart_child',str(f.engine.url.database)],env=env,input=json.dumps(private),capture_output=True,text=True,timeout=25)
    assert result.returncode==0,'Fresh-process application read failed; private payload omitted'
    assert json.loads(result.stdout)['fresh_authenticated_API_read'] is True


def test_original_chair_guard_is_held_through_commit(application,monkeypatch):
    f=application;r=approved(f);body={**preview(f,r).json()['command'],'operation_id':str(uuid4())}
    from services import chair_authority_service as chair_authority
    from sqlalchemy import event
    original=chair_authority.authorized;held=[];committed=[]
    @contextmanager
    def guarded(actor):
        with original(actor) as value:
            held.append(True)
            try:yield value
            finally:held.pop()
    monkeypatch.setattr(chair_authority,'authorized',guarded)
    def observed(db):committed.append(bool(held))
    event.listen(Session,'after_commit',observed)
    try:assert apply(f,r,body).status_code==200
    finally:event.remove(Session,'after_commit',observed)
    assert committed==[True] and not held
