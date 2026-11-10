"""Explicit v2 adapter over unchanged SELECT-only U5PC reader.

    No production provider installation, worker/ledger rewrite or HTTP control.
"""
import time
from services.ga_research_observation import Observer as OriginalObserver,SAFETY,bound
from services.ga_run_authority import RunError,uuid
from services.ga_observation_freshness import evaluate,timestamp

VERSION='research-observation-v2'


class ContinuityObserver(OriginalObserver):
    def __init__(self,bridge,*,clock=time.time):super().__init__(bridge);self.clock=clock

    def capabilities(self,principal):
        data=super().capabilities(principal);data['contract']=VERSION;return data

    def _read(self,db,principal,run):
        overview,ctx,events,result=super()._read(db,principal,run)
        times=[]
        for event in events:
            t=event.get('observed_at')
            if t is not None and not timestamp(t):raise RunError('RESEARCH_OBSERVATION_TIMESTAMP_INVALID')
            if 'worker_state' in event and event['worker_state'] not in {'CREATED','RUNNING','RESUMING','PAUSING','STOPPING','PAUSED','COMPLETED','STOPPED','FAILED','RESOURCE_LIMITED'}:
                raise RunError('RESEARCH_OBSERVATION_STATE_INVALID')
            times.append(t)
        row=self.bridge.worker.store.row(db,self.bridge.actor(principal),run)
        latest=db.execute('SELECT state,reason,at,tip,fence FROM worker_events WHERE run=? ORDER BY id DESC LIMIT 1',(run,)).fetchone()
        processes=db.execute('SELECT status FROM l_processes WHERE run=?',(run,)).fetchall()
        base=db.execute('SELECT state,executor,lease FROM runs WHERE id=?',(run,)).fetchone()
        terminal_fence=latest is not None and (latest['fence']==row['fence'] or row['state']=='STOPPED' and row['reason']=='USER_STOP' and latest['fence']+1==row['fence'])
        terminal=(base['state']=='WORKER_'+row['state'] and base['executor'] is None and base['lease']==0 and overview['state'] in {'COMPLETED','STOPPED','FAILED','RESOURCE_LIMITED'} and latest is not None
            and latest['state']==row['state'] and latest['reason']==row['reason'] and latest['tip']==row['tip']
            and terminal_fence and all(p['status']=='EXIT_VERIFIED' for p in processes))
        overview['freshness']=evaluate(now=self.clock(),times=times,state=overview['state'],terminal_confirmed=terminal,
            terminal_at=latest['at'] if latest is not None else None)
        return overview,ctx,events,result

    def _events(self,run,events,after,limit):
        data=super()._events(run,events,after,limit)
        for event in data['items']:event.setdefault('observed_at',None)
        return data

    def listing(self,principal,offset=0,limit=10):
        data=super().listing(principal,offset,limit);data['contract']=VERSION;return data

    def detail(self,principal,run):
        data=super().detail(principal,run);data['contract']=VERSION;return data

    def telemetry(self,principal,run,after=0,limit=64):
        uuid(run);bound(after,0,256);bound(limit,1,64)
        with self.snapshot(principal) as db:
            overview,_ctx,events,_result=self._read(db,principal,run)
            return dict(contract=VERSION,**SAFETY,run_id=run,context_id=overview['context_id'],freshness=overview['freshness'],**self._events(run,events,after,limit))
