"""Original V1 parity and process-restoration proofs in an owned fictional tree."""
import copy
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import pytest
from services.ga_input_bundle import capture, digest, canonical
from services.ga_bundle_optimizer import Session


@pytest.fixture
def oracle(monkeypatch,tmp_path):
    from services import ga_service as engine,ga_checkpoint_service as checkpoints,chromosome_service
    from genetic_algorithm.operators import FitnessFunction
    from genetic_algorithm.utils import Functions
    from tests.d10.support import templates,preferences
    from sqlalchemy.engine import Engine
    backend=Path(engine.__file__).resolve().parents[1];owner=backend.parent.parent
    if not owner.name.startswith('u5c-r1-snapshot-u5h-') or owner.parent!=Path(tempfile.gettempdir()).resolve() or not (owner/'OWNED-SNAPSHOT.json').exists():
        pytest.skip('Oracle requires the owned U5H fictional source snapshot')
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Database access forbidden'))
    pref=backend/'data/faculty_preferences.json';settings=backend/'data/ga_settings.json'
    pref.write_text('[]\n');settings.write_text('{}\n')
    for obj,name,path in [(engine,'FACULTY_PREFERENCES_FILE',pref),(engine,'GA_SETTINGS_FILE',settings),
        (FitnessFunction,'PREFERENCE_FILE',pref),(FitnessFunction,'GA_SETTINGS_FILE',settings),
        (chromosome_service,'BEST_CHROMOSOME_PATH',tmp_path/'fictional-best.json')]:monkeypatch.setattr(obj,name,path)
    def bind(models):
        for name,value in zip(['list_subjects','list_faculty','lst_rooms'],models):
            monkeypatch.setattr(engine,name,value);monkeypatch.setattr(Functions,name,value)
        monkeypatch.setattr(engine,'df_faculty_pref',preferences())
    models=templates(compact=True);bind(models)
    original=random.getstate()
    yield engine,checkpoints,models,bind,tmp_path
    random.setstate(original)


def captured(engine,cp,models,configuration,run_id='00000000-0000-4000-8000-000000000811'):
    from genetic_algorithm.utils.FrozenInputs import capture_inputs
    return capture(run_id=run_id,templates=models,fallback_templates=models,legacy_preferences=engine.df_faculty_pref,
        scoring_context=capture_inputs(),configuration=configuration,
        source_identities=dict(dataset=cp.input_fingerprint(),engine=cp.engine_fingerprint(),loader='c'*64,transformation='d'*64))


@pytest.mark.parametrize('generations,fresh',[(0,0),(1,0),(1,1)])
def test_unmodified_fixed_engine_schedule_fitness_history_and_rng_parity(oracle,generations,fresh):
    engine,cp,models,bind,tmp=oracle
    parameters=dict(population_size=2,generations=generations,fresh_chromosomes=fresh,baseline_mode='fresh',mutation_attempts=1,max_restarts=5)
    bundle=captured(engine,cp,models,parameters)
    initial=random.Random(710).getstate();fingerprint=cp.engine_fingerprint()
    random.setstate(initial);expected=engine.run_genetic_algorithm(**parameters);expected_rng=random.getstate()
    # Poison cached models and the legacy RNG after capture. The new entry
    # must consume its own detached model and RNG, not these mutable aliases.
    bind(([],[],[]));random.seed(999);outside=random.getstate()
    session=Session(bundle,run_id=bundle.run_id,random_state=initial);actual=session.run()
    for key in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis','baseline_source','starting_baseline_fitness']:
        assert actual[key]==expected[key]
    assert session.runtime.random.getstate()==expected_rng and random.getstate()==outside
    assert cp.engine_fingerprint()==fingerprint and actual['saved_best_updated'] is False
    assert session.receipt()['verification_status']=='VERIFIED'
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        target=Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/f'parity-{generations}-{fresh}.json'
        with target.open('x',encoding='utf-8') as f:f.write(json.dumps({'scope':'Fictional original-engine versus versioned bundle consumer; technical verification only',
            'parameters':parameters,'legacy_engine_fingerprint':fingerprint,'receipt':session.receipt(),
            'schedule_fitness_history_and_rng_equal':True,'saved_best_promotion':False,'authority':'NOT_ESTABLISHED'},indent=2)+'\n')
        if generations==0:
            closure=Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/'dependency-closure.json'
            with closure.open('x',encoding='utf-8') as f:f.write(json.dumps({'scope':'Fictional qualified function dependency environment; no model values',
                'function_code_and_defaults':session.runtime.codes,'model_method_identities':session.runtime.model_codes,
                'global_names_by_module':{namespace['__name__']:sorted(k for k in namespace if not k.startswith('__')) for namespace in session.runtime.namespaces.values()},
                'optimizer_fingerprint':session.optimizer_fingerprint,'legacy_sources_modified':False},indent=2)+'\n')


def test_checkpoint_restores_in_a_fresh_python_process(oracle):
    engine,cp,models,bind,tmp=oracle
    params=dict(population_size=2,generations=0,fresh_chromosomes=0,baseline_mode='fresh',mutation_attempts=1,max_restarts=5)
    bundle=captured(engine,cp,models,params);session=Session(bundle,run_id=bundle.run_id,random_state=random.Random(710).getstate())
    session.run(lambda *_:session.control.request_pause())
    # Raw fictional graphs/checkpoints stay only in the owned temporary tree.
    (tmp/'bundle.bin').write_bytes(bundle._raw);(tmp/'checkpoint.bin').write_bytes(session.checkpoint)
    code='''import json,sys
from pathlib import Path
from services.ga_input_bundle import InputBundle
from services.ga_bundle_optimizer import Session
p=Path(sys.argv[1]);run=sys.argv[2]
b=InputBundle.from_bytes((p/'bundle.bin').read_bytes(),run,sys.argv[3])
s=Session.restore(b,(p/'checkpoint.bin').read_bytes(),run_id=run,expected_fingerprint=sys.argv[4],expected_sequence=1,expected_parent=None)
r=s.run()
assert r['generations_completed']==0 and s.receipt()['verification_status']=='VERIFIED'
print(json.dumps({'scope':'fresh Python / fictional bundle checkpoint', 'result':'PASS','receipt':s.receipt()}))
'''
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run([__import__('sys').executable,'-B','-c',code,str(tmp),bundle.run_id,bundle.fingerprint,session.checkpoint_fingerprint],
        cwd=Path(engine.__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout[-2000:]+result.stderr[-2000:]
    # Import chatter in this owned source tree is fictional; archive only the
    # final structured child result, never arbitrary module stdout.
    public=json.loads(result.stdout.strip().splitlines()[-1]);assert public['result']=='PASS'
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        with (Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/'fresh-process.json').open('x',encoding='utf-8') as f:f.write(json.dumps(public,indent=2)+'\n')


def test_nonzero_preferences_and_weights_match_original(oracle):
    engine,cp,models,bind,tmp=oracle
    backend=Path(engine.__file__).resolve().parents[1]
    rows=[{'faculty_code':code,'faculty_priority':1,'use_subject_preference':True,
           'subject_importance':5,'preferred_subjects':['SYN101'],'use_day_preference':False,
           'use_time_preference':False,'use_gap_preference':False} for code in [990001,990002]]
    (backend/'data/faculty_preferences.json').write_text(json.dumps(rows))
    (backend/'data/ga_settings.json').write_text(json.dumps({'subject_penalty':91,'day_penalty':37,'time_penalty':41}))
    parameters=dict(population_size=2,generations=1,fresh_chromosomes=0,baseline_mode='fresh',mutation_attempts=1,max_restarts=5)
    bundle=captured(engine,cp,models,parameters)
    initial=random.Random(710).getstate();random.setstate(initial)
    expected=engine.run_genetic_algorithm(**parameters);rng=random.getstate()
    session=Session(bundle,run_id=bundle.run_id,random_state=initial);actual=session.run()
    assert expected['best_fitness']>0
    for key in ['schedule','best_fitness','history','fitness_breakdown','faculty_analysis']:assert actual[key]==expected[key]
    assert session.runtime.random.getstate()==rng
    if os.environ.get('U5H_PROTOCOL_EVIDENCE'):
        with (Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/'nonzero-parity.json').open('x',encoding='utf-8') as f:
            f.write(json.dumps({'scope':'Fictional preference/weight variation; unchanged original mathematics',
                'best_fitness':actual['best_fitness'],'fitness_breakdown':actual['fitness_breakdown'],
                'schedule_fitness_history_rng_equal':True,'receipt':session.receipt()},indent=2)+'\n')
