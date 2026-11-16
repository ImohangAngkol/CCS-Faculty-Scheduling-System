"""Owned fictional snapshot qualification; never run against working datasets."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='0dcc3e942d0b79c0e6358aa151208c014b307300'
OVERLAY=['backend/services/ga_research_experiments.py', 'backend/routers/research_experiments.py', 'backend/tests/test_research_experiments.py', 'backend/tests/test_research_experiments_live.py', 'frontend/src/researchExperiments/panel.html', 'frontend/src/researchExperiments/console.mjs', 'frontend/src/researchExperiments/model.mjs', 'frontend/tests/researchExperiments.test.mjs', 'frontend/tests/researchExperiments.live.mjs', 'docs/testing/dashboard-u5pf/serve_experiment.py','docs/testing/dashboard-u5pf/verify_export.py']
SELECTIONS={'offline':['tests/test_research_experiments.py','-k','not real_native'],'metrics':['tests/test_research_experiments.py::test_metrics_distinguish_observed_derived_unavailable'],'experiments':['tests/test_research_experiments.py'],'operator': ['tests/test_research_operator.py'], 'native': ['tests/test_supervised_worker.py'], 'parity': ['tests/test_ga_bundle_parity.py'], 'legacy': ['tests/test_ga_input_bundle_checkpoint_qualification.py'], 'continuity': ['tests/test_observation_continuity.py'], 'receipts': ['tests/test_ga_input_receipt.py'], 'bridge': ['tests/test_research_bridge.py::test_native_original_455_assignments_history_breakdown_rng', 'tests/test_research_bridge.py::test_native_real_parent_interruption_truthful_after_restart', 'tests/test_research_bridge.py::test_native_wall_limit_and_crash_are_distinct', 'tests/test_research_bridge.py::test_native_storage_failure_no_success_or_best'], 'live': ['tests/test_research_experiments_live.py'], 'handoff': [], 'handoff-probe': [], 'physical': ['tests/test_windows_supervision.py']}


def git(*args):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,stderr=subprocess.PIPE)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    SELECTIONS['native-export']=['tests/test_research_experiments.py::test_real_native_completed_experiment_and_all_readonly_exports']
    selections=sys.argv[1:] or ['experiments']
    assert all(s in SELECTIONS for s in selections)
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only').strip()
    index=sha(ROOT/'.git/index')
    owned=Path(tempfile.mkdtemp(prefix='u5c-r1-snapshot-u5h-')).resolve()
    assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/'OWNED-SNAPSHOT.json').write_text(json.dumps(dict(head=HEAD,scope='FICTIONAL_U5PF_ONLY')))
    snapshot=owned/'repository';snapshot.mkdir()
    roots=git('ls-tree','-z','--name-only',HEAD).decode().split('\0')
    children=git('ls-tree','-z','--name-only',HEAD+':backend').decode().split('\0')
    excluded={'data','saved_chromosomes','run_checkpoints','generation_snapshots','run_input_receipts_v1','run_provenance_v1','constrained_runs_v2'}
    paths=[p for p in roots if p and p!='backend']+['backend/'+p for p in children if p and p not in excluded]
    with (owned/'source.tar').open('xb') as stream:subprocess.run(['git','-c','core.autocrlf=false','archive',HEAD,'--',*paths],cwd=ROOT,stdout=stream,check=True)
    with tarfile.open(owned/'source.tar') as archive:
        for m in archive.getmembers():assert (snapshot/m.name).resolve().is_relative_to(snapshot) and not m.issym() and not m.islnk()
        archive.extractall(snapshot,filter='data')
    original_main=(snapshot/'backend/main.py').read_bytes()
    legacy=git('show','d6db077793da52b7559351a5d0f8e6d54608cb77:backend/main.py')
    recipe=json.loads((ROOT/'docs/testing/dashboard-u5c-r1/release-byte-layout.json').read_text())
    assert hashlib.sha256(legacy).hexdigest()==next(v['canonical_sha256'] for v in recipe['files'] if v['path']=='backend/main.py')
    (snapshot/'backend/main.py').write_bytes(legacy)
    bootstrap=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5c-r1/fictional_bootstrap.py'))
    bootstrap['prepare'](snapshot)
    # P-A intentionally changed this fingerprinted caller. The old newline
    # recipe is inapplicable to that new source: keep its current exact Git
    # bytes, and apply the old recipe only to byte-verified unchanged files.
    current_release='backend/services/chromosome_service.py'
    assert sha(snapshot/current_release)==hashlib.sha256(git('show',HEAD+':'+current_release)).hexdigest()
    bootstrap['release_bytes'](snapshot,{**recipe,'files':[v for v in recipe['files'] if v['path']!=current_release]})
    (snapshot/'backend/main.py').write_bytes(original_main)
    # Existing M race qualification explicitly compares a frozen old guard.
    # Supply its exact historical source only in the disposable test namespace.
    import ast
    historical=git('show','b4c8da7942bddfec63564a1e1f8de31e1db3e491:backend/services/ga_input_receipt.py').decode()
    assert hashlib.sha256(historical.encode()).hexdigest()=='2b418773be9ba119ff39fc87157e28d364462d139eb46b4c12f4a99f18fb5c5e'
    node=next(n for n in ast.parse(historical).body if isinstance(n,ast.FunctionDef) and n.name=='directory')
    (snapshot/'backend/tests/u5m_frozen_guard.py').write_text('from uuid import UUID\nfrom services.ga_input_receipt import error\nRECEIPTS_DIR=None\n'+ast.get_source_segment(historical,node)+'\n')
    # Preserve the committed P-A byte-qualified dependency/caller after the
    # historical bootstrap's release-layout preparation; no hash is spoofed.
    for name in ['backend/services/chromosome_service.py','backend/services/saved_best_policy.py']:
        (snapshot/name).write_bytes(git('show',HEAD+':'+name))
    hashes={}
    for name in OVERLAY:
        data=(ROOT/name).read_bytes();target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);hashes[name]=sha(ROOT/name)
    subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'.venv'),str(ROOT/'.venv')],capture_output=True,check=True)
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}}
    env['PYTHONDONTWRITEBYTECODE']='1'
    sanitizer=runpy.run_path(str(ROOT/'backend/services/evidence_sanitization.py'))['sanitize']
    failed=False
    for selection in selections:
        target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-'+selection);target.mkdir()
        child=dict(env,U5PF_EVIDENCE=str(target),U5PE_EVIDENCE=str(target),U5PC_EVIDENCE=str(target),U5PB_EVIDENCE=str(target),U5H_PROTOCOL_EVIDENCE=str(target))
        if selection=='legacy':child['D10_V1_BASELINE_RECORD']=str(target)
        command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','--tb=short',*SELECTIONS[selection],
            '--basetemp',str(owned/('pytest-'+selection))]
        if selection in {'live','handoff'}:
            subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'frontend/node_modules'),str(ROOT/'frontend/node_modules')],capture_output=True,check=True)
            runpy.run_path(str(ROOT/'docs/testing/dashboard-u5pa/isolate_vite_cache.py'))['prepare'](snapshot,owned)
        if selection in {'handoff','handoff-probe'}:command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','../docs/testing/dashboard-u5pf/serve_experiment.py','--fictional-only']+(['--probe'] if selection=='handoff-probe' else [])
        start=datetime.now().astimezone().isoformat();tick=time.monotonic()
        try:
            if selection=='handoff':
                result=subprocess.run(command,cwd=snapshot/'backend',env=child,text=True,timeout=360)
                code=result.returncode;out='Operator-only handoff output shown privately; no credential content captured.';err=''
            else:
                result=subprocess.run(command,cwd=snapshot/'backend',env=child,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=600)
                code=result.returncode;out=result.stdout;err=result.stderr
        except subprocess.TimeoutExpired as e:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(e.stdout);err=decode(e.stderr)+'\nHARNESS_BOUND_EXCEEDED; owned process review required.'
        row=dict(selection=selection,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.monotonic()-tick,
            exit_code=code,command=command,stdout=sanitizer(out),stderr=sanitizer(err),head=HEAD,source_sha256=hashes,
            scope='Owned empty import tables + fictional D10/J bundles + private new SQLite; no production database/authority',
            snapshot=str(snapshot),no_staging=True,completed=code==0)
        with (target/'command.json').open('x',encoding='utf-8') as f:json.dump(row,f,indent=2);f.write('\n')
        print(json.dumps(dict(selection=selection,exit_code=code,evidence=target.relative_to(ROOT).as_posix())),flush=True)
        if code:failed=True;break
    assert sha(ROOT/'.git/index')==index and git('rev-parse','HEAD').decode().strip()==HEAD
    return 1 if failed else 0


if __name__=='__main__':raise SystemExit(main())
