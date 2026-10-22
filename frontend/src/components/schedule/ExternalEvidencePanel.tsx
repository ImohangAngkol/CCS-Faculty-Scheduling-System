import {EVIDENCE_LABEL} from "../../api/externalEvidence";
import type {EvidenceTrust} from "../../api/externalEvidence";

export default function ExternalEvidencePanel({value,supplier,reference}:{value?:EvidenceTrust|null;supplier:string;reference:string}) {
  return <section aria-label="Evidence verification review" className="min-w-0 space-y-2 break-words rounded-lg border border-teal-300 bg-teal-50 p-4 text-sm">
    <h3 className="font-semibold text-teal-900">{EVIDENCE_LABEL}</h3>
    <p>Claimed supplying college: {supplier||"Unknown"} · Administrator-entered evidence reference: {reference||"Missing"}. These are claims, not issuer authentication.</p>
    <p>Document presence, filenames, email domains and matching hashes do not establish issuing authority. This review never institutionally confirms a schedule.</p>
    {!value ? <p role="status">Evidence not yet evaluated for current inputs. Check readiness to evaluate trust server-side. No institutional provider is configured by default.</p> : <>
      <p><strong>Evidence outcome: {value.outcome}</strong> · Institutionally confirmed: No · Active in GA: No</p>
      <p>Verified issuer: {value.verified_issuer||"Not established"} · Issuing organization: {value.issuing_organization||"Not established"}</p>
      <p>Evidence identity: {value.evidence_id||"Not established"} · Revision: {value.evidence_revision||"Unknown"} · Type: {value.evidence_type||"Not established"} · Method: {value.verification_method||"Not established"}</p>
      <p>Authority policy: {value.policy_revision||"Not established"} · Configuration provenance: {value.policy_provenance||"Unavailable"}</p>
      <p>Authorized organizations: {value.authority_organizations.join(", ")||"Not established"} · Terms: {value.authority_terms.join(", ")||"Not established"} · Courses: {value.authority_subjects.join(", ")||"Not established"}</p>
      <p>Source/candidate fingerprint match: {value.source_match?"Yes":"Not established"} · Academic-term coverage: {value.term_match?"Yes":"Not established"} · Evidence scope: {value.coverage_mode||"Not established"}</p>
      <p>Last provider check: {value.verified_at||"Unavailable"} · Valid until: {value.valid_until||"Not established"} · Revocation status: {value.revocation_status}. Unknown status cannot establish trust.</p>
      <p>Freshness: current only for this assessment and these inputs; edits, expiry or policy/evidence changes require re-evaluation. Printing rechecks the provider.</p>
      <ul>{value.rows.map(row=><li key={row.source_row}>Evidence source row {row.source_row}: {row.outcome}</li>)}</ul>
      {value.findings.map((finding,i)=><p key={i} className="text-red-900"><strong>{finding.code}</strong>{finding.source_row!==null?" · Source row "+finding.source_row:""} · {finding.explanation} Action: {finding.action}</p>)}
    </>}
  </section>;
}
