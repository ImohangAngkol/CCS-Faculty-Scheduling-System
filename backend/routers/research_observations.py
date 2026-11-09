"""GET-only research observations. Production source remains unavailable."""
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query,Response,Request
from services.preference_authorization import require_principal
from services.ga_research_observation import configured_observer
from services.ga_run_authority import RunError


def service(request:Request):
    value=getattr(request.app.state,'research_observer',None) or configured_observer()
    if value is None:raise HTTPException(503,{'code':'RESEARCH_OBSERVATION_UNAVAILABLE','message':'No isolated research observation source is configured. Institutional optimization remains blocked.'})
    return value


def private(response:Response):response.headers['Cache-Control']='no-store'
router=APIRouter(prefix='/api/research/observations',tags=['Read-only fictional research'],dependencies=[Depends(private)])


def perform(fn):
    try:return fn()
    except RunError as e:raise HTTPException(e.status,{'code':e.code}) from None
    except (ValueError,TypeError,OSError,KeyError,AttributeError):raise HTTPException(409,{'code':'RESEARCH_OBSERVATION_REJECTED'}) from None


@router.get('/capabilities')
def capabilities(p=Depends(require_principal),s=Depends(service)):return perform(lambda:s.capabilities(p))


@router.get('/runs')
def listing(offset:int=Query(0,ge=0,le=1024),limit:int=Query(10,ge=1,le=10),p=Depends(require_principal),s=Depends(service)):
    return perform(lambda:s.listing(p,offset,limit))


@router.get('/runs/{run}')
def detail(run:UUID,p=Depends(require_principal),s=Depends(service)):return perform(lambda:s.detail(p,str(run)))


@router.get('/runs/{run}/telemetry')
def telemetry(run:UUID,after:int=Query(0,ge=0,le=256),limit:int=Query(64,ge=1,le=64),p=Depends(require_principal),s=Depends(service)):
    return perform(lambda:s.telemetry(p,str(run),after,limit))


def create_app(observer=None):
    """Optional isolated host. Includes session auth only, no GA write routes."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from routers.auth import router as auth
    app=FastAPI(title='Read-only fictional research console');app.state.research_observer=observer
    app.include_router(router)
    # Reuse original real session/CSRF handlers; never account-management or GA
    # control handlers. Session writes are distinct from research observation.
    app.include_router(APIRouter(routes=[r for r in auth.routes if r.path in {'/api/auth/login','/api/auth/logout','/api/auth/me'}]))
    @app.middleware('http')
    async def loopback(request,call_next):
        if not request.client or request.client.host not in {'127.0.0.1','::1'}:
            return JSONResponse({'detail':{'code':'RESEARCH_LOOPBACK_REQUIRED'}},403,headers={'Cache-Control':'no-store'})
        response=await call_next(request);response.headers['Cache-Control']='no-store';return response
    return app
