"""Opt-in fictional host only; no registration or provider in ordinary main."""
from pathlib import Path
from fastapi import Depends
from fastapi.responses import HTMLResponse, JSONResponse, Response
from routers.prototype_workload import create_app as workload_app
from services.preference_authorization import require_principal
from services.prototype_scheduling import Submission
from services.prototype_workload import require
from services.ga_run_authority import RunError


def create_app(service=None, identity_db=None):
    app = workload_app(service.workload if service else None, identity_db)

    def configured():
        require(service is not None and identity_db is not None, 'PROTOTYPE_UNCONFIGURED', 503)

    @app.exception_handler(RunError)
    async def run_error(_request, exc):
        return JSONResponse({'detail': {'code': exc.code}}, exc.status, headers={'Cache-Control': 'no-store'})

    @app.get('/api/prototype/scheduling/context')
    def context(principal=Depends(require_principal)):
        configured()
        return service.context(principal)

    @app.post('/api/prototype/scheduling/runs')
    def submit(request: Submission, principal=Depends(require_principal)):
        configured()
        result = service.submit(principal, request)
        code = 409 if result['state'] in {'INPUT_INFEASIBLE', 'RESOURCE_BLOCKED'} else 202
        return JSONResponse(result, code)

    @app.get('/api/prototype/scheduling/runs/{run}')
    def inspect(run: str, principal=Depends(require_principal)):
        configured()
        return service.inspect(principal, run)

    @app.get('/api/prototype/scheduling/requests/{nonce}')
    def lookup(nonce: str, principal=Depends(require_principal)):
        configured()
        return service.lookup(principal, nonce)

    assets = Path(__file__).resolve().parents[2] / 'frontend/src/prototypeScheduling'

    @app.get('/prototype/scheduling', response_class=HTMLResponse)
    def page():
        return HTMLResponse((assets / 'index.html').read_text(encoding='utf-8'), headers={
            'Content-Security-Policy': "default-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"})

    for filename in ['console.mjs', 'model.mjs']:
        app.add_api_route('/prototype/scheduling/' + filename,
            (lambda name: lambda: Response((assets / name).read_bytes(), media_type='text/javascript'))(filename),
            methods=['GET'], include_in_schema=False)
    return app
