"""Additive administrator-only current-evaluation projection; no worker or storage writes."""
from fastapi import APIRouter, Depends
from services.preference_authorization import require_admin
from routers.ga_history import read
from services.ga_evaluation_v2 import evaluation

router = APIRouter(prefix="/api/ga", tags=["Current Evaluation"], dependencies=[Depends(require_admin)])


@router.get("/current-evaluation")
def current_evaluation():
    return read(evaluation)


@router.get("/source-qualification")
def source_qualification():
    from services.ga_source_qualification import status
    return status()


@router.get("/runs/{run_id}/input-receipt")
def input_receipt(run_id: str):
    from services.ga_input_receipt import read as receipt
    return read(lambda: receipt(run_id))
