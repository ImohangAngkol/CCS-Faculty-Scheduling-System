"""D10 compatibility gate evidence; no database credentials inherited by children."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import runpy

ROOT = Path(__file__).resolve().parents[3]
ZONE = timezone(timedelta(hours=8))
COMMANDS = {
    "lint-baseline": (["node", "node_modules/eslint/bin/eslint.js", "--stdin", "--stdin-filename", "src/pages/admin/ScheduleView.tsx"], ROOT / "frontend"),
    "v2-live": ([str(ROOT / ".venv/Scripts/python.exe"), "-B", "-m", "pytest", "-p", "no:cacheprovider",
        "tests/d10/test_v2_live.py", "-q", "-s", "--tb=short", "--show-capture=no"], ROOT / "backend"),
    "browser-regressions": (["node", "--test", "--test-concurrency=1", "tests/dashboardD1.browser.test.mjs", "tests/mySchedule.browser.test.mjs", "tests/externalSchedules.browser.test.mjs", "tests/externalReview.browser.test.mjs", "tests/externalHandoff.browser.test.mjs", "tests/externalLegacy.browser.test.mjs", "tests/externalReadiness.browser.test.mjs", "tests/externalEvidence.browser.test.mjs"], ROOT / "frontend"),
    "supported-v1": ([str(ROOT / ".venv/Scripts/python.exe"), "-B", "docs/testing/dashboard-d10/verify_supported_v1.py"], ROOT),
    "contracts": (["node", "--test", "tests/constrainedGA.test.mjs", "tests/externalConfirmations.test.mjs", "tests/externalEvidence.test.mjs", "tests/externalReadiness.test.mjs", "tests/externalLegacy.test.mjs", "tests/externalHandoff.test.mjs", "tests/externalReview.test.mjs", "tests/externalSchedules.test.mjs", "tests/mySchedule.test.mjs", "tests/dashboardD1.test.mjs", "tests/auth.test.mjs", "tests/authSessionRace.test.mjs", "tests/preferenceModel.test.mjs", "tests/preferenceApi.test.mjs", "tests/gaMonitoring.test.mjs", "tests/gaRecovery.test.mjs", "tests/gaLogs.test.mjs", "tests/gaHistory.test.mjs", "tests/fitnessReporting.test.mjs", "tests/facultyDisplay.test.mjs"], ROOT / "frontend"),
    "v2-browser": (["node", "--test", "tests/constrainedGA.browser.test.mjs"], ROOT / "frontend"),
    "ga-browser": (["node", "--test", "tests/gaMonitoring.browser.test.mjs"], ROOT / "frontend"),
    "v2-api": ([str(ROOT / ".venv/Scripts/python.exe"), "-B", "-m", "pytest",
        "-p", "no:cacheprovider", "tests/d10/test_v2_api.py", "-q", "--tb=short", "--show-capture=no"], ROOT / "backend"),
    "build": (["npm.cmd", "run", "build"], ROOT / "frontend"),
    "lint": (["node", "node_modules/eslint/bin/eslint.js", "src/api/constrainedGA.ts", "src/components/ga/ConstrainedRunPanel.tsx", "src/components/ga/ConstrainedResultPanel.tsx", "src/pages/admin/GenerateSchedule.tsx", "src/pages/admin/ScheduleView.tsx", "src/pages/admin/FitnessAnalysis.tsx"], ROOT / "frontend"),
    "v2-engine": ([str(ROOT / ".venv/Scripts/python.exe"), "-B", "-m", "pytest",
        "-p", "no:cacheprovider", "tests/d10/test_v2_engine.py", "-q", "--tb=short", "--show-capture=no"], ROOT / "backend"),
    "v1-fixtures": ([str(ROOT / ".venv/Scripts/python.exe"), "-B", "-m", "pytest",
        "-p", "no:cacheprovider", "tests/d10/test_v1_baseline.py", "-q", "--tb=short", "--show-capture=no"], ROOT / "backend"),
    "retained-v1": ([str(ROOT / ".venv/Scripts/python.exe"), "-B",
                     "docs/testing/dashboard-d10/check_retained_v1.py"], ROOT),
    "current-v1-continuation": ([str(ROOT / ".venv/Scripts/python.exe"), "-B", "-m", "pytest",
        "-p", "no:cacheprovider", "tests/test_ga_pause_resume.py::test_uninterrupted_and_json_restored_population_are_exactly_equivalent",
        "-q", "--tb=short"], ROOT / "backend"),
}
for key in ("backend", "backend-regressions", "ga-resource-regressions", "academic-offline", "live"):
    command,cwd=runpy.run_path(str(ROOT/"docs/testing/dashboard-d9/run_checks.py"))["COMMANDS"][key]
    COMMANDS[key]=(command,ROOT/cwd)

SCOPES={
    "retained-v1":"Unchanged V1 loader against owned historical copies; accepted pre-existing incompatibility, not continuation acceptance",
    "current-v1-continuation":"Existing bounded V1 pause/resume equivalence with controlled operator returns and actual checkpoint I/O",
    "v1-fixtures":"Fictional current-release V1 fixtures with original operators and actual checkpoint I/O/continuation",
    "supported-v1":"Actual pre-V2 supported V1 checkpoint copies, original operators and real continuation",
    "v2-engine":"Fictional V2 kernel, constraints and checkpoint tests; authority doubles are unit boundaries, not institutional verification",
    "v2-api":"Actual FastAPI ASGI auth and D8/D9 transactions against owned SQLite with fictional resources/providers; no browser or PostgreSQL",
    "v2-live":"Actual Edge to FastAPI HTTP/SQLite and real GA operators with entirely fictional resources/providers; no PostgreSQL or genuine authority",
    "v2-browser":"Actual Edge/React with synthetic HTTP replies; no live FastAPI authorization or GA execution",
    "browser-regressions":"Existing D1-D8 actual Edge/React regressions with synthetic HTTP replies",
    "ga-browser":"Existing GA actual Edge/React regressions with synthetic HTTP replies",
    "contracts":"Frontend API/model contracts, not rendered UI or live backend authorization",
    "backend":"Existing D2-D9 FastAPI/validation regressions using fictional fixtures and SQLite",
    "backend-regressions":"Existing auth and GA control regression fixtures, no production database",
    "ga-resource-regressions":"Original preassignment/reset/resource regression fixtures; current academic inputs read internally, never modified",
    "academic-offline":"Academic foundation offline tests only; no PostgreSQL cases selected",
    "live":"Existing D9 actual Edge/FastAPI HTTP/SQLite regressions with fictional providers; no PostgreSQL",
    "build":"Production frontend compilation/bundling, not browser or database acceptance",
    "lint":"Focused ESLint; existing warnings are retained without changing legacy page logic",
    "lint-baseline":"Read-only ESLint of the exact HEAD ScheduleView source via stdin, to classify existing warnings",
}


def main():
    key = sys.argv[1]
    command, cwd = COMMANDS[key]
    stamp = datetime.now(ZONE).strftime("%Y%m%dT%H%M%S%f+0800") + "-" + key
    evidence = ROOT / "docs/testing/dashboard-d10" / stamp
    evidence.mkdir(exist_ok=False)
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
        "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "HOMEDRIVE", "HOMEPATH", "PATHEXT", "NUMBER_OF_PROCESSORS",
        "OS", "SYSTEMDRIVE", "ALLUSERSPROFILE", "PUBLIC", "PROGRAMW6432", "PROCESSOR_ARCHITECTURE", "USERNAME", "USERDOMAIN"}
    child = {k:v for k,v in os.environ.items() if k.upper() in allowed}
    child.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if cwd == ROOT / "backend":
        owned = Path(tempfile.gettempdir()) / ("d10-compat-pytest-" + stamp)
        if owned.exists():
            raise RuntimeError("Refusing to reuse a pytest temporary root")
        command = [*command, "--basetemp", str(owned)]
    if key == "v1-fixtures":
        child["D10_V1_BASELINE_RECORD"] = str(evidence)
    if key in {"v2-browser","v2-live"}:
        child["D10_SCREENSHOT_DIR"] = str(ROOT / "docs/screenshots/dashboard-d10" / stamp)
    started, tick = datetime.now(ZONE).isoformat(), time.monotonic()
    standard_input=None
    if key=="lint-baseline":
        standard_input=subprocess.check_output(["git","show","HEAD:frontend/src/pages/admin/ScheduleView.tsx"],cwd=ROOT).decode("utf-8")
    result = subprocess.run(command, cwd=cwd, env=child, input=standard_input,capture_output=True, text=True, encoding="utf-8", errors="replace")
    sys.path.insert(0, str(ROOT / "backend"))
    from services.evidence_sanitization import sanitize_tree
    record = sanitize_tree({"check": key, "command": command, "cwd": str(cwd.relative_to(ROOT)),
        "started_at": started, "finished_at": datetime.now(ZONE).isoformat(),
        "elapsed_seconds": round(time.monotonic()-tick, 3), "exit_code": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr,
        "environment": "Whitelisted OS variables only; no database URLs, credentials or approval flags",
        "scope": SCOPES[key],
        "stdin_source":"git show HEAD:frontend/src/pages/admin/ScheduleView.tsx" if key=="lint-baseline" else None,
        "sanitization": "Complete/truncated session artifacts, sensitive assignments, headers, keys and credential URIs sanitized before writing"})
    (evidence / "command.json").write_text(json.dumps(record, indent=2, ensure_ascii=True)+"\n", encoding="utf-8")
    print(json.dumps({"evidence": evidence.relative_to(ROOT).as_posix(), "exit_code": result.returncode,
                      "stdout_tail": record["stdout"][-3000:], "stderr_tail": record["stderr"][-1000:]}, ensure_ascii=True))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
