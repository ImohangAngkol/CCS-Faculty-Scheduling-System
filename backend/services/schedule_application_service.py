"""D13 authorized immutable publication; no GA execution or file writes."""
from contextlib import ExitStack
from dataclasses import asdict,replace
import json
from types import SimpleNamespace
from uuid import UUID,uuid4
from sqlalchemy import select,update
from identity_models import User,now
from adjustment_models import AdjustmentRequest
from chair_models import ChairDecision
from application_models import PublishedHead,PublishedVersion,ScheduleApplication
from schemas.adjustments import Preview
from services import adjustment_service as requests, adjustment_schedule_service as schedules
from services import chair_authority_service as chair,chair_decision_projection as decisions,chair_review_service as chair_review
from services import application_authority_service as authority,published_schedule_source as publication,schedule_version_store as store
from services.schedule_service import problem


def target(db,ctx):
    with ctx.session_factory() as expected:
        if expected.get_bind().url!=db.get_bind().url:raise problem(503,'APPLICATION_TARGET_MISMATCH','Publication and identity storage targets differ. Application is blocked.')


def owned_scope(db,id,directory,grant,lock=False):
    record=db.get(AdjustmentRequest,id)
    if record is None:raise problem(404,'APPLICATION_REQUEST_NOT_FOUND','No request is available within your verified department scope.')
    binding=authority.scope(directory,grant,record)
    if lock:
        db.scalar(select(User).where(User.id==record.owner_id).with_for_update())
        record=db.scalar(select(AdjustmentRequest).where(AdjustmentRequest.id==id).with_for_update().execution_options(populate_existing=True))
    requests.verify(db,record)
    return record,binding


def eligible(db,record):
    decision=decisions.decision_for(db,record)
    if record.status!='SUBMITTED' or not decision or decision['status']!='APPROVED_PENDING_APPLICATION':
        raise problem(409,'APPLICATION_APPROVAL_REQUIRED','A valid immutable Chair approval for this submitted request is required.')
    return decision


def verify_chair(stack,db,record,decision):
    actor=db.get(User,UUID(decision['actor_id']))
    if actor is None or not actor.is_active:raise problem(409,'APPROVAL_AUTHORITY_UNAVAILABLE','The original approving account is unavailable.')
    directory,grant=stack.enter_context(chair.authorized(actor))
    binding=chair.scope(directory,grant,record);provenance=decision['provenance']
    if (binding.department_id!=decision['department_id'] or grant.reference!=provenance['mandate_reference']
        or grant.policy_digest!=provenance['policy_digest'] or binding.reference!=provenance['scope_reference']):
        raise problem(409,'APPROVAL_AUTHORITY_CHANGED','The approval authority or department policy changed. No historical approval is reinterpreted.')
    return lambda:chair.recheck(directory,grant,actor,record,binding)


def reviewed(stack,db,ctx,record,binding):
    decision=eligible(db,record)
    if binding.department_id!=decision['department_id']:raise problem(409,'APPROVAL_SCOPE_CHANGED','The approved department and current request scope differ.')
    chair_check=verify_chair(stack,db,record,decision)
    version,source,content=store.current(db,ctx,lock=True)
    owner=db.get(User,record.owner_id)
    if owner is None:raise problem(409,'APPLICATION_OWNER_UNAVAILABLE','The original faculty account is unavailable.')
    identity=SimpleNamespace(faculty_id=str(record.faculty_id))
    requests.verified_actor(db,owner,identity)
    body=Preview.model_validate(json.loads(record.content_json)['input'])
    # Keep findings reviewable rather than converting a full-policy discrepancy
    # into D12's generic approval rejection. The complete gate runs below.
    result=schedules.validate(replace(source,check_proposal=lambda *args:None),identity,body)
    if result['constraint_digest']!=decision['constraint_digest']:
        raise problem(409,'APPLICATION_GEC_CHANGED','The approved GEC constraint set changed; a new approval is required.')
    snapshot=chair_review.trusted_snapshot(db,source)
    original=next(m for m in source.meetings if m.id==result['original']['id'])
    proposed=replace(original,**result['proposal'])
    after=tuple(proposed if m.id==original.id else m for m in source.meetings)
    validation=publication.complete_validation(ctx,source,after)
    codes={f['code'] for f in validation['findings']}
    for finding in result['validation']['findings']:
        if finding['code'] not in codes:validation['findings'].append(finding)
    if validation['findings']:validation['outcome']='BLOCKED'
    source.check_current();chair_check()
    return {'decision':decision,'version':version,'source':source,'content':content,'result':result,'snapshot':snapshot,
        'after':after,'validation':validation,'chair_check':chair_check}


def queue(db,actor,include_applied=False):
    with authority.authorized(actor) as (directory,grant):
        rows=db.scalars(select(AdjustmentRequest).join(ChairDecision,ChairDecision.request_id==AdjustmentRequest.id).where(ChairDecision.action=='APPROVE').order_by(AdjustmentRequest.id).limit(1001)).all()
        if len(rows)>1000:raise problem(503,'APPLICATION_QUEUE_LIMIT','The entire application queue exceeds the supported bound.')
        items=[]
        for r in rows:
            try:binding=authority.scope(directory,grant,r)
            except Exception as error:
                from fastapi import HTTPException
                if isinstance(error,HTTPException) and error.status_code==404:continue
                raise
            requests.verify(db,r);decision=eligible(db,r);applied=store.application_for(db,r)
            if applied and not include_applied:continue
            c=json.loads(r.content_json)
            items.append({'id':str(r.id),'department_id':binding.department_id,'faculty_id':str(r.faculty_id),'subject':c['review']['original']['subject'],'section':c['review']['original']['section'],'status':'APPLIED' if applied else 'PENDING_APPLICATION','decision_id':decision['id']})
        authority.recheck(directory,grant,actor)
        return {'items':items}


def preview(db,actor,id):
    with ExitStack() as stack:
        directory,grant=stack.enter_context(authority.authorized(actor));ctx=stack.enter_context(publication.context());stack.enter_context(db.begin());chair_review.transaction(db);target(db,ctx)
        record,binding=owned_scope(db,id,directory,grant)
        applied=store.application_for(db,record)
        detail=requests.detail(db,record,SimpleNamespace(faculty_id=str(record.faculty_id)))
        if applied:
            authority.recheck(directory,grant,actor,record,binding)
            return {'request':detail,'application':applied,'can_apply':False,'status':'APPLIED','before':None,'after':None,'validation':None,'current':None,'command':None}
        r=reviewed(stack,db,ctx,record,binding);s=r['source'];v=r['version']
        authority.recheck(directory,grant,actor,record,binding)
        return {'request':detail,'application':None,'status':'PENDING_APPLICATION' if r['validation']['outcome']=='VALID' else 'APPLICATION_BLOCKED','can_apply':r['validation']['outcome']=='VALID',
            'before':r['result']['original'],'after':r['result']['proposal'],'validation':r['validation'],
            'current':{'id':str(v.id) if v else None,'sequence':v.sequence if v else 1,'revision':s.revision},
            'command':{'decision_id':r['decision']['id'],'decision_digest':r['decision']['payload_digest'],'expected_revision':s.revision,'expected_sequence':v.sequence if v else 1,'constraint_digest':s.constraint_digest}}


def apply(db,actor,id,body):
    command_digest=schedules.digest({'request_id':str(id),**body.model_dump(mode='json')})
    with ExitStack() as stack:
        directory,grant=stack.enter_context(authority.authorized(actor));ctx=stack.enter_context(publication.context());stack.enter_context(db.begin());chair_review.transaction(db);target(db,ctx)
        actor=db.scalar(select(User).where(User.id==actor.id).with_for_update().execution_options(populate_existing=True))
        if actor is None or not actor.is_active:raise problem(403,'APPLICATION_ACCOUNT_UNAVAILABLE','The authenticated application account is no longer active.')
        record,binding=owned_scope(db,id,directory,grant,lock=True)
        replay=db.scalar(select(ScheduleApplication).where(ScheduleApplication.actor_id==actor.id,ScheduleApplication.operation_id==body.operation_id))
        if replay:
            if replay.request_id!=id or replay.command_digest!=command_digest:raise problem(409,'APPLICATION_IDEMPOTENCY_MISMATCH','This operation key was used for a different application.')
            authority.recheck(directory,grant,actor,record,binding)
            return store.application_for(db,record)
        if store.application_for(db,record):raise problem(409,'ALREADY_APPLIED','This request already has a committed application.')
        r=reviewed(stack,db,ctx,record,binding);v=r['version'];s=r['source'];decision=r['decision'];sequence=v.sequence if v else 1
        if (str(body.decision_id)!=decision['id'] or body.decision_digest!=decision['payload_digest'] or body.expected_revision!=s.revision or body.expected_sequence!=sequence or body.constraint_digest!=s.constraint_digest):
            raise problem(409,'APPLICATION_REFERENCES_CHANGED','The approval or publication references changed. Preview again before applying.')
        if r['validation']['outcome']!='VALID':raise problem(409,'APPLICATION_SCHEDULE_INVALID','The complete resulting schedule has hard-constraint findings. Application is blocked.')
        stamp=now();key=publication.key(ctx)
        if v is None:
            content=store.base_content(ctx);v=PublishedVersion(id=uuid4(),schedule_key=key,sequence=1,revision=s.revision,previous_id=None,content_json=requests.canonical(content),content_digest=schedules.digest(content),created_at=stamp)
            db.add(v);db.flush();db.add(PublishedHead(schedule_key=key,version_id=v.id,sequence=1));db.flush()
        content={**r['content'],'origin':'POST_GA_AUTHORIZED_ADJUSTMENT','previous_revision':s.revision,'constraint_digest':s.constraint_digest,'meetings':[asdict(m) for m in r['after']]}
        new=PublishedVersion(id=uuid4(),schedule_key=key,sequence=sequence+1,revision=schedules.digest(content),previous_id=v.id,content_json=requests.canonical(content),content_digest=schedules.digest(content),created_at=stamp)
        db.add(new);db.flush()
        payload={'request_id':str(id),'decision_id':decision['id'],'decision_digest':decision['payload_digest'],'actor_id':str(actor.id),'department_id':binding.department_id,'operation_id':str(body.operation_id),'command_digest':command_digest,
            'previous_version_id':str(v.id),'new_version_id':str(new.id),'previous_revision':v.revision,'new_revision':new.revision,'academic_year':s.academic_year,'term':s.term,'constraint_digest':s.constraint_digest,'validation':r['validation'],'constraint_heads':[h.model_dump(mode='json') for h in r['snapshot'].heads],
            'application_authority_reference':grant.reference,'application_policy_digest':grant.policy_digest,'scope_reference':binding.reference,'publication_reference':ctx.publication_reference,'applied_at':stamp.isoformat(),'status':'APPLIED','GA_modified':False}
        db.add(ScheduleApplication(id=uuid4(),request_id=id,decision_id=UUID(decision['id']),actor_id=actor.id,department_id=UUID(binding.department_id),operation_id=body.operation_id,previous_version_id=v.id,new_version_id=new.id,command_digest=command_digest,payload_json=requests.canonical(payload),payload_digest=schedules.digest(payload),created_at=stamp));db.flush()
        changed=db.execute(update(PublishedHead).where(PublishedHead.schedule_key==key,PublishedHead.version_id==v.id,PublishedHead.sequence==sequence).values(version_id=new.id,sequence=sequence+1).execution_options(synchronize_session=False))
        if changed.rowcount!=1:raise problem(409,'PUBLISHED_VERSION_CHANGED','Another publication won. The application was rolled back.')
        s.check_current();r['chair_check']()
        if chair_review.trusted_snapshot(db,s).digest!=r['snapshot'].digest:raise problem(409,'APPLICATION_TRUST_CHANGED','Institutional trust changed before commit.')
        authority.recheck(directory,grant,actor,record,binding)
        result=store.application_for(db,record)
        # The original Chair guard was acquired during review, after begin().
        # Commit before ExitStack releases that guard, keeping all authority,
        # publication and trust leases held across the persistence boundary.
        db.commit()
    return result


def versions(db,actor,version_id=None):
    with authority.authorized(actor) as (directory,grant),publication.context() as ctx:
        target(db,ctx);current,source,_=store.current(db,ctx);ctx.source.check_current();key=publication.key(ctx)
        rows=db.scalars(select(PublishedVersion).where(PublishedVersion.schedule_key==key).order_by(PublishedVersion.sequence)).all()
        if version_id:rows=[row for row in rows if row.id==version_id]
        if version_id and not rows:raise problem(404,'PUBLISHED_VERSION_NOT_FOUND','No version is available within this publication scope.')
        result=[]
        for row in rows:
            _,content,meetings=store.checked_version(db,row.id,key);visible=[]
            for meeting in meetings:
                record=SimpleNamespace(faculty_id=meeting.faculty_id,content_json=requests.canonical({'review':{'original':asdict(meeting)},'input':{'academic_year':source.academic_year,'term':source.term}}))
                try:authority.scope(directory,grant,record);visible.append(asdict(meeting))
                except Exception as error:
                    from fastapi import HTTPException
                    if not isinstance(error,HTTPException) or error.status_code!=404:raise
            result.append({'id':str(row.id),'sequence':row.sequence,'revision':row.revision,'previous_id':str(row.previous_id) if row.previous_id else None,'origin':content['origin'],'meetings':visible,'department_filtered':True})
        authority.recheck(directory,grant,actor)
        return {'versions':result,'current_version_id':str(current.id) if current else None,'source_revision':source.revision,'read_only':True}
