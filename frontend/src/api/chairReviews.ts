import {z} from "zod";
import axios from "axios";
import {apiClient} from "../services/apiSession.ts";
import {record,review} from "./adjustments.ts";
import {chairDecision} from "./chairDecisions.ts";

const base="/api/chair-reviews";
const access=z.object({capability:z.literal("department_chair"),departments:z.array(z.object({id:z.string().uuid(),label:z.string()}).strict())}).strict();
const queue=z.object({items:z.array(z.object({id:z.string().uuid(),version:z.number(),faculty_id:z.string().uuid(),department_id:z.string().uuid(),subject:z.string(),section:z.string(),submitted_at:z.string(),status:z.enum(["SUBMITTED","APPROVED_PENDING_APPLICATION","REJECTED"])}).strict())}).strict();
const detail=z.object({request:record,faculty_id:z.string().uuid(),department_id:z.string().uuid(),current_review:review.nullable(),approval_block:z.object({code:z.string(),message:z.string()}).strict().nullable(),can_approve:z.boolean(),can_reject:z.boolean(),decision_history:z.array(chairDecision),schedule_changed:z.literal(false)}).strict();
export type ChairAccess=z.infer<typeof access>;
export type ChairQueue=z.infer<typeof queue>;
export type ChairReview=z.infer<typeof detail>;
export async function getChairAccess(signal?:AbortSignal){return access.parse((await apiClient.get(base+"/access",{signal})).data);}
export async function getChairQueue(department_id:string,include_decided:boolean,signal?:AbortSignal){return queue.parse((await apiClient.get(base,{params:{department_id:department_id||undefined,include_decided},signal})).data);}
export async function getChairReview(id:string){return detail.parse((await apiClient.get(`${base}/${encodeURIComponent(id)}`)).data);}
export async function decideChair(row:ChairReview,action:"approve"|"reject",explanation:string,operation_id:string){return chairDecision.parse((await apiClient.post(`${base}/${row.request.id}/${action}`,{operation_id,expected_version:row.request.version,explanation,content_digest:row.request.content_digest,schedule_revision:row.request.content.input.revision,constraint_digest:row.request.content.review.constraint_digest})).data);}
export function chairError(error:unknown,fallback:string){
  if(axios.isAxiosError(error)){
    if(error.response?.status===401)return "Sign in again to verify your account.";
    const detail=error.response?.data?.detail;
    if(detail&&typeof detail.code==="string"&&typeof detail.message==="string")return `${detail.code}: ${detail.message}`;
    if(error.response?.status===403)return "A current, independently verified Department Chair mandate is required.";
    return fallback;
  }
  return fallback;
}
