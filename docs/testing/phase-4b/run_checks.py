"""Run named isolated checks and store timestamped, sanitized evidence.

Run from the repository root using its virtualenv Python. The PostgreSQL group
is opt-in and delegates all database safety checks to the acceptance fixture.
"""
import argparse
from datetime import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GA_SUITES = ["test_ga_monitoring", "test_ga_safe_stop", "test_ga_refresh_recovery",
             "test_ga_pause_resume", "test_ga_paused_recovery", "test_ga_control_conflicts",
             "test_ga_logs", "test_ga_unicode_diagnostics", "test_ga_generation_history",
             "test_ga_history_checkpoint_recovery"]


def main():
    # Evidence output must not fail on Windows cp1252 checkmarks, as the first
    # frontend collection attempt did. JSON artifacts always use UTF-8 bytes.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=["admission", "postgresql", "browser-offline", "auth", "ga", "domain", "frontend-auth", "frontend-preferences", "frontend-ga", "build", "lint"])
    args = parser.parse_args()
    run_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z") + "-" + args.group + "-" + uuid4().hex[:8]
    temporary = str(Path(tempfile.gettempdir()) / ("phase4b-" + run_id))
    selection = {
        "admission": ["backend/tests/test_ga_input_validation.py", "backend/tests/test_phase4b_database_safety.py", "backend/tests/test_phase4b_browser_fixture.py"],
        "postgresql": ["backend/tests/test_phase4b_postgresql.py"],
        "browser-offline": ["backend/tests/test_phase4b_database_safety.py", "backend/tests/test_phase4b_browser_safety.py",
                            "backend/tests/test_phase4b_browser_fixture.py", "backend/tests/test_phase4b_browser_evidence.py",
                            "backend/tests/test_phase4b_browser_recovery.py"],
        "auth": ["backend/tests/test_phase4a_auth.py", "backend/tests/test_phase4a_final_verification.py", "-k", "not real_browser"],
        "ga": [*[f"backend/tests/{name}.py" for name in GA_SUITES], "-k", "not browser"],
        "domain": [f"backend/tests/{name}.py" for name in ["test_tournament_selection", "test_preassigned_assignments", "test_ga_hard_constraints", "test_ga_api_crossover", "test_preference_toggles", "test_preference_integrity", "test_preference_validation", "test_metadata_api", "test_fitness_reporting"]],
    }
    cwd = ROOT
    if args.group in selection:
        command = [sys.executable, "-m", "pytest", *selection[args.group], "-q", "-p", "no:cacheprovider",
                   "--disable-warnings", "--tb=short", "--maxfail=2", "--basetemp=" + temporary]
    else:
        cwd = ROOT / "frontend"
        scripts = {"frontend-auth": "test:auth", "frontend-preferences": "test:preferences", "frontend-ga": "test:ga", "build": "build"}
        if args.group == "lint":
            command = ["cmd", "/d", "/c", "node_modules\\.bin\\eslint.cmd", "src/services/auth.ts", "src/services/apiSession.ts",
                       "src/context/AuthContext.tsx", "src/routes/ProtectedRoute.tsx", "src/pages/admin/Accounts.tsx"]
        else:
            command = ["cmd", "/d", "/c", "npm.cmd", "run", scripts[args.group]]
    started = datetime.now().astimezone().isoformat()
    clock = time.monotonic()
    print(f"Running {args.group}; recording sanitized evidence as {run_id}.json", flush=True)
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    output = result.stdout + result.stderr
    # Withhold the complete URL even if a future library unexpectedly emits it.
    private_urls = [os.environ.get(name) for name in ("PHASE4B_TEST_DATABASE_URL", "PHASE4B_BROWSER_DATABASE_URL")]
    for private_url in filter(None, private_urls):
        from urllib.parse import unquote, urlsplit
        try:
            password = urlsplit(private_url).password
        except ValueError:
            password = None
        for private in (private_url, password, unquote(password) if password else None):
            if private: output = output.replace(private, "[PRIVATE VALUE WITHHELD]")
    output = re.sub(r"postgres(?:ql)?(?:\+\w+)?://[^\s\"']+", "[DATABASE URL WITHHELD]", output)
    record = {"run_id": run_id, "group": args.group, "started_at": started,
              "ended_at": datetime.now().astimezone().isoformat(), "elapsed_seconds": round(time.monotonic() - clock, 3),
              "cwd": str(cwd.relative_to(ROOT)) if cwd != ROOT else "repository root",
              "command": command, "exit_code": result.returncode, "python": platform.python_version(),
              "packages": {name: importlib.metadata.version(name) for name in ["pytest", "SQLAlchemy", "fastapi", "alembic", "psycopg2-binary"]},
              "phase4b_test_url_present": bool(private_urls[0]),
              "phase4b_browser_url_present": bool(private_urls[1]), "output": output}
    (HERE / (run_id + ".json")).write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(output, end="")
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
