"""Own-account and D11 source projections, without promoting legacy GA files."""
from contextlib import contextmanager
from dataclasses import replace
from services import published_schedule_source as publication,schedule_version_store as store
from services.schedule_service import problem


@contextmanager
def review_context():
    with publication.context(required=False) as ctx:
        if ctx is None:yield None;return
        with ctx.session_factory() as db:
            version,source,_=store.current(db,ctx)
        expected=source.revision
        def unchanged():
            ctx.source.check_current()
            with ctx.session_factory() as db:
                _,fresh,_=store.current(db,ctx)
                if fresh.revision!=expected:raise problem(409,'PUBLISHED_VERSION_CHANGED','The published version changed during this operation.')
        yield replace(source,check_current=unchanged)


def own(db,identity):
    with publication.context(required=False) as ctx:
        if ctx is None:return None
        from services.schedule_application_service import target
        target(db,ctx);version,source,_=store.current(db,ctx);ctx.source.check_current()
        names={r.id:r.name for r in source.rooms}
        assignments=[{'subject':m.subject,'title':m.title or None,'section':m.section,'type':m.component,'day':m.day,'start':m.start,'end':m.end,'room':names.get(m.room_id)} for m in source.meetings if m.faculty_id==identity.faculty_id]
        return {'schema_version':2,'availability':'available' if assignments else 'empty','faculty_id':identity.faculty_id,'faculty_code':identity.faculty_code,
            'source':{'kind':'published_schedule','label':'Published schedule with authorized post-GA changes' if version and version.sequence>1 else 'Verified published source',
                'version_id':str(version.id) if version else None,'sequence':version.sequence if version else 1,'revision':source.revision,'academic_year':source.academic_year,'term':source.term,'post_ga_changes':bool(version and version.sequence>1),'constraint_status':'NOT_RECHECKED_READ_ONLY'},'assignments':assignments}
