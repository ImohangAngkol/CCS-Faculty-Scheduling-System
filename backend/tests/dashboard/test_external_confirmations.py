"""D9 actual API/auth and file-backed SQLite ledger; no institutional data."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from dataclasses import replace
import importlib.util
import io
import json
from pathlib import Path
from uuid import uuid4,UUID

import pytest
from sqlalchemy import create_engine,select,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from alembic.migration import MigrationContext
from alembic.operations import Operations

from confirmation_models import ConfirmationBase,ExternalRecord,ExternalRevision,ConfirmationEvent,guard_sql,transition_sql
from services import confirmation_authority_service as authority,external_confirmation_service as ledger
from services import external_schedule_verification_service as evidence
from tests.dashboard.test_my_schedule import fixture,ORIGIN
from tests.dashboard.test_external_preview import session
from tests.dashboard.test_external_readiness import api_source,metadata,isolate
from tests.dashboard.evidence_support import install_fictional

ENDPOINT='/api/external-confirmations'


@pytest.fixture
def setup(fixture,monkeypatch):
    ConfirmationBase.metadata.create_all(fixture.engine)
    with fixture.engine.begin() as db:
        for sql in guard_sql('sqlite')+transition_sql('sqlite'):db.exec_driver_sql(sql)
    install_fictional(monkeypatch)
    return fixture


def permit(monkeypatch):
    def grant(context):
        now=datetime.now(timezone.utc)
        return authority.Authorization(context_digest=authority.digest(context),policy_reference='fictional-confirmation-policy.1',policy_digest='a'*64,
            actor_id=context.actor_id,action=context.action,state='AUTHORIZED',issued_at=(now-timedelta(seconds=1)).isoformat(),expires_at=(now+timedelta(seconds=120)).isoformat())
    monkeypatch.setattr(authority,'authorization_for',grant)


def proposal(fixture,headers,record_id=None,version=0,change=None):
    preview=api_source(fixture,headers);meta=metadata()
    if change:change(meta)
    review={'review_token':preview['review_token'],'metadata':meta,'mappings':[]}
    result=fixture.client.post('/api/external-schedules/readiness',json=review,headers=headers)
    assert result.status_code==200
    review['assessment_receipt']=result.json()['assessment_receipt']
    body={'record_id':record_id or str(uuid4()),'revision_id':str(uuid4()),'expected_version':version,'reason':'Fictional reviewed source revision','review':review}
    response=fixture.client.post(ENDPOINT+'/revisions',json=body,headers=headers)
    assert response.status_code==200
    return body


def command(body,version=None):return {'operation_id':str(uuid4()),'expected_version':body['expected_version'] if version is None else version,'reason':'Fictional institutional decision','review':body['review']}
def decision(fixture,headers,body,action='confirm',cmd=None):return fixture.client.post(ENDPOINT+'/revisions/'+body['revision_id']+'/'+action,json=cmd or command(body),headers=headers)
def history(fixture,headers,body):return fixture.client.get(ENDPOINT+'/records/'+body['record_id'],headers=headers).json()


def test_admin_and_verified_evidence_alone_never_confirm(setup,monkeypatch):
    f=setup;headers=session(f);body=proposal(f,headers)
    response=decision(f,headers,body,'request-confirmation');assert response.status_code==200 and response.json()['state']=='BLOCKED'
    assert decision(f,headers,body).status_code==403
    assert history(f,headers,body)['record']['status']=='PROPOSED'
    with Session(f.engine) as db:assert not db.scalars(select(ConfirmationEvent)).all()


def test_default_evidence_blocks_even_authorized_actor(setup,monkeypatch):
    f=setup;headers=session(f);monkeypatch.setattr(evidence,'verification_for',lambda *a,**kw:None);permit(monkeypatch)
    body=proposal(f,headers)
    assert decision(f,headers,body).status_code==403


def test_fictional_confirmation_revision_supersession_and_revocation(setup,monkeypatch):
    f=setup;headers=session(f);permit(monkeypatch);first=proposal(f,headers)
    assert decision(f,headers,first,'validate').json()['eligible'] is True
    assert decision(f,headers,first).json()['state']=='CONFIRMED'
    old=history(f,headers,first);assert old['record']['version']==1
    def changed(meta):meta['rows'][0]['proposed_meeting']={'days':['T'],'start':'10:00','end':'11:00','reason':'Fictional issuer amendment','evidence_reference':'Fictional revised evidence'}
    second=proposal(f,headers,first['record_id'],1,changed)
    assert history(f,headers,second)['record']['current_revision_id']==first['revision_id']
    assert decision(f,headers,second).status_code==200
    after=history(f,headers,second);assert after['record']['current_revision_id']==second['revision_id']
    assert after['events'][1]['previous_event_id']==after['events'][0]['id'] and len(after['revisions'])==2
    revoke={'operation_id':str(uuid4()),'expected_version':2,'reason':'Fictional issuer withdrawal'}
    assert f.client.post(ENDPOINT+'/records/'+first['record_id']+'/revoke',json=revoke,headers=headers).status_code==200
    after=history(f,headers,second);assert after['record']['status']=='REVOKED' and after['record']['current_revision_id'] is None
    assert len(after['events'])==3
    assert f.client.get(ENDPOINT+'/revisions/'+first['revision_id'],headers=headers).json()['content']['candidate']['rows'][0]['original']['days']==['M']


def test_restart_durability_and_immutable_sql_history(setup,monkeypatch):
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers);assert decision(f,headers,body).status_code==200
    # Independent engine and fresh SQLAlchemy process state read the same file.
    other=create_engine(f.engine.url)
    try:
        with Session(other) as db:
            r=db.get(ExternalRevision,UUID(body['revision_id']));assert ledger.digest(json.loads(r.content_json))==r.content_digest
            assert db.scalar(select(ExternalRecord.version))==1
        for table in ['gec_revisions','gec_events','gec_records']:
            for operation in ['DELETE','UPDATE']:
                sql=f'DELETE FROM {table}' if operation=='DELETE' else f'UPDATE {table} SET '+('reason=reason' if table!='gec_records' else 'version=version')
                with pytest.raises(IntegrityError):
                    with other.begin() as db:db.exec_driver_sql(sql)
    finally:other.dispose()
    import subprocess,sys
    code="""import sys,json,sqlite3,hashlib
p=json.load(sys.stdin)
with sqlite3.connect(p['path']) as db:
 row=db.execute('SELECT content_json,content_digest FROM gec_revisions WHERE id=?',(p['revision'].replace('-',''),)).fetchone()
 assert hashlib.sha256(json.dumps(json.loads(row[0]),sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()==row[1]
 assert db.execute('SELECT count(*) FROM gec_events').fetchone()[0]==1
print('DURABILITY_PASS')
"""
    result=subprocess.run([sys.executable,'-B','-c',code],input=json.dumps({'path':f.engine.url.database,'revision':body['revision_id']}),capture_output=True,text=True)
    assert result.returncode==0 and result.stdout.strip()=='DURABILITY_PASS'


@pytest.mark.parametrize('change',['version','term','evidence','metadata','revoked','issuer','policy','provider_failure'])
def test_freshness_scope_and_provider_failure_prevent_confirmation(setup,monkeypatch,change):
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers);cmd=command(body)
    if change=='version':cmd['expected_version']=999
    if change=='term':cmd['review']['metadata']['term']='Other fictional semester'
    if change=='metadata':cmd['review']['metadata']['rows'][0]['title']='Different fictional title'
    if change=='evidence':cmd['review']['metadata']['evidence_reference']='Substituted evidence'
    if change=='revoked':monkeypatch.setattr(evidence,'authority_policy_for',lambda _:None)
    if change=='issuer':monkeypatch.setattr(authority,'authorization_for',lambda _:None)
    if change=='policy':
        real=authority.authorization_for
        monkeypatch.setattr(authority,'authorization_for',lambda ctx:real(ctx).model_copy(update={'context_digest':'f'*64}))
    if change=='provider_failure':
        def failed(_):raise RuntimeError('Fictional provider diagnostic never logged')
        monkeypatch.setattr(authority,'authorization_for',failed)
    assert decision(f,headers,body,cmd=cmd).status_code in {403,409}
    assert history(f,headers,body)['events']==[]


def test_duplicate_and_stale_operations_never_append_twice(setup,monkeypatch):
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers);cmd=command(body)
    assert decision(f,headers,body,cmd=cmd).status_code==200
    assert decision(f,headers,body,cmd=cmd).status_code==409
    assert len(history(f,headers,body)['events'])==1


def test_later_evidence_revocation_preserves_history_and_requires_independent_withdrawal(setup,monkeypatch):
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers)
    assert decision(f,headers,body).status_code==200
    monkeypatch.setattr(evidence,'authority_policy_for',lambda _:None)
    after=history(f,headers,body)
    assert after['record']['status']=='CONFIRMED' and after['record']['current_evidence_status']=='NOT_RECHECKED'
    newer=proposal(f,headers,body['record_id'],1)
    assert decision(f,headers,newer).status_code in {403,409}
    original=authority.authorization_for
    monkeypatch.setattr(authority,'authorization_for',lambda _:None)
    revoke={'operation_id':str(uuid4()),'expected_version':1,'reason':'Fictional withdrawn evidence'}
    path=ENDPOINT+'/records/'+body['record_id']+'/revoke'
    assert f.client.post(path,json=revoke,headers=headers).status_code==403
    monkeypatch.setattr(authority,'authorization_for',original)
    assert f.client.post(path,json=revoke,headers=headers).status_code==200
    after=history(f,headers,body)
    assert len(after['events'])==2 and after['record']['current_revision_id'] is None


def test_corrupt_stored_evidence_fails_with_safe_integrity_error():
    from fastapi import HTTPException
    for value,expected in [('not-json',None),('{}','a'*64)]:
        with pytest.raises(HTTPException) as caught:ledger.checked_evidence(value,expected)
        assert caught.value.status_code==503 and caught.value.detail['code']=='LEDGER_INTEGRITY'


def test_rollback_of_failed_event_leaves_head_and_history_unchanged(setup,monkeypatch):
    from sqlalchemy import event
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers)
    def fail(*args):raise IntegrityError('injected rollback',None,None)
    event.listen(ConfirmationEvent,'after_insert',fail)
    try:assert decision(f,headers,body).status_code==409
    finally:event.remove(ConfirmationEvent,'after_insert',fail)
    data=history(f,headers,body);assert data['events']==[] and data['record']['version']==0


def test_authentication_role_origin_csrf_and_forged_flags(setup):
    f=setup
    assert f.client.get(ENDPOINT).status_code==401
    assert f.client.get(ENDPOINT,headers=session(f,'faculty')).status_code==403
    headers=session(f);body=proposal(f,headers)
    assert f.client.post(ENDPOINT+'/revisions',json=body,headers={'Origin':ORIGIN}).status_code==403
    assert f.client.post(ENDPOINT+'/revisions',json=body,headers={**headers,'Origin':'https://evil.invalid'}).status_code==403
    assert decision(f,headers,body,cmd={**command(body),'authorized':True}).status_code==422
    assert f.client.post(ENDPOINT+'/revisions',json={**body,'confirmed':True},headers=headers).status_code==422


def test_cross_session_cannot_persist_or_confirm_another_preview(setup):
    f=setup;headers=session(f);body=proposal(f,headers);other=session(f)
    assert decision(f,other,body).status_code==409


def test_concurrent_confirmation_transactions_have_one_winner(setup,monkeypatch):
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers)
    # Fresh transactions/connections, serialized DB transition guard, no shared Session.
    revision=UUID(body['revision_id']);record=UUID(body['record_id'])
    with Session(f.engine) as db:
        actor=db.scalar(select(ExternalRevision.created_by));snapshot=db.get(ExternalRevision,revision)
        content_hash=snapshot.content_digest
    def attempt(_):
        try:
            with Session(f.engine) as db,db.begin():
                db.add(ConfirmationEvent(id=uuid4(),record_id=record,revision_id=revision,previous_event_id=None,sequence=1,action='CONFIRM',
                    actor_id=actor,policy_reference='fictional-policy',policy_digest='a'*64,evidence_digest=ledger.digest({}),content_digest=content_hash,evidence_json='{}',reason='Fictional concurrency test'))
                db.flush()
            return True
        except IntegrityError:return False
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(attempt,range(2)))==[False,True]
    assert len(history(f,headers,body)['events'])==1


def test_concurrent_authenticated_api_confirmations_have_one_winner(setup,monkeypatch):
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:decision(f,headers,body).status_code,range(2)))
    assert sorted(results)==[200,409]


@pytest.mark.parametrize('change',[{'actor_id':str(uuid4())},{'action':'REVOKE'},{'state':'SUSPENDED'},{'context_digest':'b'*64},{'expires_at':'2020-01-01T00:00:00Z'}])
def test_confirmation_grant_requires_fresh_actor_action_and_context(setup,monkeypatch,change):
    f=setup;headers=session(f);permit(monkeypatch);body=proposal(f,headers);original=authority.authorization_for
    monkeypatch.setattr(authority,'authorization_for',lambda ctx:original(ctx).model_copy(update=change))
    assert decision(f,headers,body).status_code==403


def test_migration_is_additive_frozen_and_offline_only():
    path=Path(__file__).resolve().parents[2]/'migrations/versions/d9_0001_confirmation_ledger.py'
    spec=importlib.util.spec_from_file_location('d9_migration',path);migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    assert migration.down_revision=='4c_0001'
    for fn in [migration.upgrade,migration.downgrade]:
        output=io.StringIO();ctx=MigrationContext.configure(dialect_name='postgresql',opts={'as_sql':True,'output_buffer':output})
        with Operations.context(ctx):fn()
        sql=output.getvalue()
        assert 'gec_records' in sql and 'faculty_preferences' not in sql and 'CASCADE' not in sql
        if fn==migration.upgrade:
            assert sql.count('CREATE TABLE')==3 and 'FOR UPDATE' in sql and 'immutable GEC history' in sql
            assert 'ix_gec_revisions_record_id' in sql and 'ix_gec_events_record_id' in sql
            assert all(statement in migration.DDL for statement in guard_sql('postgresql')+transition_sql('postgresql'))
        else:assert 'downgrade refuses retained history' in sql
