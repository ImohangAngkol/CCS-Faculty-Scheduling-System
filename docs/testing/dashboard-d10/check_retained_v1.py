"""Check unchanged V1 restoration against owned copies, without printing payloads.

This is a compatibility gate, not a fingerprint override or a V2 implementation.
Checkpoint copies contain historical input data: keep them in a temporary local
directory, never archive them, and remove only that newly owned directory.
"""
from contextlib import redirect_stderr, redirect_stdout
import gzip
import hashlib
import io
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    # Imports read academic data. Do not retain or export their diagnostics.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        from services import ga_checkpoint_service as checkpoints
        from genetic_algorithm.utils import Functions as scheduling
    original_root = checkpoints.CHECKPOINTS_DIR
    artifacts = sorted(original_root.glob("*/checkpoint-*.json.gz"))
    if not artifacts:
        raise RuntimeError("No retained checkpoint artifacts were found")
    before = {p: sha(p) for p in artifacts}
    engines = {checkpoints.engine_fingerprint(1), checkpoints.engine_fingerprint(2)}
    current_inputs = checkpoints.input_fingerprint()
    rng = random.getstate()
    findings = []
    temp_parent = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="d10-retained-v1-") as owned:
        temporary = Path(owned).resolve()
        if temporary.parent != temp_parent or not temporary.name.startswith("d10-retained-v1-"):
            raise RuntimeError("Unexpected temporary copy location")
        try:
            # Artifact destination only; validation, fingerprints, inputs and RNG
            # remain the real V1 implementation with no compatibility bypass.
            checkpoints.CHECKPOINTS_DIR = temporary
            for index, source in enumerate(artifacts, 1):
                directory = temporary / source.parent.name
                directory.mkdir(exist_ok=True)
                copied = directory / source.name
                shutil.copyfile(source, copied)
                if sha(copied) != before[source]:
                    raise RuntimeError("Checkpoint copy integrity failed")
                with gzip.open(copied, "rb") as stream:
                    content = stream.read(checkpoints.MAX_JSON_BYTES + 1)
                if len(content) > checkpoints.MAX_JSON_BYTES:
                    raise RuntimeError("Retained artifact exceeds the V1 size bound")
                envelope = json.loads(content)
                payload = envelope["payload"]
                checksum_valid = hashlib.sha256(checkpoints.canonical(payload)).hexdigest() == envelope["sha256"]
                outcome, code = "RESTORED", None
                try:
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        checkpoints.load_checkpoint(source.parent.name,
                            (scheduling.list_subjects, scheduling.list_faculty, scheduling.lst_rooms), source.name)
                except checkpoints.CheckpointError as error:
                    outcome, code = "REJECTED", error.code
                findings.append({"artifact_number": index, "copy_identical": True,
                    "checksum_valid": checksum_valid,
                    "input_fingerprint_matches_current": payload["input_fingerprint"] == current_inputs,
                    "engine_matches_either_supported_V1_scoring_policy": payload["engine_fingerprint"] in engines,
                    "loader_outcome": outcome, "loader_code": code})
                # Release large decoded documents before inspecting the next file.
                del content, envelope, payload
        finally:
            checkpoints.CHECKPOINTS_DIR = original_root
    if random.getstate() != rng or any(sha(p) != before[p] for p in artifacts):
        raise RuntimeError("Retained artifact or RNG preservation failed")
    restored = sum(row["loader_outcome"] == "RESTORED" for row in findings)
    return {"scope": "Actual unchanged V1 loader against byte-identical temporary copies; no continuation attempted after rejection",
        "artifacts_checked": len(findings), "restorations_succeeded": restored,
        "restorations_rejected": len(findings)-restored, "findings": findings,
        "historical_continuation_demonstrated": False,
        "checkpoint_originals_unchanged": True, "temporary_copies_removed": not temporary.exists(),
        "RNG_unchanged_after_imports": True, "GA_generations_executed": 0,
        "database_connections": 0, "application_files_modified": 0,
        "decision": "STOP: no retained checkpoint restored on the current baseline; historical continuation acceptance is not demonstrated"}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=True))
    raise SystemExit(2 if not result["restorations_succeeded"] else 0)
