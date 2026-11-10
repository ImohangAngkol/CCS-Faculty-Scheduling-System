// All labels, IDs and observations here are explicitly fictional HTTP fixtures.
import {detail,run,other,hash,safety} from './researchObservations.fixtures.mjs';
export {run,other,hash};
export const safety2={...safety,contract:'research-observation-v2'};
export function observation(state='FRESH',now=Date.now()/1000){
 const d=structuredClone(detail);d.contract='research-observation-v2';d.overview.state='RUNNING';d.overview.worker_state='RUNNING';
 const age=state==='STALE'?31:state==='UNKNOWN'?-3:state==='TERMINAL'?60:1;
 d.overview.freshness={contract:'research-freshness-v1',state,telemetry_state:state==='TERMINAL'?'STALE':state,reason:state==='FRESH'?'RECENT_DURABLE_OBSERVATION':state==='STALE'?'OBSERVATION_AGE_EXCEEDED':state==='TERMINAL'?'DURABLE_TERMINAL_OUTCOME':'FUTURE_OBSERVATION',server_verified_at:now,last_verified_observation_at:now-age,age_seconds:age,threshold_seconds:30,tolerated_clock_skew_seconds:2,terminal_confirmed:state==='TERMINAL',terminal_recorded_at:state==='TERMINAL'?now-50:null,worker_health:'NOT_ESTABLISHED_BY_OBSERVATION_HTTP',timestamp_source:'SIGNED_DURABLE_RESEARCH_LEDGER'};
 if(state==='TERMINAL'){d.overview.state='COMPLETED';d.overview.worker_state='COMPLETED';}
 return d;
}
export function missing(now=Date.now()/1000){
 const d=observation('UNKNOWN',now);d.overview.run_id=other;d.overview.state='CREATED';d.overview.worker_state='CREATED';d.overview.best_so_far_fitness=null;
 d.overview.freshness={...d.overview.freshness,last_verified_observation_at:null,age_seconds:null,reason:'MISSING_TIMESTAMP'};
 d.overview.context_qualification='UNVERIFIED_NOT_CONSUMED';d.fitness={availability:'UNAVAILABLE_NOT_RECORDED',points:[]};return d;
}
