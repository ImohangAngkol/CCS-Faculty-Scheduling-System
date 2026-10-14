"""Explicit scoring policy, with exact-source compatibility for legacy runs."""
import base64
import hashlib
import json
import zlib
from pathlib import Path

MANIFEST = Path(__file__).with_name("fitness_policy_compatibility.json")


def scoring_version(inputs):
    version = (inputs or {}).get("preference_scoring_version", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported preference scoring policy.")
    return version


def legacy_source(relative_path, current):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != manifest.get("compatible_policy_helper"):
        raise ValueError("Legacy policy bridge source differs from the verified release.")
    entry = manifest["legacy_sources"].get(relative_path)
    if entry is None:
        return current
    if hashlib.sha256(current).hexdigest() != manifest["compatible_sources"].get(relative_path):
        raise ValueError("Installed source is not the verified legacy-compatible release.")
    original = zlib.decompress(base64.b64decode(entry["zlib_base64"], validate=True))
    if hashlib.sha256(original).hexdigest() != entry["sha256"]:
        raise ValueError("Legacy source provenance failed integrity checks.")
    return original
