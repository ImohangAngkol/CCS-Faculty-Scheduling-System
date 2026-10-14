"""Keep new durable GA lifecycle/checkpoint writes out of institutional storage."""
import pytest


@pytest.fixture(autouse=True)
def verified_admin_for_legacy_regressions(request, monkeypatch):
    """Old behavior suites test scheduling, not credentials; provide explicit principal.

    The Phase 4A identity suite separately exercises real sessions and every route.
    No production bypass, middleware exemption or client header is installed.
    """
    name = request.module.__name__.split(".")[-1]
    modules = {"test_metadata_api", "test_fitness_reporting", "test_api", "test_api_validation"}
    if not (name.startswith("test_ga_") or name in modules):
        yield
        return
    from main import app
    from services.preference_authorization import current_principal, PreferencePrincipal
    monkeypatch.setitem(app.dependency_overrides, current_principal, lambda: PreferencePrincipal("admin"))
    yield


@pytest.fixture(autouse=True)
def isolated_checkpoints(monkeypatch, tmp_path):
    from services import ga_checkpoint_service
    monkeypatch.setattr(ga_checkpoint_service, "CHECKPOINTS_DIR", tmp_path / "run_checkpoints")
    from services import ga_history_service
    monkeypatch.setattr(ga_history_service, "SNAPSHOTS_DIR", tmp_path / "generation_snapshots")
