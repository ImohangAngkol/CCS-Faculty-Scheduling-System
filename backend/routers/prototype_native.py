"""Opt-in, versioned bounded segment API; ordinary main.py is untouched."""
from fastapi import Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from routers.prototype_cycle import create_app as cycle_app
from services.preference_authorization import require_principal
from services.prototype_native_adapter import NativeAdapter
from services.prototype_workload import require


class Segment(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    request_id: str


def create_app(adapter=None, identity_db=None):
    require(adapter is None or type(adapter) is NativeAdapter, 'NATIVE_SERVER_ADAPTER_REQUIRED')
    app = cycle_app(adapter.cycle if adapter else None, identity_db)

    def configured():
        require(adapter is not None and identity_db is not None, 'NATIVE_ADAPTER_UNCONFIGURED', 503)

    @app.get('/api/prototype/native-v1/runs/{run}')
    def status(run: str, principal=Depends(require_principal)):
        configured();return adapter.status(principal, run)

    @app.post('/api/prototype/native-v1/runs/{run}/segment')
    def segment(run: str, command: Segment, principal=Depends(require_principal)):
        configured();return adapter.step(principal, run, command.request_id)

    @app.post('/api/prototype/native-v1/runs/{run}/recover')
    def recover(run: str, principal=Depends(require_principal)):
        configured();return adapter.recover(principal, run)

    @app.get('/api/prototype/native-v1/runs/{run}/export/{kind}')
    def export(run: str, kind: str, principal=Depends(require_principal)):
        configured();raw=adapter.export_run(principal,run,kind)
        return Response(raw,media_type={'json':'application/json','csv':'text/csv','txt':'text/plain'}[kind],
            headers={'Cache-Control':'no-store','Content-Disposition':f'attachment; filename="fictional-native-protocol.{kind}"'})

    return app
