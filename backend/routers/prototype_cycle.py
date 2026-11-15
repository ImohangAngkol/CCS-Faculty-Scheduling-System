"""Scoped observation/admission/review API. NO GA execution/recovery endpoint."""
from pathlib import Path
from fastapi import Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from routers.prototype_inputs import create_app as input_app
from services.prototype_cycle import Admission, Decision
from services.prototype_workload import require
from services.preference_authorization import require_principal


class Stop(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    request_id: str


def create_app(cycle=None, identity_db=None):
    app = input_app(cycle.inputs if cycle else None, identity_db)

    def configured():
        require(cycle is not None and identity_db is not None, 'CYCLE_UNCONFIGURED', 503)

    @app.get('/api/prototype/cycle/runs')
    def listing(principal=Depends(require_principal)):
        configured(); return cycle.listing(principal)

    @app.post('/api/prototype/cycle/admissions')
    def admit(command: Admission, principal=Depends(require_principal)):
        configured()
        result = cycle.admit(principal, command)
        return JSONResponse(result, 409 if result['state'] == 'INPUT_INFEASIBLE' else 201)

    @app.get('/api/prototype/cycle/runs/{run}')
    def detail(run: str, principal=Depends(require_principal)):
        configured(); return cycle.inspect(principal, run)

    @app.post('/api/prototype/cycle/runs/{run}/stop')
    def stop(run: str, command: Stop, principal=Depends(require_principal)):
        configured(); return cycle.request_stop(principal, run, command.request_id)

    @app.post('/api/prototype/cycle/runs/{run}/decision')
    def decide(run: str, command: Decision, principal=Depends(require_principal)):
        configured(); return cycle.decide(principal, run, command)

    @app.get('/api/prototype/cycle/compare/{left}/{right}')
    def compare(left: str, right: str, principal=Depends(require_principal)):
        configured(); return cycle.compare(principal, left, right)

    @app.get('/api/prototype/cycle/runs/{run}/export/{kind}')
    def research_export(run: str, kind: str, principal=Depends(require_principal)):
        configured()
        raw = cycle.export_run(principal, run, kind)
        return Response(raw, media_type={'json': 'application/json', 'csv': 'text/csv', 'txt': 'text/plain'}[kind],
            headers={'Content-Disposition': f'attachment; filename="fictional-research.{kind}"', 'Cache-Control': 'no-store'})

    @app.get('/api/prototype/cycle/versions')
    def versions(principal=Depends(require_principal)):
        configured(); return cycle.versions(principal)

    @app.get('/api/prototype/cycle/timetable/{code}')
    def timetable(code: int, principal=Depends(require_principal)):
        configured(); return cycle.timetable(principal, code)

    @app.get('/api/prototype/cycle/versions/{number}/export/{kind}')
    def export(number: int, kind: str, principal=Depends(require_principal)):
        configured()
        raw = cycle.export_version(principal, number, kind)
        return Response(raw, media_type={'json': 'application/json', 'csv': 'text/csv', 'txt': 'text/plain'}[kind],
            headers={'Content-Disposition': f'attachment; filename="fictional-prototype-{number}.{kind}"', 'Cache-Control': 'no-store'})

    assets = Path(__file__).resolve().parents[2]/'frontend/src/prototypeCycle'

    @app.get('/prototype/cycle', response_class=HTMLResponse)
    def page():
        return HTMLResponse((assets/'index.html').read_text(encoding='utf-8'), headers={
            'Content-Security-Policy': "default-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"})

    for name in ['model.mjs', 'console.mjs']:
        app.add_api_route('/prototype/cycle/'+name,
            (lambda filename: lambda: Response((assets/filename).read_bytes(), media_type='text/javascript'))(name),
            methods=['GET'], include_in_schema=False)
    return app
