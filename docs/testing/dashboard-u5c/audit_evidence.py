"""Replay U5C evidence hashes/privacy/preservation; no database or Git writes."""
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

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
HEAD = "4bf03c144d5a404889a83cc89befad0495b673e5"
MODIFIED = ["backend/routers/ga_evaluation.py", "frontend/src/components/ga/CurrentEvaluation.tsx"]
NEW = ["backend/services/ga_source_qualification.py", "backend/tests/test_ga_source_qualification.py",
    "frontend/src/services/sourceQualification.ts", "frontend/src/components/ga/SourceQualification.tsx",
    "frontend/tests/sourceQualification.fixtures.mjs", "frontend/tests/sourceQualification.test.mjs",
    "frontend/tests/sourceQualification.browser.test.mjs"]
REPORT = "docs/dashboard-u5c-institutional-context-qualification.md"
ENTRY_MODIFIED = {"backend/data/faculty_preferences.json", "backend/data/ga_settings.json",
    "frontend/src/components/ga/ConvergenceChart.tsx", "frontend/src/components/ga/GALiveConsole.tsx",
    "frontend/src/components/ga/LiveGAMonitor.tsx", "frontend/src/components/ga/WorkloadChart.tsx",
    "frontend/src/components/ga/workloadChart.css", "frontend/src/pages/admin/FitnessAnalysis.tsx",
    "frontend/src/pages/admin/GenerateSchedule.tsx", "frontend/src/pages/admin/SubjectManagement.tsx",
    "frontend/tests/evaluationCoverage.browser.test.mjs"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory="+str(ROOT), *args], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).decode("utf-8")


def inspect():
    assert git("rev-parse", "HEAD").strip() == HEAD, "HEAD_CHANGED_STOP"
    assert git("branch", "--show-current").strip() == "main", "BRANCH_CHANGED_STOP"
    baseline = json.loads((BASE/"preservation-baseline.json").read_text(encoding="utf-8"))
    assert len(baseline) == 3168 and len([p for p in baseline if p.startswith("backend/data/")]) == 23
    for name, digest in baseline.items():
        if name not in MODIFIED:
            assert (ROOT/name).is_file() and sha(ROOT/name) == digest, "PRESERVATION_MISMATCH_STOP: "+name
    assert not git("diff", "--cached", "--name-only").strip(), "STAGED_CONTENT_STOP"
    assert set(git("diff", "--name-only").splitlines()) == ENTRY_MODIFIED | set(MODIFIED), "UNEXPECTED_TRACKED_PATH_STOP"
    subprocess.run(["git", "diff", "--check", "--", *MODIFIED], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"), capture_output=True, check=True)
    prior = {}
    for milestone in ("u5a", "u5b"):
        prior.update(json.loads((ROOT/f"docs/testing/dashboard-{milestone}/manifest.json").read_text(encoding="utf-8"))["artifact_sha256"])
    for name, digest in prior.items():
        if name not in MODIFIED:
            assert sha(ROOT/name) == digest, "PRIOR_ARTIFACT_MISMATCH_STOP: "+name
    manifest_path = (BASE/"manifest.json").relative_to(ROOT).as_posix()
    own = sorted(set([*MODIFIED, *NEW, REPORT, manifest_path,
        *(p.relative_to(ROOT).as_posix() for p in BASE.rglob("*") if p.is_file())]))
    untracked = set(git("ls-files", "--others", "--exclude-standard", "-z").split("\0")) - {""}
    assert not untracked - set(baseline) - set(own), "UNAPPROVED_NEW_PATH_STOP"
    paths = [ROOT/name for name in own if name != manifest_path]
    # Compare private names locally without printing or retaining them. Protected
    # preferences/settings are only raw-hashed, never parsed by this auditor.
    registry = json.loads((ROOT/"backend/data/faculty_identities.json").read_text(encoding="utf-8"))["faculty"]
    names = {re.sub(r"\s+", " ", value.strip().upper()) for row in registry
        for value in (row["name"], *row.get("aliases", [])) if len(value.strip()) >= 8}
    patterns = [r"eyJ[A-Za-z0-9_=-]{16,}", r"(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}",
        r"(?i)\b(?:postgresql|postgres|mysql)(?:\+\w+)?://[^\s]+", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"(?i)https?://[^\s/]+:[^\s/@]+@", r"(?i)(?<![\w])(?:set-cookie|authorization)\s*:\s*[^\s]{16,}"]
    pngs = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix == ".png":
            raw = path.read_bytes()
            assert raw[:8] == b"\x89PNG\r\n\x1a\n", "PNG_FORMAT_STOP"
            width, height = struct.unpack(">II", raw[16:24]); offset, chunks = 8, []
            while offset < len(raw):
                size = struct.unpack(">I", raw[offset:offset+4])[0]
                kind = raw[offset+4:offset+8]
                assert zlib.crc32(raw[offset+4:offset+8+size]) == struct.unpack(">I", raw[offset+8+size:offset+12+size])[0], "PNG_CRC_STOP"
                assert kind not in {b"tEXt", b"zTXt", b"iTXt", b"eXIf"}, "IMAGE_METADATA_STOP"
                chunks.append(kind.decode("ascii"));offset += 12+size
            assert offset == len(raw) and chunks[-1] == "IEND"
            pngs.append(dict(path=relative, width=width, height=height, chunks=chunks))
            continue
        content = path.read_text(encoding="utf-8")
        assert content.endswith("\n") and all(line == line.rstrip() for line in content.splitlines()), "WHITESPACE_STOP: "+relative
        normalized = re.sub(r"\s+", " ", content.upper())
        assert not any(re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)", normalized) for name in names), "PRIVATE_IDENTITY_STOP_WITHHELD"
        assert not any(re.search(pattern, content) for pattern in patterns), "SENSITIVE_PATTERN_STOP_WITHHELD"
    attempts = []
    for path in sorted(BASE.glob("*/command.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        counts = {key:int(value) for key,value in re.findall(r"(?m)^\S+ (tests|pass|fail|skipped|cancelled) (\d+)\s*$",record["stdout"])}
        if record["selection"].startswith("backend"):
            counts = {key:int(value) for value,key in re.findall(r"(\d+) (passed|failed|skipped|errors?)",record["stdout"].split("short test summary info")[-1])}
        assert not record["timed_out"], "RUNNER_TIMEOUT_REVIEW_REQUIRED"
        attempts.append(dict(path=path.relative_to(ROOT).as_posix(), selection=record["selection"], exit_code=record["exit_code"], counts=counts))
    final = {item["selection"]:item for item in attempts}
    for selection,count in [("backend",45),("backend-regressions",88)]:
        assert final[selection]["exit_code"] == 0 and final[selection]["counts"]["passed"] == count
    for selection,count in [("focused",13),("regressions",212)]:
        item=final[selection]
        assert item["exit_code"] == 0 and item["counts"]["pass"] == count, "FINAL_TEST_STOP: "+selection
        assert item["counts"]["fail"] == item["counts"]["skipped"] == item["counts"]["cancelled"] == 0
    for selection in ["build","bundle","lint","integrity","source-inspection","cdp-isolated","cdp-chrome"]:
        assert final[selection]["exit_code"] == 0, "FINAL_CHECK_STOP: "+selection
    observed = json.loads(json.loads((ROOT/final["source-inspection"]["path"]).read_text(encoding="utf-8"))["stdout"])
    assert observed["default_academic_provider"] == "UNCONFIGURED"
    assert len(observed["observation"]["cached_tables"]) == 5
    assert all(row["status"] == "MATCH" for row in observed["observation"]["cached_tables"])
    failures = [item for item in attempts if item["exit_code"]]
    assert len(failures) == 2 and all(item["selection"] == "browser" and item["counts"]["tests"] == 1 for item in failures)
    for item in failures:
        failed_record=json.loads((ROOT/item["path"]).read_text(encoding="utf-8"))
        assert "CDP timeout: Runtime.enable" in failed_record["stdout"], "FAILURE_ATTRIBUTION_CHANGED_STOP"
        browser=json.loads((ROOT/item["path"]).with_name("browser-results.json").read_text(encoding="utf-8"))
        assert browser["scenarios"] == [] and browser["captures"] == [] and browser["requests"] == []
    probes=[]
    for selection in ["cdp-isolated","cdp-chrome"]:
        record=json.loads((ROOT/final[selection]["path"]).read_text(encoding="utf-8"))
        probe=json.loads(record["stdout"])
        assert probe["observations"][0]["timed_out"] is False
        assert all(item["timed_out"] for item in probe["observations"][1:])
        probes.append(probe)
    assert pngs == [], "UNREVIEWED_SCREENSHOT_STOP"
    assert git("rev-parse", "HEAD").strip() == HEAD and sha(ROOT/".git/index") == baseline[".git/index"]
    return dict(schema_version=1, milestone="U5C", status="VERIFIED_PARTIAL_READ_ONLY_FOUNDATION", head=HEAD,
        production_qualification="BLOCKED", provider="UNCONFIGURED", current_eligibility_granted=False,
        baseline_paths=3168, unchanged_baseline_paths=3166, academic_paths=23,
        protected_preferences_and_settings="BYTE_IDENTICAL_TO_LOCAL_ENTRY_STATE; UNSTAGED; RAW_HASH_ONLY",
        git_index_head="UNCHANGED", baseline_ga_scoring_rng_fingerprints_migrations_checkpoints_schedules_previous_evidence="UNCHANGED",
        prior_latest_u5a_u5b_hashes_verified=len(set(prior)-set(MODIFIED)),
        exact_u5c_inventory=own, modified_from_entry=MODIFIED, new_files=[name for name in own if name not in MODIFIED],
        preexisting_tracked_modifications=sorted(ENTRY_MODIFIED), staged_files=[],
        artifact_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        attempts=attempts, final_checks=final, historical_unsuccessful_attempts=failures,
        backend_focused=45, backend_regressions=88, frontend_focused=13, frontend_regressions=212,
        browser_scenarios=dict(u5c_defined=8,u5c_executed=0,passes=0,initialization_failures=2,u5a_u5b_browser_regressions="NOT_RERUN_DUE_TO_RENDERER_BLOCKER",live_backend=False),
        blank_page_diagnostics=probes, pngs=pngs,
        visual_privacy_review="No screenshots captured; no application scenario or visual acceptance established.",
        privacy="PASS encoded-fragment/header/credential patterns and in-memory private identity comparison; no source rows exported",
        whitespace="PASS", failure_history="RETAINED; two Edge attempts timed out at Runtime.enable before scenarios; Edge and Chrome blank-page renderer commands also timed out; underlying cause unconfirmed",
        source_observation="Five current cached tables match files; full consumed model binding NOT ESTABLISHED",
        database_connections=0, production_ga_executions=0, activation_or_persistence_changes=False,
        warnings=["Existing Starlette/httpx and anyio deprecations", "Existing Vite mixed import and chunk size warnings", "Existing Git dangling objects retained"],
        blockers=["Institutional owner/authority/approval/effective context source absent", "Actual transformed/frozen/resumed run consumption binding absent",
            "Current diagnostic not integrated into a future configured provider; production activation prohibited pending reviewed binding and enforcement",
            "Saved Best persistence and V2 aggregation remain separate"],
        limitations=["Projection comparison validates supplied complete semantic digests, not actual optimizer consumption",
            "Cached tables and sampled fingerprints are not an atomic loader receipt", "No live browser-to-FastAPI or fresh database acceptance",
            "No new source-qualified GA execution or U5C CURRENT classification", "Browser/visual/accessibility/device acceptance not established due to initialization blocker"])


def main():
    finding=inspect(); path=BASE/"manifest.json"
    if sys.argv[1:] == ["--record"]:
        finding["recorded_at"]=datetime.now().astimezone().isoformat()
        with path.open("x",encoding="utf-8") as stream:stream.write(json.dumps(finding,indent=2,ensure_ascii=False)+"\n")
    else:
        previous=json.loads(path.read_text(encoding="utf-8"))
        for key,value in finding.items():assert previous[key]==value,"MANIFEST_MISMATCH_STOP: "+key
    print(json.dumps(dict(status="U5C_AUDIT_PASSED",inventory=len(finding["exact_u5c_inventory"]),hashed_artifacts=len(finding["artifact_sha256"]),
        unchanged_baseline_paths=3166,privacy="PASS",whitespace="PASS",production="BLOCKED")))


if __name__ == "__main__":main()
