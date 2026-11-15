"""Separate fictional input desk. No ordinary main registration or run endpoint."""
from fastapi import Depends
from fastapi.responses import HTMLResponse, Response
from pathlib import Path
from services.preference_authorization import require_principal
from services.prototype_workload import require
from services.prototype_inputs import Weights, Preference, Freeze
from routers.prototype_workload import create_app as workload_app


def create_app(inputs=None, identity_db=None):
    app = workload_app(inputs.workload if inputs else None, identity_db)

    def configured():
        require(inputs is not None and identity_db is not None, 'INPUTS_UNCONFIGURED', 503)

    @app.get('/api/prototype/inputs/weights')
    def weights(principal=Depends(require_principal)):
        configured()
        return inputs.weights(principal)

    @app.post('/api/prototype/inputs/weights/approve')
    def approve(command: Weights, principal=Depends(require_principal)):
        configured()
        return inputs.approve_weights(principal, command)

    @app.get('/api/prototype/inputs/preferences/{code}')
    def preference(code: int, principal=Depends(require_principal)):
        configured()
        return inputs.preference(principal, code)

    @app.put('/api/prototype/inputs/preferences/{code}')
    def save(code: int, command: Preference, principal=Depends(require_principal)):
        configured()
        return inputs.save_preference(principal, code, command)

    @app.get('/api/prototype/inputs/selection')
    def selection(principal=Depends(require_principal)):
        configured()
        return inputs.selection(principal)

    @app.post('/api/prototype/inputs/prepare')
    def prepare(command: Freeze, principal=Depends(require_principal)):
        configured()
        return inputs.prepare(principal, command)

    @app.get('/api/prototype/inputs/prepared/{identity}')
    def prepared(identity: str, principal=Depends(require_principal)):
        configured()
        return inputs.prepared(principal, identity)

    assets = Path(__file__).resolve().parents[2]/'frontend/src/prototypeInputs'

    @app.get('/prototype/inputs', response_class=HTMLResponse)
    def page():
        return HTMLResponse((assets/'index.html').read_text(encoding='utf-8'), headers={
            'Content-Security-Policy': "default-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"})

    for name in ['model.mjs', 'console.mjs']:
        app.add_api_route('/prototype/inputs/'+name,
            (lambda filename: lambda: Response((assets/filename).read_bytes(), media_type='text/javascript'))(name),
            methods=['GET'], include_in_schema=False)

    return app
