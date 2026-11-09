"""U5O actual registry/anonymous HTTP and tiny checkpoint telemetry; no repairs."""
import ast
import inspect
import json
import os
from pathlib import Path
import re
import time
import textwrap
from uuid import uuid4
import pytest
from fastapi.routing import APIRoute,iter_route_contexts
from services.ga_worker_contract import fictional_source
from tests.test_deployment_identity_qualification import identity

def record(name,value):
    target=Path(os.environ['U5H_PROTOCOL_EVIDENCE'])/name
    with target.open('x',encoding='utf-8') as f:f.write(json.dumps(value,indent=2)+'\n')

def test_actual_registered_routes_and_unauthenticated_boundaries(identity,monkeypatch):
    fictional_source()
    from main import app
    from sqlalchemy.engine import Engine
    original=Engine.connect
    def connect(engine,*a,**k):
        if engine is not identity.engine:pytest.fail('Non-owned database connection forbidden')
        return original(engine,*a,**k)
    monkeypatch.setattr(Engine,'connect',connect)
    from services import ga_service,chromosome_service
    def forbidden(*a,**k):pytest.fail('Unauthenticated request attempted optimizer/persistence')
    monkeypatch.setattr(ga_service,'run_genetic_algorithm',forbidden);monkeypatch.setattr(chromosome_service,'save_best_if_better',forbidden)
    rows=[];unexpected=[];root=Path(__file__).resolve().parents[2]
    def dependencies(dep,seen=None):
        seen=set() if seen is None else seen
        for d in dep.dependencies:
            call=d.call;name=getattr(call,'__module__','')+'.'+getattr(call,'__qualname__',str(type(call)))
            if name not in seen:seen.add(name);dependencies(d,seen)
        return seen
    contexts=list(iter_route_contexts(app.routes))
    for route in contexts:
        if not isinstance(route.original_route,APIRoute):continue
        fn=route.endpoint;file=Path(inspect.getsourcefile(fn)).resolve().relative_to(root).as_posix();line=inspect.getsourcelines(fn)[1]
        tree=ast.parse(textwrap.dedent(inspect.getsource(fn)))
        calls=sorted({ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n,ast.Call)})
        pattern=route.path_format
        concrete=pattern
        for field in route.dependant.path_params:
            annotation=getattr(field,'type_',getattr(getattr(field,'field_info',None),'annotation',None))
            value='0' if annotation is int or field.name in {'faculty_code','generation','generation_number'} else '00000000-0000-4000-8000-000000009991'
            concrete=concrete.replace('{'+field.name+'}',value)
        for method in sorted(route.methods):
            if method in {'HEAD','OPTIONS'}:continue
            response=identity.client.request(method,concrete,json={} if method in {'POST','PUT','PATCH'} else None)
            public=pattern in {'/','/api/health','/api/auth/login'}
            verdict='PUBLIC_LIVENESS' if pattern in {'/','/api/health'} else 'PUBLIC_LOGIN_VALIDATION' if pattern=='/api/auth/login' else 'DENIED_AUTHENTICATION' if response.status_code==401 else 'DENIED_ORIGIN_OR_AUTHORIZATION' if response.status_code==403 else 'VALIDATION_ONLY_NOT_AUTH_PROOF' if response.status_code==422 else 'UNEXPECTED_STATUS_REVIEW'
            if not public and response.status_code not in {401,403,422}:unexpected.append(dict(method=method,path=pattern,status=response.status_code))
            rows.append(dict(method=method,path=pattern,endpoint=fn.__name__,file=file,line=line,
                dependencies=sorted(dependencies(route.dependant)),direct_calls=calls,status_without_credentials=response.status_code,
                anonymous_probe=verdict,verification='ACTUAL_FASTAPI_TESTCLIENT_AND_OWNED_SQLITE; NOT_NETWORK_OR_INSTITUTIONAL_ACCEPTANCE'))
    record('backend-route-inventory.json',dict(scope='Actual registered APIRoutes, source/dependency inspection and anonymous HTTP handlers; builtin docs separately listed',endpoint_method_pairs=len(rows),rows=rows,unexpected=unexpected,
        builtin_routes=[dict(path=r.path,methods=sorted(r.methods or [])) for r in contexts if not isinstance(r.original_route,APIRoute)]))
    schema={(p,m.upper()) for p,methods in app.openapi()['paths'].items() for m in methods if m.lower() in {'get','post','put','patch','delete'}}
    assert schema<={(r['path'],r['method']) for r in rows},'OpenAPI routes missing from effective registry inventory'
    assert not unexpected,'Unexpected anonymous route status; see sanitized registry evidence'

def test_tiny_run_checkpoint_sizes_and_write_duration(monkeypatch):
    fictional_source()
    from sqlalchemy.engine import Engine
    monkeypatch.setattr(Engine,'connect',lambda *_a,**_k:pytest.fail('Institutional database forbidden'))
    from services.ga_owned_store import Store
    from services.ga_trusted_runs import Coordinator
    from tests.trusted_run_support import FictionalAuthority,FictionalSource,PRINCIPAL,DEPT,CATALOG
    from services import chromosome_service,ga_checkpoint_service
    def forbidden(*a,**k):pytest.fail('Legacy persistence forbidden')
    monkeypatch.setattr(chromosome_service,'save_best_if_better',forbidden);monkeypatch.setattr(ga_checkpoint_service,'save_checkpoint',forbidden)
    store=Store.create(max_runs=2);source=FictionalSource(1);coordinator=Coordinator(store,FictionalAuthority(),source)
    run=coordinator.admit(PRINCIPAL,DEPT,str(uuid4()),CATALOG)['run_id'];original=store.checkpoint;measurements=[]
    def save(*args,**kwargs):
        tick=time.perf_counter();out=original(*args,**kwargs)
        measurements.append(dict(checkpoint_bytes=len(args[3]),sequence=args[5],write_seconds=time.perf_counter()-tick));return out
    monkeypatch.setattr(store,'checkpoint',save)
    from benchmarks.memory_study import ProcessMemory,Sampler
    process=ProcessMemory();memory_before=process.read();sampler=Sampler(process)
    coordinator.command(PRINCIPAL,run,'pause')
    with sampler:
        tick=time.perf_counter();paused=coordinator.execute(PRINCIPAL,run);pause_elapsed=time.perf_counter()-tick
        assert paused['state']=='PAUSED' and measurements
        checkpoint=coordinator.checkpoint(PRINCIPAL,run)
        tick=time.perf_counter();done=coordinator.execute(PRINCIPAL,run,resume=True);resume_elapsed=time.perf_counter()-tick
    elapsed=pause_elapsed+resume_elapsed
    assert done['state']=='COMPLETED';result=coordinator.result(PRINCIPAL,run)
    assert result['best_fitness']==0 and not result['saved_best_updated']
    record('tiny-run-measurements.json',dict(scope='One fictional 2-faculty/2-offering H/I run, population 2, one generation. Instrumented durable checkpoint calls include validation/transaction; not a performance benchmark or seven-day extrapolation.',wall_seconds=elapsed,checkpoint_writes=measurements,
        stored_database_bytes=(store.root/'records.sqlite3').stat().st_size,paused_checkpoint_bytes=len(checkpoint),initialization_pause_seconds=pause_elapsed,continuation_seconds=resume_elapsed,final_fitness=0,convergence_claim=False,
        initial_rng_saved=True,seed_exported=False,production_storage_changed=False,memory_before=memory_before,memory_after=process.read(),memory_sampling=sampler.result()))

def test_characterize_legacy_saved_best_comparison_without_provenance_gate(monkeypatch):
    fictional_source()
    from services import chromosome_service as service
    # Actual decision function, mocked serialized payloads, no disk IO. These
    # numbers illustrate incompatible contexts, not a measured schedule score.
    existing={'subject_keys':['FIC101::FIC-A'],'best_fitness':100.0,'input_fingerprint':'a'*64,'configuration_fingerprint':'b'*64}
    current={'subject_keys':existing['subject_keys'],'input_fingerprint':'c'*64,'configuration_fingerprint':'d'*64}
    writes=[]
    monkeypatch.setattr(service,'load_saved_best_payload',lambda:existing)
    monkeypatch.setattr(service,'chromosome_to_payload',lambda chromosome,score:{**current,'best_fitness':score})
    monkeypatch.setattr(service,'write_payload',lambda payload,path:writes.append(payload))
    saved,_=service.save_best_if_better(object(),90.0)
    assert saved and len(writes)==1
    skipped,_=service.save_best_if_better(object(),110.0)
    assert not skipped and len(writes)==1
    record('legacy-saved-best-characterization.json',dict(scope='Actual legacy save decision with fictional mocked payloads and in-memory writer; no real Saved Best access or mutation',same_subject_keys=True,input_and_configuration_differ=True,lower_numeric_foreign_score_saved=True,higher_numeric_foreign_score_rejected=True,provenance_gate_present=False,classification='LEGACY_PERSISTENCE_CONTRACT_GAP; NOT_A_NEW_U5O_FIX'))
