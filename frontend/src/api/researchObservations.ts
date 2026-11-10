import {z} from "zod";
import {apiClient} from "../services/apiSession.ts";
const hash=z.string().regex(/^[a-f0-9]{64}$/),id=z.string().uuid(),score=z.number().finite().nullable();
const safety={read_only:z.literal(true),operational_controls:z.literal(false),production_admission:z.literal("BLOCKED"),institutional_saved_best_promotion:z.literal("BLOCKED"),continuous_ui:z.literal("DISABLED"),active_restore:z.literal(false),seven_day:z.literal("NO_GO")};
const contract={contract:z.literal("research-observation-v1"),...safety};
const states=z.enum(["CREATED","RUNNING","RESUMING","PAUSING","STOPPING","PAUSED","COMPLETED","STOPPED","FAILED","RESOURCE_LIMITED","INTERRUPTED","RECOVERY_REQUIRED"]);
const overview=z.object({run_id:id,state:states,worker_state:states,reason:z.string().nullable(),state_classification:z.enum(["DERIVED","OBSERVED"]),generation:z.number().int().min(0).max(20).nullable(),best_so_far_fitness:score,current_fitness:z.null(),current_fitness_availability:z.literal("UNAVAILABLE_NOT_EXPOSED"),satisfaction_metrics:z.null(),satisfaction_availability:z.literal("UNAVAILABLE_NOT_EMITTED"),created_at:z.number().finite(),last_observed_at:z.number().finite().nullable(),checkpoint_sequence:z.number().int().min(0).max(21),checkpoint_fingerprint:hash.nullable(),context_id:hash,context_qualification:z.enum(["TRUSTED_FICTIONAL_CONSUMPTION","UNVERIFIED_NOT_CONSUMED"])}).strict();
const event=z.object({run_id:id,sequence:z.number().int().positive(),worker_state:states.optional(),generation:z.number().int().min(0).max(20).nullable().optional(),best_so_far_fitness:score.optional(),current_fitness:z.null().optional(),current_fitness_availability:z.literal("UNAVAILABLE_NOT_EXPOSED").optional(),satisfaction_metrics:z.null().optional(),satisfaction_availability:z.literal("UNAVAILABLE_NOT_EMITTED").optional(),checkpoint:hash.nullable().optional(),exit_reason:z.string().nullable().optional(),observed_at:z.number().finite(),elapsed_wall_seconds:z.number().finite().nonnegative().optional(),elapsed_classification:z.string().optional(),generation_and_best_classification:z.string().optional(),recovery_state:states.optional(),reason:z.string().optional(),classification:z.string().optional()}).strict();
const page={items:z.array(event).max(64),total:z.number().int().min(0).max(256),after:z.number().int().nonnegative().optional(),next_after:z.number().int().positive().nullable()};
const point=z.object({run_id:id,generation:z.number().int().min(0).max(20),best_ever_fitness:z.number().finite(),classification:z.literal("OBSERVED_ORIGINAL_RESULT_HISTORY")}).strict();
const capabilitiesV1=z.object({...contract,scope:z.literal("FICTIONAL_RESEARCH_ONLY"),available:z.literal(true),message:z.string(),maximum_page_size:z.literal(64),maximum_run_page_size:z.literal(10)}).strict();
const runsV1=z.object({...contract,items:z.array(overview).max(10),total:z.number().int().min(0).max(1024),offset:z.number().int().nonnegative(),next_offset:z.number().int().positive().nullable()}).strict();
const detailV1=z.object({...contract,overview,provenance:z.object({context:z.record(z.string(),z.string().max(256)).refine(c=>['academic_year','term','dataset_identity'].every(k=>c[k]?.startsWith('FICTIONAL-'))),evaluation_fingerprint:hash,configuration_fingerprint:hash,institutional_authorization:z.literal(false)}).strict(),fitness:z.object({availability:z.enum(["OBSERVED","UNAVAILABLE_NOT_RECORDED"]),points:z.array(point).max(21)}).strict(),telemetry:z.object(page).strict(),observation_notice:z.string()}).strict();
const eventsV1=z.object({...contract,run_id:id,context_id:hash,...page}).strict();
const observedTime=z.number().finite().min(0).max(8640000000000).nullable();
export const freshnessSchema=z.object({contract:z.literal("research-freshness-v1"),state:z.enum(["FRESH","STALE","UNKNOWN","TERMINAL"]),telemetry_state:z.enum(["FRESH","STALE","UNKNOWN"]),reason:z.enum(["MISSING_TIMESTAMP","SERVER_CLOCK_UNVERIFIABLE","INVALID_TIMESTAMP","FUTURE_OBSERVATION","OBSERVATION_TIME_REVERSED","RECENT_DURABLE_OBSERVATION","OBSERVATION_AGE_EXCEEDED","WITHIN_CLOCK_SKEW_TOLERANCE","OWNERSHIP_OR_ORPHAN_UNCERTAIN","TERMINAL_OUTCOME_NOT_INDEPENDENTLY_CONFIRMED","DURABLE_TERMINAL_OUTCOME"]),server_verified_at:observedTime,last_verified_observation_at:observedTime,age_seconds:z.number().finite().nullable(),threshold_seconds:z.literal(30),tolerated_clock_skew_seconds:z.literal(2),terminal_confirmed:z.boolean(),terminal_recorded_at:observedTime,worker_health:z.literal("NOT_ESTABLISHED_BY_OBSERVATION_HTTP"),timestamp_source:z.literal("SIGNED_DURABLE_RESEARCH_LEDGER")}).strict().refine(f=>{
  const hasTimes=f.server_verified_at!==null&&f.last_verified_observation_at!==null;
  if(hasTimes?(f.age_seconds===null||Math.abs(f.age_seconds-(f.server_verified_at!-f.last_verified_observation_at!))>0.000001):f.age_seconds!==null)return false;
  if(f.state==="TERMINAL"?(!f.terminal_confirmed||f.terminal_recorded_at===null||f.server_verified_at===null||f.terminal_recorded_at>f.server_verified_at+2):(f.terminal_confirmed||f.terminal_recorded_at!==null))return false;
  if(f.telemetry_state==="FRESH"&&(!hasTimes||f.age_seconds! < -2||f.age_seconds!>30))return false;
  if(f.telemetry_state==="STALE"&&(!hasTimes||f.age_seconds!<=30))return false;
  return f.state!=="FRESH"||f.telemetry_state==="FRESH";
});
const v2Contract={...contract,contract:z.literal("research-observation-v2")};
const overview2=overview.extend({freshness:freshnessSchema}).strict();
const event2=event.extend({observed_at:observedTime}).strict();
const detailV2=detailV1.extend({...v2Contract,overview:overview2,telemetry:z.object({...page,items:z.array(event2).max(64)}).strict()}).strict();
export const capabilitiesSchema=z.discriminatedUnion('contract',[capabilitiesV1,capabilitiesV1.extend(v2Contract).strict()]);
export const runsSchema=z.discriminatedUnion('contract',[runsV1,runsV1.extend({...v2Contract,items:z.array(overview2).max(10)}).strict()]);
export const detailSchema=z.discriminatedUnion('contract',[detailV1,detailV2]);
export const eventsSchema=z.discriminatedUnion('contract',[eventsV1,eventsV1.extend({...v2Contract,freshness:freshnessSchema,items:z.array(event2).max(64)}).strict()]);
export type ResearchRun=z.infer<typeof overview>|z.infer<typeof overview2>;
export type ResearchDetail=z.infer<typeof detailSchema>;
export type ResearchEvent=z.infer<typeof event>|z.infer<typeof event2>;
export function validateDetail(input:unknown,run:string){
  const data=detailSchema.parse(input);
  if(data.overview.run_id!==run||data.fitness.points.some((p,i,a)=>p.run_id!==run||(i>0&&(p.generation<=a[i-1].generation||p.best_ever_fitness>a[i-1].best_ever_fitness)))
    ||data.telemetry.items.some((p,i,a)=>p.run_id!==run||(i>0&&p.sequence<=a[i-1].sequence))
    ||(data.fitness.availability==="OBSERVED")!==Boolean(data.fitness.points.length))throw new Error("Unverifiable research observations");
  if(data.contract==="research-observation-v2"&&data.overview.freshness.state==="TERMINAL"&&!["COMPLETED","STOPPED","FAILED","RESOURCE_LIMITED"].includes(data.overview.state))throw new Error("Unverifiable terminal observation");
  return data;
}
const base="/api/research/observations";
export const researchCapabilities=async(signal?:AbortSignal)=>capabilitiesSchema.parse((await apiClient.get(base+"/capabilities",{signal,timeout:8000})).data);
export async function researchRuns(offset=0,signal?:AbortSignal){
  const data=runsSchema.parse((await apiClient.get(base+"/runs",{params:{offset,limit:10},signal,timeout:8000})).data);
  if(data.offset!==offset||new Set(data.items.map(r=>r.run_id)).size!==data.items.length||data.offset+data.items.length>data.total||data.next_offset!==((offset+data.items.length<data.total)?offset+data.items.length:null))throw new Error("Unverifiable research run page");
  return data;
}
export const researchDetail=async(run:string,signal?:AbortSignal)=>validateDetail((await apiClient.get(base+"/runs/"+encodeURIComponent(run),{signal,timeout:8000})).data,run);
export async function researchEvents(run:string,after:number,context:string,signal?:AbortSignal){
  const data=eventsSchema.parse((await apiClient.get(base+"/runs/"+encodeURIComponent(run)+"/telemetry",{params:{after,limit:64},signal,timeout:8000})).data);
  if(data.run_id!==run||data.context_id!==context||data.after!==after||data.items.some((p,i,a)=>p.run_id!==run||p.sequence<=after||(i>0&&p.sequence<=a[i-1].sequence)))throw new Error("Unverifiable research page");
  return data;
}
