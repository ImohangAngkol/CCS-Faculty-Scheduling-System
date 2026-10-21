"""D5 isolated checks. No PostgreSQL environment, provisioning or migrations."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
ZONE = timezone(timedelta(hours=8))
CONTRACTS = ["externalHandoff", "externalReview", "externalSchedules", "mySchedule", "dashboardD1", "auth", "authSessionRace", "preferenceModel", "preferenceApi", "gaMonitoring", "gaRecovery", "gaLogs", "gaHistory", "fitnessReporting", "facultyDisplay"]
PYTHON = str(ROOT / ".venv/Scripts/python.exe")
COMMANDS = {
    "backend": ([PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "tests/dashboard/test_external_handoff.py", "tests/dashboard/test_external_review.py", "tests/dashboard/test_external_preview.py", "tests/dashboard/test_my_schedule.py", "-q", "--tb=short"], "backend"),
    "backend-regressions": ([PYTHON, "-B", "-m", "pytest", "-p", "no:cacheprovider", "tests/test_phase4a_auth.py", "tests/test_ga_control_conflicts.py", "-q", "--tb=short"], "backend"),
    "contracts": (["node", "--test", *(f"tests/{name}.test.mjs" for name in CONTRACTS)], "frontend"),
    "build": (["npm.cmd", "run", "build"], "frontend"),
    "lint": (["node", "node_modules/eslint/bin/eslint.js", "src/components/schedule/ExternalScheduleHandoff.tsx", "src/api/externalSchedules.ts", "src/pages/admin/ExternalSchedules.tsx", "src/components/schedule/ExternalScheduleReview.tsx", "src/components/schedule/externalReviewModel.ts"], "frontend"),
    "browser": (["node", "--test", "tests/externalHandoff.browser.test.mjs"], "frontend"),
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
    evidence = ROOT / "docs/testing/dashboard-d5" / run
    evidence.mkdir(parents=True, exist_ok=False)
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA", "HOMEDRIVE", "HOMEPATH", "PATHEXT", "NUMBER_OF_PROCESSORS", "OS", "SYSTEMDRIVE", "ALLUSERSPROFILE", "PUBLIC", "PROGRAMW6432", "PROCESSOR_ARCHITECTURE", "USERNAME", "USERDOMAIN", "SESSIONNAME"}
    child = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    if args.check == "browser":
        child["D5_SCREENSHOT_DIR"] = str(ROOT / "docs/screenshots/dashboard-d5" / run)
    command, cwd = COMMANDS[args.check]
    if args.check == "backend-regressions":
        # A unique, previously absent pytest root avoids ACL/ownership conflicts
        # with earlier sandbox-created pytest directories. Never reuse a root.
        owned_temp = Path(tempfile.gettempdir()) / ("dashboard-d5-" + run)
        if owned_temp.exists():
            raise RuntimeError("Refusing an existing regression temporary root")
        command = [*command, "--basetemp", str(owned_temp)]
    started = datetime.now(ZONE).isoformat(); tick = time.monotonic()
    result = subprocess.run(command, cwd=ROOT / cwd, env=child, capture_output=True, text=True, encoding="utf-8", errors="replace")
    record = {"check": args.check, "command": command, "cwd": cwd,
              "started_at": started, "finished_at": datetime.now(ZONE).isoformat(),
              "elapsed_seconds": round(time.monotonic()-tick, 3), "exit_code": result.returncode,
              "stdout": result.stdout, "stderr": result.stderr,
              "environment": "Whitelisted OS environment; no DB URLs, approval flags or credential variables",
              "scope": "Real FastAPI ASGI auth with isolated SQLite/synthetic resources" if args.check == "backend" else "See report for fixture and regression scope"}
    (evidence / "command.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"evidence": evidence.relative_to(ROOT).as_posix(), **record}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
