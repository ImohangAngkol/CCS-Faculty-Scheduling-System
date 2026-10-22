"""D8 isolated checks. No PostgreSQL environment, provisioning or migrations."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import re
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
ZONE = timezone(timedelta(hours=8))
CONTRACTS = ["externalEvidence", "externalReadiness", "externalLegacy", "externalHandoff", "externalReview", "externalSchedules", "mySchedule", "dashboardD1", "auth", "authSessionRace", "preferenceModel", "preferenceApi", "gaMonitoring", "gaRecovery", "gaLogs", "gaHistory", "fitnessReporting", "facultyDisplay"]
PYTHON = str(ROOT / ".venv/Scripts/python.exe")
COMMANDS = {
    "live": ([PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "tests/dashboard/test_external_evidence_live.py", "-q", "-s", "--tb=short"], "backend"),
    "ga-resource-regressions": ([PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "tests/test_preassigned_assignments.py::test_reset_and_rollback_preserve_declarations", "tests/test_preassigned_assignments.py::test_room_and_section_conflicts_apply", "tests/test_preassigned_assignments.py::test_external_overlap_and_future_preassignment", "-q", "--tb=short"], "backend"),
    "backend": ([PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "tests/dashboard/test_external_evidence.py", "tests/dashboard/test_external_readiness.py", "tests/dashboard/test_external_legacy.py", "tests/dashboard/test_external_handoff.py", "tests/dashboard/test_external_review.py", "tests/dashboard/test_external_preview.py", "tests/dashboard/test_my_schedule.py", "-q", "--tb=short"], "backend"),
    "backend-regressions": ([PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "tests/test_phase4a_auth.py", "tests/test_ga_control_conflicts.py", "-q", "--tb=short"], "backend"),
    "contracts": (["node", "--test", *(f"tests/{name}.test.mjs" for name in CONTRACTS)], "frontend"),
    "build": (["npm.cmd", "run", "build"], "frontend"),
    "lint": (["node", "node_modules/eslint/bin/eslint.js", "src/api/externalEvidence.ts", "src/components/schedule/ExternalEvidencePanel.tsx", "src/api/externalReadiness.ts", "src/components/schedule/ExternalScheduleReadiness.tsx", "src/components/schedule/ReadinessDocument.tsx", "src/components/schedule/LegacyScheduleProvenance.tsx", "src/components/schedule/ExternalScheduleHandoff.tsx", "src/api/externalSchedules.ts", "src/pages/admin/ExternalSchedules.tsx", "src/components/schedule/ExternalScheduleReview.tsx", "src/components/schedule/externalReviewModel.ts"], "frontend"),
    "d5-browser": (["node", "--test", "tests/externalHandoff.browser.test.mjs"], "frontend"),
    "d6-browser": (["node", "--test", "tests/externalLegacy.browser.test.mjs"], "frontend"),
    "browser": (["node", "--test", "tests/externalEvidence.browser.test.mjs"], "frontend"),
    "d7-browser": (["node", "--test", "tests/externalReadiness.browser.test.mjs"], "frontend"),
    "d4-browser": (["node", "--test", "tests/externalReview.browser.test.mjs"], "frontend"),
    "d3-browser": (["node", "--test", "tests/externalSchedules.browser.test.mjs"], "frontend"),
    "d2-browser": (["node", "--test", "tests/mySchedule.browser.test.mjs"], "frontend"),
    "d1-browser": (["node", "--test", "tests/dashboardD1.browser.test.mjs"], "frontend"),
    "ga-browser": (["node", "--test", "tests/gaMonitoring.browser.test.mjs"], "frontend"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=COMMANDS)
    args = parser.parse_args()
    run = datetime.now(ZONE).strftime("%Y%m%dT%H%M%S%f+0800") + "-" + args.check
    evidence = ROOT / "docs/testing/dashboard-d8" / run
    evidence.mkdir(parents=True, exist_ok=False)
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "HOMEDRIVE", "HOMEPATH", "PATHEXT", "NUMBER_OF_PROCESSORS", "OS", "SYSTEMDRIVE", "ALLUSERSPROFILE", "PUBLIC", "PROGRAMW6432", "PROCESSOR_ARCHITECTURE", "USERNAME", "USERDOMAIN", "SESSIONNAME"}
    child = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    child["PYTHONIOENCODING"] = "utf-8"
    child["PYTHONUTF8"] = "1"
    if args.check in {"browser", "live"}:
        child["D8_SCREENSHOT_DIR"] = str(ROOT / "docs/screenshots/dashboard-d8" / run)
    command, cwd = COMMANDS[args.check]
    if args.check in {"backend", "backend-regressions", "ga-resource-regressions", "live"}:
        # A unique, previously absent pytest root avoids ACL/ownership conflicts
        # with earlier sandbox-created pytest directories. Never reuse a root.
        owned_temp = Path(tempfile.gettempdir()) / ("dashboard-d8-" + run)
        if owned_temp.exists():
            raise RuntimeError("Refusing an existing regression temporary root")
        command = [*command, "--basetemp", str(owned_temp)]
    started = datetime.now(ZONE).isoformat(); tick = time.monotonic()
    result = subprocess.run(command, cwd=ROOT / cwd, env=child, capture_output=True, text=True, encoding="utf-8", errors="replace")
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from services.evidence_sanitization import sanitize, sanitize_tree
    record = {"check": args.check, "command": command, "cwd": cwd,
              "started_at": started, "finished_at": datetime.now(ZONE).isoformat(),
              "elapsed_seconds": round(time.monotonic()-tick, 3), "exit_code": result.returncode,
              "stdout": sanitize(result.stdout), "stderr": sanitize(result.stderr),
              "sanitization": "D8 whole sensitive-line, complete/truncated encoded fragment, header, key and credential-URI sanitization applied before evidence writes and summaries",
              "environment": "Whitelisted OS environment; no DB URLs, approval flags or credential variables",
              "scope": "Real FastAPI ASGI auth with isolated SQLite/synthetic resources" if args.check == "backend" else "See report for fixture and regression scope"}
    (evidence / "command.json").write_text(json.dumps(sanitize_tree(record), indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"evidence": evidence.relative_to(ROOT).as_posix(), "exit_code": result.returncode, "summary": sanitize(result.stdout)[-1200:], "stderr_tail": sanitize(result.stderr)[-600:]}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
