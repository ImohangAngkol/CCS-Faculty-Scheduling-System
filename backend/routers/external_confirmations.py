"""Independent D9 ledger API; existing real admin/session/Origin/CSRF guards."""
from uuid import UUID
from fastapi import APIRouter,Depends
from sqlalchemy.exc import IntegrityError,OperationalError,SQLAlchemyError
from database import get_identity_db
from services.auth_service import authenticated_session
from services.preference_authorization import require_admin
from services import external_confirmation_service as ledger
from schemas.external_confirmation import ProposedRevision,ConfirmationCommand,RevocationCommand
from routers.external_schedules import review_payload
from fastapi import Request

router=APIRouter(prefix='/api/external-confirmations',tags=['GEC confirmation ledger'],dependencies=[Depends(require_admin)])


def execute(action):
    try:return action()
    except IntegrityError:ledger.fail('DUPLICATE_OR_STALE_OPERATION','Operation identifier or revision conflicts with the current ledger.',409)
    except OperationalError:ledger.fail('LEDGER_UNAVAILABLE','Ledger unavailable or concurrent write conflict. Reload history before retrying.',503)
    except SQLAlchemyError:ledger.fail('LEDGER_UNAVAILABLE','Confirmation persistence is unavailable; no success is claimed.',503)


@router.get('')
def records(db=Depends(get_identity_db)):return execute(lambda:ledger.list_records(db))


@router.get('/records/{record_id}')
def history(record_id:UUID,db=Depends(get_identity_db)):return execute(lambda:ledger.history(db,record_id))


@router.get('/revisions/{revision_id}')
def revision(revision_id:UUID,db=Depends(get_identity_db)):return execute(lambda:ledger.revision_detail(db,revision_id))


@router.post('/revisions')
async def propose(request:Request,db=Depends(get_identity_db),account=Depends(authenticated_session)):
    body=await review_payload(request,ProposedRevision)
    return execute(lambda:ledger.propose(db,body,account))


@router.post('/revisions/{revision_id}/{operation}')
async def decision(revision_id:UUID,operation:str,request:Request,db=Depends(get_identity_db),account=Depends(authenticated_session)):
    if operation not in {'validate','request-confirmation','confirm'}:ledger.fail('UNKNOWN_OPERATION','Unknown confirmation operation.',404)
    body=await review_payload(request,ConfirmationCommand)
    return execute(lambda:(ledger.confirm if operation=='confirm' else ledger.request_confirmation)(db,revision_id,body,account))


@router.post('/records/{record_id}/revoke')
async def revoke(record_id:UUID,request:Request,db=Depends(get_identity_db),account=Depends(authenticated_session)):
    body=await review_payload(request,RevocationCommand)
    return execute(lambda:ledger.revoke(db,record_id,body,account))
