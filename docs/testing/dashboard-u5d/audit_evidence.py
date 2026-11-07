"""Replay U5D preservation/privacy/evidence; no staging or database access."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
HEAD="d6db077793da52b7559351a5d0f8e6d54608cb77"
MODIFIED=[".gitignore","backend/routers/genetic_algorithm.py","backend/routers/ga_evaluation.py","backend/tests/conftest.py"]
NEW=["backend/services/ga_input_receipt.py","backend/tests/test_ga_input_receipt.py"]
REPORT="docs/dashboard-u5d-run-bound-loader-receipt.md"
ENTRY={"backend/data/faculty_preferences.json","backend/data/ga_settings.json",
    "frontend/src/components/ga/ConvergenceChart.tsx","frontend/src/components/ga/GALiveConsole.tsx",
    "frontend/src/components/ga/LiveGAMonitor.tsx","frontend/src/components/ga/WorkloadChart.tsx",
    "frontend/src/components/ga/workloadChart.css","frontend/src/pages/admin/FitnessAnalysis.tsx",
    "frontend/src/pages/admin/GenerateSchedule.tsx","frontend/src/pages/admin/SubjectManagement.tsx",
    "frontend/tests/evaluationCoverage.browser.test.mjs"}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args,input=None):
    return subprocess.check_output(["git","-c","safe.directory="+str(ROOT),*args],cwd=ROOT,input=input,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS="0"),stderr=subprocess.PIPE)


def inspect(record=False):
    assert git("rev-parse","HEAD").decode().strip()==HEAD,"HEAD_CHANGED_STOP"
    assert git("branch","--show-current").decode().strip()=="main"
    assert not git("diff","--cached","--name-only").strip(),"STAGED_CONTENT_STOP"
    baseline=json.loads((BASE/"preservation-baseline.json").read_text(encoding="utf-8"))
    assert len(baseline)==3248 and sum(name.startswith("backend/data/") for name in baseline)==23
    for name,digest in baseline.items():
        if name not in MODIFIED:assert (ROOT/name).is_file() and sha(ROOT/name)==digest,"PRESERVATION_STOP: "+name
    assert set(git("diff","--name-only").decode().splitlines())==ENTRY|set(MODIFIED)
    assert not (ROOT/"backend/run_input_receipts_v1").exists(),"REAL_RECEIPT_STORE_CREATED_STOP"
    subprocess.run(["git","diff","--check","--",*MODIFIED],cwd=ROOT,capture_output=True,check=True)
    manifest="docs/testing/dashboard-u5d/manifest.json"
    inventory=sorted(set([*MODIFIED,*NEW,REPORT,manifest,"docs/testing/dashboard-u5d/staging-plan.json",
        *(p.relative_to(ROOT).as_posix() for p in BASE.rglob("*") if p.is_file())]))
    assert not any(p.startswith("backend/data/") or Path(p).name.startswith(".env") for p in inventory)
    untracked=set(git("ls-files","--others","--exclude-standard","-z").decode().split("\0"))-{''}
    assert not untracked-set(baseline)-set(inventory),"UNEXPECTED_NEW_PATH_STOP"
    plan=dict(base_head=HEAD,checkpoint_paths=inventory,partial_staging_required=[],excluded_tracked_paths=sorted(ENTRY),
        actual_staging=False,commit_and_push_authorized=False,
        per_command_staging_template=["git","-c","core.autocrlf=false","add","--","<one literal checkpoint_paths entry>"],
        recommended_commit_message="feat(ga): record unverified run-bound input observations",
        prerequisites=["Separate checkpoint authorization and fresh upstream comparison", "Verify raw artifact hashes and exact staged names/count",
            "Verify index blobs without changing protected local JSON", "Exclude runtime receipts and all unrelated U4/Live/research work"],
        scope="Partial observation contract only; full optimizer consumption and institutional activation remain blocked")
    plan_path=BASE/"staging-plan.json"
    if record:
        with plan_path.open("x",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(plan,indent=2)+"\n")
    else:assert json.loads(plan_path.read_text(encoding="utf-8"))==plan
    attempts=[]
    for path in sorted(BASE.glob("*/command.json")):
        item=json.loads(path.read_text(encoding="utf-8"))
        counts={key:int(value) for key,value in re.findall(r"(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$",item["stdout"])}
        if item["selection"].startswith("backend"):
            counts={key:int(value) for value,key in re.findall(r"(\d+) (passed|failed|skipped|errors?)",item["stdout"].split("short test summary info")[-1])}
        assert item["exit_code"]==0 and not item["timed_out"],"ATTEMPT_FAILURE_REVIEW_REQUIRED"
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(),selection=item["selection"],exit_code=item["exit_code"],counts=counts))
    final={item["selection"]:item for item in attempts}
    for selection,count in [("backend",36),("backend-regressions",133)]:
        assert final[selection]["counts"]["passed"]==count
    for selection,count in [("focused",13),("regressions",166)]:
        assert final[selection]["counts"]["pass"]==count
        assert all(final[selection]["counts"][key]==0 for key in ["fail","skipped","cancelled"])
    for selection in ["build","bundle","lint","integrity"]:assert final[selection]["exit_code"]==0
    assert [item["counts"]["passed"] for item in attempts if item["selection"]=="backend"]==[29,32,35,36]
    names_registry=json.loads((ROOT/"backend/data/faculty_identities.json").read_text(encoding="utf-8"))["faculty"]
    names={re.sub(r"\s+"," ",value.strip().upper()) for row in names_registry for value in [row["name"],*row.get("aliases",[])] if len(value.strip())>=8}
    patterns=[r"eyJ[A-Za-z0-9_=-]{16,}",r"(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}",r"(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",r"(?i)https?://[^\s/]+:[^\s/@]+@",r"(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}"]
    hashes={};oids={}
    for name in inventory:
        if name==manifest:continue
        path=ROOT/name;raw=path.read_bytes();content=raw.decode("utf-8")
        assert content.endswith("\n") and all(line==line.rstrip() for line in content.splitlines()),"WHITESPACE_STOP: "+name
        upper=re.sub(r"\s+"," ",content.upper())
        assert not any(re.search(r"(?<!\w)"+re.escape(value)+r"(?!\w)",upper) for value in names),"PRIVATE_NAME_STOP_WITHHELD"
        assert not any(re.search(pattern,content) for pattern in patterns),"SENSITIVE_PATTERN_STOP_WITHHELD"
        hashes[name]=sha(path)
        oids[name]=git("hash-object","--stdin",input=raw).decode().strip()
        assert oids[name]==git("-c","core.autocrlf=false","hash-object","--path="+name,"--stdin",input=raw).decode().strip()
    assert git("rev-parse","HEAD").decode().strip()==HEAD and sha(ROOT/".git/index")==baseline[".git/index"]
    return dict(milestone="U5D",status="PARTIALLY_IMPLEMENTED",full_consumption_verification="BLOCKED_BY_UNRESOLVED_LOADER_BEHAVIOR",head=HEAD,
        verification_status_capability="UNVERIFIED_ONLY",institutional_provider="UNCONFIGURED",current_eligibility_granted=False,
        exact_checkpoint_inventory=inventory,modified_from_entry=MODIFIED,new_files=[n for n in inventory if n not in MODIFIED],
        partial_staging_required=[],preexisting_tracked_modifications=sorted(ENTRY),staged_files=[],
        baseline_paths=3248,unchanged_baseline_paths=3244,protected_academic_paths=23,
        protected_preferences_settings="BYTE_IDENTICAL_TO_LOCAL_ENTRY; UNSTAGED; RAW_HASHED_ONLY",
        original_ga_scoring_rng_fingerprints_migrations_checkpoints_saved_best_schedules_prior_evidence="UNCHANGED",
        git_index_head="UNCHANGED",artifact_sha256=hashes,proposed_git_blob_oids=oids,
        attempts=attempts,final_checks=final,focused_backend=36,backend_regressions=133,frontend_contracts=179,
        real_http_fixture="One owned loopback FastAPI receipt-read test, fictional principals, temporary files, Engine.connect forbidden; no live GA through HTTP",
        real_engine_fixture="Unchanged V1 plain/wrapped parity plus actual pause/load/resume, fictional models, temporary stores; no production authority",
        browser_tests="NOT RUN; no frontend changes; prior U5C-R1 browser evidence remains historical",
        actual_institutional_database_connections=0,post_status="No database operations, migrations, staging, commits or pushes",
        privacy="PASS patterns and in-memory private identity comparison; no graph/profile/preference payloads, credentials or signed session artifacts archived",
        whitespace="PASS",source_storage_runtime="No real receipt directory created by tests; ignored new runtime tree; immutable side records only",
        limitations=["Pre-call aliases and callback context samples do not prove every optimizer read", "No complete source/term/dataset-to-model mapping or atomic input freeze",
            "Graph representation includes ordering; no cross-process semantic equivalence claim", "Hash/encoding caps are not a measured peak-RAM bound; overhead not benchmarked",
            "32 generation observations maximum; no callback inserted when absent", "No resume, legacy helper, V2 or saved seed consumption attestation",
            "Checksums are not cryptographic institutional signatures", "No process-kill/power-loss durability test or complete browser-to-GA journey",
            "Existing private import dependencies and supported-release newline prerequisite remain", "Production institutional context and complete consumption verification remain blocked"])


def main():
    record=sys.argv[1:]==["--record"];finding=inspect(record);path=BASE/"manifest.json"
    if record:
        finding["recorded_at"]=datetime.now().astimezone().isoformat()
        with path.open("x",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(finding,indent=2)+"\n")
    else:
        previous=json.loads(path.read_text(encoding="utf-8"))
        for key,value in finding.items():assert previous[key]==value,"MANIFEST_MISMATCH_STOP: "+key
    print(json.dumps(dict(status="U5D_AUDIT_PASSED",checkpoint_paths=len(finding["exact_checkpoint_inventory"]),hashed_artifacts=len(finding["artifact_sha256"]),
        unchanged_baseline_paths=3244,privacy="PASS",whitespace="PASS",full_consumption_verification="BLOCKED",staged=False)))


if __name__=="__main__":main()
