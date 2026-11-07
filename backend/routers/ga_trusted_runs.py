"""Separate versioned admission routes. Production dependencies unavailable."""
from uuid import UUID
from fastapi import APIRouter,Body,Depends,HTTPException,Response
from pydantic import BaseModel,ConfigDict,Field
from services.preference_authorization import require_principal
from services.ga_run_authority import RunError
from services.ga_trusted_runs import configured_service

def private_response(response:Response):response.headers['Cache-Control']='no-store'

router=APIRouter(prefix='/api/ga/bound-runs',tags=['Trusted bundle runs v1'],dependencies=[Depends(private_response)])

class Admission(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    department_id:str
    request_id:str
    catalog_reference:str=Field(min_length=1,max_length=100)

def service():
    value=configured_service()
    if value is None:raise HTTPException(503,{'code':'GA_TRUSTED_RUNS_UNAVAILABLE','message':'Scoped optimization authority, trusted capture and owned storage are not configured.'})
    return value

def perform(function):
    try:return function()
    except RunError as error:raise HTTPException(error.status,{'code':error.code}) from None
    except (ValueError,TypeError,OSError):raise HTTPException(409,{'code':'GA_TRUSTED_RUN_REJECTED'}) from None

@router.get('/capabilities')
def capabilities(principal=Depends(require_principal)):
    return {'contract':'ga-trusted-admission-v1','available':False,'production_authority':'UNAVAILABLE',
        'production_storage':'UNCONFIGURED','continuous_worker':False,'admin_implies_chair':False}

@router.post('')
def admit(body:Admission,principal=Depends(require_principal),backend=Depends(service)):
    return perform(lambda:backend.admit(principal,body.department_id,body.request_id,body.catalog_reference))

@router.get('/{run_id}')
def status(run_id:UUID,principal=Depends(require_principal),backend=Depends(service)):
    return perform(lambda:backend.status(principal,str(run_id)))

@router.post('/{run_id}/{action}')
def control(run_id:UUID,action:str,body:dict|None=Body(default=None),principal=Depends(require_principal),backend=Depends(service)):
    if body is not None:raise HTTPException(422,{'code':'GA_RUN_CONTROL_BODY_UNSUPPORTED'})
    if action not in {'execute','resume','pause','stop'}:raise HTTPException(404,{'code':'GA_RUN_COMMAND_INVALID'})
    if action in {'pause','stop'}:return perform(lambda:backend.command(principal,str(run_id),action))
    return perform(lambda:backend.execute(principal,str(run_id),resume=action=='resume'))

@router.get('/{run_id}/checkpoint')
def checkpoint(run_id:UUID,principal=Depends(require_principal),backend=Depends(service)):
    return Response(perform(lambda:backend.checkpoint(principal,str(run_id))),media_type='application/octet-stream',headers={'Cache-Control':'no-store'})

@router.get('/{run_id}/result')
def result(run_id:UUID,principal=Depends(require_principal),backend=Depends(service)):
    return perform(lambda:backend.result(principal,str(run_id)))
