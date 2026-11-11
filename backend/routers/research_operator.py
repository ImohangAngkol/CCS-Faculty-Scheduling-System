"""Explicit isolated factory only; never included in ordinary main.py."""
from pathlib import Path
import sqlite3
from uuid import UUID
from fastapi import Depends,HTTPException
from fastapi.responses import HTMLResponse,Response,JSONResponse
from pydantic import BaseModel,ConfigDict
from routers.research_observations import create_app as observations
from services.preference_authorization import require_principal
from services.ga_run_authority import RunError
from services.ga_worker_contract import fictional_source


class RequestIdentity(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    request_id:str


def create_app(operator=None):
    fictional_source()
    app=observations(operator.observer if operator else None)
    @app.middleware('http')
    async def unavailable(request,call_next):
        # A missing operator cannot fall through to an ordinary identity DB.
        if operator is None:return JSONResponse({'detail':{'code':'OPERATOR_UNCONFIGURED'}},503,headers={'Cache-Control':'no-store'})
        return await call_next(request)
    def service():
        if operator is None:raise HTTPException(503,{'code':'OPERATOR_UNCONFIGURED'})
        return operator
    def call(fn):
        try:return fn()
        except RunError as e:raise HTTPException(e.status,{'code':e.code}) from None
        except (sqlite3.Error,OSError,ValueError,KeyError,TypeError):raise HTTPException(503,{'code':'OPERATOR_UNAVAILABLE_REVIEW_REQUIRED'}) from None
    @app.get('/api/research/operator/capabilities')
    def caps(p=Depends(require_principal),o=Depends(service)):return call(lambda:o.capabilities(p))
    @app.post('/api/research/operator/start',status_code=202)
    def start(body:RequestIdentity,p=Depends(require_principal),o=Depends(service)):
        return call(lambda:o.control(p,str(body.request_id),'start'))
    @app.get('/api/research/operator/runs/{run}')
    def runtime(run:UUID,p=Depends(require_principal),o=Depends(service)):
        return call(lambda:o.runtime(p,str(run)))
    @app.get('/api/research/operator/requests/{request}')
    def request_status(request:UUID,p=Depends(require_principal),o=Depends(service)):
        return call(lambda:o.request_status(p,str(request)))
    @app.post('/api/research/operator/runs/{run}/stop',status_code=202)
    def stop(run:UUID,body:RequestIdentity,p=Depends(require_principal),o=Depends(service)):
        return call(lambda:o.control(p,str(body.request_id),'stop',str(run)))
    assets=Path(__file__).resolve().parents[2]/'frontend/src/researchOperator'
    @app.get('/research/operator',response_class=HTMLResponse)
    def page():return HTMLResponse((assets/'console.html').read_text(encoding='utf-8'),headers={'Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"})
    @app.get('/research/operator.mjs')
    def script():return Response((assets/'console.mjs').read_bytes(),media_type='text/javascript')
    return app
