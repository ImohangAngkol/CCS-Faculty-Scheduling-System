"""Opt-in isolated app factory; deliberately NOT registered in main.py."""
from uuid import UUID
from fastapi import FastAPI, APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from services.preference_authorization import require_principal
from services.ga_research_bridge import configured_service
from services.ga_run_authority import RunError


class Admission(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    request_id:str


def create_app(bridge=None):
    app=FastAPI(title='Isolated fictional GA research only')
    app.state.research_bridge=bridge
    router=APIRouter(prefix='/api/research/ga',dependencies=[Depends(require_principal)])

    def service(request:Request,principal=Depends(require_principal)):
        # The actual authenticated_session dependency enforces cookie/CSRF and
        # account validity. A client role/department header is never authority.
        value=request.app.state.research_bridge
        if value is None:value=configured_service()
        if value is None:raise HTTPException(503,{'code':'RESEARCH_BRIDGE_UNCONFIGURED'})
        try:value.actor(principal)
        except RunError as e:raise HTTPException(e.status,{'code':e.code}) from None
        return value

    def perform(fn):
        try:return fn()
        except RunError as e:raise HTTPException(e.status,{'code':e.code}) from None
        except (ValueError,TypeError,OSError):raise HTTPException(409,{'code':'RESEARCH_INTEGRITY_REJECTED'}) from None

    @app.middleware('http')
    async def private(request,call_next):
        if not request.client or request.client.host not in {'127.0.0.1','::1'}:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':{'code':'RESEARCH_LOOPBACK_REQUIRED'}},403,headers={'Cache-Control':'no-store'})
        response=await call_next(request);response.headers['Cache-Control']='no-store';return response

    @router.get('/capabilities')
    def capabilities(p=Depends(require_principal),b=Depends(service)):
        return perform(lambda:b.capabilities(p))

    @router.post('/runs')
    def admit(body:Admission,p=Depends(require_principal),b=Depends(service)):
        return perform(lambda:b.admit(p,body.request_id))

    @router.get('/runs/{run}')
    def status(run:UUID,p=Depends(require_principal),b=Depends(service)):
        return perform(lambda:b.observe(p,str(run)))

    @router.get('/runs/{run}/telemetry')
    def telemetry(run:UUID,p=Depends(require_principal),b=Depends(service)):
        return perform(lambda:b.telemetry(p,str(run)))

    @router.post('/runs/{run}/{action}')
    def control(run:UUID,action:str,body:dict|None=Body(default=None),p=Depends(require_principal),b=Depends(service)):
        if body is not None:raise HTTPException(422,{'code':'RESEARCH_CONTROL_BODY_UNSUPPORTED'})
        if action not in {'start','stop','compare-research-best'}:raise HTTPException(404,{'code':'RESEARCH_ACTION_NOT_EXPOSED'})
        fn={'start':b.start,'stop':b.stop,'compare-research-best':b.compare_best}[action]
        return perform(lambda:fn(p,str(run)))

    app.include_router(router)
    return app
