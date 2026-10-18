"""Test-only browser application isolation. No DB/server action at import time."""
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import UUID, uuid4, uuid5

from tests.phase4b_database_safety import SafetyError

ORIGIN = "http://localhost:5189"
NAMESPACE = UUID("3941ef71-857f-49a6-9e8d-7344b93f8404")


@dataclass(frozen=True)
class SyntheticFaculty:
    code: int
    stable_id: str
    seniority_level: int = 1
    admin_load: int = 0
    research_load: int = 0
    extension_load: int = 0
    current_teaching_load: int = 0
    required_teaching_load: int = 24
    absolute_max_teaching_load: int = 40
    overload_warning_threshold: int = 30
    specializations: tuple = ()
    eligible_subjects: frozenset = frozenset()
    is_external: bool = False


def synthetic_identities():
    from services.identity_service import FacultyIdentity
    return tuple(FacultyIdentity(str(uuid5(NAMESPACE, str(code))), code,
                                f"Browser Faculty {code}", f"Browser Synthetic Faculty {code}")
                 for code in (0, 1))


def storage_bindings():
    """Single inventory for read/write aliases, also asserted by offline tests."""
    import importlib
    from routers import preferences, chromosomes
    from services import ga_service, ga_checkpoint_service, ga_history_service
    from services import ga_control_service, chromosome_service
    from genetic_algorithm.operators import FitnessFunction
    ga_router = importlib.import_module("routers.genetic_algorithm")
    return (
        (preferences, "PREFERENCE_FILE", "preferences.json"),
        (preferences, "GA_SETTINGS_FILE", "settings.json"),
        (ga_service, "FACULTY_PREFERENCES_FILE", "preferences.json"),
        (ga_service, "GA_SETTINGS_FILE", "settings.json"),
        (FitnessFunction, "PREFERENCE_FILE", "preferences.json"),
        (FitnessFunction, "GA_SETTINGS_FILE", "settings.json"),
        (ga_checkpoint_service, "CHECKPOINTS_DIR", "checkpoints"),
        (ga_history_service, "SNAPSHOTS_DIR", "history"),
        (ga_control_service, "STOPPED_RUNS_DIR", "stopped"),
        (ga_router, "LATEST_RESULT_FILE", "latest.json"),
        (chromosomes, "LATEST_RESULT_FILE", "latest.json"),
        (chromosome_service, "SAVED_CHROMOSOME_DIR", "saved"),
        (chromosome_service, "BEST_CHROMOSOME_PATH", "saved/best.json"),
        (chromosome_service, "UPLOADED_CHROMOSOME_PATH", "saved/uploaded.json"),
    )


def no_ga(*_args, **_kwargs):
    from fastapi import HTTPException
    raise HTTPException(409, "GA execution and resume are disabled in this isolated browser fixture.")


def assert_storage_isolated(root):
    root = Path(root).resolve()
    for module, attribute, relative in storage_bindings():
        target = Path(getattr(module, attribute)).resolve()
        if target != root / relative or not target.is_relative_to(root):
            raise SafetyError("Browser storage isolation failed; no startup or migration permitted.")


@contextmanager
def isolated_application(root, engine, *, unavailable=None):
    """Storage/engine overrides only: genuine auth, role, CSRF and ownership checks.

    Offline tests supply an isolated SQLite engine, explicitly not PG evidence.
    The executable helper supplies only its independently verified browser engine.
    """
    import importlib
    import pytest
    from fastapi import HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import database
    import identity_admin
    from main import app
    from services import auth_service as auth, identity_service, metadata_service
    from services.ga_control_service import RunRegistry

    root = Path(root).resolve()
    if root == Path(tempfile.gettempdir()).resolve() or not root.is_relative_to(Path(tempfile.gettempdir()).resolve()):
        raise SafetyError("Browser application storage must be inside owned OS-temporary storage.")
    root.mkdir(parents=True, exist_ok=True)
    unavailable = Path(unavailable).resolve() if unavailable else root / "unavailable"
    if not unavailable.is_relative_to(root.parent):
        raise SafetyError("Fault marker must belong to the private fixture directory.")
    identities = synthetic_identities()
    ga_router = importlib.import_module("routers.genetic_algorithm")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(identity_service, "load_faculty_identities", lambda: identities)
        patch.setattr(identity_admin, "load_faculty_identities", lambda: identities)
        patch.setattr(metadata_service.scheduling, "list_faculty", [
            SyntheticFaculty(row.faculty_code, row.faculty_id) for row in identities])
        patch.setattr(metadata_service.scheduling, "list_subjects", [])
        for module, attribute, relative in storage_bindings():
            patch.setattr(module, attribute, root / relative)
        for attribute in ("_admit_execution", "_launch_resume", "generate_schedule", "run_genetic_algorithm"):
            patch.setattr(ga_router, attribute, no_ga)
        from services import ga_service
        patch.setattr(ga_service, "generate_schedule", no_ga)
        patch.setattr(ga_service, "run_genetic_algorithm", no_ga)
        patch.setattr(ga_router, "_run_registry", RunRegistry())
        patch.setattr(database, "identity_engine", lambda: engine)
        patch.setattr(identity_admin, "identity_engine", lambda: engine)

        def isolated_db():
            if unavailable.exists():
                raise HTTPException(503, "Isolated browser identity database unavailable (injected acceptance fault).")
            yield from database.get_identity_db()

        patch.setattr(app, "dependency_overrides", {
            database.get_identity_db: isolated_db, auth.authenticated_db: isolated_db})
        patch.setattr(auth, "LOGIN_LIMITER", auth.LoginLimiter())
        patch.setenv("AUTH_COOKIE_SECURE", "false")
        patch.setenv("AUTH_ALLOWED_ORIGINS", ORIGIN)
        for middleware in app.user_middleware:
            if middleware.cls is CORSMiddleware:
                patch.setitem(middleware.kwargs, "allow_origins", [ORIGIN])
        patch.setattr(app, "middleware_stack", None)
        patch.setattr(app.router, "routes", list(app.router.routes))
        instance = str(uuid4())

        @app.get("/__phase4b_fixture", include_in_schema=False)
        def fixture_identity():
            return {"fixture": "phase4b-browser", "instance_id": instance,
                    "synthetic_profiles": True, "ga_execution": False}

        assert_storage_isolated(root)
        # Only new synthetic/empty files inside the already-verified temp root.
        for name, content in (("preferences.json", "[]\n"), ("settings.json", "{}\n")):
            with (root / name).open("x", encoding="utf-8") as stream:
                stream.write(content)
        yield {"app": app, "identities": identities, "instance_id": instance,
               "unavailable": unavailable, "root": root}


def validate_ready_path(ready):
    ready = Path(ready)
    parent = ready.parent
    if (ready.is_symlink() or parent.is_symlink() or parent.exists()
            or not parent.name.startswith("phase4b-browser-") or ready.name != "ready.json"
            or not parent.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())):
        raise SafetyError("Use ready.json in a NEW phase4b-browser-* directory under OS temporary storage.")
    return ready.resolve()


def secure_private_directory(root):
    """Apply and verify ACLs only on the newly owned fixture directory."""
    root = Path(root).resolve()
    if not root.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not root.name.startswith("phase4b-browser-"):
        raise SafetyError("Refusing ACL changes outside an owned temporary fixture directory.")
    if os.name != "nt":
        root.chmod(0o700)
        if root.stat().st_mode & 0o077:
            raise SafetyError("Private fixture permissions could not be verified.")
        return
    script = r"""$ErrorActionPreference = 'Stop'
$target = $env:PHASE4B_PRIVATE_DIRECTORY
$user = [Security.Principal.WindowsIdentity]::GetCurrent().User
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$admins = [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$acl = [Security.AccessControl.DirectorySecurity]::new()
$acl.SetOwner($user)
$acl.SetAccessRuleProtection($true, $false)
foreach ($sid in @($user, $system, $admins)) {
  $rule = [Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
  $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $target -AclObject $acl
$check = Get-Acl -LiteralPath $target
$allowed = @($user.Value, $system.Value, $admins.Value)
if (-not $check.AreAccessRulesProtected -or $check.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $user.Value) { throw 'ACL verification failed' }
$rules = $check.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])
if ($rules.Count -ne 3) { throw 'Unexpected ACL entries' }
foreach ($rule in $rules) {
  if ($rule.IdentityReference.Value -notin $allowed -or $rule.AccessControlType -ne 'Allow' -or $rule.FileSystemRights -ne 'FullControl') { throw 'Unsafe ACL' }
}
"""
    environment = {key: value for key, value in os.environ.items() if key.upper() in {
        "SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP", "USERPROFILE"}}
    environment["PHASE4B_PRIVATE_DIRECTORY"] = str(root)
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            env=environment,
                            capture_output=True, timeout=15)
    if result.returncode:
        raise SafetyError("Private Windows fixture ACL could not be established/verified; details withheld.")


def migrate_browser_database(url, *, approved=False):
    if not approved:
        raise SafetyError("Browser initialization requires explicit Stage B approval.")
    from tests.phase4b_browser_safety import inspect_empty_browser_database
    inspect_empty_browser_database(url)  # immediately before the first DDL
    import pytest
    from alembic import command
    from alembic.config import Config
    with pytest.MonkeyPatch.context() as patch:
        # This is a verified browser URL, never a fallback to an application URL.
        patch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
        command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")


def seed_browser_accounts(engine, password):
    from sqlalchemy.orm import Session
    from identity_admin import import_faculty, bootstrap_admin
    name = "browser-admin@test.invalid"
    with Session(engine) as db, db.begin():
        if import_faculty(db) != 2 or not bootstrap_admin(db, name, password):
            raise SafetyError("Unexpected browser seed state; no reset is permitted.")
    return name
