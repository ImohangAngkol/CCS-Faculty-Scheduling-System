import {API_BASE,apiFetch} from "./apiSession.ts";
export type Candidate = "generation_best" | "best_ever";
export type Dimension = "subject" | "day" | "time";
export type Choice = {generation:number;candidate:Candidate;chromosome_id:string};
export type Source = Choice & {run_id:string;input_fingerprint:string;engine_fingerprint:string;configuration_fingerprint:string};
export type Meeting = {subject:string;section:string;type:string;day:string;start:string;end:string;room:string;title?:string};
export type Faculty = {faculty:string;teaching_units:number|null;target:number|null;target_deviation:number|null;preparations:number;
  satisfaction:Record<Dimension,number|null>;preference_status:Record<Dimension,string>;preference_explanations:Record<Dimension,string>;
  hours:Record<string,number>;weekly_hours:number;average_deviation:number|null;assignments:Meeting[];preferred:Record<string,unknown>|null;unavailable_reason:string|null};
export type Receipt = {status:"UNVERIFIED"|"UNAVAILABLE";record_state:string;reasons:string[]};
export type Analysis = {schema_version:1;source:Source;fitness:number;faculty:Faculty[];aggregates:Record<Dimension|"overall",{value:number|null;count:number;total:number;contributors:string[]}>;
  captured_faculty_average:number|null;load_imbalance:number|null;conflicts:number|null;violations:number|null;elapsed_ms:number|null;
  parameters:Record<string,number>|null;recorded_state:string;recorded_generation_count:number;metric_basis:string;
  reference_limits:{preparations:number|null;hard_units:number|null};compatibility:{classification:string;reason:string};receipt:Receipt;
  academic_context:{status:"UNVERIFIED";academic_year:string;term:string;department:string;dataset_id:string;dataset_revision:string}|null;
  recorded_generations:number[];choices:Choice[];progress:Progress[];window:{offset:number;total:number;older:boolean;newer:boolean};issues:{generation:number;code:string}[];warnings:string[]};
export type Progress={generation:number;best:number|null;average:number|null;subject:number|null;day:number|null;time:number|null;violations:number|null;elapsed_ms:number|null;subject_count:number|null;day_count:number|null;time_count:number|null;faculty_total:number|null};
export type RunPage={schema_version:1;items:{run_id:string;state:string;created_at:string;generations:number}[];offset:number;total:number;issues:string[]};
export type Comparison={schema_version:1;run_id:string;left:Source;right:Source;fitness:Delta;load_imbalance:Delta;violations:Delta;
  faculty:{faculty:string;before:Faculty|null;after:Faculty|null;changes:Record<string,number|null>;satisfaction_changes:Record<Dimension,number|null>}[];
  academic_compatibility:string;receipt:Receipt;explanation:string};
export type Delta={before:number|null;after:number|null;change:number|null};
const base=`${API_BASE}/api/ga/advanced-analysis`;
const uuid=(v:unknown)=>typeof v==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v);
const hash=(v:unknown)=>typeof v==="string"&&/^[0-9a-f]{64}$/.test(v);
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const nullable=(v:unknown)=>v===null||finite(v);
const integer=(v:unknown)=>finite(v)&&Number.isInteger(v)&&v>=0;
const fail=()=>{throw new Error("Recorded analysis identity or measurements could not be validated. No data was combined.");};
const dimensions:Dimension[]=["subject","day","time"];
const days=["monday","tuesday","wednesday","thursday","friday","saturday"];
function source(v:Source){return v&&uuid(v.run_id)&&integer(v.generation)&&["generation_best","best_ever"].includes(v.candidate)&&hash(v.chromosome_id)&&hash(v.input_fingerprint)&&hash(v.engine_fingerprint)&&hash(v.configuration_fingerprint);}
function receipt(v:Receipt){return v&&["UNVERIFIED","UNAVAILABLE"].includes(v.status)&&["MISSING","INCOMPLETE","RECORDED","INVALID","INCOMPATIBLE_CAPTURE","NOT_INSTALLED"].includes(v.record_state)&&Array.isArray(v.reasons)&&v.reasons.every(x=>typeof x==="string");}
function faculty(v:Faculty){return v&&typeof v.faculty==="string"&&integer(v.preparations)&&[v.teaching_units,v.target,v.target_deviation,v.average_deviation].every(nullable)
  &&dimensions.every(k=>v.satisfaction?.[k]===null||finite(v.satisfaction?.[k])&&v.satisfaction[k]!>=0&&v.satisfaction[k]!<=100)
  &&dimensions.every(k=>typeof v.preference_status?.[k]==="string"&&typeof v.preference_explanations?.[k]==="string")
  &&days.every(d=>finite(v.hours?.[d])&&v.hours[d]>=0)&&finite(v.weekly_hours)&&Math.abs(days.reduce((s,d)=>s+v.hours[d],0)-v.weekly_hours)<1e-7
  &&Array.isArray(v.assignments)&&v.assignments.every(r=>[r.subject,r.section,r.type,r.day,r.start,r.end,r.room].every(x=>typeof x==="string"));}
export function validateAnalysis(v:Analysis,run:string,generation:number|null,candidate:Candidate):Analysis {
  if(v?.schema_version!==1||!source(v.source)||v.source.run_id!==run||generation!==null&&v.source.generation!==generation||v.source.candidate!==candidate||!finite(v.fitness)
    ||!Array.isArray(v.faculty)||v.faculty.length>500||v.faculty.some(r=>!faculty(r))||new Set(v.faculty.map(r=>r.faculty)).size!==v.faculty.length
    ||![v.captured_faculty_average,v.load_imbalance,v.conflicts,v.violations,v.elapsed_ms].every(nullable)||!receipt(v.receipt)
    ||!Array.isArray(v.choices)||new Set(v.choices.map(c=>c.chromosome_id)).size!==v.choices.length||v.choices.some(c=>!integer(c.generation)||!hash(c.chromosome_id)||!["generation_best","best_ever"].includes(c.candidate))
    ||!v.choices.some(c=>c.chromosome_id===v.source.chromosome_id)||!Array.isArray(v.progress)||v.progress.length>50
    ||v.progress.some((p,i)=>!integer(p.generation)||i>0&&p.generation<=v.progress[i-1].generation||![p.best,p.average,p.subject,p.day,p.time,p.violations,p.elapsed_ms].every(nullable)
      ||p.faculty_total!==null&&!integer(p.faculty_total)||dimensions.some(d=>p[d]!==null&&(!finite(p[d])||p[d]!<0||p[d]!>100)
        ||p[`${d}_count`]!==null&&(!integer(p[`${d}_count`])||p.faculty_total===null||p[`${d}_count`]!>p.faculty_total)))
    ||!Array.isArray(v.recorded_generations)||v.recorded_generations.some(g=>!integer(g))||!v.recorded_generations.includes(v.source.generation)
    ||!integer(v.recorded_generation_count)||!v.compatibility||!["CURRENT","LEGACY_INCOMPATIBLE","UNKNOWN_COMPATIBILITY"].includes(v.compatibility.classification)||typeof v.compatibility.reason!=="string"
    ||!Array.isArray(v.warnings)||v.warnings.some(w=>typeof w!=="string")||!Array.isArray(v.issues))fail();
  for(const key of [...dimensions,"overall"] as const){const a=v.aggregates?.[key];const rows=v.faculty.filter(r=>key==="overall"?dimensions.every(k=>r.satisfaction[k]!==null):r.satisfaction[key]!==null);
    const expected=rows.length?rows.reduce((s,r)=>s+(key==="overall"?dimensions.reduce((t,k)=>t+r.satisfaction[k]!,0)/3:r.satisfaction[key]!),0)/rows.length:null;
    if(!a||a.count!==rows.length||a.total!==v.faculty.length||!Array.isArray(a.contributors)||JSON.stringify(a.contributors)!==JSON.stringify(rows.map(r=>r.faculty))||(a.value===null)!==(expected===null)||a.value!==null&&(!finite(a.value)||Math.abs(a.value-expected!)>1e-7))fail();}
  return v;
}
export function validateComparison(v:Comparison,run:string,left:Choice,right:Choice):Comparison{
  if(v?.schema_version!==1||v.run_id!==run||!source(v.left)||!source(v.right)||!receipt(v.receipt)||v.left.run_id!==run||v.right.run_id!==run
    ||["generation","candidate","chromosome_id"].some(k=>v.left[k as keyof Choice]!==left[k as keyof Choice]||v.right[k as keyof Choice]!==right[k as keyof Choice])
    ||v.left.chromosome_id===v.right.chromosome_id||["input_fingerprint","engine_fingerprint","configuration_fingerprint"].some(k=>v.left[k as keyof Source]!==v.right[k as keyof Source])||!Array.isArray(v.faculty))fail();
  for(const d of [v.fitness,v.load_imbalance,v.violations])if(!d||![d.before,d.after,d.change].every(nullable)||d.change!==null&&(d.before===null||d.after===null||Math.abs(d.after-d.before-d.change)>1e-7))fail();
  if(new Set(v.faculty.map(r=>r.faculty)).size!==v.faculty.length)fail();
  for(const row of v.faculty){if(row.before&&(!faculty(row.before)||row.before.faculty!==row.faculty)||row.after&&(!faculty(row.after)||row.after.faculty!==row.faculty))fail();
    for(const k of dimensions){const a=row.before?.satisfaction[k]??null,b=row.after?.satisfaction[k]??null,d=row.satisfaction_changes?.[k];if(!nullable(d)||(a===null||b===null?d!==null:d===null||Math.abs(b-a-d)>1e-7))fail();}}
  return v;
}
async function read<T>(path:string,signal?:AbortSignal):Promise<T>{const response=await apiFetch(`${base}${path}`,{signal,credentials:"include",cache:"no-store"});if(!response.ok){const body=await response.json().catch(()=>null);throw new Error(body?.detail?.message??`Recorded analysis unavailable (${response.status}). Retry without starting optimization.`);}return response.json();}
export async function getAnalysisRuns(offset:number,signal?:AbortSignal){const v=await read<RunPage>(`/runs?offset=${offset}`,signal);if(v.schema_version!==1||!Array.isArray(v.items)||v.items.some(r=>!uuid(r.run_id)||!integer(r.generations))||!integer(v.total))fail();return v;}
export async function getAdvancedAnalysis(run:string,generation:number|null,candidate:Candidate,offset:number,signal?:AbortSignal){if(!uuid(run))fail();const q=new URLSearchParams({candidate,history_offset:String(offset)});if(generation!==null)q.set("generation",String(generation));return validateAnalysis(await read<Analysis>(`/runs/${run}?${q}`,signal),run,generation,candidate);}
export async function compareAdvanced(run:string,left:Choice,right:Choice,signal?:AbortSignal){const q=new URLSearchParams({left_generation:String(left.generation),left_candidate:left.candidate,right_generation:String(right.generation),right_candidate:right.candidate});return validateComparison(await read<Comparison>(`/runs/${run}/compare?${q}`,signal),run,left,right);}
export const value=(v:number|null|undefined,unit="")=>v===null||v===undefined?"Not available":`${v.toLocaleString(undefined,{maximumFractionDigits:2})}${unit}`;
export const exact=(v:number|null)=>v===null?"Not available":String(v);
export const change=(v:number|null)=>v===null?"Not comparable":v===0?"0 (unchanged)":`${v>0?"+":""}${exact(v)}`;
