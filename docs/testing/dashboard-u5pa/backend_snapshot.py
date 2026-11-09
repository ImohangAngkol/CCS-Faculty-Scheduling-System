"""U5O isolated source qualification; fictional data, no actual staging.

Uses the committed U5C-R1 fictional bootstrap and unchanged release-byte layout;
does not spoof or disable engine fingerprints. Reuses committed prerequisites;
--working-ui copies exact entry-inventory UI bytes into the disposable snapshot.
No production authority is installed in the user's application.
"""
from datetime import datetime
import hashlib
import json
import re
import os
from pathlib import Path
import runpy
import subprocess
import tarfile
import tempfile
import time
import sys

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='ec21a67efed82f085d5e2134ef6002cf5ac69eed'
OVERLAY=['backend/services/saved_best_policy.py','backend/services/chromosome_service.py','backend/tests/test_saved_best_context.py','frontend/src/pages/admin/ScheduleApplications.tsx','frontend/src/api/scheduleApplications.ts']

def git(*args,input=None):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)

def sanitize(value):
    return runpy.run_path(str(ROOT/'backend/services/evidence_sanitization.py'))['sanitize'](value)

def main():
    if len(sys.argv) not in (2,3) or (len(sys.argv)==3 and sys.argv[2]!='--working-ui'):raise SystemExit('Specify one qualification/regression selection; see the U5O report.')
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only').strip()
    index=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()
    owned=Path(tempfile.mkdtemp(prefix='u5c-r1-snapshot-u5h-')).resolve();assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/'OWNED-SNAPSHOT.json').write_text(json.dumps({'head':HEAD,'purpose':'U5O isolated authority/capture/storage qualification; production blocked'}),encoding='utf-8')
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
    ui_hashes={}
    if '--working-ui' in sys.argv:
        entry=json.loads((BASE/'entry-review.json').read_text())
        for name in entry['tracked_modifications']+entry['untracked_files']:
            src=ROOT/name
            if name.startswith('frontend/') and src.suffix in {'.ts','.tsx','.css','.mjs','.json'}:
                dst=snapshot/name;dst.parent.mkdir(parents=True,exist_ok=True);raw=src.read_bytes();dst.write_bytes(raw)
                ui_hashes[name]=hashlib.sha256(raw).hexdigest()
    staged_main=(snapshot/'backend/main.py').read_bytes()
    legacy=git('show','d6db077793da52b7559351a5d0f8e6d54608cb77:backend/main.py')
    recipe=json.loads((ROOT/'docs/testing/dashboard-u5c-r1/release-byte-layout.json').read_text())
    assert __import__('hashlib').sha256(legacy).hexdigest()==next(x['canonical_sha256'] for x in recipe['files'] if x['path']=='backend/main.py')
    (snapshot/'backend/main.py').write_bytes(legacy)
    helper=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5c-r1/fictional_bootstrap.py'));helper['prepare'](snapshot);helper['release_bytes'](snapshot,recipe)
    (snapshot/'backend/main.py').write_bytes(staged_main)
    compatibility=False
    import ast
    original_receipt=git('show','b4c8da7942bddfec63564a1e1f8de31e1db3e491:backend/services/ga_input_receipt.py').decode('utf-8')
    assert hashlib.sha256(original_receipt.encode('utf-8')).hexdigest()=='2b418773be9ba119ff39fc87157e28d364462d139eb46b4c12f4a99f18fb5c5e'
    node=next(n for n in ast.parse(original_receipt).body if isinstance(n,ast.FunctionDef) and n.name=='directory')
    frozen='from uuid import UUID\nfrom services.ga_input_receipt import error\nRECEIPTS_DIR=None\n'+ast.get_source_segment(original_receipt,node)+'\n'
    (snapshot/'backend/tests/u5m_frozen_guard.py').write_text(frozen,encoding='utf-8')
    overlay=[] if sys.argv[1]=='u5o-baseline' else list(OVERLAY)
    hashes={};blobs={}
    for name in overlay:
        raw=(ROOT/name).read_bytes();path=snapshot/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest();blobs[name]=git('hash-object','--stdin',input=raw).decode().strip()
    subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'.venv'),str(ROOT/'.venv')],capture_output=True,check=True)
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-snapshot');target.mkdir(exist_ok=False)
    if sys.argv[1] in {'d16-live','repair-live'}:
        cache=runpy.run_path(str(BASE/'isolate_vite_cache.py'))['prepare'](snapshot,owned)
        (target/'cache-isolation.json').write_text(json.dumps(cache,indent=2)+'\n',encoding='utf-8')
        subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'frontend/node_modules'),str(ROOT/'frontend/node_modules')],capture_output=True,check=True)
        test=snapshot/'frontend/tests/functionalReadiness.live.mjs'
        text=test.read_text(encoding='utf-8');old='resolve(root,"../docs/screenshots/dashboard-d16")'
        assert text.count(old)==1
        text=text.replace(old,'resolve('+json.dumps(str(BASE))+')')
        marker="    await check('D16-L05'"
        assert text.count(marker)==1
        diagnostic="""    await check('U5PA-A01','history-only failure preserves valid review and independent retry',async()=>{
      await writeFile(config.faultFile,'history',{flag:'wx'});faultOwned=true;
      await click('Refresh published history');await text('Published history unavailable');
      await click('Revalidate application');await text('Fresh complete-schedule validation: VALID');
      assert.equal(await evaluate(`document.querySelector('[aria-label="Application review"]')!==null`),true);
      assert.equal(await evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Apply adjustment')`),true);
      assert.equal((await api('/api/schedule-applications/'+first+'/preview')).data.can_apply,true);
      await screenshot('U5PA-A01-history-error-preview-preserved');
      await rm(config.faultFile);faultOwned=false;
      await click('Retry loading');await text('Published version history');
      await text('Fresh complete-schedule validation: VALID');
      assert.equal(await evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Apply adjustment')`),true);
      await screenshot('U5PA-A01-independent-history-retry');
    });
"""
        text=text.replace(marker,diagnostic+marker)
        stop="    await check('D16-I06'";assert text.count(stop)==1
        survey=(ROOT/'docs/testing/dashboard-u5o/live-route-survey.mjs').read_text(encoding='utf-8')
        survey=survey.replace("await eventually(()=>evaluate('Boolean(document.querySelector(\"h1,main form,form\"))'),'Route did not render a heading/form: '+path);", "try{await eventually(()=>evaluate('Boolean(document.querySelector(\"h1,main form,form\"))'),'Route did not render a heading/form: '+path);}catch(error){await screenshot('U5PA-route-render-failure');await writeFile(join(resolve(process.env.D16_SCREENSHOT_DIR),'render-failure.json'),JSON.stringify(sanitizeTree({path,actual:await evaluate('location.pathname'),text:await evaluate('document.body.innerText.slice(0,2500)'),responses:network.slice(begin)}),null,2),{flag:'wx'});throw error;}")
        if sys.argv[1]=='d16-live':text=text.replace(stop,survey+'\n'+stop)
        marker_text='  const text=value=>eventually(()=>evaluate(`document.querySelector(\'main\')?.textContent.includes(${JSON.stringify(value)})`),"Missing live UI text: "+value);'
        diagnostic_text=r"""  let u5paDiagnosticCaptured=false;const u5paHttp=[];
  const text=async value=>{try{return await eventually(()=>evaluate(`document.querySelector('main')?.textContent.includes(${JSON.stringify(value)})`),"Missing live UI text: "+value);}catch(error){if(process.env.D16_SCREENSHOT_DIR&&!u5paDiagnosticCaptured){u5paDiagnosticCaptured=true;const observation=await evaluate("({path:location.pathname,visible_text:document.body.innerText.slice(0,3000)})");await writeFile(join(resolve(process.env.D16_SCREENSHOT_DIR),'failure-diagnostic.json'),JSON.stringify(sanitizeTree({expected:value,observation,http:u5paHttp.slice(-40)}),null,2),{flag:'wx'});await screenshot('U5PA-live-failure');}throw error;}};"""
        assert marker_text in text
        text=text.replace(marker_text,diagnostic_text)
        network_probe=r"""    await command('Network.enable');socket.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.method==='Network.responseReceived'){const u=new URL(m.params.response.url);if(u.origin===config.backend)u5paHttp.push({path:u.pathname,status:m.params.response.status});}});
"""
        text=text.replace("    await check('D16-L01'",network_probe+"    await check('D16-L01'")
        test.write_text(text,encoding='utf-8',newline='\n')
        (target/'harness-transform.json').write_text(json.dumps(dict(scope='Owned test harness only; application UI and original harness unchanged',original_source_sha256=hashlib.sha256((ROOT/'frontend/tests/functionalReadiness.live.mjs').read_bytes()).hexdigest(),snapshot_harness_sha256=hashlib.sha256(test.read_bytes()).hexdigest(),changes=['U5O owned capture destination with retained path containment check','One additional real HTTP browser repaired-history isolation and retry scenario','One twenty-page render/network metadata survey; no blanket end-to-end claims'],expected_original_journey_scenarios=21,additional_repair_scenarios=1,additional_render_surveys=1 if sys.argv[1]=='d16-live' else 0),indent=2)+'\n',encoding='utf-8')
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env['PYTHONDONTWRITEBYTECODE']='1';env['U5H_PROTOCOL_EVIDENCE']=str(target)
    if sys.argv[1] in {'d16-live','repair-live'}:env['D16_SCREENSHOT_DIR']=str(target/'captures')
    if sys.argv[1]=='legacy':env['D10_V1_BASELINE_RECORD']=str(target)
    results=[]
    selections=[('u5o-baseline','test_full_system_audit'),('saved-best','test_saved_best_context'),('dashboard-all','dashboard/test_my_schedule'),('resource-regressions','test_preassigned_assignments'),('resource-fictional','test_preassigned_assignments'),('v2-engine','d10/test_v2_engine'),('v2-api','d10/test_v2_api'),('u5o-audit','test_full_system_audit'),('system-focused','dashboard/test_functional_readiness'),('system-integration','dashboard/test_system_acceptance'),('d16-live','dashboard/test_readiness_live'),('repair-live','dashboard/test_readiness_live'),('preference-scope','test_preference_scope_qualification'),('recovery','test_recovery_qualification'),('parent','test_parent_containment_qualification'),('identity','test_deployment_identity_qualification'),('chair','dashboard/test_chair_reviews'),('chair-trust','dashboard/test_chair_trust'),('application-trust','dashboard/test_application_trust'),('deterministic','test_receipt_concurrency_qualification'),('race','test_receipt_concurrency_qualification'),('supervised','test_supervised_worker'),('supervised-smoke','test_supervised_worker'),('backup','test_supervised_worker'),('receipt-isolation','test_ga_input_receipt'),('native','test_windows_supervision'),('worker','test_bounded_worker'),('smoke','test_bounded_worker'),('consumption','test_ga_bundle_optimizer'),('parity','test_ga_bundle_parity'),('legacy','test_ga_input_bundle_checkpoint_qualification'),('bundle-tests','test_ga_input_bundle'),('admission','test_trusted_runs'),('qualification','test_qualified_execution'),('receipts','test_ga_input_receipt'),('analysis','test_advanced_ga_analysis'),('readiness','test_continuous_readiness'),('backend-regressions','test_ga_source_qualification')]
    if len(sys.argv)>1:
        assert sys.argv[1] in dict(selections),'Unknown qualification selection'
        selections=[(k,n) for k,n in selections if k==sys.argv[1]]
    for key,name in selections:
        command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/'+name+'.py','--durations=10','--basetemp',str(owned/('pytest-'+key))]
        if key=='resource-fictional':command[8:8]=['-k','not authoritative_ite184_config_and_normal_preflight']
        if key=='dashboard-all':
            files=sorted((snapshot/'backend/tests/dashboard').glob('test_*.py'));files=[p for p in files if '_live' not in p.name]
            command[7:8]=[p.relative_to(snapshot/'backend').as_posix() for p in files]
        if key=='deterministic':command[8:8]=['-k','observed_equivalent_namespace']
        if key=='backup':command[8:8]=['-k','backup']
        if key=='supervised-smoke':command[7]='tests/test_supervised_worker.py::test_start_zero_original_behavior'
        if key=='smoke':command[7]='tests/test_bounded_worker.py::test_actual_process_initialization_completion_zero_and_cleanup'
        if key=='receipt-isolation':command[7]='tests/test_ga_input_receipt.py::test_distinct_thread_observations_are_isolated_not_a_concurrent_engine_claim'
        if key=='backend-regressions':command[8:8]=['tests/test_ga_academic_context.py','tests/test_ga_result_compatibility.py']
        tick=time.perf_counter();start=datetime.now().astimezone().isoformat()
        try:
            result=subprocess.run(command,cwd=snapshot/'backend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
            code=result.returncode;out=result.stdout;err=result.stderr
        except subprocess.TimeoutExpired as error:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nBound exceeded; owned process cleanup requires review.'
        row=dict(selection=key,command=command,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=sanitize(out),stderr=sanitize(err),scope='Owned source snapshot with fictional import tables and D10 models. Qualification/admission tests use new private disposable SQLite stores; other selections use isolated fictional fixtures. No PostgreSQL or institutional database. Technical verification is not institutional authorization.')
        (target/(key+'-command.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');results.append(dict(selection=key,exit_code=code));print(json.dumps(results[-1]),flush=True)
        if code:break
    assert git('rev-parse','HEAD').decode().strip()==HEAD and hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==index
    proof=dict(head=HEAD,source_sha256=hashes,ui_overlay_sha256=ui_hashes,ui_mode='working-tree' if ui_hashes else 'committed',proposed_blob_oids=blobs,results=results,qualified_selections=[k for k,n in selections],complete=len(results)==len(selections) and all(r['exit_code']==0 for r in results),fictional_source_only=True,no_u5d_u5e_u5f_app_dependency=False,no_actual_staging=True,consumption_verified_in_internal_path=True,snapshot=str(snapshot))
    (target/'snapshot-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return 0 if proof['complete'] else 1
if __name__=='__main__':raise SystemExit(main())
