"""SELECT-only projections. Never call U5PB observe/telemetry/result execution."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import math
import sqlite3
from services.ga_run_authority import RunError, Context, digest, uuid
from services.ga_research_context import derive
from services.ga_research_ledger import implementation

VERSION='research-observation-v1'
SAFETY=dict(read_only=True,operational_controls=False,production_admission='BLOCKED',
    institutional_saved_best_promotion='BLOCKED',continuous_ui='DISABLED',active_restore=False,seven_day='NO_GO')


def configured_observer():return None


def bound(value, low, high):
    if type(value) is not int or not low<=value<=high:raise RunError('RESEARCH_OBSERVATION_PAGE_INVALID',422)
    return value


class Observer:
    def __init__(self, bridge):self.bridge=bridge

    @contextmanager
    def snapshot(self, principal):
        b=self.bridge;b.actor(principal);b.worker.storage.guard()
        db=None
        try:
            # The actual handle is read-only, not merely a caller's promise.
            db=sqlite3.connect((b.worker.storage.root/'records.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=2,isolation_level=None)
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
            if db.execute('PRAGMA query_only').fetchone()[0]!=1:raise RunError('RESEARCH_READ_ONLY_REQUIRED')
            allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_TRANSACTION,sqlite3.SQLITE_PRAGMA}
            def authorize(action,a,c,*unused):
                if action not in allowed or action==sqlite3.SQLITE_PRAGMA and c is not None or action==sqlite3.SQLITE_FUNCTION and c=='load_extension':return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorize)
            ticks=[0]
            def budget():ticks[0]+=1;return int(ticks[0]>1000)
            db.set_progress_handler(budget,1000)
            if db.execute('PRAGMA user_version').fetchone()[0]!=1 or db.execute('PRAGMA journal_mode').fetchone()[0]!='delete':raise RunError('RESEARCH_OBSERVATION_STORE_UNSUPPORTED')
            if b.ledger.path.is_symlink() or b.ledger.path.is_junction():raise RunError('RESEARCH_KEY_UNVERIFIED')
            key=b.ledger.path.read_bytes()
            rows=db.execute('SELECT * FROM research_meta').fetchall()
            if (len(rows)!=1 or tuple(rows[0])!=( 'fictional-research-ledger-v1',b.ledger.release,digest(asdict(b.permit)),hashlib.sha256(key).hexdigest())
                    or key!=b.ledger.key or implementation()!=b.ledger.release):raise RunError('RESEARCH_OBSERVATION_STORE_CHANGED')
            authority=Context(b.actor(principal),b.permit.department,'status',catalog_reference=b.permit.catalog)
            with b.worker.coordinator.authorized(authority):
                with b.source(principal):yield db
        except sqlite3.Error:raise RunError('RESEARCH_OBSERVATION_STORAGE_UNAVAILABLE',503) from None
        except (KeyError,TypeError,AttributeError,ValueError) as e:
            if isinstance(e,RunError):raise
            raise RunError('RESEARCH_OBSERVATION_INTEGRITY_REJECTED') from None
        finally:
            if db is not None:
                try:db.rollback()
                finally:db.close()

    def capabilities(self, principal):
        with self.snapshot(principal):pass
        return dict(contract=VERSION,**SAFETY,scope='FICTIONAL_RESEARCH_ONLY',available=True,
            message='Read-only fictional research observations. No institutional approval or execution controls.',
            maximum_page_size=64,maximum_run_page_size=10)

    def _read(self, db, principal, run):
        b=self.bridge;actor=b.actor(principal)
        row=b.worker.store.row(db,actor,run)
        if row['department']!=b.permit.department or row['catalog']!=b.permit.catalog:raise RunError('RESEARCH_RUN_NOT_FOUND',404)
        context=b.worker.coordinator.context(actor,row,'status')
        with b.worker.coordinator.authorized(context,row['policy']):
            ctx,events=b.ledger.check(db,run)
            if derive(row,b.permit)!=ctx:raise RunError('RESEARCH_OBSERVATION_CONTEXT_CHANGED')
            result=None;best=None
            if row['tip']:
                doc,_inner=b.worker.store.checkpoint(db,row)
                pin=db.execute('SELECT tip,policy FROM l_pins WHERE run=? AND sequence=?',(run,row['sequence'])).fetchone()
                scope=db.execute('SELECT policy FROM l_runs WHERE run=?',(run,)).fetchone()
                proof=b.ledger.proof(db,run,row['sequence'])
                if (not pin or tuple(pin)!=(row['tip'],b.worker.storage.policy) or not scope or scope[0]!=b.worker.storage.policy
                        or doc['inner_hash']!=proof['inner_hash'] or row['best'] is None
                        or hashlib.sha256(row['best']).hexdigest()!=row['best_hash'] or proof['projection_fingerprint']!=row['best_hash']):
                    raise RunError('RESEARCH_OBSERVATION_CHECKPOINT_CHANGED')
                result=json.loads(row['best']);best=proof['best_fitness']
                if type(best) not in (int,float) or not math.isfinite(best) or result.get('best_fitness')!=best or result.get('generations_completed')!=row['generation']:raise RunError('RESEARCH_RESULT_INVALID')
            if row['state']=='COMPLETED' and (not row['tip'] or row['generation']!=json.loads(row['bundle'])['configuration']['generations']):raise RunError('RESEARCH_COMPLETION_UNVERIFIED')
            state,reason=b._state(db,row)
            overview=dict(run_id=run,state=state,worker_state=row['state'],reason=reason,
                state_classification='DERIVED' if state!=row['state'] else 'OBSERVED',
                generation=None if row['generation']<0 else row['generation'],best_so_far_fitness=best,
                current_fitness=None,current_fitness_availability='UNAVAILABLE_NOT_EXPOSED',
                satisfaction_metrics=None,satisfaction_availability='UNAVAILABLE_NOT_EMITTED',
                created_at=row['created'],last_observed_at=events[-1].get('observed_at') if events else None,
                checkpoint_sequence=row['sequence'],checkpoint_fingerprint=row['tip'],context_id=digest(ctx),
                context_qualification='TRUSTED_FICTIONAL_CONSUMPTION' if row['tip'] else 'UNVERIFIED_NOT_CONSUMED')
            return overview,ctx,events,result

    def listing(self, principal, offset=0, limit=10):
        bound(offset,0,1024);bound(limit,1,10);b=self.bridge
        with self.snapshot(principal) as db:
            args=(b.actor(principal),b.permit.department,b.permit.catalog)
            count=db.execute('SELECT COUNT(*) FROM runs WHERE actor=? AND department=? AND catalog=?',args).fetchone()[0]
            ids=db.execute('SELECT id FROM runs WHERE actor=? AND department=? AND catalog=? ORDER BY created DESC,id LIMIT ? OFFSET ?',(*args,limit,offset)).fetchall()
            items=[self._read(db,principal,r[0])[0] for r in ids]
            return dict(contract=VERSION,**SAFETY,items=items,total=count,offset=offset,next_offset=offset+len(items) if offset+len(items)<count else None)

    def _history(self, run, result):
        points=[];last=-1;best=math.inf
        for raw in result.get('history',[]) if result else []:
            generation=raw.get('generation');score=raw.get('best_ever_fitness',raw.get('best_fitness'))
            if type(generation) is not int or not last<generation<=20:raise RunError('RESEARCH_HISTORY_INVALID')
            if type(score) not in (int,float) or not math.isfinite(score) or score>best:raise RunError('RESEARCH_HISTORY_INVALID')
            points.append(dict(run_id=run,generation=generation,best_ever_fitness=score,classification='OBSERVED_ORIGINAL_RESULT_HISTORY'))
            last=generation;best=score
        return dict(availability='OBSERVED' if points else 'UNAVAILABLE_NOT_RECORDED',points=points)

    def _events(self, run, events, after, limit):
        bound(after,0,256);bound(limit,1,64)
        allowed={'worker_state','generation','best_so_far_fitness','current_fitness','current_fitness_availability',
            'satisfaction_metrics','satisfaction_availability','checkpoint','exit_reason','observed_at','elapsed_wall_seconds',
            'elapsed_classification','generation_and_best_classification','recovery_state','reason','classification'}
        items=[dict(run_id=run,sequence=i+1,**{k:v for k,v in e.items() if k in allowed}) for i,e in enumerate(events) if after<=i<after+limit]
        return dict(items=items,total=len(events),after=after,next_after=after+len(items) if after+len(items)<len(events) else None)

    def detail(self, principal, run):
        uuid(run)
        with self.snapshot(principal) as db:
            overview,ctx,events,result=self._read(db,principal,run)
            return dict(contract=VERSION,**SAFETY,overview=overview,
                provenance=dict(context=ctx['context'],evaluation_fingerprint=ctx['evaluation_fingerprint'],
                    configuration_fingerprint=ctx['configuration_fingerprint'],institutional_authorization=False),
                fitness=self._history(run,result),telemetry=self._events(run,events,0,64),
                observation_notice='Only persisted observations are served. Worker state may be newer; GET never backfills or writes telemetry.')

    def telemetry(self, principal, run, after=0, limit=64):
        uuid(run);bound(after,0,256);bound(limit,1,64)
        with self.snapshot(principal) as db:
            overview,_ctx,events,_result=self._read(db,principal,run)
            return dict(contract=VERSION,**SAFETY,run_id=run,context_id=overview['context_id'],**self._events(run,events,after,limit))
