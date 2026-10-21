"""Administrator-only transient previews; request bodies never spool to disk."""
from fastapi import APIRouter, Depends, Request
import json
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from schemas.external_schedule import ManualPreview, PreviewResult, ReviewRequest, ReviewProjection, ReviewHandoff
from services import external_schedule_service as service
from services.preference_authorization import require_admin

router = APIRouter(prefix="/api/external-schedules", tags=["External Schedule Preview"],
                   dependencies=[Depends(require_admin)])


def unique_json_pairs(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON key")
        result[name] = value
    return result


async def bounded_body(request, limit=service.MAX_BYTES):
    length = request.headers.get("content-length")
    if length and (not length.isdecimal() or int(length) > limit):
        service.fail("FILE_TOO_LARGE", "The preview request exceeds its byte limit.", 413)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > limit:
            service.fail("FILE_TOO_LARGE", "The preview request exceeds its byte limit.", 413)
        raw.extend(chunk)
    return bytes(raw)


@router.get("/metadata")
def metadata():
    return service.metadata()


@router.post("/preview", response_model=PreviewResult)
async def manual_preview(request: Request):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        service.fail("UNSUPPORTED_MEDIA_TYPE", "Manual preview requires application/json.", 415)
    raw = await bounded_body(request)
    try:
        payload = ManualPreview.model_validate(json.loads(raw, object_pairs_hook=unique_json_pairs))
    except (ValidationError, ValueError, RecursionError):
        service.fail("INVALID_PAYLOAD", "Provide 1–200 rows using only the documented fields and draft/tentative status.")
    return await run_in_threadpool(service.validate, payload.rows)


@router.post("/preview-file", response_model=PreviewResult)
async def file_preview(request: Request, filename: str = ""):
    service.filename_kind(filename)
    raw = await bounded_body(request)
    return await run_in_threadpool(service.parse_file, raw, filename)


async def review_payload(request: Request):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        service.fail("UNSUPPORTED_MEDIA_TYPE", "Review requires application/json.", 415)
    raw = await bounded_body(request, 2 * service.MAX_BYTES)
    try:
        payload = ReviewRequest.model_validate(json.loads(raw, object_pairs_hook=unique_json_pairs))
    except (ValidationError, ValueError, RecursionError):
        service.fail("INVALID_REVIEW_REQUEST", "Provide a preview receipt and bounded mappings to original source rows.")
    return payload


@router.post("/review", response_model=ReviewProjection)
async def review(request: Request):
    payload = await review_payload(request)
    from services.external_schedule_review_service import project
    return await run_in_threadpool(project, payload)


@router.post("/handoff", response_model=ReviewHandoff)
async def handoff(request: Request):
    payload = await review_payload(request)
    from services.external_schedule_handoff_service import prepare
    return await run_in_threadpool(prepare, payload)
