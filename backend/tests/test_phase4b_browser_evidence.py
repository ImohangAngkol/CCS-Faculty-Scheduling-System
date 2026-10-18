"""Evidence IO tests only; no Phase 4B screenshot or acceptance is generated."""
import hashlib
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def capture_io(tmp_path):
    root = Path(__file__).resolve().parents[2]
    path = root / "docs/testing/phase-4b/record_browser_evidence.py"
    spec = importlib.util.spec_from_file_location("phase4b_evidence_io", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Existing privacy-reviewed historical image, copied only to pytest temp.
    # It is NOT relabelled/archived as Phase 4B evidence; records remain pending.
    source = root / "docs/screenshots/phase-4a/manual-acceptance/before-change.png"
    image = tmp_path / "offline-io-test.png"
    image.write_bytes(source.read_bytes())
    values = dict(scenario="P4B-B02", observer="CODEX_BROWSER",
                  observed_at="2026-10-18T00:00:00+08:00", browser="Offline IO test",
                  url="http://localhost:5189/faculty/preferences", privacy_reviewed=True,
                  expected="Offline metadata validation only",
                  observed="Historical image used only for IO; no Phase 4B browser observation")
    return module, image, tmp_path / "io-metadata.json", values


def test_hash_dimensions_and_attribution_do_not_automatically_mark_pass(capture_io):
    module, image, record, values = capture_io
    result = module.record_capture(image, record, **values)
    assert result["sha256"] == hashlib.sha256(image.read_bytes()).hexdigest()
    assert result["width"] > 0 and result["height"] > 0
    assert result["status"] == "CAPTURE RECORDED - ACCEPTANCE REVIEW PENDING"
    original = record.read_bytes()
    with pytest.raises(ValueError): module.record_capture(image, record, **values)
    assert record.read_bytes() == original


@pytest.mark.parametrize("override", [
    {"privacy_reviewed": False}, {"scenario": "invented"}, {"observer": "unknown"},
    {"observed_at": "2026-10-18T00:00:00"}, {"url": "http://localhost:5173/login"},
    {"url": "http://localhost:5189/login?token=synthetic"},
    {"observed": "password=synthetic-private-value"},
])
def test_unsafe_or_incomplete_metadata_not_archived(capture_io, override):
    module, image, record, values = capture_io
    values.update(override)
    with pytest.raises(ValueError): module.record_capture(image, record, **values)
    assert not record.exists()


def test_injected_fault_label_is_mandatory_in_record(capture_io):
    module, image, record, values = capture_io
    values["scenario"] = "P4B-B06"
    result = module.record_capture(image, record, **values)
    assert "not a physical" in result["fault_scope"]
