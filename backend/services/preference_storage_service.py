"""Atomic, serialized JSON persistence for the supported one-process deployment."""
import json
import os
import tempfile
import threading
from pathlib import Path
from fastapi import HTTPException

LOCK = threading.RLock()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read(path, missing, validate):
    with LOCK:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=_pairs,
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
        except FileNotFoundError:
            return missing()
        except (OSError, ValueError, UnicodeError, RecursionError) as error:
            raise HTTPException(503, "Preference storage is unreadable or corrupt. Existing data was preserved. Ask the administrator to verify storage; do not retry by resetting preferences.") from error
        try:
            validate(data)
        except (ValueError, TypeError, KeyError, RecursionError) as error:
            raise HTTPException(503, "Preference storage has invalid records. Existing data was preserved; administrator review is required.") from error
        return data


def atomic_write(path, data):
    path = Path(path)
    temporary = None
    try:
        content = json.dumps(data, indent=4, ensure_ascii=False, allow_nan=False).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".preference-", suffix=".tmp", dir=path.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise HTTPException(503, "Preferences could not be committed. No partial file was published. Reload to verify saved data before retrying.") from error
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def update(path, missing, validate, change):
    with LOCK:
        original = read(path, missing, validate)
        updated = change(original)
        validate(updated)
        atomic_write(path, updated)
        if read(path, missing, validate) != updated:
            raise HTTPException(503, "Saved preference verification failed. Reload and contact the administrator before retrying.")
        return updated
