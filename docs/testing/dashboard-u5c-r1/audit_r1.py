"""U5C-R1 preservation, privacy and selective-checkpoint review. No staging."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
HEAD="4bf03c144d5a404889a83cc89befad0495b673e5"
UPDATED={"docs/dashboard-u5c-institutional-context-qualification.md","docs/testing/dashboard-u5c/run_checks.py"}
EXTRA="docs/testing/dashboard-u5c/20261104T232624625262+0800-cdp-default/command.json"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args,input=None):
    return subprocess.check_output(["git","-c","safe.directory="+str(ROOT),*args],cwd=ROOT,input=input,
        env=dict(os.environ,GIT_OPTIONAL_LOCKS="0"),stderr=subprocess.PIPE)


def inspect(record=False):
    assert git("rev-parse","HEAD").decode().strip()==HEAD
    assert git("branch","--show-current").decode().strip()=="main"
    assert not git("diff","--cached","--name-only").strip()
    baseline=json.loads((BASE/"preservation-baseline.json").read_text(encoding="utf-8"))
    assert len(baseline)==3197
    for name,digest in baseline.items():
        if name not in UPDATED:assert (ROOT/name).is_file() and sha(ROOT/name)==digest,"BASELINE_MISMATCH_STOP: "+name
    old=json.loads((ROOT/"docs/testing/dashboard-u5c/manifest.json").read_text(encoding="utf-8"))
    assert len(old["exact_u5c_inventory"])==31
    archived={"docs/dashboard-u5c-institutional-context-qualification.md":BASE/"entry-report.md",
        "docs/testing/dashboard-u5c/run_checks.py":BASE/"entry-run_checks.py"}
    for name,digest in old["artifact_sha256"].items():
        assert sha(archived.get(name,ROOT/name))==digest,"HISTORICAL_HASH_MISMATCH_STOP: "+name
    expected_tracked=set(old["preexisting_tracked_modifications"])|set(old["modified_from_entry"])
    assert set(git("diff","--name-only").decode().splitlines())==expected_tracked
    subprocess.run(["git","diff","--check","--",*old["modified_from_entry"]],cwd=ROOT,capture_output=True,check=True)
    inventory=sorted(set(old["exact_u5c_inventory"])|{EXTRA,
        "docs/testing/dashboard-u5c-r1/manifest.json","docs/testing/dashboard-u5c-r1/staging-plan.json"}|
        {p.relative_to(ROOT).as_posix() for p in BASE.rglob("*") if p.is_file()})
    assert not any(p.startswith("backend/data/") or Path(p).name.startswith(".env") for p in inventory)
    untracked=set(git("ls-files","--others","--exclude-standard","-z").decode().split("\0"))-{''}
    assert not untracked-set(baseline)-set(inventory),"UNAPPROVED_NEW_PATH_STOP"
    plan=dict(base_head=HEAD,checkpoint_paths=inventory,partial_staging_required=[],
        excluded_tracked_paths=old["preexisting_tracked_modifications"],
        stage_only_after_separate_authorization=True,actual_index_modified=False,
        staging_command_template=["git","-c","core.autocrlf=false","add","--","<each literal checkpoint_paths entry>"],
        prerequisites=["Fresh fetch and upstream comparison before actual checkpoint", "Verify each raw SHA-256 and exact staged path inventory",
            "Verify index blob bytes against reviewed raw artifact hashes; no broad add", "Do not include protected data or unrelated U4/Live/research files"],
        recommended_commit_message="feat(ga): add read-only academic source qualification",
        snapshot_contract="HEAD plus U5C overlay, fictional import tables and exact verified release-byte fixture; dependencies reused; no actual staging")
    plan_path=BASE/"staging-plan.json"
    if record:
        with plan_path.open("x",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(plan,indent=2)+"\n")
    else:assert json.loads(plan_path.read_text(encoding="utf-8"))==plan
    records=[]
    for path in sorted(BASE.glob("*/command.json")):
        value=json.loads(path.read_text(encoding="utf-8"))
        counts={key:int(number) for key,number in re.findall(r"(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$",value["stdout"])}
        records.append(dict(path=path.relative_to(ROOT).as_posix(),selection=value["selection"],exit_code=value["exit_code"],counts=counts))
    for selection,total in [("browser",9),("u5b-browser",18),("u5a-browser",15)]:
        item=next(row for row in records if row["selection"]==selection)
        assert item["exit_code"]==0 and item["counts"]["pass"]==total
        browser=json.loads((ROOT/item["path"]).with_name("browser-results.json").read_text(encoding="utf-8"))
        assert len(browser["scenarios"])==total-1 and all(row["status"]=="PASS" for row in browser["scenarios"])
        assert not browser["runtime_errors"] and all(row["method"]=="GET" for row in browser["requests"])
    restricted=json.loads(json.loads(next(BASE.glob("*-cdp-default/command.json")).read_text(encoding="utf-8"))["stdout"])
    unrestricted=json.loads(json.loads((ROOT/EXTRA).read_text(encoding="utf-8"))["stdout"])
    chrome=json.loads(json.loads(next(BASE.glob("*-cdp-chrome/command.json")).read_text(encoding="utf-8"))["stdout"])
    assert all(row["timed_out"] for row in restricted["observations"][1:])
    assert not any(row["timed_out"] or row["error"] for row in unrestricted["observations"]+chrome["observations"])
    snapshots=[]
    for path in sorted(BASE.glob("*-snapshot/snapshot.json")):
        value=json.loads(path.read_text(encoding="utf-8"))
        snapshots.append(dict(path=path.relative_to(ROOT).as_posix(),outcomes=value["outcomes"]))
    final_path=sorted(BASE.glob("*-snapshot/snapshot.json"))[-1]
    snapshot=json.loads(final_path.read_text(encoding="utf-8"))
    assert [row["selection"] for row in snapshot["outcomes"]]==["backend","focused","regressions","build","bundle","lint","browser"]
    assert all(row["exit_code"]==0 for row in snapshot["outcomes"])
    checks={row["selection"]:row for row in snapshot["outcomes"]}
    assert checks["backend"]["counts"]["passed"]==99 and checks["focused"]["counts"]["pass"]==13 and checks["browser"]["counts"]["pass"]==9
    assert checks["regressions"]["counts"]["pass"]==checks["regressions"]["counts"]["tests"]
    source=[p for p in old["exact_u5c_inventory"] if p.startswith(("backend/","frontend/"))]
    assert len(source)==9
    for name in source:assert sha(ROOT/name)==snapshot["overlay_sha256"][name],"TESTED_SOURCE_CHANGED_STOP"
    assert sha(ROOT/"docs/testing/dashboard-u5c/run_checks.py")==snapshot["overlay_sha256"]["docs/testing/dashboard-u5c/run_checks.py"]
    recipe=json.loads((BASE/"release-byte-layout.json").read_text(encoding="utf-8"))
    assert recipe["base_commit"]==HEAD and len(recipe["files"])==55
    for item in recipe["files"]:
        assert sha(ROOT/item["path"])==item["release_raw_sha256"]==baseline[item["path"]]
        canonical=git("show",HEAD+":"+item["path"])
        assert hashlib.sha256(canonical).hexdigest()==item["canonical_sha256"]
        indices=set(item["crlf_line_indices"])
        raw=b"".join(line[:-1]+b"\r\n" if i in indices else line for i,line in enumerate(canonical.splitlines(keepends=True)))
        assert hashlib.sha256(raw).hexdigest()==item["release_raw_sha256"]
    names_registry=json.loads((ROOT/"backend/data/faculty_identities.json").read_text(encoding="utf-8"))["faculty"]
    names={re.sub(r"\s+"," ",v.strip().upper()) for row in names_registry for v in [row["name"],*row.get("aliases",[])] if len(v.strip())>=8}
    patterns=[r"eyJ[A-Za-z0-9_=-]{16,}",r"(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}",r"(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",r"(?i)https?://[^\s/]+:[^\s/@]+@",r"(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}"]
    hashes={};pngs=[];blob_oids={}
    for name in inventory:
        if name=="docs/testing/dashboard-u5c-r1/manifest.json":continue
        path=ROOT/name;raw=path.read_bytes();hashes[name]=sha(path)
        if path.suffix==".png":
            assert raw[:8]==b"\x89PNG\r\n\x1a\n";offset=8
            while offset<len(raw):
                length=struct.unpack(">I",raw[offset:offset+4])[0];kind=raw[offset+4:offset+8]
                assert kind not in [b"tEXt",b"iTXt",b"zTXt",b"eXIf"]
                assert zlib.crc32(raw[offset+4:offset+8+length])==struct.unpack(">I",raw[offset+8+length:offset+12+length])[0]
                offset+=length+12
            assert offset==len(raw);pngs.append(name)
        else:
            content=raw.decode("utf-8");assert content.endswith("\n") and all(line==line.rstrip() for line in content.splitlines()),"WHITESPACE: "+name
            upper=re.sub(r"\s+"," ",content.upper())
            assert not any(re.search(r"(?<!\w)"+re.escape(n)+r"(?!\w)",upper) for n in names),"PRIVATE_NAME_STOP_WITHHELD"
            assert not any(re.search(p,content) for p in patterns),"SENSITIVE_PATTERN_STOP_WITHHELD"
        plain=git("hash-object","--stdin",input=raw).decode().strip()
        assert plain==git("-c","core.autocrlf=false","hash-object","--path="+name,"--stdin",input=raw).decode().strip(),"GIT_FILTER_STOP"
        blob_oids[name]=plain
    assert len(pngs)==16
    assert git("rev-parse","HEAD").decode().strip()==HEAD and sha(ROOT/".git/index")==baseline[".git/index"]
    return dict(milestone="U5C-R1",head=HEAD,checkpoint_readiness="READY_WITH_DOCUMENTED_RUNTIME_BASELINE_REQUIREMENTS",
        production_institutional_activation="BLOCKED",actual_staging=False,commits_or_pushes=False,
        exact_checkpoint_inventory=inventory,original_u5c_paths=31,additional_r1_paths=len(inventory)-31,
        partial_staging_required=[],updated_from_r1_entry=sorted(UPDATED),entry_paths=3197,unchanged_entry_paths=3195,
        protected_academic_paths=23,protected_preferences_settings="BYTE_IDENTICAL; UNSTAGED; RAW_HASH_ONLY",
        ga_scoring_fingerprints_migrations_schedules_checkpoints_saved_best_prior_evidence="BYTE_IDENTICAL_TO_ENTRY",
        original_30_artifact_hashes_verified="PASS; report and runner checked via exact entry archives",
        artifact_sha256=hashes,proposed_git_blob_oids=blob_oids,staging_config="core.autocrlf=false, per command only",
        browser=dict(u5c=8,u5b=17,u5a=14,unique_scenarios=39,snapshot_u5c_repeat=8,actual_edge=True,intercepted_http=True,live_fastapi=False),
        startup_probes=dict(restricted=restricted,unrestricted_edge=unrestricted,unrestricted_chrome=chrome),
        root_cause="Execution-context restriction reproduced by paired probes; precise OS sandbox mechanism unobserved. No application startup involved.",
        workspace_records=records,snapshot_attempts=snapshots,final_snapshot=final_path.relative_to(ROOT).as_posix(),final_snapshot_checks=checks,
        privacy="PASS patterns/private-name comparison; all 16 PNG contents reviewed; only fictional intercepted records; no image editing",pngs=pngs,
        whitespace="PASS",git_index_head="UNCHANGED",historical_failures="RETAINED; original browser failures and R1 tooling/collection/fingerprint failures",
        limits=["No live browser-to-FastAPI/database or institutional acceptance", "Installed dependencies reused, not a fresh dependency installation",
            "Canonical Git export alone fails a pre-existing strict legacy raw-source check; qualified tests require the exact unchanged release-byte fixture",
            "Real production source/authority and run-consumption binding remain unavailable", "Fresh upstream fetch/review required before separately authorized checkpoint"])


def main():
    record=sys.argv[1:]==["--record"]; finding=inspect(record)
    path=BASE/"manifest.json"
    if record:
        finding["recorded_at"]=datetime.now().astimezone().isoformat()
        with path.open("x",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(finding,indent=2)+"\n")
    else:
        prior=json.loads(path.read_text(encoding="utf-8"))
        for key,value in finding.items():assert prior[key]==value,"R1_MANIFEST_MISMATCH: "+key
    print(json.dumps(dict(status="U5C_R1_AUDIT_PASSED",checkpoint_paths=len(finding["exact_checkpoint_inventory"]),hashed_artifacts=len(finding["artifact_sha256"]),
        preservation="PASS",privacy="PASS",whitespace="PASS",staged=False,production="BLOCKED")))


if __name__=="__main__":main()
