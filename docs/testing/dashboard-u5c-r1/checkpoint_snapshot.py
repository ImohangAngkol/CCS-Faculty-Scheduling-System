"""Test a source snapshot of HEAD plus exact U5C overlays; no Git index writes.

Temporary repository is retained. Installed dependency directories are junctioned,
not installed/copied. Source and test modules come only from HEAD/approved paths.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
HEAD="4bf03c144d5a404889a83cc89befad0495b673e5"


def git(*args, **kwargs):
    return subprocess.check_output(["git","-c","safe.directory="+str(ROOT),*args],cwd=ROOT,**kwargs)


def main():
    entry_head=git("rev-parse","HEAD").decode().strip()
    subprocess.run(["git","merge-base","--is-ancestor",HEAD,entry_head],cwd=ROOT,check=True)
    assert not git("diff","--cached","--name-only").strip()
    protected={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ["backend/data/faculty_preferences.json","backend/data/ga_settings.json",".git/index"]}
    original=json.loads((ROOT/"docs/testing/dashboard-u5c/manifest.json").read_text(encoding="utf-8"))
    inventory=original["exact_u5c_inventory"]
    assert len(inventory)==31 and not any(p.startswith("backend/data/") for p in inventory)
    owned=Path(tempfile.mkdtemp(prefix="u5c-r1-snapshot-")).resolve()
    assert owned.parent==Path(tempfile.gettempdir()).resolve()
    (owned/"OWNED-SNAPSHOT.json").write_text(json.dumps({"head":HEAD,"purpose":"U5C fictional source snapshot"}),encoding="utf-8")
    archive=owned/"head.tar"; snapshot=owned/"repository";snapshot.mkdir()
    with archive.open("xb") as stream:
        subprocess.run(["git","-c","safe.directory="+str(ROOT),"-c","core.autocrlf=false","archive",HEAD],cwd=ROOT,stdout=stream,check=True)
    with tarfile.open(archive) as stream:
        for member in stream.getmembers():
            target=(snapshot/member.name).resolve()
            assert target.is_relative_to(snapshot) and not member.issym() and not member.islnk()
        stream.extractall(snapshot,members=[m for m in stream.getmembers() if not m.name.startswith("backend/data/")],filter="data")
    overlay_hashes={}
    blob_oids={}
    for relative in inventory:
        raw=(ROOT/relative).read_bytes()
        plain=git("hash-object","--stdin",input=raw).decode().strip()
        filtered=git("-c","core.autocrlf=false","hash-object","--path="+relative,"--stdin",input=raw,stderr=subprocess.PIPE).decode().strip()
        assert plain==filtered,"Unexpected Git content filtering; checkpoint requires separate review"
        target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        overlay_hashes[relative]=hashlib.sha256(raw).hexdigest();blob_oids[relative]=plain
    excluded=["frontend/src/services/liveOptimization.ts","frontend/src/services/subjectDrafts.ts",
        "frontend/src/components/ga/PreferenceOutcomeChart.tsx","frontend/src/components/dashboard/SubjectDrafts.tsx",
        "frontend/tests/liveOptimization.test.mjs","frontend/tests/catalogAnalytics.test.mjs"]
    assert not any((snapshot/path).exists() for path in excluded)
    for relative in ["frontend/src/pages/admin/FitnessAnalysis.tsx","frontend/src/pages/admin/GenerateSchedule.tsx",
                     "frontend/src/pages/admin/SubjectManagement.tsx"]:
        assert (snapshot/relative).read_bytes()==git("show",HEAD+":"+relative)
    from fictional_bootstrap import prepare, release_bytes
    bootstrap_hashes=prepare(snapshot)
    recipe=json.loads((BASE/"release-byte-layout.json").read_text(encoding="utf-8"))
    assert recipe["base_commit"]==HEAD
    release_bytes(snapshot,recipe)
    # Junctions point only to installed dependencies, never other source paths.
    for name,target in [(".venv",ROOT/".venv"),("frontend/node_modules",ROOT/"frontend/node_modules")]:
        dest=snapshot/name
        assert not dest.exists() and dest.parent.resolve().is_relative_to(snapshot)
        result=subprocess.run(["cmd","/d","/c","mklink","/J",str(dest),str(target)],capture_output=True,check=True)
    stamp=datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f%z")
    evidence=BASE/(stamp+"-snapshot");evidence.mkdir(exist_ok=False)
    allowed={"SYSTEMROOT","WINDIR","PATH","PATHEXT","TEMP","TMP","COMSPEC","LOCALAPPDATA","APPDATA","USERPROFILE","PROGRAMFILES","PROGRAMFILES(X86)"}
    env={key:value for key,value in os.environ.items() if key.upper() in allowed}
    env.update(PYTHONDONTWRITEBYTECODE="1",VITE_API_URL="http://localhost:57999",U5C_EVIDENCE_DIR=str(evidence))
    python=str(ROOT/".venv/Scripts/python.exe")
    # Use exactly the proposed checkpoint runner's commands, not worktree-only tests.
    import runpy
    commands=runpy.run_path(str(snapshot/"docs/testing/dashboard-u5c/run_checks.py"))["COMMANDS"]
    tasks=[("backend",[python,"-B","-m","pytest","-p","no:cacheprovider","-q","tests/test_ga_source_qualification.py",
            "tests/test_ga_academic_context.py","tests/test_ga_result_compatibility.py","--basetemp",str(owned/("pytest-"+uuid4().hex))]),
        *[(key,commands[key]) for key in ["focused","regressions","build","bundle","lint","browser"]]]
    outcomes=[]
    for key,command in tasks:
        cwd=snapshot/("backend" if key=="backend" else "frontend")
        start=datetime.now().astimezone().isoformat();tick=time.perf_counter()
        result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=300)
        record=dict(selection=key,command=command,cwd=str(cwd),started_at=start,ended_at=datetime.now().astimezone().isoformat(),
            elapsed_seconds=time.perf_counter()-tick,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,
            scope="HEAD plus exact U5C overlay; no unrelated source; fictional tests, no institutional services")
        (evidence/(key+"-command.json")).write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
        counts={key:int(value) for key,value in re.findall(r"(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$",result.stdout)}
        if key=="backend":counts={key:int(value) for value,key in re.findall(r"(\d+) (passed|failed|skipped|errors?)",result.stdout.split("short test summary info")[-1])}
        outcomes.append(dict(selection=key,exit_code=result.returncode,counts=counts))
        print(json.dumps(outcomes[-1]),flush=True)
        if result.returncode:break
    assert git("rev-parse","HEAD").decode().strip()==entry_head
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in protected.items())
    record=dict(head=HEAD,entry_head=entry_head,snapshot=str(snapshot),scope="No repository staging; temporary filesystem projection only; dependencies reused, no fresh install",
        original_inventory=inventory,overlay_sha256=overlay_hashes,git_blob_oids=blob_oids,excluded_unrelated_sources=excluded,
        proposed_staging_config="git -c core.autocrlf=false add -- exact approved paths; verify committed raw evidence bytes",
        fictional_import_bootstrap=bootstrap_hashes,all_repository_academic_data_excluded_from_export=True,
        release_byte_fixture="Exact unchanged baseline source hashes, canonical source equality and newline layout; original strict fingerprint checks remain active",
        release_layout_sha256=hashlib.sha256((BASE/"release-byte-layout.json").read_bytes()).hexdigest(),
        unrelated_page_edits_and_protected_local_data_excluded=True,outcomes=outcomes,
        actual_git_index_unchanged=True,temporary_snapshot_retained=True)
    (evidence/"snapshot.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    passed=all(row["exit_code"]==0 for row in outcomes) and len(outcomes)==len(tasks)
    print(json.dumps(dict(evidence=evidence.relative_to(ROOT).as_posix(),passed=passed)))
    return 0 if passed else 1


if __name__=="__main__":raise SystemExit(main())
