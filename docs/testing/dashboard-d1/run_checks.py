"""Record safe frontend checks only. Never imports application Python or reads .env.

Browser checks use synthetic responses and owned temporary profiles. No PostgreSQL
or backend service is started. Each invocation retains a new command artifact.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[3]
ZONE = timezone(timedelta(hours=8))
CONTRACTS = ["dashboardD1", "auth", "authSessionRace", "preferenceModel", "preferenceApi",
             "gaMonitoring", "gaRecovery", "gaLogs", "gaHistory", "fitnessReporting", "facultyDisplay"]
LINT = ["src/api/faculty.ts", "src/api/subjects.ts", "src/services/dashboardMetadata.ts",
        "src/components/dashboard/MetadataState.tsx", "src/pages/admin/SubjectManagement.tsx",
        "src/pages/faculty/Dashboard.tsx", "src/pages/faculty/Profile.tsx", "src/routes/AppRoutes.tsx",
        "src/layouts/FacultyLayout.tsx", "src/layouts/AdminLayout.tsx",
        "src/components/common/Sidebar.tsx", "src/components/common/Topbar.tsx"]
COMMANDS = {
    "contracts": ["node", "--test", *(f"tests/{name}.test.mjs" for name in CONTRACTS)],
    "build": ["npm.cmd", "run", "build"],
    "lint": ["node", "node_modules/eslint/bin/eslint.js", *LINT],
    "browser": ["node", "--test", "tests/dashboardD1.browser.test.mjs"],
    "ga-browser": ["node", "--test", "tests/gaMonitoring.browser.test.mjs"],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=COMMANDS)
    args = parser.parse_args()
    run = datetime.now(ZONE).strftime("%Y%m%dT%H%M%S%f+0800") + "-" + args.check
    evidence = ROOT / "docs/testing/dashboard-d1" / run
    evidence.mkdir(parents=True, exist_ok=False)
    # Only OS/runtime essentials are inherited; no DB URLs, approval flags, API
    # overrides, handoffs or credential environment reaches these child tests.
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE",
               "APPDATA", "LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA",
               "HOMEDRIVE", "HOMEPATH", "PATHEXT", "NUMBER_OF_PROCESSORS", "OS", "SYSTEMDRIVE",
               "ALLUSERSPROFILE", "PUBLIC", "PROGRAMW6432", "PROCESSOR_ARCHITECTURE", "USERNAME",
               "USERDOMAIN", "SESSIONNAME"}
    child = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    screenshots = ROOT / "docs/screenshots/dashboard-d1" / run
    if args.check == "browser":
        child["D1_SCREENSHOT_DIR"] = str(screenshots)
    started = datetime.now(ZONE).isoformat()
    tick = time.monotonic()
    result = subprocess.run(COMMANDS[args.check], cwd=ROOT / "frontend", env=child,
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    record = {"check": args.check, "command": COMMANDS[args.check], "cwd": "frontend",
              "started_at": started, "finished_at": datetime.now(ZONE).isoformat(),
              "elapsed_seconds": round(time.monotonic() - tick, 3), "exit_code": result.returncode,
              "stdout": result.stdout, "stderr": result.stderr,
              "environment": "Whitelisted OS environment; no database/approval/API credential variables",
              "browser_scope": "Synthetic API responses; actual React browser rendering; no FastAPI/PostgreSQL" if "browser" in args.check else None}
    (evidence / "command.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": evidence.relative_to(ROOT).as_posix(),
                      "screenshots": screenshots.relative_to(ROOT).as_posix() if screenshots.exists() else None,
                      **record}))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
