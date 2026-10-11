"""Keep new durable GA lifecycle/checkpoint writes out of institutional storage."""
import pytest


@pytest.fixture(autouse=True)
def isolated_checkpoints(monkeypatch, tmp_path):
    from services import ga_checkpoint_service
    monkeypatch.setattr(ga_checkpoint_service, "CHECKPOINTS_DIR", tmp_path / "run_checkpoints")
