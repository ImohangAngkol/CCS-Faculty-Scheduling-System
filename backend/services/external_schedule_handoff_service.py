"""Fresh, complete review snapshots only. No persistence, export files or approval."""
from datetime import datetime, timezone
import hashlib
import json

from schemas.external_schedule import ReviewHandoff
from services.external_schedule_review_service import project


def prepare(payload):
    # Never accept a client projection, selected/filtered subset or cached result.
    # The existing verifier checks the signed source, current references and maps.
    review = project(payload)
    canonical = json.dumps(review.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    fingerprint = hashlib.sha256(canonical).hexdigest()
    return ReviewHandoff(preview_id="d5-" + fingerprint,
                         revalidated_at=datetime.now(timezone.utc), review=review)
