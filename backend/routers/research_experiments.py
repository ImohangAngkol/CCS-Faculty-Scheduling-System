"""Opt-in research page and GET-only exports; E owns every execution route."""
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import UUID
from fastapi import Depends,HTTPException
from fastapi.responses import HTMLResponse,Response
from routers.research_operator import create_app as operator_app
from services.ga_research_experiments import Experiments
from services.preference_authorization import require_principal
from services.ga_run_authority import RunError


def create_app(operator=None):
    app=operator_app(operator);service=Experiments(operator) if operator else None
    def current():
        if service is None:raise HTTPException(503,{'code':'EXPERIMENT_UNAVAILABLE'})
        return service
    def call(fn):
        try:return fn()
        except RunError as e:raise HTTPException(e.status,{'code':e.code}) from None
        except (OSError,sqlite3.Error,ValueError,TypeError,KeyError,OverflowError):raise HTTPException(409,{'code':'EXPERIMENT_EVIDENCE_REJECTED'}) from None
    @app.get('/api/research/experiments/context')
    def context(p=Depends(require_principal),s=Depends(current)):return call(lambda:s.context(p))
    @app.get('/api/research/experiments/runs/{run}')
    def detail(run:UUID,p=Depends(require_principal),s=Depends(current)):return call(lambda:s.view(p,str(run)))
    @app.get('/api/research/experiments/runs/{run}/exports/{kind}')
    def export(run:UUID,kind:Literal['json','csv','txt'],p=Depends(require_principal),s=Depends(current)):
        raw,experiment=call(lambda:s.export(p,str(run),kind))
        return Response(raw,media_type={'json':'application/json','csv':'text/csv','txt':'text/plain'}[kind],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Disposition':f'attachment; filename="fictional-experiment-{experiment}.{kind}"'})
    assets=Path(__file__).resolve().parents[2]/'frontend/src'
    @app.get('/research/experiments',response_class=HTMLResponse)
    def page():
        html=(assets/'researchOperator/console.html').read_text(encoding='utf-8')
        panel=(assets/'researchExperiments/panel.html').read_text(encoding='utf-8')
        assert html.count('</main>')==1 and html.count('src="/research/operator.mjs"')==1
        html=html.replace('</main>',panel+'</main>').replace('src="/research/operator.mjs"','src="/research/experiment.mjs"')
        return HTMLResponse(html,headers={'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'"})
    @app.get('/research/experiment.mjs')
    def script():return Response((assets/'researchExperiments/console.mjs').read_bytes(),media_type='text/javascript')
    @app.get('/research/experiment-model.mjs')
    def model():return Response((assets/'researchExperiments/model.mjs').read_bytes(),media_type='text/javascript')
    return app
