"""Bounded expiring session heads only. No source rows, metadata, files or DB writes."""
from collections import OrderedDict
import hashlib
import hmac
import threading
import time

from services import external_schedule_review_service as review
from services import external_schedule_service as intake

TTL = 1800
MAX_HEADS = 4096
_heads = OrderedDict()
_lock = threading.RLock()


def owner(account):
    user, session = account
    return hmac.new(review._PROCESS_KEY, f"{user.id}:{session.id}".encode(), hashlib.sha256).hexdigest()


def _purge():
    now = time.time()
    for key in list(_heads):
        if _heads[key]["expires"] <= now: del _heads[key]


def bind(result, account):
    key = owner(account)
    source = review._source(result.review_token)
    source["owner"] = key
    # Fresh source identity even for identical reimports; old receipts expire.
    import secrets
    source["preview_nonce"] = secrets.token_hex(16)
    raw = review._json(source)
    import base64
    token = base64.urlsafe_b64encode(raw).decode()+"."+hmac.new(review._PROCESS_KEY, raw, hashlib.sha256).hexdigest()
    if len(token) > 1600000: intake.fail("REVIEW_SNAPSHOT_TOO_LARGE", "Split this preview into smaller batches.")
    session_expiry = account[1].expires_at
    from services.auth_service import utc
    with _lock:
        _purge()
        _heads.pop(key, None)
        _heads[key] = {"source": hashlib.sha256(token.encode()).hexdigest(), "revision": 0,
                       "assessment": None, "expires": min(time.time()+TTL, utc(session_expiry).timestamp())}
        while len(_heads) > MAX_HEADS: _heads.popitem(last=False)
    return result.model_copy(update={"review_token": token})


def current(token, key):
    source = review._source(token)
    if source.get("owner") != key:
        intake.fail("PREVIEW_SESSION_MISMATCH", "This preview is unavailable in this session. Import it again.", 409)
    with _lock:
        _purge()
        head = _heads.get(key)
        if not head or head["source"] != hashlib.sha256(token.encode()).hexdigest():
            intake.fail("PREVIEW_EXPIRED_OR_REPLACED", "This temporary preview expired or was replaced. Import it again.", 409)
        return dict(head)


def invalidate(token, key):
    with _lock:
        current(token, key)
        _heads[key]["revision"] += 1
        _heads[key]["assessment"] = None
    return {"status": "not_assessed", "preview_only": True}


def record(token, key, revision, fingerprint):
    with _lock:
        head = current(token, key)
        if head["revision"] != revision:
            intake.fail("READINESS_CHANGED", "Metadata or mappings changed while assessment was running. Assess again.", 409)
        _heads[key]["assessment"] = fingerprint


def require_assessment(token, key, revision, fingerprint):
    with _lock:
        head = current(token, key)
        if head["revision"] != revision or head["assessment"] != fingerprint:
            intake.fail("READINESS_STALE", "The assessment was invalidated or replaced. Assess the current preview again.", 409)
        return head
