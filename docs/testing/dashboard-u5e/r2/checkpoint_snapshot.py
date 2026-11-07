"""Verify HEAD plus selective U5E overlay without touching the real Git index.

All test stores and the source snapshot are owned temporary paths. Installed
dependencies are reused through junctions. No U4/Live or uncommitted U5D source
is included. Existing committed fictional-bootstrap utilities are reused.
"""
from datetime import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent
HEAD="d6db077793da52b7559351a5d0f8e6d54608cb77"
PAGE="frontend/src/pages/admin/FitnessAnalysis.tsx"
OLD='  return runId?<ConstrainedResultPanel runId={runId} analysis/>:<LegacyFitnessAnalysis/>;'
NEW='''  const advanced=params.get("view")==="advanced";
  const target=new URLSearchParams(params);if(advanced)target.delete("view");else target.set("view","advanced");
  return runId?<ConstrainedResultPanel runId={runId} analysis/>:<><nav className="mb-4"><Link className="ccs-btn-secondary inline-block" to={`?${target}`}>{advanced?"Recorded penalty details":"Advanced faculty analysis"}</Link></nav>{advanced?<AdvancedAnalysis/>:<LegacyFitnessAnalysis/>}</>;'''
IMPORT='import AdvancedAnalysis from "../../components/ga/AdvancedAnalysis";\n'
OVERLAY=["backend/main.py","backend/routers/advanced_ga_analysis.py","backend/services/advanced_ga_analysis.py",
    "backend/tests/test_advanced_ga_analysis.py","frontend/src/services/advancedAnalysis.ts",
    "frontend/src/components/ga/AdvancedAnalysis.tsx","frontend/tests/advancedAnalysis.test.mjs",
    "frontend/tests/advancedAnalysis.browser.test.mjs","frontend/tests/advancedAnalysis.fixtures.mjs",
    "docs/testing/dashboard-u5e/fictional-api.json","frontend/src/services/analysisChartPresentation.ts",
    "frontend/tests/advancedAnalysisInteraction.test.mjs","frontend/tests/advancedAnalysisInteraction.browser.test.mjs"]


def git(*args,input=None):
    return subprocess.check_output(["git","-c","safe.directory="+str(ROOT),*args],cwd=ROOT,input=input,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS="0"),stderr=subprocess.PIPE)


def integration(raw):
    source=raw.decode().replace("\r\n","\n")
    assert source.count(OLD)==1 and IMPORT not in source
    return source.replace('import ConstrainedResultPanel from "../../components/ga/ConstrainedResultPanel";\n',
        'import ConstrainedResultPanel from "../../components/ga/ConstrainedResultPanel";\n'+IMPORT).replace(OLD,NEW).encode()


def main():
    assert git("rev-parse","HEAD").decode().strip()==HEAD
    assert not git("diff","--cached","--name-only").strip()
    before=hashlib.sha256((ROOT/".git/index").read_bytes()).hexdigest()
    old=git("show",HEAD+":"+PAGE);new=integration(old)
    patch="".join(difflib.unified_diff(old.decode().splitlines(keepends=True),new.decode().splitlines(keepends=True),fromfile="a/"+PAGE,tofile="b/"+PAGE))
    patchpath=BASE.parent/"fitness-analysis-integration.patch"
    if patchpath.exists():assert patchpath.read_bytes()==patch.encode()
    else:patchpath.write_bytes(patch.encode())
    git("apply","--check","--cached",str(patchpath))
    # Exact reverse integration proves all prior mixed-page bytes are retained.
    entry=json.loads((BASE.parent/"preservation-baseline.json").read_text(encoding="utf-8"))
    current=(ROOT/PAGE).read_bytes()
    eol=b"\r\n" if b"\r\n" in current else b"\n"
    restored=current.replace(IMPORT.encode().replace(b"\n",eol),b"").replace(NEW.encode().replace(b"\n",eol),OLD.encode())
    assert hashlib.sha256(restored).hexdigest()==entry[PAGE],"Mixed page contains unrelated changes since U5E entry"
    owned=Path(tempfile.mkdtemp(prefix="u5c-r1-snapshot-")).resolve()
    assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/"OWNED-SNAPSHOT.json").write_text(json.dumps({"head":HEAD,"purpose":"U5E R2 selective checkpoint"}),encoding="utf-8")
    archive=owned/"head.tar";snapshot=owned/"repository";snapshot.mkdir()
    with archive.open("xb") as stream:subprocess.run(["git","-c","safe.directory="+str(ROOT),"-c","core.autocrlf=false","archive",HEAD],cwd=ROOT,stdout=stream,check=True)
    with tarfile.open(archive) as stream:
        for m in stream.getmembers():assert (snapshot/m.name).resolve().is_relative_to(snapshot) and not m.issym() and not m.islnk()
        stream.extractall(snapshot,members=[m for m in stream.getmembers() if not m.name.startswith("backend/data/")],filter="data")
    helpers=runpy.run_path(str(ROOT/"docs/testing/dashboard-u5c-r1/fictional_bootstrap.py"))
    fictional=helpers['prepare'](snapshot)
    # Reproduce unchanged release bytes before adding the intentional main.py overlay.
    helpers['release_bytes'](snapshot,json.loads((ROOT/"docs/testing/dashboard-u5c-r1/release-byte-layout.json").read_text(encoding="utf-8")))
    hashes={};oids={}
    for name in OVERLAY:
        raw=(ROOT/name).read_bytes();path=snapshot/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest();oids[name]=git("hash-object","--stdin",input=raw).decode().strip()
    (snapshot/PAGE).write_bytes(new);hashes[PAGE]=hashlib.sha256(new).hexdigest();oids[PAGE]=git("hash-object","--stdin",input=new).decode().strip()
    assert not (snapshot/"backend/services/ga_input_receipt.py").exists()
    for name in ["frontend/src/components/ga/PreferenceOutcomeChart.tsx","frontend/src/services/liveOptimization.ts","frontend/src/services/subjectDrafts.ts"]:assert not (snapshot/name).exists()
    for name,target in [(".venv",ROOT/".venv"),("frontend/node_modules",ROOT/"frontend/node_modules")]:
        dest=snapshot/name;assert not dest.exists() and dest.parent.resolve().is_relative_to(snapshot)
        subprocess.run(["cmd","/d","/c","mklink","/J",str(dest),str(target)],capture_output=True,check=True)
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-snapshot');target.mkdir(exist_ok=False)
    commands=runpy.run_path(str(BASE/"run_checks.py"))['COMMANDS']
    allowed={"SYSTEMROOT","WINDIR","PATH","PATHEXT","TEMP","TMP","COMSPEC","LOCALAPPDATA","APPDATA","USERPROFILE","PROGRAMFILES","PROGRAMFILES(X86)"}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE="1",VITE_API_URL="http://localhost:57999",U5E_EVIDENCE_DIR=str(target))
    outcomes=[]
    for key in ['backend','focused','regressions','build','bundle','lint','browser']:
        cmd=commands[key]
        if key=='backend':cmd=[str(ROOT/'.venv/Scripts/python.exe'),'-B','-m','pytest','-p','no:cacheprovider','-q','tests/test_advanced_ga_analysis.py','--basetemp',str(owned/'pytest')]
        start=datetime.now().astimezone().isoformat();tick=time.perf_counter()
        try:
            result=subprocess.run(cmd,cwd=snapshot/('backend' if key=='backend' else 'frontend'),env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240)
        except subprocess.TimeoutExpired:
            raise RuntimeError('Snapshot command timed out; owned children and incomplete evidence require review')
        record=dict(selection=key,command=cmd,scope='HEAD plus U5E-only overlay; fictional temporary files, no database',started_at=start,
            ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
        (target/(key+'-command.json')).write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        outcomes.append({'selection':key,'exit_code':result.returncode})
        print(json.dumps(outcomes[-1]),flush=True)
        if result.returncode:break
    assert git('rev-parse','HEAD').decode().strip()==HEAD and hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==before
    proof=dict(base_head=HEAD,snapshot=str(snapshot),source_sha256=hashes,blob_oids=oids,fictional_bootstrap_hashes=fictional,
        no_actual_staging=True,no_u5d_dependency=True,results=outcomes,complete=len(outcomes)==7 and all(r['exit_code']==0 for r in outcomes))
    (target/'snapshot-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    return 0 if proof['complete'] else 1


if __name__=='__main__':raise SystemExit(main())
