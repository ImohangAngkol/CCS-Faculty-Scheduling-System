import {z} from "zod";
import axios from "axios";
import {apiClient} from "../services/apiSession.ts";
import {chairDecision} from "./chairDecisions.ts";

const meeting = z.object({id:z.string(), subject_id:z.string(), section_id:z.string(), subject:z.string(), title:z.string(), section:z.string(), component:z.enum(["Lecture","Laboratory"]), day:z.string(), start:z.string(), end:z.string(), room_id:z.string()}).strict();
const proposal = z.object({day:z.enum(["M","T","W","TH","F","S"]), start:z.string(), end:z.string(), room_id:z.string()}).strict();
const validation = z.object({outcome:z.enum(["VALID_PROPOSAL","REQUIRES_REVIEW"]), findings:z.array(z.object({code:z.string(),message:z.string()}).strict()),conflict_free:z.boolean(),approval:z.literal("AWAITING_FUTURE_D12_CHAIR_DECISION")}).strict().refine(v=>v.conflict_free===(v.findings.length===0)&&v.conflict_free===(v.outcome==="VALID_PROPOSAL"),"Inconsistent validation findings");
export const review = z.object({original:meeting,proposal,validation,constraint_digest:z.string()}).strict();
const input = z.object({schedule_id:z.string(),revision:z.string(),assignment_id:z.string(),academic_year:z.string(),term:z.string(),proposal,justification:z.string()}).strict();
export const record = z.object({id:z.string().uuid(),status:z.enum(["DRAFT","SUBMITTED","WITHDRAWN","APPROVED_PENDING_APPLICATION","REJECTED"]),version:z.number().int().positive(),created_at:z.string(),updated_at:z.string(),submitted_at:z.string().nullable(),withdrawn_at:z.string().nullable(),content_digest:z.string(),content:z.object({input,review}).strict(),freshness:z.object({state:z.enum(["CURRENT","STALE","UNAVAILABLE"]),code:z.string().nullable(),validation:validation.nullable()}).strict(),history:z.array(z.object({request_id:z.string(),sequence:z.number(),action:z.enum(["CREATED","SUBMITTED","WITHDRAWN"]),actor_id:z.string(),operation_id:z.string(),previous_digest:z.string().nullable(),content_digest:z.string(),created_at:z.string(),validation:validation.nullable()}).strict()),schedule_changed:z.literal(false),approval:z.enum(["NOT_IMPLEMENTED_D11","APPROVED_PENDING_APPLICATION","REJECTED"]),base_status:z.literal("SUBMITTED").optional(),decision:chairDecision.optional()}).strict().refine(r=>r.decision ? r.base_status==="SUBMITTED"&&r.status===r.decision.status&&r.approval===r.status : ["DRAFT","SUBMITTED","WITHDRAWN"].includes(r.status)&&r.approval==="NOT_IMPLEMENTED_D11"&&!r.base_status,"Inconsistent decision projection");
const assignments = z.object({schedule_id:z.string(),revision:z.string(),academic_year:z.string(),term:z.string(),constraint_digest:z.string(),assignments:z.array(meeting),rooms:z.array(z.object({id:z.string(),name:z.string(),kind:z.string()}).strict()),label:z.string()}).strict();
const listing = z.object({items:z.array(record),next_cursor:z.string().uuid().nullable()}).strict();
export type AssignmentBundle = z.infer<typeof assignments>;
export type AdjustmentInput = z.infer<typeof input>;
export type AdjustmentRecord = z.infer<typeof record>;
export type AdjustmentReview = z.infer<typeof review>;
const base = "/api/adjustment-requests";
export async function getAdjustmentAssignments(signal?:AbortSignal) {return assignments.parse((await apiClient.get(base+"/assignments",{signal})).data);}
export async function listAdjustments(signal?:AbortSignal,before?:string) {return listing.parse((await apiClient.get(base,{signal,params:before?{before}:undefined})).data);}
export async function getAdjustment(id:string) {return record.parse((await apiClient.get(base+"/"+encodeURIComponent(id))).data);}
export async function previewAdjustment(body:AdjustmentInput) {return review.parse((await apiClient.post(base+"/preview",body)).data);}
export async function createAdjustment(body:AdjustmentInput,operation_id:string) {return record.parse((await apiClient.post(base,{...body,operation_id})).data);}
export async function transitionAdjustment(row:AdjustmentRecord,action:"submit"|"withdraw",operation_id:string) {return record.parse((await apiClient.post(`${base}/${row.id}/${action}`,{operation_id,expected_version:row.version})).data);}
export function adjustmentError(error:unknown,fallback:string):string {
  if(axios.isAxiosError(error)) {
    if(error.response?.status===401)return "Sign in again to verify your account.";
    if(error.response?.status===403)return "Your faculty account or session is not authorized for this operation.";
    const detail=error.response?.data?.detail;
    if(detail&&typeof detail.code==="string"&&typeof detail.message==="string")return `${detail.code}: ${detail.message}`;
    return fallback;
  }
  return error instanceof Error?error.message:fallback;
}
