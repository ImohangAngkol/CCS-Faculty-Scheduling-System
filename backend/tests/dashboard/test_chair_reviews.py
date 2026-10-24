"""Actual authentication and transactional API, fictional Chair directory only."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from identity_models import User
from chair_models import ChairDecision
from adjustment_models import AdjustmentEvent, AdjustmentRequest
from services import chair_authority_service as authority, chair_review_service as service
from services import adjustment_schedule_service as schedules
from tests.dashboard.test_adjustments import setup, fixture, session, create, command, request_for, ENDPOINT, IDS, ORIGIN

BASE='/api/chair-reviews'
DEPT='70000000-0000-4000-8000-000000000001'
OTHER='70000000-0000-4000-8000-000000000002'


@pytest.fixture
def chair(setup, monkeypatch):
    f=setup
    with Session(f.engine) as db:
        f.chair_id=db.scalar(select(User.id).where(User.username=='admin@example.invalid'))
    f.chair_state='ACTIVE';f.role='department_chair';f.age=0;f.scope=DEPT;f.self_chair=None
    f.authority_changed=False;f.calls=0
    class Directory:
        def mandate_for(self, actor):
            if actor not in {str(f.chair_id),str(f.self_chair)}: return None
            stamp=datetime.now(timezone.utc)-timedelta(seconds=f.age)
            f.calls+=1
            return authority.Mandate(actor_id=UUID(actor),role=f.role,state=f.chair_state,departments=((DEPT,'Fictional Computing Department'),),reference='fictional-chair-mandate-v1' if not f.authority_changed or f.calls<3 else 'fictional-chair-mandate-v2',policy_digest='a'*64,issued_at=stamp,expires_at=stamp+timedelta(seconds=120))
        def department_for(self, faculty,subject,section,year,term):
            return authority.ScopeBinding(department_id=f.scope,faculty_id=faculty,subject_id=subject,section_id=section,academic_year=year,term=term,reference='fictional-scope-v1')
    @contextmanager
    def directory():
        with f.guard: yield Directory()
    monkeypatch.setattr(authority,'institutional_chair_directory',directory)
    # Workflow fixture uses an explicitly fictional, mutable trusted snapshot.
    # Real D8/D9/D10 validation is tested independently in test_chair_trust.py.
    f.trust=True
    def trusted(db, source):
        if not f.trust: raise service.problem(503,'CHAIR_TRUST_UNAVAILABLE','Fictional trust is unavailable.')
        if source.constraint_digest!=f.snapshot.digest: raise service.problem(409,'GEC_CONSTRAINT_SET_CHANGED','Fictional constraint revision changed.')
        return f.snapshot
    monkeypatch.setattr(service,'trusted_snapshot',trusted)
    f.directory=directory
    yield f
    with Session(f.engine) as db:
        for r in db.scalars(select(AdjustmentRequest)).all():
            from services.adjustment_service import verify
            verify(db,r)


def submitted(f, **changes):
    f.headers=session(f);r=create(f,request_for(f,**changes));reply=command(f,r,'submit');assert reply.status_code==200
    return reply.json()


def decision_body(r, **changes):
    return dict(operation_id=str(uuid4()),expected_version=r['version'],explanation='Fictional independent Chair decision explanation.',content_digest=r['content_digest'],schedule_revision=r['content']['input']['revision'],constraint_digest=r['content']['review']['constraint_digest'],**changes)


def decide(f,r,action='approve',body=None):
    return f.client.post(f"{BASE}/{r['id']}/{action}",headers=f.chair_headers,json=body or decision_body(r))


@pytest.mark.parametrize('action,status',[('approve','APPROVED_PENDING_APPLICATION'),('reject','REJECTED')])
def test_full_decision_owner_visibility_idempotency_and_history(chair,action,status):
    f=chair;r=submitted(f);before=r['history'];f.chair_headers=session(f,'admin')
    assert f.client.get(BASE+'/access').json()['capability']=='department_chair'
    assert len(f.client.get(BASE).json()['items'])==1
    review=f.client.get(BASE+'/'+r['id']).json();assert review['can_approve'] and review['can_reject']
    body=decision_body(r);reply=decide(f,r,action,body);assert reply.status_code==200,reply.json()
    d=reply.json();assert d['status']==status and d['schedule_changed'] is False and d['explanation']==body['explanation']
    assert decide(f,r,action,body).json()==d
    assert decide(f,r,action).status_code==409
    assert decide(f,r,'reject' if action=='approve' else 'approve').status_code==409
    assert f.client.get(BASE).json()=={'items':[]}
    assert f.client.get(BASE+'?include_decided=true').json()['items'][0]['status']==status
    assert f.client.get(BASE+'/'+r['id']+'/history').json()['history']==[d]
    f.headers=session(f);own=f.client.get(ENDPOINT+'/'+r['id']).json()
    assert own['status']==status and own['history']==before and own['version']==2
    assert own['decision']==d and own['base_status']=='SUBMITTED'
    assert command(f,own,'withdraw').status_code==409
    assert f.client.get(ENDPOINT+'/'+r['id']+'/status').json()['decision']==d
    # A different SQLAlchemy session proves durable storage, not response-only state.
    with Session(f.engine) as db:
        assert db.scalar(select(ChairDecision)).payload_digest==d['payload_digest']
        assert len(db.scalars(select(AdjustmentEvent)).all())==2
    import os, subprocess, sys
    from services import auth_service as auth
    env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT'}}
    private={'request_id':r['id'],'private_session':f.client.cookies.get(auth.COOKIE_NAME),'expected_status':status,'expected_digest':d['payload_digest']}
    child=subprocess.run([sys.executable,'-B','-m','tests.dashboard.chair_restart_child',str(f.engine.url.database)],env=env,input=json.dumps(private),capture_output=True,text=True,timeout=25)
    assert child.returncode==0,'Fresh-process decision read failed; no private payload emitted'
    assert json.loads(child.stdout)['fresh_authenticated_API_read'] is True


@pytest.mark.parametrize('mode',['anonymous','faculty','admin_without_mandate','wrong_role','expired','revoked','unconfigured'])
def test_no_authority_fails_closed(chair,monkeypatch,mode):
    f=chair;r=submitted(f)
    if mode=='anonymous':f.client.cookies.clear();headers={'Origin':ORIGIN}
    elif mode=='faculty':headers=f.headers
    else:
        headers=session(f,'admin')
        if mode=='admin_without_mandate':f.chair_id=uuid4()
        if mode=='wrong_role':f.role='admin'
        if mode=='expired':f.age=200
        if mode=='revoked':f.chair_state='REVOKED'
        if mode=='unconfigured':monkeypatch.setattr(authority,'institutional_chair_directory',lambda:None)
    reply=f.client.post(BASE+'/'+r['id']+'/approve',headers=headers,json=decision_body(r))
    assert reply.status_code==(401 if mode=='anonymous' else 503 if mode=='unconfigured' else 403)
    with Session(f.engine) as db:assert db.scalar(select(ChairDecision)) is None


def test_cross_department_read_decision_and_filter_do_not_leak(chair):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin');f.scope=OTHER
    assert f.client.get(BASE).json()=={'items':[]}
    assert f.client.get(BASE+'/'+r['id']).status_code==404
    assert decide(f,r).status_code==404
    assert f.client.get(BASE+'?department_id='+OTHER).status_code==403


def test_no_self_decision_even_with_verified_mandate(chair):
    f=chair;r=submitted(f)
    with Session(f.engine) as db:f.self_chair=db.scalar(select(User.id).where(User.username=='faculty0@example.invalid'))
    f.chair_headers=f.headers
    for action in ['approve','reject']:assert decide(f,r,action).status_code==403
    assert not f.client.get(BASE+'/'+r['id']).json()['can_approve']


@pytest.mark.parametrize('state',['draft','withdrawn'])
def test_ineligible_states(chair,state):
    f=chair;r=create(f)
    if state=='withdrawn':r=command(f,r,'withdraw').json()
    f.chair_headers=session(f,'admin')
    assert decide(f,r).status_code==409


@pytest.mark.parametrize('field,value',[('expected_version',99),('content_digest','b'*64),('schedule_revision','c'*64),('constraint_digest','d'*64)])
def test_optimistic_bindings_are_not_authority(chair,field,value):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin');body=decision_body(r);body[field]=value
    assert decide(f,r,body=body).status_code==409


@pytest.mark.parametrize('change',['stale','term','trust','owner_binding'])
def test_current_validation_blocks_approval_but_not_rejection(chair,monkeypatch,change):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin')
    if change=='trust':f.trust=False
    elif change=='owner_binding':
        with Session(f.engine) as db,db.begin():db.scalar(select(User).where(User.username=='faculty0@example.invalid')).is_active=False
    else:
        base=f.provider
        @contextmanager
        def changed():
            with base() as s:yield replace(s,**({'revision':'c'*64} if change=='stale' else {'term':'Unrecognized term'}))
        monkeypatch.setattr(schedules,'institutional_schedule_source',changed)
    blocked=decide(f,r);assert blocked.status_code in (409,503)
    assert decide(f,r,'reject').status_code==200


@pytest.mark.parametrize('kind',['faculty','room','section','gec','availability','component_rules'])
def test_fresh_resource_conflicts_block_approval(chair,monkeypatch,kind):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin');base=f.provider
    @contextmanager
    def changed():
        with base() as s:
            first=s.meetings[0]
            if kind in {'faculty','room','section'}:
                extra=replace(first,id='another-meeting',day='F',faculty_id=first.faculty_id if kind=='faculty' else str(IDS[1]),section_id=first.section_id if kind=='section' else 'section-b',room_id='lec' if kind=='room' else 'lab')
                s=replace(s,meetings=s.meetings+(extra,))
            elif kind=='gec':
                from services.ga_v2_constraints import Commitment
                fixed=Commitment(record_id='fictional',revision_id='fictional',source_row=1,source_sha256='e'*64,subject='Fictional External',day='F',start=450,end=630,sections=('section-a',),faculty=None,room=None)
                s=replace(s,commitments=(fixed,))
            elif kind=='availability':s=replace(s,windows=())
            else:
                def invalid(*args):raise ValueError('Fictional component rule')
                s=replace(s,check_proposal=invalid)
            yield s
    monkeypatch.setattr(schedules,'institutional_schedule_source',changed)
    review=f.client.get(BASE+'/'+r['id']).json()
    assert not review['can_approve'] and review['can_reject']
    assert review['current_review']['validation']['findings']
    assert decide(f,r).status_code==409


def test_explanation_extra_fields_csrf_and_rollback(chair):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin');body=decision_body(r)
    for bad in [{**body,'explanation':'short'},{**body,'department_id':DEPT},{**body,'actor_id':str(f.chair_id)},{**body,'bypass':True}]:
        assert decide(f,r,body=bad).status_code==422
    assert f.client.post(BASE+'/'+r['id']+'/reject',json=body,headers={'Origin':ORIGIN}).status_code==403
    f.after_check=lambda:setattr(f,'trust',False)
    assert decide(f,r).status_code==503
    with Session(f.engine) as db:assert db.scalar(select(ChairDecision)) is None


def test_final_decisions_immutable_in_database(chair):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin');assert decide(f,r).status_code==200
    for sql in ["UPDATE faculty_adjustment_decisions SET action='REJECT'",'DELETE FROM faculty_adjustment_decisions',"UPDATE faculty_adjustment_requests SET status='WITHDRAWN',version=version+1"]:
        with pytest.raises(IntegrityError),f.engine.begin() as db:db.exec_driver_sql(sql)


def test_authority_change_during_decision_rolls_back(chair):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin')
    f.after_check=lambda:setattr(f,'chair_state','REVOKED')
    assert decide(f,r).status_code==403
    with Session(f.engine) as db:assert db.scalar(select(ChairDecision)) is None


def test_directory_outage_is_sanitized_and_no_write(chair,monkeypatch):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin')
    def unavailable():raise RuntimeError('Fictional private provider detail, never returned')
    monkeypatch.setattr(authority,'institutional_chair_directory',unavailable)
    reply=decide(f,r);assert reply.status_code==503 and 'private provider detail' not in reply.text


def test_idempotency_key_cannot_be_reused_for_other_content(chair):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin');body=decision_body(r)
    assert decide(f,r,'reject',body).status_code==200
    assert decide(f,r,'reject',{**body,'explanation':'A different fictional explanation.'}).status_code==409


@pytest.mark.parametrize('competitor',['reject','withdraw'])
def test_concurrent_final_commands_only_one_wins(chair,monkeypatch,competitor):
    f=chair;r=submitted(f);f.chair_headers=session(f,'admin')
    # Independent trusted-directory contexts deliberately do not serialize the
    # writers. Correctness must come from SQL transactions/guards, not f.guard.
    with f.directory() as directory: pass
    @contextmanager
    def independent_directory(): yield directory
    monkeypatch.setattr(authority,'institutional_chair_directory',independent_directory)
    import threading
    start=threading.Barrier(2)
    with Session(f.engine) as db:
        actor=db.get(User,f.chair_id);db.expunge(actor)
        owner=db.scalar(select(User).where(User.username=='faculty0@example.invalid'));db.expunge(owner)
    from schemas.chair_reviews import DecisionCommand
    from schemas.adjustments import Transition
    from services import adjustment_service as d11
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError
    def work(action):
        try:
            start.wait(timeout=5)
            with Session(f.engine) as db:
                if action=='withdraw':
                    d11.transition(db,owner,SimpleNamespace(faculty_id=str(IDS[0])),UUID(r['id']),action,Transition(operation_id=uuid4(),expected_version=2))
                else:service.decide(db,actor,UUID(r['id']),action.upper(),DecisionCommand.model_validate(decision_body(r)))
            return 'ok'
        except (HTTPException,SQLAlchemyError):return 'blocked'
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(work,['approve',competitor]))
    assert sorted(results)==['blocked','ok']
    with Session(f.engine) as db:
        record=db.get(AdjustmentRequest,UUID(r['id']));final=db.scalar(select(ChairDecision))
        assert (record.status=='WITHDRAWN' and final is None) or (record.status=='SUBMITTED' and final is not None)
