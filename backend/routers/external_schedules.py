"""Administrator-only transient previews; request bodies never spool to disk."""
from fastapi import APIRouter, Depends, Request
import json
import base64
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from schemas.external_schedule import ManualPreview, PreviewResult, ReviewRequest, ReviewProjection, ReviewHandoff, LegacyUpload
from typing import Literal
from services import external_schedule_service as service
from services.preference_authorization import require_admin
from services.auth_service import authenticated_session
from services import external_schedule_preview_lifecycle as lifecycle
from schemas.external_readiness import AssessmentRequest, HandoffRequest, ReadinessAssessment, ReadinessHandoff

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
async def manual_preview(request: Request, account=Depends(authenticated_session)):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        service.fail("UNSUPPORTED_MEDIA_TYPE", "Manual preview requires application/json.", 415)
    raw = await bounded_body(request)
    try:
        payload = ManualPreview.model_validate(json.loads(raw, object_pairs_hook=unique_json_pairs))
    except (ValidationError, ValueError, RecursionError):
        service.fail("INVALID_PAYLOAD", "Provide 1–200 rows using only the documented fields and draft/tentative status.")
    result = await run_in_threadpool(service.validate, payload.rows)
    return lifecycle.bind(result, account)


@router.post("/preview-file", response_model=PreviewResult)
async def file_preview(request: Request, filename: str = "", import_format: Literal["canonical", "legacy_gec"] = "canonical", account=Depends(authenticated_session)):
    service.filename_kind(filename)
    if import_format == "legacy_gec":
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            service.fail("UNSUPPORTED_MEDIA_TYPE", "Legacy preview requires a bounded JSON upload envelope.", 415)
        envelope = await bounded_body(request, 2 * service.MAX_BYTES)
        try:
            payload = LegacyUpload.model_validate(json.loads(envelope, object_pairs_hook=unique_json_pairs))
            raw = base64.b64decode(payload.content_base64, validate=True)
        except (ValidationError, ValueError, RecursionError):
            service.fail("INVALID_LEGACY_UPLOAD", "Provide bounded base64 CSV bytes and preview metadata. No rows were accepted.")
        result = await run_in_threadpool(service.parse_file, raw, filename, import_format, payload.metadata)
        return lifecycle.bind(result, account)
    raw = await bounded_body(request)
    result = await run_in_threadpool(service.parse_file, raw, filename)
    return lifecycle.bind(result, account)


async def review_payload(request: Request, model=ReviewRequest):
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        service.fail("UNSUPPORTED_MEDIA_TYPE", "Review requires application/json.", 415)
    raw = await bounded_body(request, 2 * service.MAX_BYTES)
    try:
        payload = model.model_validate(json.loads(raw, object_pairs_hook=unique_json_pairs))
    except (ValidationError, ValueError, RecursionError):
        service.fail("INVALID_REVIEW_REQUEST", "Provide a preview receipt and bounded mappings to original source rows.")
    return payload


@router.post("/review", response_model=ReviewProjection)
async def review(request: Request, account=Depends(authenticated_session)):
    payload = await review_payload(request)
    from services.external_schedule_review_service import project
    lifecycle.invalidate(payload.review_token, lifecycle.owner(account))
    return await run_in_threadpool(project, payload)


@router.post("/handoff", response_model=ReadinessHandoff | ReviewHandoff)
async def handoff(request: Request, account=Depends(authenticated_session)):
    payload = await review_payload(request, HandoffRequest)
    owner = lifecycle.owner(account)
    lifecycle.current(payload.review_token, owner)
    if payload.metadata is not None or payload.assessment_receipt is not None:
        if payload.metadata is None or payload.assessment_receipt is None:
            service.fail("READINESS_ASSESSMENT_REQUIRED", "Provide current completion metadata and its assessment receipt.", 409)
        from services.external_schedule_readiness_service import prepare_handoff
        return await run_in_threadpool(prepare_handoff, payload, owner)
    from services.external_schedule_handoff_service import prepare
    return await run_in_threadpool(prepare, payload)


@router.post("/readiness", response_model=ReadinessAssessment)
async def readiness(request: Request, account=Depends(authenticated_session)):
    payload = await review_payload(request, AssessmentRequest)
    from services.external_schedule_readiness_service import assess
    return await run_in_threadpool(assess, payload, lifecycle.owner(account))


@router.post("/readiness/invalidate")
async def invalidate_readiness(request: Request, account=Depends(authenticated_session)):
    payload = await review_payload(request)
    return lifecycle.invalidate(payload.review_token, lifecycle.owner(account))
