"""Immutable D13 version chains. Reads never initialize or advance a head."""
from dataclasses import asdict,replace
import json
from sqlalchemy import select
from application_models import PublishedHead,PublishedVersion,ScheduleApplication
from services import adjustment_schedule_service as schedules
from services import published_schedule_source as publication
from services.schedule_service import problem


def base_content(ctx):
    source=ctx.source
    return {'contract':'published-schedule-d13.1','schedule_id':source.schedule_id,'academic_year':source.academic_year,'term':source.term,
        'constraint_digest':source.constraint_digest,'publication_reference':ctx.publication_reference,'origin_revision':source.revision,
        'previous_revision':None,'origin':'VERIFIED_PUBLISHED_SOURCE','meetings':[asdict(m) for m in source.meetings]}


def checked_version(db,id,key):
    row=db.get(PublishedVersion,id)
    try:
        if row is None or row.schedule_key!=key:raise ValueError()
        content=json.loads(row.content_json)
        if schedules.digest(content)!=row.content_digest or content['contract']!='published-schedule-d13.1':raise ValueError()
        if row.sequence==1:
            if row.previous_id is not None or row.revision!=content['origin_revision'] or content['previous_revision'] is not None:raise ValueError()
        else:
            parent=db.get(PublishedVersion,row.previous_id)
            if parent is None or parent.schedule_key!=key or parent.sequence!=row.sequence-1 or parent.revision!=content['previous_revision'] or row.revision!=row.content_digest:raise ValueError()
        meetings=tuple(schedules.Meeting(**m) for m in content['meetings'])
        if len({m.id for m in meetings})!=len(meetings):raise ValueError()
        return row,content,meetings
    except (ValueError,KeyError,TypeError):raise problem(503,'PUBLISHED_VERSION_INTEGRITY','Published schedule version integrity could not be verified.') from None


def current(db,ctx,lock=False):
    key=publication.key(ctx);query=select(PublishedHead).where(PublishedHead.schedule_key==key)
    if lock:query=query.with_for_update().execution_options(populate_existing=True)
    head=db.scalar(query)
    if head is None:return None,with_validator(ctx,ctx.source),base_content(ctx)
    if head.sequence>1000:raise problem(503,'PUBLISHED_HISTORY_LIMIT','The complete version history exceeds the supported bound.')
    row,content,meetings=checked_version(db,head.version_id,key)
    cursor=row
    while cursor.previous_id:
        application=db.scalar(select(ScheduleApplication).where(ScheduleApplication.new_version_id==cursor.id))
        if application is None:raise problem(503,'PUBLISHED_VERSION_INTEGRITY','A publication has no authorized application record.')
        from adjustment_models import AdjustmentRequest
        record=db.get(AdjustmentRequest,application.request_id)
        from services.adjustment_service import verify
        verify(db,record);application_for(db,record)
        parent,_,_=checked_version(db,cursor.previous_id,key);cursor=parent
    _,base,_=checked_version(db,cursor.id,key)
    identity=lambda c:{k:v for k,v in c.items() if k!='constraint_digest'}
    if identity(base)!=identity(base_content(ctx)) or row.sequence!=head.sequence:
        raise problem(409,'PUBLISHED_ORIGIN_CHANGED','The authoritative published origin changed. No automatic rebase or replacement is permitted.')
    return row,with_validator(ctx,replace(ctx.source,revision=row.revision,meetings=meetings)),content


def with_validator(ctx,source):
    def validate(original,proposal):
        changed=tuple(replace(m,**proposal.model_dump()) if m.id==original.id else m for m in source.meetings)
        if publication.complete_validation(ctx,source,changed)['outcome']!='VALID':raise ValueError('Complete schedule validation failed')
    return replace(source,check_proposal=validate)


def application_for(db,record):
    row=db.scalar(select(ScheduleApplication).where(ScheduleApplication.request_id==record.id))
    if row is None:return None
    try:
        from services.chair_decision_projection import decision_for
        decision=decision_for(db,record);payload=json.loads(row.payload_json)
        if not decision or decision['action']!='APPROVE' or decision['id']!=str(row.decision_id) or schedules.digest(payload)!=row.payload_digest or payload['decision_digest']!=decision['payload_digest']:raise ValueError()
        for k,v in {'request_id':str(record.id),'decision_id':str(row.decision_id),'actor_id':str(row.actor_id),'department_id':str(row.department_id),'operation_id':str(row.operation_id),'previous_version_id':str(row.previous_version_id),'new_version_id':str(row.new_version_id),'command_digest':row.command_digest}.items():
            if payload[k]!=v:raise ValueError()
        old=db.get(PublishedVersion,row.previous_version_id);new=db.get(PublishedVersion,row.new_version_id)
        if old is None or new is None or new.previous_id!=old.id or old.revision!=payload['previous_revision'] or new.revision!=payload['new_revision']:raise ValueError()
        _,before,meetings=checked_version(db,old.id,old.schedule_key);_,after,result=checked_version(db,new.id,new.schedule_key)
        content=json.loads(record.content_json);body=content['input'];proposal=body['proposal']
        expected=tuple(replace(m,**proposal) if m.id==body['assignment_id'] else m for m in meetings)
        if expected!=result or not any(m.id==body['assignment_id'] and m.faculty_id==str(record.faculty_id) for m in meetings):raise ValueError()
        if (payload['previous_revision']!=body['revision'] or payload['constraint_digest']!=content['review']['constraint_digest']
            or payload['department_id']!=decision['department_id'] or payload['status']!='APPLIED'
            or after!={**before,'origin':'POST_GA_AUTHORIZED_ADJUSTMENT','previous_revision':old.revision,'constraint_digest':payload['constraint_digest'],'meetings':[asdict(m) for m in expected]}):raise ValueError()
        return {'id':str(row.id),'status':'APPLIED','applied_at':payload['applied_at'],'previous_version_id':str(old.id),'new_version_id':str(new.id),'previous_revision':old.revision,'new_revision':new.revision,'sequence':new.sequence,'constraint_digest':payload['constraint_digest'],'payload_digest':row.payload_digest,'schedule_changed':True}
    except (ValueError,KeyError,TypeError):raise problem(503,'APPLICATION_INTEGRITY_FAILED','The retained application record could not be verified.') from None
