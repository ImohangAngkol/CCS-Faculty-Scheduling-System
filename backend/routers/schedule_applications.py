from uuid import UUID
from fastapi import APIRouter,Depends,Request
from database import get_identity_db
from services.auth_service import authenticated_session
from routers.external_schedules import review_payload
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from schemas.schedule_applications import ApplicationCommand
from services import schedule_application_service as service,application_authority_service as authority
from services.schedule_service import problem

router=APIRouter(prefix='/api/schedule-applications',tags=['Controlled schedule application'])

def execute(db,action):
    try:return action()
    except IntegrityError:
        db.rollback()
        raise problem(409,'APPLICATION_CONCURRENT_UPDATE','An application or publication won this transaction, or persistence rejected it. Reload before retrying.') from None
    except SQLAlchemyError:
        db.rollback()
        raise problem(503,'APPLICATION_STORAGE_UNAVAILABLE','Publication persistence is unavailable. No successful application is claimed.') from None

@router.get('/access')
def access(account=Depends(authenticated_session)):
    with authority.authorized(account[0]) as (directory,grant):
        authority.recheck(directory,grant,account[0])
        return {'capability':'schedule_application','departments':[{'id':id,'label':label} for id,label in grant.departments]}

@router.get('')
def queue(include_applied:bool=False,account=Depends(authenticated_session),db=Depends(get_identity_db)):
    return execute(db,lambda:service.queue(db,account[0],include_applied))

@router.get('/versions')
def versions(version_id:UUID|None=None,account=Depends(authenticated_session),db=Depends(get_identity_db)):
    return execute(db,lambda:service.versions(db,account[0],version_id))

@router.get('/{request_id}/preview')
def preview(request_id:UUID,account=Depends(authenticated_session),db=Depends(get_identity_db)):
    return execute(db,lambda:service.preview(db,account[0],request_id))

@router.get('/{request_id}/status')
def status(request_id:UUID,account=Depends(authenticated_session),db=Depends(get_identity_db)):
    return preview(request_id,account,db)

@router.get('/{request_id}/history')
def history(request_id:UUID,account=Depends(authenticated_session),db=Depends(get_identity_db)):
    result=preview(request_id,account,db)
    return {'applications':[result['application']] if result['application'] else []}

@router.post('/{request_id}/apply')
async def apply(request_id:UUID,request:Request,account=Depends(authenticated_session),db=Depends(get_identity_db)):
    with authority.authorized(account[0]):pass
    body=await review_payload(request,ApplicationCommand)
    return execute(db,lambda:service.apply(db,account[0],request_id,body))
