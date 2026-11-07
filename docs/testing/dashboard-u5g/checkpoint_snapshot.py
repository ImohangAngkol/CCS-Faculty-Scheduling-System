"""HEAD + U5G-only source qualification; fictional data, no actual staging.

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

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='d6db077793da52b7559351a5d0f8e6d54608cb77'
OVERLAY=['backend/services/ga_input_bundle.py','backend/tests/test_ga_input_bundle.py','backend/tests/test_ga_input_bundle_checkpoint_qualification.py']
def git(*args,input=None):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),*args],cwd=ROOT,input=input,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)

def main():
    assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('diff','--cached','--name-only').strip()
    index=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()
    owned=Path(tempfile.mkdtemp(prefix='u5c-r1-snapshot-u5g-')).resolve();assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/'OWNED-SNAPSHOT.json').write_text(json.dumps({'head':HEAD,'purpose':'U5G immutable capture and unchanged legacy checkpoint qualification; consumption blocked'}),encoding='utf-8')
    snapshot=owned/'repository';snapshot.mkdir();archive=owned/'head.tar'
    with archive.open('xb') as stream:subprocess.run(['git','-c','safe.directory='+str(ROOT),'-c','core.autocrlf=false','archive',HEAD],cwd=ROOT,stdout=stream,check=True)
    with tarfile.open(archive) as source:
        for member in source.getmembers():assert (snapshot/member.name).resolve().is_relative_to(snapshot) and not member.issym() and not member.islnk()
        source.extractall(snapshot,members=[m for m in source.getmembers() if not m.name.startswith('backend/data/')],filter='data')
    helper=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5c-r1/fictional_bootstrap.py'));helper['prepare'](snapshot)
    helper['release_bytes'](snapshot,json.loads((ROOT/'docs/testing/dashboard-u5c-r1/release-byte-layout.json').read_text(encoding='utf-8')))
    hashes={};blobs={}
    for name in OVERLAY:
        raw=(ROOT/name).read_bytes();path=snapshot/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest();blobs[name]=git('hash-object','--stdin',input=raw).decode().strip()
    for name in ['backend/services/ga_input_receipt.py','backend/services/advanced_ga_analysis.py','backend/services/continuous_readiness.py']:assert not (snapshot/name).exists()
    subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'.venv'),str(ROOT/'.venv')],capture_output=True,check=True)
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-snapshot');target.mkdir(exist_ok=False)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env['PYTHONDONTWRITEBYTECODE']='1'
    results=[]
    for key,name in [('bundle-tests','test_ga_input_bundle'),('fixed','test_ga_input_bundle_checkpoint_qualification')]:
        command=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/'+name+'.py','--durations=10','--basetemp',str(owned/('pytest-'+key))]
        tick=time.perf_counter();start=datetime.now().astimezone().isoformat()
        try:
            result=subprocess.run(command,cwd=snapshot/'backend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
            code=result.returncode;out=result.stdout;err=result.stderr
        except subprocess.TimeoutExpired as error:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nBound exceeded; owned process cleanup requires review.'
        row=dict(selection=key,command=command,started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=out,stderr=err,scope='HEAD plus U5G-only source; fictional import tables/D10 models. Original fixed GA does NOT consume the new bundle; scoring-copy parity and legacy continuation are qualified separately. No database access.')
        (target/(key+'-command.json')).write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8');results.append(dict(selection=key,exit_code=code));print(json.dumps(results[-1]),flush=True)
        if code:break
    assert git('rev-parse','HEAD').decode().strip()==HEAD and hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==index
    proof=dict(head=HEAD,source_sha256=hashes,proposed_blob_oids=blobs,results=results,complete=len(results)==2 and all(r['exit_code']==0 for r in results),fictional_source_only=True,no_u5d_u5e_u5f_app_dependency=True,no_actual_staging=True,consumption_verified=False,snapshot=str(snapshot))
    (target/'snapshot-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return 0 if proof['complete'] else 1
if __name__=='__main__':raise SystemExit(main())
