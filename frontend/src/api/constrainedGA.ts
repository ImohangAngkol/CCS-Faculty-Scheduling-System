import {z} from "zod";
import axios from "axios";
import {apiClient, API_BASE} from "../services/apiSession.ts";

const hash=z.string().regex(/^[a-f0-9]{64}$/), id=z.string().uuid();
const head=z.object({record_id:id,revision_id:id,event_id:id,version:z.number().int().positive(),content_digest:hash,evidence_digest:hash,source_sha256:hash,source_hash_kind:z.enum(["original_file","canonical_manual_content"])}).strict();
const commitment=z.object({record_id:id,revision_id:id,source_row:z.number().int().positive(),source_sha256:hash,source_hash_kind:z.enum(["original_file","canonical_manual_content"]),subject:z.string(),day:z.enum(["M","T","W","TH","F","S"]),start:z.number().int(),end:z.number().int(),sections:z.array(z.string()).min(1),faculty:z.string().nullable(),room:z.string().nullable()}).strict();
const schedule=z.object({subject:z.string(),title:z.string(),type:z.string(),day:z.string(),start:z.string(),end:z.string(),section:z.string(),faculty:z.string(),room:z.string()}).strict();
export const diagnosticsSchema=z.record(z.string(),z.number().int().nonnegative());
export const statusSchema=z.object({legacy_mode:z.literal("LEGACY_V1"),constrained_mode:z.literal("CONSTRAINED_V2"),engine_version:z.literal("ga-constrained-v2.1"),production_status:z.literal("BLOCKED"),message:z.string()}).strict();
export const constraintsSchema=z.object({execution_mode:z.literal("CONSTRAINED_V2"),status:z.literal("CURRENT"),academic_year:z.string(),term:z.string(),constraint_digest:hash,revisions:z.array(head).min(1).max(1000),commitments:z.number().int().positive(),activated:z.literal(false)}).strict();
const states=z.enum(["INITIALIZING","RUNNING","PAUSED","STOPPED","COMPLETED","FAILED"]);
export const resultSchema=z.object({execution_mode:z.literal("CONSTRAINED_V2"),engine_version:z.literal("ga-constrained-v2.1"),status:states,source:z.literal("GA-generated proposal"),approved:z.literal(false),academic_year:z.string(),term:z.string(),constraint_digest:hash,constraint_status:z.literal("CURRENT_AT_PUBLICATION"),revisions:z.array(head).min(1),commitments:z.array(commitment).min(1),diagnostics:diagnosticsSchema,feasibility:z.literal("VALIDATED_CANDIDATE"),generation:z.number().int().nonnegative(),population_size:z.number().int().min(2),best_fitness:z.number().finite(),fitness_breakdown:z.record(z.string(),z.number().finite()),history:z.array(z.object({generation:z.number().int().nonnegative(),generation_best_fitness:z.number().finite(),best_ever_fitness:z.number().finite()}).strict()).max(101),schedule:z.array(schedule).max(10000)}).strict();
export const runSchema=z.object({run_id:id,execution_mode:z.literal("CONSTRAINED_V2"),status:states,execution_active:z.boolean(),generation:z.number().int().nonnegative().nullable(),error:z.object({code:z.string(),message:z.string()}).strict().nullable(),diagnostics:diagnosticsSchema,result:resultSchema.optional()}).strict();
export type ConstrainedRun=z.infer<typeof runSchema>;
export type ConstraintSet=z.infer<typeof constraintsSchema>;
export type SeedMode="fresh"|"saved"|"uploaded";
const endpoint=API_BASE+"/api/ga/v2";
export async function constrainedStatus(signal?:AbortSignal){return statusSchema.parse((await apiClient.get(endpoint+"/status",{signal})).data);}
export async function currentConstraints(year:string,term:string,signal?:AbortSignal){return constraintsSchema.parse((await apiClient.get(endpoint+"/constraints",{params:{academic_year:year,term},signal})).data);}
export async function startConstrained(scope:ConstraintSet,seed:SeedMode,parameters:{population_size:number;generations:number}){return runSchema.parse((await apiClient.post(endpoint+"/runs",{academic_year:scope.academic_year,term:scope.term,constraint_digest:scope.constraint_digest,seed,parameters})).data);}
export async function constrainedRun(runId:string,signal?:AbortSignal){return runSchema.parse((await apiClient.get(endpoint+"/runs/"+id.parse(runId),{signal})).data);}
export async function controlConstrained(runId:string,action:"pause"|"resume"|"stop"){return runSchema.parse((await apiClient.post(endpoint+"/runs/"+id.parse(runId)+"/control",{action})).data);}
export function constrainedError(error:unknown){
  if(axios.isAxiosError(error)){
    if(error.response?.status===401)return "Sign in again to access constrained scheduling.";
    if(error.response?.status===403)return "Only an authorized administrator may access constrained scheduling.";
    const detail=z.object({code:z.string().max(100),message:z.string().max(500)}).safeParse(error.response?.data?.detail);
    if(detail.success)return `${detail.data.code}: ${detail.data.message}`;
    return "Constrained scheduling is unavailable. Check the backend and retry.";
  }
  return "The constrained scheduling response is incomplete or incompatible. Retry after checking the backend.";
}
