"""Faculty-only request APIs. No Chair decisions or schedule writes."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from database import get_identity_db
from routers.schedules import bound_faculty
from routers.external_schedules import review_payload
from schemas.adjustments import Create, Preview, Transition
from services import adjustment_service as service
from services.auth_service import authenticated_session
from services.schedule_service import problem

router = APIRouter(prefix='/api/adjustment-requests', tags=['Faculty adjustment requests'], dependencies=[Depends(bound_faculty)])


def execute(db, action):
    try:
        return action()
    except IntegrityError:
        db.rollback()
        raise problem(409, 'DUPLICATE_OR_CONCURRENT_REQUEST', 'An operation or active proposal already exists, or another update won. Reload your requests before retrying.') from None
    except SQLAlchemyError:
        db.rollback()
        raise problem(503, 'REQUEST_STORAGE_UNAVAILABLE', 'Request persistence is unavailable. No successful transition is claimed; reload before retrying.') from None


@router.get('/assignments')
def assignments(identity=Depends(bound_faculty)):
    return service.assignments(identity)


@router.post('/preview')
async def preview(request: Request, identity=Depends(bound_faculty)):
    body = await review_payload(request, Preview)
    return service.preview(identity, body)


@router.get('')
def listing(before: UUID | None = None, identity=Depends(bound_faculty), account=Depends(authenticated_session), db=Depends(get_identity_db)):
    return execute(db, lambda: service.listing(db, account[0], identity, before))


@router.post('', status_code=201)
async def create(request: Request, identity=Depends(bound_faculty), account=Depends(authenticated_session), db=Depends(get_identity_db)):
    body = await review_payload(request, Create)
    return execute(db, lambda: service.create(db, account[0], identity, body))


@router.get('/{request_id}')
def detail(request_id: UUID, identity=Depends(bound_faculty), account=Depends(authenticated_session), db=Depends(get_identity_db)):
    return execute(db, lambda: service.detail(db, service.owner(db, request_id, account[0], identity), identity))


@router.get('/{request_id}/history')
def history(request_id: UUID, identity=Depends(bound_faculty), account=Depends(authenticated_session), db=Depends(get_identity_db)):
    return {'history': detail(request_id, identity, account, db)['history']}


@router.get('/{request_id}/status')
def status(request_id: UUID, identity=Depends(bound_faculty), account=Depends(authenticated_session), db=Depends(get_identity_db)):
    result = detail(request_id, identity, account, db)
    return {k: result[k] for k in ('id', 'status', 'version', 'freshness', 'approval', 'schedule_changed')}


@router.post('/{request_id}/{action}')
async def transition(request_id: UUID, action: str, request: Request, identity=Depends(bound_faculty), account=Depends(authenticated_session), db=Depends(get_identity_db)):
    if action not in {'submit', 'withdraw'}:
        raise problem(404, 'UNKNOWN_REQUEST_ACTION', 'Only submission and withdrawal are implemented in D11.')
    body = await review_payload(request, Transition)
    return execute(db, lambda: service.transition(db, account[0], identity, request_id, action, body))
