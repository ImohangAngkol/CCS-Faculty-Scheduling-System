import type {ResearchDetail,ResearchEvent,ResearchRun} from '../api/researchObservations';

export function observationReliability(run:ResearchRun,elapsedMilliseconds=0){
  if(!('freshness' in run))return {state:'UNKNOWN' as const,reason:'LEGACY_SOURCE_WITHOUT_FRESHNESS',lastVerified:null,serverVerified:null};
  const f=run.freshness;
  const elapsed=Math.max(0,elapsedMilliseconds)/1000;
  const aged=f.state==='FRESH'&&f.age_seconds!==null&&f.age_seconds+elapsed>f.threshold_seconds;
  return {state:aged?'STALE' as const:f.state,reason:aged?'BROWSER_AGE_SINCE_SERVER_VERIFICATION':f.reason,lastVerified:f.last_verified_observation_at,serverVerified:f.server_verified_at};
}
export function researchTime(value:number|null|undefined){
  if(value==null||!Number.isFinite(value)||value<0||value>8640000000000)return 'Unavailable';
  return new Date(value*1000).toISOString();
}
export function authorizeCachedObservation(error:unknown){
  const status=(error as {response?:{status?:number}})?.response?.status;
  return ![401,403,404,409,410,422].includes(status??0);
}
export function validateObservationAdvance(old:ResearchDetail|undefined,next:ResearchDetail){
  if(!old)return next;
  if(old.overview.run_id!==next.overview.run_id||old.overview.context_id!==next.overview.context_id
    ||next.overview.checkpoint_sequence<old.overview.checkpoint_sequence||next.telemetry.total<old.telemetry.total
    ||old.telemetry.items.some((e,i)=>JSON.stringify(e)!==JSON.stringify(next.telemetry.items[i])))throw new Error('Observation history regressed or changed');
  return next;
}
export function mergeObservations(first:ResearchEvent[],extra:ResearchEvent[]){
  const out=[...first,...extra];
  if(out.length>256||out.some((e,i)=>i>0&&e.sequence!==out[i-1].sequence+1))throw new Error('Observation page sequence changed');
  return out;
}
