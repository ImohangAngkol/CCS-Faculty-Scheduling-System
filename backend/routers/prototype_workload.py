"""Separate opt-in fictional qualification host; never registered in main.py."""
from pathlib import Path
import sqlite3
from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from services.prototype_workload import Change, PolicyError
from services.preference_authorization import require_principal


def create_app(service=None, identity_db=None):
    app = FastAPI(title='Fictional workload qualification prototype')
    if service is not None and identity_db is not None:
        from routers.auth import router
        from services import auth_service
        from database import get_identity_db
        app.include_router(APIRouter(routes=[r for r in router.routes
            if r.path in {'/api/auth/login', '/api/auth/logout', '/api/auth/me'}]))
        app.dependency_overrides[get_identity_db] = identity_db
        app.dependency_overrides[auth_service.authenticated_db] = identity_db

    @app.middleware('http')
    async def isolated(request: Request, call_next):
        if not request.client or request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
            return JSONResponse({'detail': {'code': 'PROTOTYPE_LOOPBACK_REQUIRED'}}, 403)
        if request.url.path.startswith('/api/') and (service is None or identity_db is None):
            return JSONResponse({'detail': {'code': 'PROTOTYPE_UNCONFIGURED'}}, 503, headers={'Cache-Control': 'no-store'})
        reply = await call_next(request)
        reply.headers['Cache-Control'] = 'no-store'
        reply.headers['X-Content-Type-Options'] = 'nosniff'
        return reply

    @app.exception_handler(PolicyError)
    async def policy_error(_request, exc):
        return JSONResponse({'detail': {'code': exc.code}}, exc.status, headers={'Cache-Control': 'no-store'})

    @app.exception_handler(sqlite3.Error)
    async def database_error(_request, _exc):
        return JSONResponse({'detail': {'code': 'PROTOTYPE_STORAGE_UNAVAILABLE'}}, 503, headers={'Cache-Control': 'no-store'})

    @app.exception_handler(ValueError)
    async def invalid_evidence(_request, _exc):
        return JSONResponse({'detail': {'code': 'PROTOTYPE_EVIDENCE_INVALID'}}, 409, headers={'Cache-Control': 'no-store'})

    @app.get('/api/prototype/workload')
    def view(principal=Depends(require_principal)):
        return service.view(principal)

    @app.put('/api/prototype/workload')
    def save(change: Change, principal=Depends(require_principal)):
        return service.save(principal, change)

    assets = Path(__file__).resolve().parents[2] / 'frontend/src/prototypeWorkload'

    @app.get('/prototype/workload', response_class=HTMLResponse)
    def page():
        return HTMLResponse((assets / 'index.html').read_text(encoding='utf-8'), headers={
            'Content-Security-Policy': "default-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"})

    for filename, media in [('console.mjs', 'text/javascript'), ('model.mjs', 'text/javascript'), ('style.css', 'text/css')]:
        # No query parameters can select arbitrary files.
        app.add_api_route('/prototype/workload/' + filename,
                          (lambda name, kind: lambda: Response((assets / name).read_bytes(), media_type=kind))(filename, media),
                          methods=['GET'], include_in_schema=False)
    return app
