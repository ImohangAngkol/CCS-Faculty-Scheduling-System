"""Additive administrator-only current-evaluation projection; no worker or storage writes."""
from fastapi import APIRouter, Depends
from services.preference_authorization import require_admin
from routers.ga_history import read
from services.ga_evaluation_v2 import evaluation

router = APIRouter(prefix="/api/ga", tags=["Current Evaluation"], dependencies=[Depends(require_admin)])


@router.get("/current-evaluation")
def current_evaluation():
    return read(evaluation)
