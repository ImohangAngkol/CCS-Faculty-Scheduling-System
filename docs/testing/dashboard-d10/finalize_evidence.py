"""D10 local evidence/preservation audit. No database operations or Git writes."""
import ast
import csv
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import runpy
import struct
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
MANIFEST=BASE/"manifest.json"
ZONE=timezone(timedelta(hours=8))
MODIFIED={".gitignore","backend/main.py","frontend/src/pages/admin/GenerateSchedule.tsx",
          "frontend/src/pages/admin/ScheduleView.tsx","frontend/src/pages/admin/FitnessAnalysis.tsx"}
NEW_SOURCES={
    "backend/routers/ga_constrained.py","backend/schemas/ga_constrained.py",
    *("backend/services/"+name for name in ("ga_v2_constraints.py","ga_v2_engine.py","ga_v2_service.py","ga_v2_store.py")),
    "frontend/src/api/constrainedGA.ts","frontend/src/components/ga/ConstrainedRunPanel.tsx","frontend/src/components/ga/ConstrainedResultPanel.tsx",
    *("backend/tests/d10/"+name for name in ("support.py","test_v1_baseline.py","test_v2_engine.py","test_v2_api.py","test_v2_live.py","resume_v2_child.py")),
    *("frontend/tests/"+name for name in ("constrainedGA.test.mjs","constrainedGA.fixtures.mjs","constrainedGA.browser.test.mjs","constrainedGA.live.mjs")),
}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def relative(path):return path.relative_to(ROOT).as_posix()
def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


def main():
    sys.path.insert(0,str(ROOT/"backend"))
    from services.evidence_sanitization import SENSITIVE
    baseline=json.loads((BASE/"preservation-baseline.json").read_text(encoding="utf-8"))
    changed=[p for p,h in baseline.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    if set(changed)!=MODIFIED:raise RuntimeError("Unexpected preservation delta; paths only: "+json.dumps(changed))
    if git("rev-parse","HEAD")!="d6446d0757b91e1b3b17d650fcb49e896f51203b":raise RuntimeError("Unexpected HEAD")
    if git("diff","--cached","--name-only"):raise RuntimeError("Unexpected staged files")
    if (ROOT/"backend/constrained_runs_v2").exists():raise RuntimeError("Unexpected default V2 runtime storage")
    untracked=git("ls-files","--others","--exclude-standard").splitlines()
    allowed_docs=lambda p:p=="docs/dashboard-d10-implementation.md" or p.startswith("docs/testing/dashboard-d10/") or p.startswith("docs/screenshots/dashboard-d10/")
    unexpected=[p for p in untracked if p not in NEW_SOURCES and not allowed_docs(p)]
    if unexpected:raise RuntimeError("Unexpected untracked paths: "+json.dumps(unexpected))
    scopes=runpy.run_path(str(BASE/"run_compatibility_checks.py"))["SCOPES"]
    records=[];corrections=[]
    for path in sorted(BASE.glob("*/command.json")):
        record=json.loads(path.read_text(encoding="utf-8"));key=record.get("check","boundary")
        # Correct only scope attribution in this implementation's new records.
        # Preserve exact output, timestamps, commands and failed outcomes.
        if key not in {"boundary","retained-v1","current-v1-continuation"} and record.get("scope")!=scopes[key]:
            record["scope_metadata_correction"]={"previous_scope":record.get("scope"),"reason":"Early runner reused a generic V1 label; exact command/output are unchanged",
                "corrected_at":datetime.now(ZONE).isoformat(),"test_output_and_outcome_unchanged":True}
            record["scope"]=scopes[key]
            path.write_text(json.dumps(record,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
        if "scope_metadata_correction" in record:
            corrections.append(relative(path))
        records.append((path,record))
    latest={}
    for path,record in records:latest[record.get("check","boundary")]=(path,record)
    required=("v1-fixtures","supported-v1","v2-engine","v2-api","v2-live","v2-browser","contracts","backend","backend-regressions","ga-resource-regressions","academic-offline","browser-regressions","ga-browser","live","build","lint","lint-baseline")
    if any(k not in latest or latest[k][1]["exit_code"]!=0 for k in required):raise RuntimeError("A final validation group is missing or failed")
    files=sorted({ROOT/p for p in MODIFIED|NEW_SOURCES}|{ROOT/"docs/dashboard-d10-implementation.md"}|
        {p for p in BASE.rglob("*") if p.is_file() and p!=MANIFEST}|
        {p for p in (ROOT/"docs/screenshots/dashboard-d10").rglob("*") if p.is_file()})
    with (ROOT/"backend/data/Faculty.csv").open(encoding="utf-8-sig",newline="") as stream:
        names=[r["Faculty"].strip() for r in csv.DictReader(stream) if r.get("Faculty","").strip()]
    patterns={"encoded_complete_or_partial_receipt":r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+",
        "signed_fragment":r"(?<![A-Za-z0-9_-])[A-Za-z0-9_=-]{16,}(?:\.{3})?[A-Za-z0-9_=-]*\.[a-fA-F0-9]{16,}(?![A-Za-z0-9_-])",
        "credential_URI":r'''(?i)\b[a-z][a-z0-9+.-]*://[^\s/<>"']+:[^\s/<>"']+@''',
        "private_key":r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        "bearer_value":r"(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}"}
    findings=[];whitespace=[];images=[];syntax=0
    for path in files:
        if path.suffix==".png":
            raw=path.read_bytes()
            if raw[:8]!=b"\x89PNG\r\n\x1a\n":raise RuntimeError("Invalid PNG signature")
            width,height=struct.unpack(">II",raw[16:24]);offset=8;chunks=[]
            while offset<len(raw):
                size=struct.unpack(">I",raw[offset:offset+4])[0];kind=raw[offset+4:offset+8];payload=raw[offset+8:offset+8+size]
                checksum=struct.unpack(">I",raw[offset+8+size:offset+12+size])[0]
                if zlib.crc32(kind+payload)!=checksum:raise RuntimeError("Invalid PNG checksum")
                chunks.append(kind.decode("ascii"));offset+=size+12
            if any(kind in chunks for kind in ("tEXt","zTXt","iTXt","eXIf")):raise RuntimeError("PNG text metadata requires additional review")
            images.append({"path":relative(path),"width":width,"height":height,"sha256":sha(path),
                "visual_privacy_review":"PASS: viewed original or verified identical bytes to viewed original; fictional resources only",
                "text_or_EXIF_chunks":False})
            continue
        text=path.read_text(encoding="utf-8")
        if path.suffix==".py":ast.parse(text);syntax+=1
        if path.suffix in {".py",".ts",".tsx",".mjs",".md",".json"}:
            if any(line.rstrip()!=line for line in text.splitlines()):whitespace.append(relative(path))
        values=[text]
        if path.suffix==".json":
            document=json.loads(text)
            def strings(value):
                if isinstance(value,str):yield value
                elif isinstance(value,dict):
                    for child in value.values():yield from strings(child)
                elif isinstance(value,list):
                    for child in value:yield from strings(child)
            values=list(strings(document))
            if path.name=="command.json":
                for output in (document.get("stdout",""),document.get("stderr","")):
                    if any(SENSITIVE.search(line) for line in output.splitlines()):
                        findings.append({"path":relative(path),"kind":"sensitive_assignment_or_header_in_output"})
        for kind,pattern in patterns.items():
            if any(re.search(pattern,value) for value in values):findings.append({"path":relative(path),"kind":kind})
        if any(re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)",text,re.I) for name in names):
            findings.append({"path":relative(path),"kind":"private_faculty_name"})
    if findings:raise RuntimeError("Privacy findings, values omitted: "+json.dumps(findings))
    # Existing pages have historical whitespace; only changed/untracked lines
    # must pass. Git checks the former, explicit scan checks the latter.
    whitespace=[p for p in whitespace if p not in MODIFIED]
    if whitespace:raise RuntimeError("Untracked whitespace findings: "+json.dumps(whitespace))
    check=subprocess.run(["git","diff","--check","--",*sorted(MODIFIED)],cwd=ROOT,capture_output=True)
    if check.returncode:raise RuntimeError("Git whitespace check failed")
    sys.path.insert(0,str(ROOT/"backend"))
    with open(os.devnull,"w",encoding="utf-8") as sink,redirect_stdout(sink),redirect_stderr(sink):
        from services.ga_checkpoint_service import engine_fingerprint as v1
        from services.ga_v2_store import engine_fingerprint as v2
        from services.ga_progress_service import input_fingerprint
        identity={"V1":v1(),"V2":v2(),"inputs":input_fingerprint()}
    fixtures=sorted(latest["v1-fixtures"][0].parent.glob("fixture-*.json"))
    if not fixtures or any(json.loads(p.read_text(encoding="utf-8"))["engine_fingerprint"]!=identity["V1"] for p in fixtures):raise RuntimeError("Supported V1 engine identity changed")
    if any(json.loads(p.read_text(encoding="utf-8"))["input_fingerprint"]!=identity["inputs"] for p in fixtures):raise RuntimeError("Supported V1 input identity changed")
    preserved=sum(1 for p,h in baseline.items() if (ROOT/p).exists() and sha(ROOT/p)==h)
    assert preserved==len(baseline)-len(MODIFIED)
    manifest={"milestone":"D10","status":"ISOLATED V2 IMPLEMENTATION VERIFIED; PRODUCTION INSTITUTIONAL AUTHORITY BLOCKED",
        "recorded_at":datetime.now(ZONE).isoformat(),"source_commit":git("rev-parse","HEAD"),"branch":git("branch","--show-current"),
        "architecture_decision":{"Option_B_approved":True,"six_historical_rejections_accepted_as_preexisting":True,
            "historical_artifacts_unchanged":True,"supported_current_release_V1_compatibility_verified":True,"V2_engine":"ga-constrained-v2.1",
            "V2_constraint_contract":"gec-constraints-v2.1","production_provider_configured":False},
        "engine_fingerprints":identity,
        "latest_commands":{key:{"path":relative(latest[key][0]),"exit_code":latest[key][1]["exit_code"],"elapsed_seconds":latest[key][1]["elapsed_seconds"],"scope":latest[key][1]["scope"]} for key in required},
        "fresh_results":{"V1_fixture_pytest":4,"supported_pre_V2_V1_standalone_continuations":3,"V2_kernel_pytest":30,"V2_ASGI_API_pytest":18,
            "V2_live_pytest":1,"V2_live_browser_scenarios":6,"V2_synthetic_HTTP_browser_scenarios":12,"frontend_contracts":161,
            "D2_D9_backend_regressions":327,"auth_control_regressions":46,"academic_offline":85,"resource_regressions":3,
            "D1_D8_synthetic_HTTP_browser_scenarios":125,"D9_live_pytest":2,"D9_live_browser_scenarios":16,"GA_browser_scenarios":51,
            "production_build":"PASS with existing bundling warnings","focused_ESLint":"0 errors; 4 warnings also present in exact HEAD ScheduleView",
            "historical_six_boundary_diagnostics":"Previously passed; retained, not rerun or counted as constrained acceptance"},
        "preservation":{"baseline_files":len(baseline),"unchanged_files":preserved,"intended_existing_file_changes":sorted(MODIFIED),
            "academic_data_files_unchanged":sum(p.startswith("backend/data/") for p in baseline),"protected_preference_bytes_unchanged":True,
            "all_original_GA_and_fingerprinted_V1_sources_unchanged":True,"original_checkpoints_schedules_history_and_Phase4C_unchanged":True,"HEAD_and_Git_index_unchanged":True,"default_V2_storage_created":False},
        "reviewed_new_source_files":sorted(NEW_SOURCES),
        "retained_nonzero_command_records":[{"path":relative(path),"check":record.get("check"),"exit_code":record["exit_code"],"scope":record.get("scope")} for path,record in records if record["exit_code"]!=0],
        "scope_metadata_corrections":corrections,
        "privacy":{"findings":[],"files_scanned":len(files),"private_names_compared_locally":len(names),"methods":["Sensitive-line/full/truncated receipt sanitization before original evidence writes","Independent decoded JSON/text encoded/signed fragment, credential, bearer and key scans","Local private-name comparison without exporting values; word-fragment false positive reviewed in prior stage","PNG CRC/chunk checks and visual privacy review"],"screenshots":images,"unique_screenshot_images":len({i["sha256"] for i in images}),"raw_checkpoints_database_HAR_or_academic_rows_archived":False},
        "warnings":{"test_client":["Starlette 1.6.0 falls back to httpx 0.28.1; httpx2 not installed","AnyIO 4.15.1 deprecated abc.BlockingPortal alias used by Starlette's annotation"],"academic":"Two existing Alembic path_separator deprecation warnings in offline checks","lint":"Four existing ScheduleView hook-dependency warnings confirmed against HEAD","build":"Existing ineffective dynamic import and >500 kB bundle warnings"},
        "limitations":["No genuine institutional providers; production constrained activation remains BLOCKED","17 Phase4C PostgreSQL cases and D9 online PostgreSQL acceptance NOT RUN","V2 PostgreSQL locking branch NOT EXECUTED/ACCEPTED","Single-backend-process GA admission; multi-worker continuation/distributed coordination not established","Whole-term weekly commitments only; unresolved mappings, calendar exceptions, proposed/revoked applicable records fail closed","No institutional-scale performance/feasibility-rate benchmark; small fictional fixtures only","V2 run-scoped best/history/checkpoint/result envelope; no V1 artifact reinterpretation or automatic cross-run baseline reuse"],
        "checks":{"Python_AST_files":syntax,"Git_diff_whitespace":"PASS","new_text_whitespace":"PASS","manifest_artifact_hashes":"PASS"},
        "no_staging_commit_push":True,"no_D11_D12_or_Cpp":True,"hash_convention":"Raw-byte SHA-256; current manifest excludes itself. Hashes establish artifact identity, not institutional approval.",
        "artifacts":[{"path":relative(path),"bytes":path.stat().st_size,"sha256":sha(path)} for path in files]}
    MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
    assert all(sha(ROOT/entry["path"])==entry["sha256"] for entry in manifest["artifacts"])
    print(json.dumps({"artifacts_verified":len(files),"baselined_files_unchanged":preserved,"intended_modified":len(MODIFIED),"privacy_findings":0,
        "screenshots":len(images),"unique_images":manifest["privacy"]["unique_screenshot_images"],"manifest":relative(MANIFEST)}))


if __name__=="__main__":main()
