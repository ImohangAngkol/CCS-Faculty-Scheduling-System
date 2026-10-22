import {z} from "zod";
import {apiClient, API_BASE} from "../services/apiSession.ts";
import {reviewProjectionSchema, handoffIdentity} from "./externalSchedules.ts";
import type {ExternalPreview, RowMapping} from "./externalSchedules.ts";

export const READINESS_LABEL = "CONFIRMATION-READINESS REVIEW ONLY — NOT CONFIRMED OR ACTIVE IN GA";
const proposal = z.object({days:z.array(z.string()).max(7),start:z.string(),end:z.string(),reason:z.string(),evidence_reference:z.string()}).strict();
export const rowCompletionSchema = z.object({source_row:z.number().int().positive(),title:z.string(),component:z.enum(["unknown","lecture","laboratory","external_meeting"]),section_ids:z.array(z.string()).max(12),shared:z.enum(["unknown","single_section","shared"]),room_applicability:z.enum(["unknown","applicable","not_applicable"]),instructor_applicability:z.enum(["unknown","applicable","not_applicable"]),evidence_reference:z.string(),proposed_meeting:proposal.nullable()}).strict();
export const completionSchema = z.object({supplier:z.string(),source_reference:z.string(),source_revision:z.string(),evidence_reference:z.string(),academic_year:z.string(),term:z.string(),effective_start:z.string(),effective_end:z.string(),timezone:z.string(),recurrence:z.enum(["unknown","weekly","unsupported"]),exceptions:z.enum(["unknown","none_reported","listed_unsupported"]),exception_notes:z.string(),rows:z.array(rowCompletionSchema).max(200)}).strict();
export type CompletionMetadata = z.infer<typeof completionSchema>;
export type RowCompletion = z.infer<typeof rowCompletionSchema>;
export const assessmentSchema = z.object({policy_version:z.literal("d7.1"),label:z.literal(READINESS_LABEL),status:z.enum(["READY","BLOCKED"]),approved:z.literal(false),activated:z.literal(false),persisted:z.literal(false),metadata_origin:z.literal("administrator_provided"),verification_status:z.enum(["unavailable","requires_verification","verified_for_readiness"]),verification_reference:z.string().nullable(),authority_policy_version:z.string().nullable(),metadata:completionSchema,source_fingerprint:z.string().regex(/^[a-f0-9]{64}$/),input_fingerprint:z.string().regex(/^[a-f0-9]{64}$/),assessment_fingerprint:z.string().regex(/^d7-[a-f0-9]{64}$/),reference_digest:z.string().regex(/^[a-f0-9]{64}$/),blocker_count:z.number().int().nonnegative(),warning_count:z.number().int().nonnegative(),findings:z.array(z.object({code:z.string(),severity:z.enum(["blocker","warning"]),field:z.string(),source_row:z.number().int().positive().nullable(),related_rows:z.array(z.number().int().positive()),explanation:z.string(),action:z.string()}).strict()).max(5000),effective_review:reviewProjectionSchema,original_row_count:z.number().int().positive(),assessed_at:z.string().datetime({offset:true}),expires_at:z.string().datetime({offset:true}),assessment_receipt:z.string().nullable()}).strict();
export type ReadinessAssessment = z.infer<typeof assessmentSchema>;
const endpoint=API_BASE+"/api/external-schedules";

export function emptyCompletion(source:ExternalPreview):CompletionMetadata {
  return {supplier:"",source_reference:"",source_revision:"",evidence_reference:"",academic_year:"",term:"",effective_start:"",effective_end:"",timezone:"",recurrence:"unknown",exceptions:"unknown",exception_notes:"",rows:source.rows.map(r=>({source_row:r.source_row,title:"",component:"unknown",section_ids:[],shared:"unknown",room_applicability:"unknown",instructor_applicability:"unknown",evidence_reference:"",proposed_meeting:null}))};
}

export async function verifyAssessment(value:unknown, source:ExternalPreview, metadata:CompletionMetadata):Promise<ReadinessAssessment> {
  const data=assessmentSchema.parse(value);
  const blockers=data.findings.filter(f=>f.severity==="blocker").length;
  const warnings=data.findings.length-blockers;
  const {assessment_fingerprint,assessed_at,expires_at,assessment_receipt,...content}=data;
  void assessed_at;void assessment_receipt;
  if ((await handoffIdentity(content)).replace(/^d5-/,"d7-")!==assessment_fingerprint
      || JSON.stringify(data.metadata)!==JSON.stringify(metadata)
      || data.original_row_count!==source.rows.length || data.effective_review.rows.length!==source.rows.length
      || data.effective_review.source_sha256!==source.source_sha256 || data.effective_review.source_name!==source.source_name
      || data.effective_review.reference_digest!==data.reference_digest
      || new Set(data.effective_review.rows.map(r=>r.source_row)).size!==source.rows.length
      || data.effective_review.rows.some(r=>!source.rows.some(s=>s.source_row===r.source_row))
      || data.blocker_count!==blockers || data.warning_count!==warnings || (data.status==="READY")!==(blockers===0)
      || data.status==="READY" && (data.verification_status!=="verified_for_readiness" || !data.verification_reference || !data.authority_policy_version)
      || Date.parse(expires_at)<=Date.now()) throw new Error("The readiness assessment could not be verified. Assess the current preview again.");
  return data;
}

export async function assessReadiness(source:ExternalPreview,mappings:RowMapping[],metadata:CompletionMetadata,signal?:AbortSignal) {
  if(!source.review_token)throw new Error("Reimport this source with the current backend.");
  const response=await apiClient.post(endpoint+"/readiness",{review_token:source.review_token,mappings,metadata},{signal});
  const data=await verifyAssessment(response.data,source,metadata);
  if(!data.assessment_receipt)throw new Error("The current session assessment receipt is missing.");
  return data;
}

export async function invalidateReadiness(source:ExternalPreview) {
  if(source.review_token)await apiClient.post(endpoint+"/readiness/invalidate",{review_token:source.review_token,mappings:[]});
}
