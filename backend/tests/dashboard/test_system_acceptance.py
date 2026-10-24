"""D14 cross-release acceptance with real services and entirely fictional data."""
from contextlib import contextmanager
from dataclasses import replace
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import time
from uuid import UUID,uuid4

import pandas as pd
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from confirmation_models import ConfirmationBase,guard_sql,transition_sql
from application_models import PublishedVersion,ScheduleApplication
from services import ga_v2_service as ga,ga_v2_constraints as constraints,ga_v2_store as store
from services import chair_review_service,adjustment_schedule_service as schedules,published_schedule_source as published
from services import application_authority_service,external_schedule_verification_service as verification
from services import auth_service as auth,ga_service
from tests.dashboard.test_schedule_applications import application,chair,setup,fixture,publisher,counts,IDS,ORIGIN
from tests.dashboard.test_chair_reviews import session,decide
from tests.dashboard.test_adjustments import create,command
from tests.dashboard.test_external_confirmations import isolate,permit,proposal,decision
from tests.dashboard.evidence_support import install_fictional
from tests.dashboard.test_chair_trust import REAL_TRUST
from tests.d10.test_v2_engine import catalog_for
from tests.d10.test_v2_api import wait


def measure(name,values):
    """Only allow explicitly public numeric observations, never raw responses."""
    target=os.environ.get('D14_METRICS_DIR')
    if not target:return
    root=Path(__file__).resolve().parents[3]/'docs/testing/dashboard-d14'
    directory=Path(target).resolve();assert directory.is_relative_to(root.resolve())
    directory.mkdir(exist_ok=True)
    assert all(type(v) in (int,float,bool,str) for v in values.values())
    with (directory/(name+'.json')).open('x',encoding='utf-8') as out:json.dump(values,out,indent=2)


@pytest.fixture
def system(application,monkeypatch,tmp_path):
    f=application
    # Actual model calendars extend through 22:00. D11's older hand-authored
    # fixture used 19:00, which cannot describe all genuine generated rows.
    f.windows=tuple((*window[:-1],'22:00') for window in f.windows)
    ConfirmationBase.metadata.create_all(f.engine)
    with f.engine.begin() as db:
        for sql in guard_sql('sqlite')+transition_sql('sqlite'):db.exec_driver_sql(sql)
    install_fictional(monkeypatch);permit(monkeypatch)
    # Explicit fixture eligibility makes normal bound faculty own actual output.
    f.members[0].eligible_subjects={'SYN101'};f.members[1].eligible_subjects={'SYN202'};f.members[2].eligible_subjects=set()
    values=copy.deepcopy((f.courses,f.members,ga_service.lst_rooms))
    catalog=catalog_for(values).model_copy(update={'sections':(('synthetic-section-a','SYN-A'),('synthetic-section-b','SYN-B')),
        'faculty':tuple((str(id),str(i)) for i,id in enumerate(IDS)),'rooms':(('SYN LEC','SYN LEC'),('SYN LAB','SYN LAB'))})
    preferences=pd.DataFrame({'Faculty_Code':[0,1,2],'Faculty_Prio':[1,1,1],'Preferred Subjects':[None]*3,'Preferred Day(s)':[None]*3})
    deployment=ga.Deployment(catalog,constraints.LedgerAuthority(lambda:Session(f.engine),catalog,values),values,preferences)
    f.deployment=deployment;f.publish_file=tmp_path/'d14-explicit-publication.json';published_results={}
    monkeypatch.setattr(ga,'institutional_deployment',lambda year,term:deployment)
    monkeypatch.setattr(store,'STORE',tmp_path/'v2');monkeypatch.setattr(ga,'JOBS',{})
    monkeypatch.setattr(chair_review_service,'trusted_snapshot',REAL_TRUST)
    from services import metadata_service
    monkeypatch.setattr(metadata_service.scheduling,'list_subjects',f.courses)
    f.headers=session(f,'admin');f.confirmation=proposal(f,f.headers)
    assert decision(f,f.headers,f.confirmation).status_code==200
    # All preference/settings aliases point at NEW owned synthetic files.
    from routers import preferences as preferences_router
    from genetic_algorithm.operators import FitnessFunction
    preference_file=tmp_path/'faculty-preferences.json';settings_file=tmp_path/'settings.json'
    preference_file.write_text('[]',encoding='utf-8');settings_file.write_text(json.dumps(preferences_router.GASetting().to_dict()),encoding='utf-8')
    for module,key,path in ((preferences_router,'PREFERENCE_FILE',preference_file),(preferences_router,'GA_SETTINGS_FILE',settings_file),
        (ga_service,'FACULTY_PREFERENCES_FILE',preference_file),(ga_service,'GA_SETTINGS_FILE',settings_file),
        (FitnessFunction,'PREFERENCE_FILE',preference_file),(FitnessFunction,'GA_SETTINGS_FILE',settings_file)):
        monkeypatch.setattr(module,key,path)
    f.preference_file=preference_file
    # This is an explicit TEST-ONLY publication authorization, not an app API.
    # Browser/backend tests supply the exact completed run through an owned file.
    @contextmanager
    def publication():
        if not f.publish_file.is_file():raise ValueError('No fictional published source has been designated')
        id=str(UUID(json.loads(f.publish_file.read_text(encoding='utf-8'))['run_id']))
        original=store.path_for(id).read_bytes()
        if id not in published_results:published_results[id]=(original,copy.deepcopy(ga.inspect(id)['result']))
        recorded,result=published_results[id];assert original==recorded
        if result['status']!='COMPLETED':raise ValueError('Only completed validated proposals can be designated')
        # Do not nest a second SQLite BEGIN IMMEDIATE around D11/D13's own
        # transaction. Those services recheck the actual ledger in that same
        # transaction; this source guard pins only the immutable generated file.
        with Session(f.engine) as ledger_db:snapshot=constraints._read_snapshot(ledger_db,catalog,values)
        with f.guard:
            assert result['constraint_digest']==snapshot.digest
            room_ids={'SYN LEC':'lec','SYN LAB':'lab'}
            meetings=tuple(schedules.Meeting(schedules.digest(row),str(IDS[int(row['faculty'])]),
                {'SYN101':'subject-a','SYN202':'subject-b'}[row['subject']],{'SYN-A':'section-a','SYN-B':'section-b'}[row['section']],
                row['subject'],row.get('title',''),row['section'],row['type'],row['day'],row['start'],row['end'],room_ids[row['room']]) for row in result['schedule'])
            fixed=tuple(c.model_copy(update={'sections':tuple({'synthetic-section-a':'section-a','synthetic-section-b':'section-b'}[s] for s in c.sections),
                'room':room_ids[dict(catalog.rooms)[c.room]] if c.room else None}) for c in snapshot.commitments)
            def unchanged():
                assert store.path_for(id).read_bytes()==original,'Original generated result changed'
                assert str(UUID(json.loads(f.publish_file.read_text(encoding='utf-8'))['run_id']))==id
            source=schedules.ReviewSchedule('fictional-published-v2-'+id,schedules.digest(result),catalog.academic_year,catalog.term,
                snapshot.digest,meetings,f.rooms,f.windows,fixed,unchanged,lambda *a:None)
            yield published.PublicationContext(source,'fictional-explicit-publisher:'+id,'fictional-full-policy.1',lambda:Session(f.engine),
                values,tuple((str(v),str(i)) for i,v in enumerate(IDS)),(('subject-a','SYN101'),('subject-b','SYN202')),
                (('section-a','SYN-A'),('section-b','SYN-B')),'required','fictional-enrollment-capacity.1',(('section-a',20),('section-b',15)),(('lec',40),('lab',30)))
    monkeypatch.setattr(published,'institutional_publication_source',publication)
    f.publication_provider=publication
    yield f
    end=time.monotonic()+30
    while any(j.active for j in ga.JOBS.values()) and time.monotonic()<end:time.sleep(.01)
    assert not any(j.active for j in ga.JOBS.values())


def generate(f):
    f.headers=session(f,'admin');c=f.client.get('/api/ga/v2/constraints',params={'academic_year':f.deployment.catalog.academic_year,'term':f.deployment.catalog.term})
    assert c.status_code==200
    body={'academic_year':f.deployment.catalog.academic_year,'term':f.deployment.catalog.term,'constraint_digest':c.json()['constraint_digest'],
        'parameters':{'population_size':2,'generations':2,'fresh_chromosomes':0,'mutation_attempts':2,'crossover_attempts':2,'max_restarts':5,'candidate_attempts':5}}
    start=time.perf_counter();reply=f.client.post('/api/ga/v2/runs',headers=f.headers,json=body);assert reply.status_code==202
    run=reply.json()['run_id'];final=wait(f,run);assert final['status']=='COMPLETED',final.get('error')
    result=final['result'];assert result['source']=='GA-generated proposal' and not result['approved']
    f.publish_file.write_text(json.dumps({'run_id':run}),encoding='utf-8')
    return run,result,round((time.perf_counter()-start)*1000,3)


def own_proposal(f):
    f.headers=session(f,0);assignments=f.client.get('/api/adjustment-requests/assignments');assert assignments.status_code==200
    data=assignments.json();row=next(r for r in data['assignments'] if r['component']=='Laboratory')
    diagnostics=set()
    for day in ('F','S','TH','T','W','M'):
        for start,end in (('07:30','10:30'),('10:30','13:30'),('13:00','16:00'),('16:00','19:00')):
            body={'schedule_id':data['schedule_id'],'revision':data['revision'],'assignment_id':row['id'],'academic_year':data['academic_year'],'term':data['term'],
                'proposal':{'day':day,'start':start,'end':end,'room_id':row['room_id']},'justification':'Fictional complete system acceptance adjustment.'}
            reply=f.client.post('/api/adjustment-requests/preview',headers=f.headers,json=body)
            if reply.status_code==200 and reply.json()['validation']['outcome']=='VALID_PROPOSAL':return body
            if reply.status_code==200:diagnostics.update(v['code'] for v in reply.json()['validation']['findings'])
            else:diagnostics.add('HTTP_'+str(reply.status_code))
    pytest.fail('No valid adjustment in fictional generated timetable; discrepancy codes only: '+','.join(sorted(diagnostics)))


def approved_generated(f):
    run,result,elapsed=generate(f);body=own_proposal(f)
    r=create(f,{**body,'operation_id':str(uuid4())});submitted=command(f,r,'submit');assert submitted.status_code==200;r=submitted.json()
    f.chair_headers=session(f,'admin');response=decide(f,r);assert response.status_code==200,response.status_code
    return run,result,elapsed,r


@pytest.mark.parametrize('sample',[1,2,3])
def test_actual_confirmed_generation_request_approval_application_and_history(system,sample):
    f=system;rng=random.getstate();original=f.path.read_bytes();run,result,elapsed,r=approved_generated(f)
    generated=store.path_for(run).read_bytes();publisher(f)
    begin=time.perf_counter();preview=f.client.get('/api/schedule-applications/'+r['id']+'/preview');assert preview.status_code==200
    p=preview.json();assert p['can_apply'] and p['validation']['outcome']=='VALID';assert counts(f)==[0,0,0]
    review_ms=round((time.perf_counter()-begin)*1000,3)
    begin=time.perf_counter();response=f.client.post('/api/schedule-applications/'+r['id']+'/apply',headers=f.apply_headers,json={**p['command'],'operation_id':str(uuid4())})
    assert response.status_code==200,response.status_code;apply_ms=round((time.perf_counter()-begin)*1000,3)
    versions=f.client.get('/api/schedule-applications/versions').json()['versions'];assert len(versions)==2
    assert sum(a!=b for a,b in zip(versions[0]['meetings'],versions[1]['meetings']))==1
    with Session(f.engine) as db:assert len(db.scalars(select(ScheduleApplication)).all())==1
    f.headers=session(f,0);assert f.client.get('/api/adjustment-requests/'+r['id']).json()['status']=='APPLIED'
    timetable=f.client.get('/api/schedules/me').json();assert timetable['source']['post_ga_changes'] and timetable['source']['sequence']==2
    assert store.path_for(run).read_bytes()==generated and f.path.read_bytes()==original and random.getstate()==rng
    with f.deployment.authority.pinned() as snapshot:
        assert result['constraint_digest']==snapshot.digest and result['revisions'][0]['revision_id']==f.confirmation['revision_id']
        from services.chromosome_service import payload_to_chromosome
        from services.ga_v2_engine import admit,reduced_templates
        reduced=reduced_templates(snapshot,f.deployment.templates)
        chromosome=payload_to_chromosome(result,*copy.deepcopy(reduced))
        admit(chromosome,snapshot,reduced)
    measure('complete-workflow-'+str(sample),{'GA_ms':elapsed,'complete_preview_ms':review_ms,'atomic_application_ms':apply_ms,
        'best_fitness':result['best_fitness'],'generated_meetings':len(result['schedule']),'confirmed_heads':len(result['revisions']),
        'published_versions':2,'hard_constraint_validation':'PASS','fitness_recalculated_by_application':False,'sample_size':1})


def test_current_real_confirmation_revocation_blocks_generated_application(system):
    f=system;run,result,elapsed,r=approved_generated(f);generated=store.path_for(run).read_bytes()
    headers=session(f,'admin');reply=f.client.post('/api/external-confirmations/records/'+f.confirmation['record_id']+'/revoke',headers=headers,
        json={'operation_id':str(uuid4()),'expected_version':1,'reason':'Fictional D14 revocation after actual GA and approval'})
    assert reply.status_code==200;publisher(f)
    assert f.client.get('/api/schedule-applications/'+r['id']+'/preview').status_code in (409,503)
    assert counts(f)==[0,0,0] and store.path_for(run).read_bytes()==generated


def test_owned_preferences_round_trip_identity_and_invalid_input(system):
    f=system;headers=session(f,0)
    body={'gap_preference':'Compact','gap_importance':5,'use_gap_preference':True}
    response=f.client.put('/preferences/0',headers=headers,json=body);assert response.status_code==200,response.status_code
    assert f.client.get('/preferences/0').json()['gap_preference']=='Compact'
    assert f.client.get('/preferences/0').json()['gap_importance']==5
    assert f.client.get('/preferences/1').status_code==403
    assert f.client.put('/preferences/0',headers=headers,json={'gap_importance':999}).status_code==422
    assert json.loads(f.preference_file.read_text(encoding='utf-8'))[0]['gap_importance']==5


def test_storage_unavailable_is_sanitized_and_recovers_without_partial_publication(system):
    from sqlalchemy import event
    from sqlalchemy.exc import OperationalError
    f=system;run,result,elapsed,r=approved_generated(f);publisher(f)
    preview=f.client.get('/api/schedule-applications/'+r['id']+'/preview').json()
    body={**preview['command'],'operation_id':str(uuid4())}
    def unavailable(*args):raise OperationalError('fictional isolated SQLite storage unavailable',None,None)
    event.listen(PublishedVersion,'before_insert',unavailable)
    try:
        reply=f.client.post('/api/schedule-applications/'+r['id']+'/apply',headers=f.apply_headers,json=body)
        assert reply.status_code==503 and reply.json()['detail']['code']=='APPLICATION_STORAGE_UNAVAILABLE'
        assert 'sqlite' not in reply.text.lower() and 'content_json' not in reply.text
    finally:event.remove(PublishedVersion,'before_insert',unavailable)
    assert counts(f)==[0,0,0]
    assert f.client.post('/api/schedule-applications/'+r['id']+'/apply',headers=f.apply_headers,json=body).status_code==200
