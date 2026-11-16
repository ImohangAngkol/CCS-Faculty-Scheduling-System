"""Fictional owned-snapshot acceptance; no institutional connections or stores."""
import csv
import io
import json
import os
from pathlib import Path
from uuid import uuid4
import pytest
from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned fictional snapshot required',allow_module_level=True)
from services.ga_research_experiments import Experiments,improvement,number,CAPS
from services.ga_research_operator import Operator
from services.ga_run_authority import RunError,digest
from services.preference_authorization import PreferencePrincipal
from routers.research_experiments import create_app
from tests.test_research_bridge import fixture,http_fixture,client_for
from tests.test_research_operator import finished,diagnostic
from tests.test_research_observations import files
from tests.trusted_run_support import PRINCIPAL,OTHER


@pytest.mark.parametrize('initial,final,delta,reason',[(500,475,25,None),(0,0,0,'ZERO_BASELINE'),(-4,-8,4,'NEGATIVE_BASELINE'),(None,0,None,'COMPARABLE_VALUES_NOT_RECORDED'),(False,0,None,'COMPARABLE_VALUES_NOT_RECORDED'),(float('nan'),0,None,'COMPARABLE_VALUES_NOT_RECORDED'),(1e308,-1e308,None,'NUMERIC_RANGE')])
def test_metrics_distinguish_observed_derived_unavailable(initial,final,delta,reason):
    a,p=improvement(initial,final);assert a['value']==delta
    if reason:assert p['value'] is None and p['reason']==reason
    else:assert p['value']==5


def test_existing_execution_and_observation_routes_are_reused():
    from main import app
    assert '/research/experiments' not in app.openapi()['paths']
    routes=create_app().openapi()['paths']
    assert all(set(v)=={'get'} for k,v in routes.items() if k.startswith('/api/research/experiments'))
    assert len([k for k in routes if k.startswith('/api/research/observations')])==4
    assert sorted(k for k,v in routes.items() if 'post' in v and k.startswith('/api/research/'))==['/api/research/operator/runs/{run}/stop','/api/research/operator/start']


def test_synthetic_formatter_only_roundtrip_bounds_and_tamper(tmp_path):
    """Independent encoding unit test; mocked view is NOT consumption evidence."""
    from services.ga_research_experiments import VERSION,observed,unavailable
    from services.ga_run_authority import canonical
    import runpy
    run='00000000-0000-4000-8000-000000000991'
    experiment='00000000-0000-4000-8000-000000000992'
    context=dict(dataset='FICTIONAL-UNIT-ONLY',academic_year='FICTIONAL-YEAR',term='FICTIONAL-TERM',department_id=run,context_fingerprint='a'*64)
    provenance=dict(input_bundle_fingerprint='b'*64,engine_fingerprint='c'*64,optimizer_version='ga-bundle-consumer-v1',fitness_version='original-penalty-preference-v2',configuration_fingerprint='d'*64)
    record=dict(schema=VERSION,run_id=run,experiment_id=experiment,fictional_context=context,provenance=provenance,
        checkpoint_observations=[dict(generation=0,best_so_far_fitness=0.0)],original_generation_history=[dict(generation=0,best_ever_fitness=0.0)],
        termination=dict(state='COMPLETED',reason='UNIT_TEST_ONLY'),evidence_notice='Synthetic formatter unit only, not worker evidence.')
    for key in ['actual_generation_count','initial_fitness','final_best_fitness','fitness_improvement','elapsed_admission_to_terminal']:
        record[key]=observed(0.0,'UNIT_TEST_ONLY')
    for key in ['percentage_improvement','soft_penalty_breakdown','preference_satisfaction','hard_conflict_counts']:
        record[key]=unavailable('UNIT_TEST_ONLY')
    s=object.__new__(Experiments);s.clock=lambda:1.0
    s.view=lambda _p,_r:dict(exportable=True,record=record,record_sha256=digest(record),verification='VERIFIED_RECORDED_FICTIONAL_RESULT',freshness={})
    paths={}
    for kind in CAPS:
        raw,identity=s.export(None,run,kind);assert identity==experiment
        paths[kind]=tmp_path/('synthetic-unit.'+kind);paths[kind].write_bytes(raw)
        old=CAPS[kind];CAPS[kind]=len(raw)-1
        try:
            with pytest.raises(RunError,match='TOO_LARGE'):s.export(None,run,kind)
        finally:CAPS[kind]=old
    verify=runpy.run_path(str(Path.cwd().parent/'docs/testing/dashboard-u5pf/verify_export.py'))['verify']
    assert verify(paths['json'],paths['csv'],paths['txt'])['status']=='CONTENT_CONSISTENCY_VERIFIED'
    doc=json.loads(paths['json'].read_bytes());doc['record']['final_best_fitness']['value']=1
    paths['json'].write_bytes(canonical(doc))
    with pytest.raises(AssertionError,match='HASH_REJECTED'):verify(paths['json'])


def test_real_native_completed_experiment_and_all_readonly_exports(fixture):
    b,_=fixture(generations=1);o=Operator(b,initialize=True);s=Experiments(o)
    run=o.control(PRINCIPAL,str(uuid4()),'start')['run_id'];finished(b,run)
    diagnostic(b,run,'native-completed-worker-diagnostic')
    before=files(b);view=s.view(PRINCIPAL,run);assert view['exportable'];record=view['record']
    assert record['termination']['state']=='COMPLETED' and record['actual_generation_count']['value']==1
    assert record['initial_fitness']['value']==record['final_best_fitness']['value']==0
    assert record['fitness_improvement']['value']==0 and record['percentage_improvement']['reason']=='ZERO_BASELINE'
    assert [x['generation'] for x in record['original_generation_history']]==[0,1]
    assert record['checkpoint_observations'][0]['generation']==0
    assert record['preference_satisfaction']['value'] is None and record['hard_conflict_counts']['value'] is None
    assert not record['rng_provenance']['exact_replay_from_export']
    assert Experiments(Operator(b)).view(PRINCIPAL,run)['experiment_id']==view['experiment_id']
    bodies={k:s.export(PRINCIPAL,run,k)[0] for k in CAPS}
    doc=json.loads(bodies['json']);assert digest(doc['record'])==view['record_sha256']==doc['record_sha256']
    rows=list(csv.DictReader(io.StringIO(bodies['csv'].decode())));assert rows and all(x['run_id']==run and x['record_sha256']==view['record_sha256'] for x in rows)
    assert {x['series'] for x in rows}=={'checkpoint','generation'}
    text='\n'.join(v.decode() for v in bodies.values())
    for forbidden in ['initial_rng','random_state','password','csrf_token','signature','Faculty_Code','eligible_subjects','checkpoint_payload']:
        assert forbidden not in text
    assert files(b)==before,'Read/export mutated owned storage'
    for kind in CAPS:
        with pytest.raises(RunError):s.export(PreferencePrincipal('admin',user_id=OTHER),run,kind)
    for kind in CAPS:
        old=CAPS[kind];CAPS[kind]=1
        try:
            with pytest.raises(RunError,match='TOO_LARGE'):s.export(PRINCIPAL,run,kind)
        finally:CAPS[kind]=old
    folder=Path(os.environ['U5PF_EVIDENCE'])
    for kind,body in bodies.items():
        with (folder/('native-completed-export.'+kind)).open('xb') as f:f.write(body)
    import runpy
    verify=runpy.run_path(str(Path.cwd().parent/'docs/testing/dashboard-u5pf/verify_export.py'))['verify']
    assert verify(folder/'native-completed-export.json',folder/'native-completed-export.csv',folder/'native-completed-export.txt')['status']=='CONTENT_CONSISTENCY_VERIFIED'
    bad=folder/'deliberately-corrupt-export.csv'
    changed=list(csv.DictReader(io.StringIO(bodies['csv'].decode())))
    changed[0]['best_so_far_fitness']='99'
    with bad.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(changed[0]));writer.writeheader();writer.writerows(changed)
    with pytest.raises(AssertionError):verify(folder/'native-completed-export.json',bad)
    with b.worker.storage.transaction() as db:db.execute("UPDATE research_proofs SET signature='corrupt' WHERE run=?",(run,))
    for kind in CAPS:
        with pytest.raises(RunError):s.export(PRINCIPAL,run,kind)


def test_pending_missing_metrics_interruption_and_stale_metadata(fixture):
    b,_=fixture();o=Operator(b,initialize=True);s=Experiments(o);run=b.admit(PRINCIPAL,str(uuid4()))['run_id']
    before=files(b);d=s.view(PRINCIPAL,run);assert not d['exportable'] and d['generation']['value'] is None and d['record'] is None
    assert Experiments(o,clock=lambda:b.worker.clock()+100).view(PRINCIPAL,run)['freshness']['telemetry_state']=='STALE'
    for kind in CAPS:
        with pytest.raises(RunError,match='NOT_VERIFIED'):s.export(PRINCIPAL,run,kind)
    assert files(b)==before
    with b.worker.storage.transaction() as db:
        db.execute("UPDATE runs SET executor='fictional-expired-owner',lease=1 WHERE id=?",(run,));db.execute("UPDATE workers SET state='RUNNING' WHERE run=?",(run,))
    d=s.view(PRINCIPAL,run);assert d['runtime']['recorded_state']=='INTERRUPTED' and d['freshness']['state']=='UNKNOWN' and not d['exportable']


def test_actual_session_export_authorization_and_no_new_privileged_routes(http_fixture):
    f=http_fixture;o=Operator(f.bridge,initialize=True);app=create_app(o);app.dependency_overrides.update(f.app().dependency_overrides)
    run=f.bridge.admit(PRINCIPAL,str(uuid4()))['run_id']
    with client_for(app) as c:
        assert c.get('/api/research/experiments/context').status_code==401
        headers=f.login(c)
        assert c.get('/api/research/experiments/context').json()['contexts'][0]['context']['dataset']=='FICTIONAL-DATASET'
        assert c.get('/api/research/experiments/runs/'+run).status_code==200
        for kind in CAPS:
            r=c.get('/api/research/experiments/runs/'+run+'/exports/'+kind);assert r.status_code==409 and r.headers['cache-control']=='no-store'
        assert c.get('/api/research/experiments/runs/'+run+'/exports/pdf').status_code==422
        assert c.post('/api/research/operator/start',headers=headers,json=dict(request_id=str(uuid4()),context='client-forged')).status_code==422
    with client_for(app) as c:
        f.login(c,'unscoped')
        for path in ['/context','/runs/'+run,'/runs/'+run+'/exports/json']:
            assert c.get('/api/research/experiments'+path).status_code==403
