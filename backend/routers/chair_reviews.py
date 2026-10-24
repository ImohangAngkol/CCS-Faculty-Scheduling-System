"""Independent institutional Chair mandate; account roles alone never suffice."""
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from database import get_identity_db
from routers.external_schedules import review_payload
from schemas.chair_reviews import DecisionCommand
from services.auth_service import authenticated_session
from services import chair_review_service as service, chair_authority_service as authority
from services.schedule_service import problem

router = APIRouter(prefix='/api/chair-reviews', tags=['Department Chair reviews'])


def execute(db, action):
    try: return action()
    except IntegrityError:
        db.rollback()
        raise problem(409, 'CHAIR_CONCURRENT_DECISION', 'A decision or withdrawal won this transaction. Reload before retrying.') from None
    except SQLAlchemyError:
        db.rollback()
        raise problem(503, 'CHAIR_STORAGE_UNAVAILABLE', 'Decision storage is unavailable. No successful decision is claimed; reload before retrying.') from None


@router.get('/access')
def access(account=Depends(authenticated_session)):
    with authority.authorized(account[0]) as (directory, grant):
        authority.recheck(directory, grant, account[0])
        return {'capability':'department_chair', 'departments':[{'id':id,'label':label} for id,label in grant.departments]}


@router.get('')
def pending(department_id: UUID | None = None, include_decided: bool = False, account=Depends(authenticated_session), db=Depends(get_identity_db)):
    return execute(db, lambda: service.pending(db, account[0], str(department_id) if department_id else None, include_decided))


@router.get('/{request_id}')
def review(request_id: UUID, account=Depends(authenticated_session), db=Depends(get_identity_db)):
    return execute(db, lambda: service.review(db, account[0], request_id))


@router.get('/{request_id}/history')
def history(request_id: UUID, account=Depends(authenticated_session), db=Depends(get_identity_db)):
    result = review(request_id, account, db)
    return {'history':result['decision_history'], 'schedule_changed':False}


@router.get('/{request_id}/status')
def status(request_id: UUID, account=Depends(authenticated_session), db=Depends(get_identity_db)):
    result = review(request_id, account, db)
    return {'status':result['request']['status'], 'decision_history':result['decision_history'], 'schedule_changed':False}


@router.post('/{request_id}/{action}')
async def decide(request_id: UUID, action: str, request: Request, account=Depends(authenticated_session), db=Depends(get_identity_db)):
    # Verify authority before parsing or inspecting private request content.
    with authority.authorized(account[0]): pass
    if action not in {'approve','reject'}: raise problem(404, 'CHAIR_UNKNOWN_ACTION', 'Only approval and rejection are supported.')
    body = await review_payload(request, DecisionCommand)
    return execute(db, lambda: service.decide(db, account[0], request_id, action.upper(), body))
