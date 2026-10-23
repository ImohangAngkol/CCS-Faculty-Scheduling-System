"""Independent constrained V2 API, protected by existing admin/session/CSRF."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from schemas.ga_constrained import RunRequest, ControlRequest
from routers.external_schedules import review_payload
from services.preference_authorization import require_admin
from services import ga_v2_service as service
from services.ga_v2_constraints import ConstraintError

router=APIRouter(prefix="/api/ga/v2",tags=["Constrained GA V2"],dependencies=[Depends(require_admin)])


def execute(action):
    try:
        return action()
    except ConstraintError as error:
        unavailable=any(word in error.code for word in ("UNAVAILABLE","AUTHORITY","EVIDENCE","LEDGER"))
        raise HTTPException(503 if unavailable else 409, {"code":error.code,"message":str(error)}) from None
    except Exception:
        raise HTTPException(503,{"code":"V2_UNAVAILABLE","message":"Constrained execution is unavailable; no successful schedule is claimed."}) from None


@router.get("/status")
def status():
    return {"legacy_mode":"LEGACY_V1","constrained_mode":"CONSTRAINED_V2","engine_version":"ga-constrained-v2.1",
        "production_status":"BLOCKED","message":"No genuine institutional deployment is configured. Fictional test providers do not establish institutional approval."}


@router.get("/constraints")
def constraints(academic_year:str,term:str):
    return execute(lambda:service.constraints(academic_year,term))


@router.post("/runs",status_code=202)
async def start(request:Request):
    body=await review_payload(request,RunRequest)
    return execute(lambda:service.start(body))


@router.get("/runs/{run_id}")
def inspect(run_id:UUID):
    return execute(lambda:service.inspect(str(run_id)))


@router.post("/runs/{run_id}/control")
async def control(run_id:UUID,request:Request):
    body=await review_payload(request,ControlRequest)
    return execute(lambda:service.control(str(run_id),body.action))
