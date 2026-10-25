import {z} from "zod";
import {apiClient} from "../services/apiSession.ts";
import {record,review} from "./adjustments.ts";
import {applicationSchema} from "./scheduleApplicationModel.ts";
export {chairError as applicationError} from "./chairReviews.ts";
const base="/api/schedule-applications";
const access=z.object({capability:z.literal("schedule_application"),departments:z.array(z.object({id:z.string().uuid(),label:z.string()}).strict())}).strict();
const queue=z.object({items:z.array(z.object({id:z.string().uuid(),department_id:z.string().uuid(),faculty_id:z.string().uuid(),subject:z.string(),section:z.string(),status:z.enum(["PENDING_APPLICATION","APPLIED"]),decision_id:z.string().uuid()}).strict())}).strict();
const command=z.object({decision_id:z.string().uuid(),decision_digest:z.string(),expected_revision:z.string(),expected_sequence:z.number().int().positive(),constraint_digest:z.string()}).strict();
const preview=z.object({request:record,application:applicationSchema.nullable(),can_apply:z.boolean(),status:z.enum(["APPLIED","PENDING_APPLICATION","APPLICATION_BLOCKED"]),before:review.shape.original.nullable(),after:review.shape.proposal.nullable(),validation:z.object({outcome:z.enum(["VALID","BLOCKED"]),findings:z.array(z.object({code:z.string(),message:z.string()}).strict()),policy_reference:z.string(),capacity_applicability:z.enum(["required","not_applicable"]),capacity_reference:z.string(),fitness_recalculated:z.literal(false)}).strict().nullable(),current:z.object({id:z.string().uuid().nullable(),sequence:z.number().int().positive(),revision:z.string()}).strict().nullable(),command:command.nullable()}).strict().refine(p=>p.status==="APPLIED"?Boolean(p.application&&p.request.application?.id===p.application.id&&!p.can_apply&&!p.command):!p.application&&(p.can_apply?(p.status==="PENDING_APPLICATION"&&p.validation?.outcome==="VALID"&&p.command!==null):p.status==="APPLICATION_BLOCKED"),"Inconsistent application eligibility");
const meeting=review.shape.original.extend({faculty_id:z.string()}).strict();
const versions=z.object({versions:z.array(z.object({id:z.string().uuid(),sequence:z.number().int().positive(),revision:z.string(),previous_id:z.string().uuid().nullable(),origin:z.enum(["VERIFIED_PUBLISHED_SOURCE","POST_GA_AUTHORIZED_ADJUSTMENT"]),meetings:z.array(meeting),department_filtered:z.literal(true)}).strict()),current_version_id:z.string().uuid().nullable(),source_revision:z.string(),read_only:z.literal(true)}).strict();
export type ApplicationPreview=z.infer<typeof preview>;
export type ApplicationQueue=z.infer<typeof queue>;
export type PublishedVersions=z.infer<typeof versions>;
export async function applicationAccess(signal?:AbortSignal){return access.parse((await apiClient.get(base+"/access",{signal})).data);}
export async function applicationQueue(include_applied=false,signal?:AbortSignal){return queue.parse((await apiClient.get(base,{params:{include_applied},signal})).data);}
export async function applicationPreview(id:string){return preview.parse((await apiClient.get(`${base}/${encodeURIComponent(id)}/preview`)).data);}
export async function applyAdjustment(row:ApplicationPreview,operation_id:string){if(!row.command)throw new Error("Preview required");return applicationSchema.parse((await apiClient.post(`${base}/${row.request.id}/apply`,{...row.command,operation_id})).data);}
export async function publishedVersions(version_id?:string,signal?:AbortSignal){return versions.parse((await apiClient.get(base+"/versions",{params:{version_id},signal})).data);}
