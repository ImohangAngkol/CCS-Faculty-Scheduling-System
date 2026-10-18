"""Owned browser-only loopback fixture. Stage B approval is required to initialize.

Import is inert. The original PostgreSQL acceptance database is never selected.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import secrets
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))


def reserve_listener():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        listener.set_inheritable(False)
        return listener
    except Exception:
        listener.close()
        raise


def wait_for_stop(stop, thread, lifetime_seconds):
    deadline = time.monotonic() + lifetime_seconds
    warned = set()
    while True:
        if stop.exists(): return "requested_stop"
        if not thread.is_alive():
            raise RuntimeError("Owned browser worker exited unexpectedly")
        remaining = deadline - time.monotonic()
        if remaining <= 0: return "deadline"
        for threshold in (600, 300, 60):
            if remaining <= threshold and threshold not in warned and lifetime_seconds > threshold:
                print(f"Owned browser fixture: at most {threshold // 60} minutes remaining.", flush=True)
                warned.add(threshold)
        time.sleep(min(0.2, remaining))


def write_handoff(ready, values):
    if ready.exists() or ready.is_symlink():
        raise FileExistsError("Refusing existing private handoff")
    pending = ready.with_suffix(".pending")
    with pending.open("x", encoding="utf-8") as handoff:
        json.dump(values, handoff)
    pending.rename(ready)  # private, complete handoff; Windows refuses overwrite


def abort_owned_process():
    # A daemon worker must not outlive ownership of its database. Terminate
    # this fixture process only, before unwinding/releasing the session lock.
    # Keep ACL-protected artifacts for review rather than deleting underneath it.
    print("BLOCKED: owned worker did not stop; terminating this fixture process only; private artifacts retained.", flush=True)
    os._exit(2)


def run_fixture(ready, *, allow_initialization=False, allow_recovery=False, lifetime_seconds=1800):
    from tests.phase4b_database_safety import SafetyError
    from tests.phase4b_browser_safety import designated_browser_url, inspect_empty_browser_database
    from tests import phase4b_browser_support as support
    from tests import phase4b_browser_recovery as recovery

    if allow_initialization == allow_recovery:
        raise SafetyError("Stage B approval requires exactly one initialization or recovery flag.")
    if type(lifetime_seconds) is not int or not 60 <= lifetime_seconds <= 14400:
        raise SafetyError("Browser lifetime must be 60 through 14400 seconds; default is 1800.")
    url = designated_browser_url()  # no old test/application URL fallback
    ready = support.validate_ready_path(ready)
    root = ready.parent
    stop, unavailable = ready.with_suffix(".stop"), ready.with_suffix(".unavailable")
    owned_root = False
    listener = server = thread = engine = None
    stage = "private_storage"
    try:
        # Bind our own socket before DB changes. No process/service is stopped.
        listener = reserve_listener()
        root.mkdir(exist_ok=False)
        owned_root = True
        support.secure_private_directory(root)
        stage = "database_preflight"
        if not allow_recovery:
            inspect_empty_browser_database(url)
        from sqlalchemy import create_engine
        engine = create_engine(url, hide_parameters=True, connect_args={
            "connect_timeout": 5, "options": "-c statement_timeout=5000 -c lock_timeout=5000"})
        with recovery.claim_browser_database(url) as owned_db:
            if allow_recovery:
                recovery.verify_recovery(owned_db)
                owned_db.rollback()
            stage = "storage_isolation"
            with support.isolated_application(root / "storage", engine, unavailable=unavailable) as state:
                support.assert_storage_isolated(state["root"])
                if allow_recovery:
                    stage = "recovery_revalidation_and_rotation"
                    password = secrets.token_urlsafe(24)
                    name = recovery.rotate_browser_administrator(owned_db, password, approved=True)
                else:
                    stage = "approved_empty_initialization"
                    support.migrate_browser_database(url, approved=True)
                    password = secrets.token_urlsafe(24)
                    name = support.seed_browser_accounts(engine, password)
                import uvicorn
                stage = "owned_server_startup"
                server = uvicorn.Server(uvicorn.Config(
                    state["app"], host="127.0.0.1", port=listener.getsockname()[1],
                    access_log=False, log_level="critical", lifespan="off", log_config=None))
                thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
                try:
                    thread.start()
                    deadline = time.monotonic() + 15
                    while not server.started:
                        if not thread.is_alive() or time.monotonic() >= deadline:
                            raise SafetyError("Owned browser server did not start; synthetic DB retained for review.")
                        time.sleep(0.05)
                    stage = "private_handoff"
                    write_handoff(ready, {"backend": f"http://localhost:{listener.getsockname()[1]}",
                                         "username": name, "password": password,
                                         "instance_id": state["instance_id"], "database": recovery.BROWSER_DATABASE})
                    print("Owned synthetic browser fixture ready; private handoff withheld.", flush=True)
                    print(f"Owned browser fixture lifetime: {lifetime_seconds // 60} minutes; no automatic extension.", flush=True)
                    expires = datetime.now(timezone.utc) + timedelta(seconds=lifetime_seconds)
                    print(f"Owned browser fixture window ends at {expires.isoformat()}.", flush=True)
                    stage = "serving"
                    reason = wait_for_stop(stop, thread, lifetime_seconds)
                    print(f"Owned browser fixture stopping; reason={reason}.", flush=True)
                finally:
                    server.should_exit = True
                    thread.join(timeout=20)
                    if thread.is_alive():
                        abort_owned_process()
    except Exception:
        print(f"Owned browser fixture failed; stage={stage}; private details withheld.", flush=True)
        raise
    finally:
        if server:
            server.should_exit = True
        if thread and thread.is_alive():
            thread.join(timeout=20)
        if thread and thread.is_alive():
            # Never dispose resources beneath a still-running owned thread.
            # The CLI exits its own daemon-thread process, not another service.
            raise SafetyError("Owned server still active; private resources retained.")
        if engine:
            engine.dispose()
        if listener:
            listener.close()
        if owned_root:
            # Remove only private handoff/control files, also after setup errors.
            # Never recursively delete storage, a database or another service.
            for marker in (ready, ready.with_suffix(".pending"), stop, unavailable):
                if marker.is_symlink():
                    raise SafetyError("Unexpected marker link; retained for review.")
                marker.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--allow-browser-database-initialization", action="store_true")
    mode.add_argument("--allow-browser-database-recovery", action="store_true")
    parser.add_argument("--lifetime-seconds", type=int, default=1800)
    args = parser.parse_args()
    try:
        run_fixture(args.ready_file, allow_initialization=args.allow_browser_database_initialization,
                    allow_recovery=args.allow_browser_database_recovery, lifetime_seconds=args.lifetime_seconds)
    except Exception:
        # No exception/SQL/credential echo. Specific read-only preflight is separate.
        print("BLOCKED: browser fixture approval, target, isolation or startup checks failed; private details withheld.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
