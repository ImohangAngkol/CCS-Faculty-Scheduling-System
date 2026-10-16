"""Temporary Phase 4A evidence server; never a production startup command.

Reuses the existing real-authentication fixture. Readiness credentials are written
only to an explicitly selected, new OS-temp handoff; never to docs or stdout.
No GA is run. Browser/UI actions are performed separately against this fixture.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path, required=True)
    args = parser.parse_args()
    ready = args.ready_file.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if (not ready.is_relative_to(temp_root) or ready.exists()
            or not ready.name.startswith("phase4a-evidence-")):
        raise ValueError("Use a new phase4a-evidence-* handoff under the OS temporary directory.")
    stop = ready.with_suffix(".stop")
    if stop.exists():
        raise ValueError("Refusing to reuse an existing stop marker.")

    import pytest
    import uvicorn
    from main import app
    from routers import faculty as faculty_router
    from schemas.faculty import FacultyMetadata
    from services import identity_service, ga_checkpoint_service, ga_history_service
    from services import chromosome_service, ga_control_service
    import importlib
    ga_router = importlib.import_module("routers.genetic_algorithm")
    import identity_admin

    spec = importlib.util.spec_from_file_location(
        "phase4a_existing_auth_fixture", ROOT / "backend/tests/test_phase4a_auth.py")
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    # Keep the established UUID/code adapter, but never expose original names.
    synthetic = tuple(replace(row, name=f"Synthetic Faculty {row.faculty_code}", aliases=())
                      for row in identity_service.load_faculty_identities())
    with tempfile.TemporaryDirectory(prefix="phase4a-evidence-storage-", dir=ready.parent) as folder, pytest.MonkeyPatch.context() as patch:
        storage = Path(folder)
        for module in (identity_service, identity_admin, tests):
            patch.setattr(module, "load_faculty_identities", lambda: synthetic)
        patch.setattr(ga_checkpoint_service, "CHECKPOINTS_DIR", storage / "checkpoints")
        patch.setattr(ga_history_service, "SNAPSHOTS_DIR", storage / "history")
        patch.setattr(ga_control_service, "STOPPED_RUNS_DIR", storage / "stopped")
        patch.setattr(ga_router, "LATEST_RESULT_FILE", storage / "latest.json")
        patch.setattr(chromosome_service, "SAVED_CHROMOSOME_DIR", storage / "saved")
        patch.setattr(chromosome_service, "BEST_CHROMOSOME_PATH", storage / "saved/best.json")
        patch.setattr(chromosome_service, "UPLOADED_CHROMOSOME_PATH", storage / "saved/uploaded.json")
        # Privacy-specific metadata fixture: no original academic profile or
        # faculty/course eligibility relationship is displayed or exported.
        def synthetic_metadata(faculty):
            code = faculty.code
            identity = next(row for row in synthetic if row.faculty_code == code)
            return FacultyMetadata(
                faculty_id=identity.faculty_id, faculty_code=code,
                display_code=f"Faculty {code}", name=identity.name,
                seniority_level=1, admin_load=0, research_load=0, extension_load=0,
                current_teaching_load=0, required_teaching_load=24,
                absolute_max_teaching_load=40, specializations=[], eligible_subject_codes=[])
        patch.setattr(faculty_router, "faculty_metadata", synthetic_metadata)
        patch.setattr(faculty_router, "list_faculty_metadata", lambda: [
            synthetic_metadata(faculty_router._resolve_faculty(row.faculty_code)) for row in synthetic])
        patch.setattr(faculty_router, "list_subject_metadata", lambda *_args, **_kwargs: [])
        fixture = tests.identity_app.__wrapped__(storage, patch)
        server = thread = None
        fixture_yielded = False
        try:
            _client, _engine, password, _tmp = next(fixture)
            fixture_yielded = True
            from fastapi.middleware.cors import CORSMiddleware
            for middleware in app.user_middleware:
                if middleware.cls is CORSMiddleware:
                    patch.setitem(middleware.kwargs, "allow_origins", ["http://localhost:5189"])
            patch.setenv("AUTH_ALLOWED_ORIGINS", "http://localhost:5189")
            patch.setattr(app, "middleware_stack", None)
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(
                app, host="127.0.0.1", port=port, access_log=False, log_level="error", lifespan="off"))
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            deadline = time.monotonic() + 15
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("Isolated evidence server did not start.")
                time.sleep(0.05)
            with ready.open("x", encoding="utf-8") as handle:
                os.chmod(ready, 0o600)
                json.dump({"backend": f"http://localhost:{port}", "password": password}, handle)
            print("Isolated evidence server ready; temporary credentials withheld.", flush=True)
            deadline = time.monotonic() + 1800
            while not stop.exists() and time.monotonic() < deadline and thread.is_alive():
                time.sleep(0.2)
        finally:
            if server:
                server.should_exit = True
            if thread:
                thread.join(timeout=15)
                if thread.is_alive():
                    raise RuntimeError("Evidence server did not stop; temporary storage retained by process.")
            # Pytest resumes yield fixtures normally so post-yield disposal runs.
            # Generator.close() would skip the original engine.dispose() line,
            # leaving Windows SQLite handles open during TemporaryDirectory cleanup.
            if fixture_yielded:
                try:
                    next(fixture)
                except StopIteration:
                    pass
            else:
                fixture.close()
            ready.unlink(missing_ok=True)
            stop.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
