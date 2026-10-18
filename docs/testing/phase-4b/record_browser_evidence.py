"""Record hashes/metadata for an existing, genuinely observed browser PNG.

No screenshot generation, browser control or automatic acceptance claim. A human
or Computer Use operator must observe the result and review privacy first.
"""
import hashlib
import json
from pathlib import Path
import re
import struct

SCENARIOS = {f"P4B-B{number:02d}" for number in range(1, 7)}


def record_capture(image, record, *, scenario, observer, observed_at, browser,
                   url, expected, observed, privacy_reviewed=False):
    from datetime import datetime
    from urllib.parse import urlsplit
    image, record = Path(image), Path(record)
    if (scenario not in SCENARIOS or observer not in {"CODEX_BROWSER", "USER_CONFIRMED"}
            or not privacy_reviewed or not all((browser.strip(), expected.strip(), observed.strip()))):
        raise ValueError("Observed scenario, attribution and explicit privacy review are required.")
    moment = datetime.fromisoformat(observed_at)
    if moment.utcoffset() is None:
        raise ValueError("Capture timestamp must include a timezone offset.")
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname != "localhost" or parsed.port != 5189
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Record only the verified local frontend URL without credentials/query/fragment.")
    notes = " ".join((browser, expected, observed))
    if re.search(r"(?i)bearer\s+\S+|postgres(?:ql)?(?:\+\w+)?://|(?:password|csrf_token|session_cookie)\s*[:=]", notes):
        raise ValueError("Do not archive credential-bearing evidence notes.")
    if (image.is_symlink() or record.is_symlink() or record.exists()
            or image.parent.resolve() != record.parent.resolve() or record.suffix != ".json"):
        raise ValueError("Do not follow image links or overwrite existing evidence.")
    payload = image.read_bytes()
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise ValueError("A real existing PNG capture is required.")
    width, height = struct.unpack(">II", payload[16:24])
    if not width or not height:
        raise ValueError("Invalid screenshot dimensions.")
    result = {"scenario": scenario, "observer": observer,
              "status": "CAPTURE RECORDED - ACCEPTANCE REVIEW PENDING",
              "observed_at": observed_at, "browser": browser, "url": url,
              "expected": expected, "observed": observed, "privacy_reviewed": True,
              "screenshot": image.name, "sha256": hashlib.sha256(payload).hexdigest(),
              "width": width, "height": height,
              "scope": "Operator-attested actual capture; hashing cannot independently prove authenticity/privacy."}
    if scenario == "P4B-B06":
        result["fault_scope"] = "Injected fixture 503; not a physical PostgreSQL service outage."
    with record.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    return result
