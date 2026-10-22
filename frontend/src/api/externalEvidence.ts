import {z} from "zod";

export const EVIDENCE_LABEL = "EVIDENCE VERIFICATION REVIEW — NOT INSTITUTIONALLY CONFIRMED OR ACTIVE IN GA";
const outcome = z.enum(["VERIFIED","UNVERIFIED","INVALID","EXPIRED","REVOKED","STALE","UNSUPPORTED","PROVIDER_UNAVAILABLE"]);
const text = z.string().max(1000);
export const evidenceTrustSchema = z.object({
  version:z.literal("d8.1"), label:z.literal(EVIDENCE_LABEL), outcome,
  evidence_id:text.nullable(), evidence_revision:text.nullable(), verified_issuer:text.nullable(), issuing_organization:text.nullable(),
  evidence_type:text.nullable(), verification_method:text.nullable(), policy_revision:text.nullable(),
  policy_digest:z.string().regex(/^[a-f0-9]{64}$/).nullable(), policy_provenance:text.nullable(),
  authority_organizations:z.array(text).max(100), authority_terms:z.array(text).max(100), authority_subjects:z.array(text).max(1000),
  source_match:z.boolean(), term_match:z.boolean(), coverage_mode:z.enum(["exact_source","authorized_revision"]).nullable(),
  verified_at:z.string().datetime({offset:true}).nullable(), valid_until:z.string().datetime({offset:true}).nullable(),
  revocation_status:z.enum(["good","revoked","unknown"]),
  rows:z.array(z.object({source_row:z.number().int().positive(),outcome}).strict()).max(200),
  findings:z.array(z.object({code:text,explanation:text,action:text,source_row:z.number().int().positive().nullable()}).strict()).max(5000),
  institutionally_confirmed:z.literal(false), activated:z.literal(false),
}).strict();
export type EvidenceTrust = z.infer<typeof evidenceTrustSchema>;

export function verifyEvidenceCoverage(value:EvidenceTrust, rows:number[]) {
  if(value.rows.length!==rows.length || new Set(value.rows.map(r=>r.source_row)).size!==rows.length
    || value.rows.some(r=>!rows.includes(r.source_row))
    || value.findings.some(f=>f.source_row!==null&&!rows.includes(f.source_row))
    || value.outcome==="VERIFIED" && (!value.verified_issuer || !value.evidence_id || !value.policy_revision || !value.policy_digest
      || !value.policy_provenance || !value.source_match || !value.term_match || !value.verification_method
      || value.revocation_status!=="good" || !value.valid_until || Date.parse(value.valid_until)<=Date.now()
      || value.rows.some(r=>r.outcome!=="VERIFIED") || value.findings.length>0)) {
    throw new Error("The evidence findings could not be verified. Reassess the current preview.");
  }
}
