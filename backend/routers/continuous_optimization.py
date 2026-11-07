"""Administrator-readable foundation only. No start/control API is installed."""
from fastapi import APIRouter, Depends, HTTPException, Request
from services.preference_authorization import require_admin
from services.continuous_readiness import readiness

router = APIRouter(prefix="/api/ga/continuous", tags=["Continuous readiness"], dependencies=[Depends(require_admin)])


@router.get("/readiness")
def get_readiness(request: Request):
    if request.query_params or request.headers.get("content-length", "0") != "0" or request.headers.get("transfer-encoding"):
        raise HTTPException(422, "Continuous readiness accepts no configuration or activation input.")
    return readiness()
