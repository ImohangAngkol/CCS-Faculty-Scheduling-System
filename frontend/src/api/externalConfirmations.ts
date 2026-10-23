import {z} from "zod";
import {apiClient,API_BASE} from "../services/apiSession.ts";
import {reviewProjectionSchema} from "./externalSchedules.ts";
import {completionSchema} from "./externalReadiness.ts";
import type {CompletionMetadata} from "./externalReadiness.ts";
import type {RowMapping} from "./externalSchedules.ts";

export type ConfirmationReview={review_token:string;mappings:RowMapping[];metadata:CompletionMetadata;assessment_receipt:string};
const id=z.string().uuid(), hash=z.string().regex(/^[a-f0-9]{64}$/);
const record=z.object({id,academic_year:z.string(),term:z.string(),supplier:z.string(),version:z.number().int().nonnegative(),head_event_id:id.nullable(),status:z.enum(["PROPOSED","CONFIRMED","REVOKED"]),current_revision_id:id.nullable(),current_evidence_status:z.literal("NOT_RECHECKED"),activated:z.literal(false)}).strict();
export const recordsSchema=z.object({records:z.array(record).max(100),has_more:z.boolean(),confirmation_policy:z.string(),activated:z.literal(false)}).strict();
const revision=z.object({id,base_event_id:id.nullable(),content_digest:hash,reason:z.string(),created_at:z.string(),state:z.enum(["PROPOSED","CONFIRMED","SUPERSEDED","REVOKED"])}).strict();
export const historySchema=z.object({record,events:z.array(z.object({id,revision_id:id,previous_event_id:id.nullable(),sequence:z.number().int().positive(),action:z.enum(["CONFIRM","REVOKE"]),actor_id:id,policy_reference:z.string(),policy_digest:hash,content_digest:hash,evidence_digest:hash,created_at:z.string(),reason:z.string()}).strict()).max(1000),revisions:z.array(revision).max(200)}).strict();
export const detailSchema=z.object({id,record_id:id,content_digest:hash,content:z.object({version:z.literal("d9.1"),review:reviewProjectionSchema,metadata:completionSchema,candidate:reviewProjectionSchema}).strict(),evidence_at_proposal:z.unknown(),current_evidence_status:z.literal("NOT_RECHECKED"),activated:z.literal(false)}).strict();
const eligibilitySchema=z.object({revision_id:id,eligible:z.boolean(),state:z.enum(["ELIGIBLE","BLOCKED"]),blocker:z.string().nullable(),evidence_trust:z.unknown(),readiness:z.enum(["READY","BLOCKED"]),message:z.string(),persisted:z.literal(false),activated:z.literal(false)}).strict();
export type LedgerHistory=z.infer<typeof historySchema>;
export type RevisionDetail=z.infer<typeof detailSchema>;
const proposalResult=z.object({revision_id:id,record_id:id,state:z.literal("PROPOSED"),persisted:z.literal(true),activated:z.literal(false)}).strict();
const decisionResult=z.object({event_id:id,state:z.enum(["CONFIRMED","REVOKED"]),persisted:z.literal(true),activated:z.literal(false)}).strict();
const endpoint=API_BASE+"/api/external-confirmations";
export async function listConfirmations(signal?:AbortSignal){return recordsSchema.parse((await apiClient.get(endpoint,{signal})).data);}
export async function confirmationHistory(recordId:string,signal?:AbortSignal){return historySchema.parse((await apiClient.get(endpoint+"/records/"+id.parse(recordId),{signal})).data);}
export async function confirmationRevision(revisionId:string,signal?:AbortSignal){return detailSchema.parse((await apiClient.get(endpoint+"/revisions/"+id.parse(revisionId),{signal})).data);}
export async function proposeConfirmation(recordId:string,expectedVersion:number,reason:string,review:ConfirmationReview){return proposalResult.parse((await apiClient.post(endpoint+"/revisions",{record_id:id.parse(recordId),revision_id:crypto.randomUUID(),expected_version:expectedVersion,reason,review})).data);}
export async function requestConfirmation(revisionId:string,expectedVersion:number,reason:string,review:ConfirmationReview){return eligibilitySchema.parse((await apiClient.post(endpoint+"/revisions/"+id.parse(revisionId)+"/request-confirmation",{operation_id:crypto.randomUUID(),expected_version:expectedVersion,reason,review})).data);}
export async function confirmRevision(revisionId:string,expectedVersion:number,reason:string,review:ConfirmationReview){return decisionResult.parse((await apiClient.post(endpoint+"/revisions/"+id.parse(revisionId)+"/confirm",{operation_id:crypto.randomUUID(),expected_version:expectedVersion,reason,review})).data);}
export async function revokeConfirmation(recordId:string,expectedVersion:number,reason:string){return decisionResult.parse((await apiClient.post(endpoint+"/records/"+id.parse(recordId)+"/revoke",{operation_id:crypto.randomUUID(),expected_version:expectedVersion,reason})).data);}
