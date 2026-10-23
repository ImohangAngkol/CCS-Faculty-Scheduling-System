"""D9 transactional ledger. No GA imports, file storage, startup DDL or engines."""
from datetime import datetime,timezone
import hashlib
import json
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select,func
from confirmation_models import ExternalRecord,ExternalRevision,ConfirmationEvent
from services import external_schedule_readiness_service as readiness, external_schedule_preview_lifecycle as life
from services import confirmation_authority_service as authority
from services.evidence_sanitization import sanitize_tree,sanitize


def fail(code,message,status=409):raise HTTPException(status,{'code':code,'message':message})
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def timestamp(value):return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).isoformat()
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()


def checked_evidence(value,expected=None):
    try:evidence=json.loads(value)
    except ValueError:fail('LEDGER_INTEGRITY','Stored evidence integrity could not be established.',503)
    if expected is not None and digest(evidence)!=expected:
        fail('LEDGER_INTEGRITY','Stored evidence digest mismatch.',503)
    return evidence


def safe_reason(value):
    if not value.strip() or sanitize(value)!=value:fail('UNSAFE_REASON','Provide a reason without credentials or session artifacts.',422)
    return value.strip()


def fresh(review,account):
    handoff=readiness.prepare_handoff(review,life.owner(account))
    content={'version':'d9.1','review':handoff.review.model_dump(),'metadata':handoff.readiness.metadata.model_dump(),
             'candidate':handoff.readiness.effective_review.model_dump()}
    if sanitize_tree(content)!=content or len(canonical(content).encode())>524288:
        fail('UNSAFE_OR_OVERSIZED_SNAPSHOT','Split the proposal or remove sensitive data; nothing was stored.',422)
    return content,handoff.readiness


def record_for(db,record_id,lock=False):
    query=select(ExternalRecord).where(ExternalRecord.id==record_id)
    if lock:query=query.with_for_update()
    result=db.scalar(query)
    if result is None:fail('RECORD_NOT_FOUND','Unknown GEC record.',404)
    return result


def checked_revision(db,revision_id):
    revision=db.get(ExternalRevision,revision_id)
    if revision is None:fail('REVISION_NOT_FOUND','Unknown GEC revision.',404)
    try:content=json.loads(revision.content_json)
    except ValueError:fail('LEDGER_INTEGRITY','Revision integrity could not be established.',503)
    if digest(content)!=revision.content_digest:fail('LEDGER_INTEGRITY','Revision content digest mismatch.',503)
    return revision,content


def propose(db,payload,account):
    reason=safe_reason(payload.reason)
    with life._lock,db.begin():
        content,result=fresh(payload.review,account)
        record=db.get(ExternalRecord,payload.record_id)
        meta=result.metadata
        if record is None:
            if payload.expected_version!=0:fail('STALE_VERSION','A new record must use version zero.')
            record=ExternalRecord(id=payload.record_id,academic_year=meta.academic_year,term=meta.term,supplier=meta.supplier,version=0)
            db.add(record);db.flush()
        else:record=record_for(db,payload.record_id,True)
        if record.version!=payload.expected_version:fail('STALE_VERSION','Reload the current record before proposing a revision.')
        if (record.academic_year,record.term,record.supplier)!=(meta.academic_year,meta.term,meta.supplier):
            fail('RECORD_SCOPE_MISMATCH','A revision cannot change its record academic year, term or supplier.',422)
        if not all((meta.academic_year,meta.term,meta.supplier)):fail('RECORD_SCOPE_REQUIRED','Complete the sourced year, term and supplier first.',422)
        if db.scalar(select(func.count()).select_from(ExternalRevision).where(ExternalRevision.record_id==record.id))>=200:
            fail('REVISION_LIMIT','This prototype record has reached its bounded revision limit.',422)
        db.add(ExternalRevision(id=payload.revision_id,record_id=record.id,base_event_id=record.head_event_id,
            created_by=account[0].id,reason=reason,content_json=canonical(content),content_digest=digest(content),
            evidence_json=canonical(result.evidence_trust.model_dump())))
        db.flush()
    return {'revision_id':str(payload.revision_id),'record_id':str(payload.record_id),'state':'PROPOSED','persisted':True,'activated':False}


def eligibility(db,revision_id,payload,account):
    revision,stored=checked_revision(db,revision_id);record=record_for(db,revision.record_id,True)
    if record.version!=payload.expected_version or record.head_event_id!=revision.base_event_id:
        fail('STALE_VERSION','This proposal is based on a prior decision. Prepare a new revision against the current record.')
    content,result=fresh(payload.review,account)
    if digest(content)!=revision.content_digest:fail('PROPOSAL_CHANGED','Current review does not match the stored proposal. Create a new revision.')
    if result.status!='READY' or result.evidence_trust.outcome!='VERIFIED':
        return revision,record,result,None,'EVIDENCE_NOT_READY'
    ctx=authority.ConfirmationContext(str(account[0].id),'CONFIRM',str(payload.operation_id),str(record.id),str(revision.id),
        record.version,record.academic_year,record.term,record.supplier,revision.content_digest,digest(result.evidence_trust.model_dump()))
    grant=authority.require_authority(ctx)
    return revision,record,result,grant,None if grant else 'CONFIRMATION_AUTHORITY_UNAVAILABLE'


def request_confirmation(db,revision_id,payload,account):
    with life._lock,db.begin():
        revision,record,result,grant,blocker=eligibility(db,revision_id,payload,account)
        return {'revision_id':str(revision.id),'eligible':grant is not None,'state':'ELIGIBLE' if grant else 'BLOCKED',
            'blocker':blocker,'evidence_trust':result.evidence_trust.model_dump(),'readiness':result.status,
            'message':'Confirmation is a separate server-authorized operation.' if grant else 'Fresh trusted evidence and independent institutional confirmation authority are required.',
            'persisted':False,'activated':False}


def confirm(db,revision_id,payload,account):
    reason=safe_reason(payload.reason)
    with life._lock,db.begin():
        revision,record,result,grant,blocker=eligibility(db,revision_id,payload,account)
        if grant is None:fail(blocker,'Confirmation is blocked; no independent authorized institutional decision was established.',403)
        evidence=result.evidence_trust.model_dump()
        event=ConfirmationEvent(id=payload.operation_id,record_id=record.id,revision_id=revision.id,previous_event_id=record.head_event_id,
            sequence=record.version+1,action='CONFIRM',actor_id=account[0].id,reason=reason,
            policy_reference=grant.policy_reference,policy_digest=grant.policy_digest,evidence_digest=digest(evidence),
            content_digest=revision.content_digest,evidence_json=canonical(evidence))
        db.add(event);db.flush()  # DB guards atomically advance the head.
    return {'event_id':str(payload.operation_id),'state':'CONFIRMED','activated':False,'persisted':True}


def revoke(db,record_id,payload,account):
    reason=safe_reason(payload.reason)
    with db.begin():
        record=record_for(db,record_id,True)
        if record.version!=payload.expected_version:fail('STALE_VERSION','Reload the current record before revocation.')
        head=db.get(ConfirmationEvent,record.head_event_id) if record.head_event_id else None
        if head is None or head.action!='CONFIRM':fail('NO_CURRENT_CONFIRMATION','There is no current confirmed revision to revoke.')
        revision,_=checked_revision(db,head.revision_id)
        checked_evidence(head.evidence_json,head.evidence_digest)
        ctx=authority.ConfirmationContext(str(account[0].id),'REVOKE',str(payload.operation_id),str(record.id),str(revision.id),record.version,
            record.academic_year,record.term,record.supplier,revision.content_digest,head.evidence_digest)
        grant=authority.require_authority(ctx)
        if grant is None:fail('CONFIRMATION_AUTHORITY_UNAVAILABLE','Independent revocation authority is required.',403)
        db.add(ConfirmationEvent(id=payload.operation_id,record_id=record.id,revision_id=revision.id,previous_event_id=head.id,
            sequence=record.version+1,action='REVOKE',actor_id=account[0].id,reason=reason,policy_reference=grant.policy_reference,
            policy_digest=grant.policy_digest,evidence_digest=head.evidence_digest,content_digest=revision.content_digest,evidence_json=head.evidence_json))
        db.flush()
    return {'event_id':str(payload.operation_id),'state':'REVOKED','persisted':True,'activated':False}


def summary(db,record):
    head=db.get(ConfirmationEvent,record.head_event_id) if record.head_event_id else None
    return {'id':str(record.id),'academic_year':record.academic_year,'term':record.term,'supplier':record.supplier,'version':record.version,
        'head_event_id':str(record.head_event_id) if record.head_event_id else None,'status':'CONFIRMED' if head and head.action=='CONFIRM' else 'REVOKED' if head else 'PROPOSED',
        'current_revision_id':str(head.revision_id) if head and head.action=='CONFIRM' else None,
        'current_evidence_status':'NOT_RECHECKED','activated':False}


def list_records(db):
    rows=db.scalars(select(ExternalRecord).order_by(ExternalRecord.created_at.desc()).limit(101)).all()
    return {'records':[summary(db,r) for r in rows[:100]],'has_more':len(rows)>100,'confirmation_policy':'Independent provider required; admin role alone cannot confirm.','activated':False}


def history(db,record_id):
    record=record_for(db,record_id);events=db.scalars(select(ConfirmationEvent).where(ConfirmationEvent.record_id==record_id).order_by(ConfirmationEvent.sequence)).all()
    revisions=db.scalars(select(ExternalRevision).where(ExternalRevision.record_id==record_id).order_by(ExternalRevision.created_at)).all()
    if len(events)>1000 or len(revisions)>200:fail('HISTORY_LIMIT','History exceeds this prototype response bound.',503)
    if record.version!=len(events) or (events[-1].id if events else None)!=record.head_event_id:
        fail('LEDGER_INTEGRITY','Decision head or event count mismatch.',503)
    for i,event in enumerate(events):
        if event.sequence!=i+1 or event.previous_event_id!=(events[i-1].id if i else None):
            fail('LEDGER_INTEGRITY','Decision chain mismatch.',503)
        revision,_=checked_revision(db,event.revision_id)
        checked_evidence(event.evidence_json,event.evidence_digest)
        if event.content_digest!=revision.content_digest:
            fail('LEDGER_INTEGRITY','Historical decision digest mismatch.',503)
    return {'record':summary(db,record),'events':[{'id':str(e.id),'revision_id':str(e.revision_id),'previous_event_id':str(e.previous_event_id) if e.previous_event_id else None,
        'sequence':e.sequence,'action':e.action,'actor_id':str(e.actor_id),'policy_reference':e.policy_reference,'policy_digest':e.policy_digest,
        'content_digest':e.content_digest,'evidence_digest':e.evidence_digest,'created_at':timestamp(e.created_at),'reason':e.reason} for e in events],
        'revisions':[{'id':str(r.id),'base_event_id':str(r.base_event_id) if r.base_event_id else None,'content_digest':r.content_digest,
            'reason':r.reason,'created_at':timestamp(r.created_at),'state':'CONFIRMED' if any(e.revision_id==r.id and e.id==record.head_event_id and e.action=='CONFIRM' for e in events)
            else 'REVOKED' if any(e.revision_id==r.id and e.id==record.head_event_id and e.action=='REVOKE' for e in events) else 'SUPERSEDED' if any(e.revision_id==r.id for e in events) else 'PROPOSED'} for r in revisions]}


def revision_detail(db,revision_id):
    revision,content=checked_revision(db,revision_id)
    return {'id':str(revision.id),'record_id':str(revision.record_id),'content_digest':revision.content_digest,'content':content,
            'evidence_at_proposal':checked_evidence(revision.evidence_json),'current_evidence_status':'NOT_RECHECKED','activated':False}
