"""HEAD + U5G/U5H/U5I source qualification; fictional data, no actual staging.

Uses the committed U5C-R1 fictional bootstrap and unchanged release-byte layout;
does not spoof or disable engine fingerprints. No U5D/U5E/U5F app dependency.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import tarfile
import tempfile
import time
import sys

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='d6db077793da52b7559351a5d0f8e6d54608cb77'
OVERLAY=['backend/services/ga_owned_store.py','backend/services/ga_run_authority.py','backend/services/ga_trusted_runs.py','backend/routers/ga_trusted_runs.py','backend/tests/test_trusted_runs.py','backend/tests/trusted_run_support.py','backend/services/ga_input_bundle.py','backend/tests/test_ga_input_bundle.py','backend/tests/test_ga_input_bundle_checkpoint_qualification.py','backend/services/ga_bundle_runtime.py','backend/services/ga_bundle_checkpoint.py','backend/services/ga_bundle_optimizer.py','backend/tests/test_ga_bundle_optimizer.py','backend/tests/test_ga_bundle_parity.py']
def git(*args,input=None):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)

def main():
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only').strip()
    index=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()
    owned=Path(tempfile.mkdtemp(prefix='u5c-r1-snapshot-u5h-')).resolve();assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/'OWNED-SNAPSHOT.json').write_text(json.dumps({'head':HEAD,'purpose':'U5I admission and isolated SQLite durability, unchanged legacy source qualification'}),encoding='utf-8')
    snapshot=owned/'repository';snapshot.mkdir();archive=owned/'head.tar'
    # Exclude academic/runtime stores before creating the source archive too,
    # rather than only omitting them during extraction. No private source data
    # or saved scheduling artifacts are needed for a fictional qualification.
    roots=git('ls-tree','-z','--name-only',HEAD).decode().split('\0')
    children=git('ls-tree','-z','--name-only',HEAD+':backend').decode().split('\0')
    excluded={'data','saved_chromosomes','run_checkpoints','generation_snapshots','run_input_receipts_v1','run_provenance_v1','constrained_runs_v2'}
    selection=[p for p in roots if p and p!='backend']+['backend/'+p for p in children if p and p not in excluded]
    with archive.open('xb') as stream:subprocess.run(['git','-c','safe.directory='+str(ROOT),'-c','core.autocrlf=false','archive',HEAD,'--',*selection],cwd=ROOT,stdout=stream,check=True)
    with tarfile.open(archive) as source:
        for member in source.getmembers():assert (snapshot/member.name).resolve().is_relative_to(snapshot) and not member.issym() and not member.islnk()
        source.extractall(snapshot,members=[m for m in source.getmembers() if not m.name.startswith('backend/data/')],filter='data')
    helper=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5c-r1/fictional_bootstrap.py'));helper['prepare'](snapshot)
    helper['release_bytes'](snapshot,json.loads((ROOT/'docs/testing/dashboard-u5c-r1/release-byte-layout.json').read_text(encoding='utf-8')))
    compatibility=len(sys.argv)>1 and sys.argv[1] in {'receipts','receipt-isolation','analysis','readiness','backend-regressions'}
    overlay=list(OVERLAY)
    if compatibility:
        overlay+=['backend/services/ga_input_receipt.py','backend/routers/ga_evaluation.py','backend/routers/genetic_algorithm.py','backend/tests/conftest.py','backend/services/advanced_ga_analysis.py','backend/routers/advanced_ga_analysis.py','backend/services/continuous_readiness.py','backend/routers/continuous_optimization.py','backend/tests/test_ga_input_receipt.py','backend/tests/test_advanced_ga_analysis.py','backend/tests/test_continuous_readiness.py']
    hashes={};blobs={}
    for name in overlay:
        raw=(ROOT/name).read_bytes();path=snapshot/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest();blobs[name]=git('hash-object','--stdin',input=raw).decode().strip()
    main=snapshot/'backend/main.py'
    text=main.read_text().replace('from routers import ga_evaluation\n','from routers import ga_evaluation\nfrom routers import ga_trusted_runs\n').replace('app.include_router(ga_evaluation.router)\n','app.include_router(ga_evaluation.router)\napp.include_router(ga_trusted_runs.router)\n')
    if compatibility:main.write_bytes((ROOT/'backend/main.py').read_bytes())
    else:main.write_text(text,encoding='utf-8',newline='\n')
    hashes['backend/main.py']=hashlib.sha256(main.read_bytes()).hexdigest()
    for name in ([] if compatibility else ['backend/services/ga_input_receipt.py','backend/services/advanced_ga_analysis.py','backend/services/continuous_readiness.py']):assert not (snapshot/name).exists()
    subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'.venv'),str(ROOT/'.venv')],capture_output=True,check=True)
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-snapshot');target.mkdir(exist_ok=False)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env['PYTHONDONTWRITEBYTECODE']='1';env['U5H_PROTOCOL_EVIDENCE']=str(target)
    results=[]
    selections=[('admission','test_trusted_runs'),('consumption','test_ga_bundle_optimizer'),('parity','test_ga_bundle_parity'),('legacy','test_ga_input_bundle_checkpoint_qualification'),('bundle-tests','test_ga_input_bundle'),('receipts','test_ga_input_receipt'),('receipt-isolation','test_ga_input_receipt'),('analysis','test_advanced_ga_analysis'),('readiness','test_continuous_readiness'),('backend-regressions','test_ga_source_qualification')]
    if len(sys.argv)>1:
        assert sys.argv[1] in dict(selections),'Unknown qualification selection'
        selections=[(k,n) for k,n in selections if k==sys.argv[1]]
    for key,name in selections:
        command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/'+name+'.py','--durations=10','--basetemp',str(owned/('pytest-'+key))]
        if key=='receipt-isolation':command[7]='tests/test_ga_input_receipt.py::test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim'
        if key=='backend-regressions':command[8:8]=['tests/test_ga_academic_context.py','tests/test_ga_result_compatibility.py']
        tick=time.perf_counter();start=datetime.now().astimezone().isoformat()
        try:
            result=subprocess.run(command,cwd=snapshot/'backend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
            code=result.returncode;out=result.stdout;err=result.stderr
        except subprocess.TimeoutExpired as error:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nBound exceeded; owned process cleanup requires review.'
        row=dict(selection=key,command=command,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=out,stderr=err,scope='HEAD plus U5H-only source; fictional import tables/D10 models. New versioned internal entry consumes the bundle; unchanged legacy entry remains separate. Technical consumption is not institutional authorization. No database access.')
        (target/(key+'-command.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');results.append(dict(selection=key,exit_code=code));print(json.dumps(results[-1]),flush=True)
        if code:break
    assert git('rev-parse','HEAD').decode().strip()==HEAD and hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==index
    proof=dict(head=HEAD,source_sha256=hashes,proposed_blob_oids=blobs,results=results,qualified_selections=[k for k,n in selections],complete=len(results)==len(selections) and all(r['exit_code']==0 for r in results),fictional_source_only=True,no_u5d_u5e_u5f_app_dependency=not compatibility,no_actual_staging=True,consumption_verified_in_internal_path=True,snapshot=str(snapshot))
    (target/'snapshot-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return 0 if proof['complete'] else 1
if __name__=='__main__':raise SystemExit(main())
