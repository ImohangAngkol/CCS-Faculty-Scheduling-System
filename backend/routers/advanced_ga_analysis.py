"""Administrator-only recorded analysis; no worker admission, scoring or writes."""
from typing import Literal
from fastapi import APIRouter,Depends,Query
from services.preference_authorization import require_admin
from routers.ga_history import read
from services import advanced_ga_analysis as analysis

router=APIRouter(prefix="/api/ga/advanced-analysis",tags=["Advanced recorded analysis"],dependencies=[Depends(require_admin)])
Candidate=Literal["generation_best","best_ever"]

@router.get("/runs")
def runs(offset:int=Query(0,ge=0)):return read(lambda:analysis.runs(offset))

@router.get("/runs/{run_id}")
def project(run_id:str,generation:int|None=Query(None,ge=0),candidate:Candidate="generation_best",history_offset:int=Query(0,ge=0)):
    return read(lambda:analysis.project(run_id,generation,candidate,history_offset))

@router.get("/runs/{run_id}/compare")
def compare(run_id:str,left_generation:int=Query(...,ge=0),right_generation:int=Query(...,ge=0),left_candidate:Candidate="generation_best",right_candidate:Candidate="generation_best"):
    return read(lambda:analysis.compare(run_id,left_generation,left_candidate,right_generation,right_candidate))
