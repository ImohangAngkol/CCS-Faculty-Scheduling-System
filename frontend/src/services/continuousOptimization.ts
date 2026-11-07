import {API_BASE,apiFetch} from "./apiSession.ts";
export type OptimizationMode="fixed"|"continuous";
export const CONTINUOUS_STATES=["IDLE","STARTING","RUNNING","PAUSING","PAUSED","RESUMING","STOPPING","STOPPED","COMPLETED","FAILED","INTERRUPTED"] as const;
export const CONTINUOUS_REQUIREMENTS=["IMMUTABLE_CONSUMPTION_REQUIRED","SCOPED_AUTHORITY_REQUIRED","VERSIONED_WORKER_REQUIRED","RESOURCE_ENFORCEMENT_REQUIRED","RUN_LOCAL_PERSISTENCE_REQUIRED"] as const;
export type ContinuousReadiness={schema_version:1;contract:"ga-continuous-foundation-v1";availability:"BLOCKED";executable:false;supported_datasets:[];
  input_consumption:"NOT_ESTABLISHED";receipt_capability:"UNVERIFIED_ONLY";institutional_authorization:"NOT_ESTABLISHED";fixed_generations:"EXISTING_PATH_UNCHANGED";
  requirements:{code:string;message:string}[];lifecycle:{states:string[];implementation:"CONTRACT_ONLY_NO_CONTINUOUS_WORKER";commands:"UNAVAILABLE"};
  safeguards:{enforcement:"NOT_IMPLEMENTED";required:string[]};existing_fixed_controls:string;best_so_far:string};
export function validateReadiness(v:ContinuousReadiness):ContinuousReadiness{
  if(v?.schema_version!==1||v.contract!=="ga-continuous-foundation-v1"||v.availability!=="BLOCKED"||v.executable!==false||!Array.isArray(v.supported_datasets)||v.supported_datasets.length
    ||v.input_consumption!=="NOT_ESTABLISHED"||v.receipt_capability!=="UNVERIFIED_ONLY"||v.institutional_authorization!=="NOT_ESTABLISHED"||v.fixed_generations!=="EXISTING_PATH_UNCHANGED"
    ||!Array.isArray(v.requirements)||v.requirements.length!==CONTINUOUS_REQUIREMENTS.length||new Set(v.requirements.map(r=>r.code)).size!==v.requirements.length
    ||CONTINUOUS_REQUIREMENTS.some(c=>!v.requirements.some(r=>r.code===c))||v.requirements.some(r=>typeof r.message!=="string"||!r.message.trim())
    ||!v.lifecycle||JSON.stringify(v.lifecycle.states)!==JSON.stringify(CONTINUOUS_STATES)||v.lifecycle.implementation!=="CONTRACT_ONLY_NO_CONTINUOUS_WORKER"||v.lifecycle.commands!=="UNAVAILABLE"
    ||v.safeguards?.enforcement!=="NOT_IMPLEMENTED"||!Array.isArray(v.safeguards.required)||!v.safeguards.required.length||v.safeguards.required.some(s=>typeof s!=="string")
    ||typeof v.existing_fixed_controls!=="string"||typeof v.best_so_far!=="string")throw new Error("Continuous readiness could not be validated. Execution remains unavailable.");
  return v;
}
export async function getContinuousReadiness(signal?:AbortSignal){
  const response=await apiFetch(`${API_BASE}/api/ga/continuous/readiness`,{method:"GET",signal,credentials:"include",cache:"no-store"});
  if(!response.ok)throw new Error(`Continuous readiness unavailable (${response.status}). No run was started. Retry the read-only check.`);
  return validateReadiness(await response.json());
}
