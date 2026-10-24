import {z} from "zod";
export const applicationSchema=z.object({id:z.string().uuid(),status:z.literal("APPLIED"),applied_at:z.string(),previous_version_id:z.string().uuid(),new_version_id:z.string().uuid(),previous_revision:z.string(),new_revision:z.string(),sequence:z.number().int().min(2),constraint_digest:z.string(),payload_digest:z.string(),schedule_changed:z.literal(true)}).strict();
