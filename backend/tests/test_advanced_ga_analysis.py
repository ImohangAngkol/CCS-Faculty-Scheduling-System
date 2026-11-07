"""Fictional recorded DTOs only; no optimization or DB. All stores temporary."""
import copy
import json
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.engine import Engine
from main import app
from services import advanced_ga_analysis as advanced,ga_history_service as history,fitness_reporting_service as reporting,ga_run_provenance
from services.preference_authorization import current_principal,PreferencePrincipal
from tests.test_ga_result_compatibility import documents,store,RUN


@pytest.fixture(autouse=True)
def isolation(monkeypatch,tmp_path):
    monkeypatch.setattr(Engine,"connect",lambda *_a,**_k:pytest.fail("Advanced analysis attempted DB access"))
    monkeypatch.setattr(ga_run_provenance,"PROVENANCE_DIR",tmp_path/"provenance")
    before=dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear();app.dependency_overrides.update(before)


def fixture(generations=2,empty=False,context=True):
    index,base=documents(fitness=10)
    engine=history.checkpoints.engine_fingerprint()
    index['engine_fingerprint']=engine
    snapshots=[];index['generations']=[]
    for generation in range(generations):
        data=copy.deepcopy(base);data['engine_fingerprint']=engine;data['generation']=generation
        data['metrics'].update(generation=generation,best_ever_fitness=10-generation,generation_best_fitness=10-generation,average_fitness=20-generation,metrics_comparable=True,elapsed_ms=generation*1000)
        rows=[] if empty else [{'faculty':'1','subject':'FIC101','section':'FIC-A','type':'Lecture','day':'Monday' if generation==0 else 'Tuesday','start':'09:00','end':'10:00','room':'Fictional room','title':'Fictional computing'},
            {'faculty':'2','subject':'FIC102','section':'FIC-B','type':'Laboratory','day':'Tuesday','start':'10:00','end':'11:30','room':'Fictional lab'}]
        workloads=[] if empty else [{'faculty':f'Faculty {i}','teaching_units':units,'required_teaching_load':24,'difference':units-24,'preparations':1,'assigned_subjects':[f'FIC10{i}']} for i,units in [(1,3),(2,2)]]
        assignments=[] if empty else [{'subject':r['subject'],'section':r['section'],'faculty':r['faculty'],'teaching_units':3 if r['faculty']=='1' else 2,'external':False,'display_name':f"Faculty {r['faculty']}",
            'lecture':[[r['day'].lower(),540,600]] if r['type']=='Lecture' else [],'laboratory':[[r['day'].lower(),600,690]] if r['type']=='Laboratory' else []} for r in rows]
        for kind in ['generation_best','best_ever']:
            data[kind]['payload'].update(schedule=rows,best_fitness=10-generation)
            data[kind]['chromosome_id']=history.candidate_id(data[kind]['payload']);data[kind]['workload']=workloads;data[kind]['reporting_assignments']=assignments
        if context:
            data['reporting_context']={'version':1,'preference_scoring_version':2,'engine_fingerprint':engine,'scorer_sha256':reporting.scorer_hash(2),'input_fingerprint':'c'*64,
                'settings':{'max_preparations':2},'faculty':[] if empty else [{'faculty':f'Faculty {i}','code':str(i),'required_teaching_load':24,'admin_load':0,'research_load':0,'extension_load':0,'overload_warning_threshold':30} for i in [1,2]],
                'preferences':{'1':{'use_subject_preference':True,'use_day_preference':True,'use_time_preference':True,'preferred_subjects':['FIC101'],'preferred_days':['Monday'],'preferred_start_time':'09:00','preferred_end_time':'10:00','subject_importance':1,'day_importance':1,'time_importance':1}}}
        else:data.pop('reporting_context',None)
        entry=copy.deepcopy(base['metrics']);entry.update(data['metrics'])
        row={'generation':generation,'timestamp':data['timestamp'],'metrics':entry,'generation_best_id':data['generation_best']['chromosome_id'],'best_ever_id':data['best_ever']['chromosome_id'],'capture_elapsed_ms':0,'validation_elapsed_ms':0,'snapshot_bytes':1}
        index['generations'].append(row);snapshots.append(data)
    history.write_document(history.directory(RUN)/'index.json',index)
    for data in snapshots:history.write_document(history.directory(RUN)/f"generation-{data['generation']:06d}.json",data)
    return index,snapshots


def test_seven_graph_inputs_hours_and_missing_preferences():
    fixture();value=advanced.project(RUN,0)
    a,b=value['faculty']
    assert a['satisfaction']=={'subject':100,'day':100,'time':100}
    assert all(v is None for v in b['satisfaction'].values())
    assert a['preparations']==1 and a['teaching_units']==3 and a['average_deviation']==.5
    assert a['weekly_hours']==1 and b['hours']['tuesday']==1.5
    assert value['aggregates']['overall']['count']==1 and value['aggregates']['overall']['value']==100
    assert value['receipt']['status'] in ('UNVERIFIED','UNAVAILABLE') and value['compatibility']['classification']!='CURRENT'


def test_history_uses_recorded_means_zero_values_and_original_context():
    fixture();value=advanced.project(RUN,1)
    assert [p['best'] for p in value['progress']]==[10,9]
    assert [p['day'] for p in value['progress']]==[100,0]
    assert value['progress'][0]['elapsed_ms']==0 and value['progress'][0]['violations']==0
    assert value['faculty'][0]['preferred']['preferred_days']==['Monday']


def test_comparison_reports_signed_changes_without_causal_claims():
    fixture();result=advanced.compare(RUN,0,'generation_best',1,'generation_best')
    assert result['fitness']['change']==-1
    assert result['faculty'][0]['satisfaction_changes']['day']==-100
    assert result['faculty'][0]['changes']['preparations']==0
    assert result['academic_compatibility']=='UNKNOWN_COMPATIBILITY'


def test_zero_faculty_and_one_snapshot_are_honest_empty_cases():
    fixture(generations=1,empty=True);value=advanced.project(RUN)
    assert value['faculty']==[] and value['captured_faculty_average'] is None
    assert value['aggregates']['overall']['value'] is None and len(value['choices'])==1
    with pytest.raises(history.HistoryError,match='distinct'):advanced.compare(RUN,0,'generation_best',0,'best_ever')


def test_missing_reporting_context_does_not_reconstruct_today_preferences():
    fixture(context=False);value=advanced.project(RUN)
    assert value['faculty'][0]['preferred'] is None
    assert all(value['faculty'][0]['satisfaction'][k] is None for k in advanced.KEYS)
    assert all(p['best'] is None for p in value['progress']) and len(value['issues'])==2
    with pytest.raises(history.HistoryError,match='captured policy'):advanced.compare(RUN,0,'generation_best',1,'generation_best')


@pytest.mark.parametrize('field',['preferences','settings','academic_term'])
def test_context_drift_is_not_combined_or_compared(field):
    _,snapshots=fixture();data=snapshots[0]
    data['reporting_context'][field]={'fictional':'different'} if field!='academic_term' else 'OTHER-FICTIONAL-TERM'
    history.write_document(history.directory(RUN)/'generation-000000.json',data)
    value=advanced.project(RUN,1)
    assert value['progress'][0]['best'] is None and value['issues']
    with pytest.raises(history.HistoryError):advanced.compare(RUN,0,'generation_best',1,'generation_best')


def test_read_operations_preserve_every_fixture_byte_and_do_not_discover_workers(monkeypatch):
    fixture();paths=list(history.SNAPSHOTS_DIR.rglob('*.json'));before={p:p.read_bytes() for p in paths}
    monkeypatch.setattr(history,'write_document',lambda *_:pytest.fail('Analysis attempted write'))
    registry=__import__('routers.genetic_algorithm',fromlist=['_run_registry'])._run_registry
    monkeypatch.setattr(registry,'discover',lambda:pytest.fail('Read-only analysis attempted lifecycle discovery'))
    advanced.runs();advanced.project(RUN);advanced.compare(RUN,0,'generation_best',1,'generation_best')
    assert {p:p.read_bytes() for p in paths}==before


@pytest.mark.parametrize('comparable',[False,None])
def test_comparison_rejects_unestablished_fitness_comparability(comparable):
    _,snapshots=fixture();data=snapshots[0]
    data['metrics']['metrics_comparable']=comparable
    history.write_document(history.directory(RUN)/'generation-000000.json',data)
    with pytest.raises(history.HistoryError):advanced.compare(RUN,0,'generation_best',1,'generation_best')


def test_optional_u5d_is_not_a_checkpoint_dependency(monkeypatch):
    fixture();original=advanced.importlib.import_module
    def absent(name):
        if name=='services.ga_input_receipt':raise ModuleNotFoundError(name=name)
        return original(name)
    monkeypatch.setattr(advanced.importlib,'import_module',absent)
    assert advanced.project(RUN)['receipt']['record_state']=='NOT_INSTALLED'


@pytest.mark.parametrize('start,end',[('09:00','09:00'),('10:00','09:00'),('25:00','26:00'),('bad','11:00')])
def test_invalid_times_rejected(start,end):
    with pytest.raises(history.HistoryError):advanced.meeting_hours([{'start':start,'end':end,'day':'Monday'}])


def test_contact_hours_merge_duplicates_and_adjacent_boundaries():
    rows=[{'start':a,'end':b,'day':'M'} for a,b in [('09:00','09:30'),('09:30','10:00'),('09:00','09:30')]]
    assert advanced.meeting_hours(rows)['monday']==1


def test_unreadable_generation_is_a_gap_not_a_silent_omission():
    fixture();path=history.directory(RUN)/'generation-000000.json';path.write_bytes(b'{bad')
    value=advanced.project(RUN,1)
    assert len(value['progress'])==2 and value['progress'][0]['best'] is None and value['issues'][0]['generation']==0


def test_unapproved_u5d_flags_cannot_be_reported_as_verified(monkeypatch):
    fixture();original=advanced.importlib.import_module
    monkeypatch.setattr(advanced.importlib,'import_module',lambda name:SimpleNamespace(read=lambda _:dict(verification_status='VERIFIED',eligible_for_current=True)) if name=='services.ga_input_receipt' else original(name))
    value=advanced.project(RUN)
    assert value['receipt']['status']=='UNVERIFIED' and value['receipt']['record_state']=='INVALID'


def test_admin_api_denies_faculty_chair_and_unauthenticated_access():
    fixture()
    with TestClient(app) as client:
        def absent():raise HTTPException(401,'Fictional authentication required')
        app.dependency_overrides[current_principal]=absent
        assert client.get('/api/ga/advanced-analysis/runs').status_code==401
        for role in ['faculty','chair']:
            app.dependency_overrides[current_principal]=lambda role=role:PreferencePrincipal(role)
            assert client.get(f'/api/ga/advanced-analysis/runs/{RUN}').status_code==403
        app.dependency_overrides[current_principal]=lambda:PreferencePrincipal('admin')
        assert client.get(f'/api/ga/advanced-analysis/runs/{RUN}').status_code==200
        assert client.post(f'/api/ga/advanced-analysis/runs/{RUN}').status_code==405
