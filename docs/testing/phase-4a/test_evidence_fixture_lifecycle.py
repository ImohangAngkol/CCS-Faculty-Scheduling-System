"""Regression for the evidence-only server's Windows-safe fixture teardown."""
import json
from pathlib import Path
import subprocess
import sys
import time

import httpx


def test_evidence_server_uses_temporary_storage_and_disposes_it(tmp_path):
    root = Path(__file__).resolve().parents[3]
    ready = tmp_path / "phase4a-evidence-lifecycle.json"
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name("serve_evidence_fixture.py")),
         "--ready-file", str(ready)], cwd=root,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 60
        while not ready.exists():
            assert process.poll() is None, "Evidence fixture exited before readiness"
            assert time.monotonic() < deadline, "Evidence fixture readiness timed out"
            time.sleep(0.05)
        credentials = json.loads(ready.read_text(encoding="utf-8"))
        assert credentials["backend"].startswith("http://localhost:")
        with httpx.Client(base_url=credentials["backend"], timeout=10) as client:
            assert client.get("/api/auth/me").status_code == 401
            response = client.post("/api/auth/login", headers={"Origin": "http://localhost:5189"},
                                   json={"username": "faculty@test.invalid", "password": credentials["password"]})
            assert response.status_code == 200
            assert response.json()["user"]["faculty"]["name"] == "Synthetic Faculty 0"
            assert client.get("/preferences/0").status_code == 200
        ready.with_suffix(".stop").touch(exist_ok=False)
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, "Evidence fixture shutdown failed (credentials withheld)"
        assert credentials["password"] not in stdout + stderr
        assert not ready.exists() and not ready.with_suffix(".stop").exists()
        assert not list(tmp_path.glob("phase4a-evidence-storage-*"))
    finally:
        if process.poll() is None:
            ready.with_suffix(".stop").touch(exist_ok=True)
            try:
                process.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.communicate(timeout=10)
