import ExternalEvidencePanel from "./ExternalEvidencePanel";
import {READINESS_LABEL} from "../../api/externalReadiness";
import type {ReadinessAssessment} from "../../api/externalReadiness";

export default function ReadinessDocument({value}:{value:ReadinessAssessment}) {
  return <section className="min-w-0 space-y-3 break-words rounded-lg border border-amber-300 bg-amber-50 p-4" aria-label="Readiness assessment">
    <ExternalEvidencePanel value={value.evidence_trust} supplier={value.metadata.supplier} reference={value.metadata.evidence_reference}/>
    <h3 className="font-semibold text-teal-900">{READINESS_LABEL}</h3>
    <p><strong>{value.status}</strong> · {value.blocker_count} blockers · {value.warning_count} warnings · Policy {value.policy_version}</p>
    <p>READY means eligible for subsequent institutional confirmation review only. Reviewing or printing never confirms, approves, publishes or activates a schedule.</p>
    <p>Verification: {value.verification_status.replaceAll("_"," ")} · Evidence: {value.verification_reference || "No trusted verification available"} · Authority policy: {value.authority_policy_version || "Not configured"}</p>
    <p>Administrator-provided completion: {value.metadata.supplier || "Supplier unknown"} · {value.metadata.source_reference || "Reference missing"} · Revision: {value.metadata.source_revision || "Unknown"}</p>
    <p>Academic year / term: {value.metadata.academic_year || "Unknown"} · {value.metadata.term || "Unknown"} · {value.metadata.effective_start || "?"}–{value.metadata.effective_end || "?"} · {value.metadata.timezone || "Timezone unknown"}</p>
    <p>Recurrence: {value.metadata.recurrence} · Exceptions: {value.metadata.exceptions} · {value.metadata.exception_notes}</p>
    <p>Source rows: {value.original_row_count}. Candidate syntax: {value.effective_review.rows.filter(r=>r.calendar_supported).length} plottable / {value.effective_review.rows.filter(r=>!r.calendar_supported).length} unsupported. Section references: {value.effective_review.rows.flatMap(r=>r.sections).filter(r=>r.state==="resolved").length} resolved / {value.effective_review.rows.flatMap(r=>r.sections).filter(r=>r.state!=="resolved").length} unresolved.</p>
    <p className="text-xs">Assessed: {value.assessed_at} · Expires: {value.expires_at} · {value.assessment_fingerprint} · Reference digest: {value.reference_digest}</p>
    <p className="break-all text-xs">Source fingerprint: {value.source_fingerprint} · Completed input fingerprint: {value.input_fingerprint}</p>
    {value.metadata.rows.map(row=><div key={row.source_row} className="border-t border-amber-200 pt-2 text-sm"><strong>Completion · source row {row.source_row}</strong><p>Title proposal: {row.title || "Retain original / unresolved"} · Component: {row.component} · Sharing: {row.shared}</p><p>Explicit sections: {row.section_ids.join(", ") || "Use D4 mappings"} · Room applicability: {row.room_applicability} · Instructor applicability: {row.instructor_applicability}</p><p>Administrator evidence claim: {row.evidence_reference || "Missing"}</p>{row.proposed_meeting && <p>Proposed meeting: {row.proposed_meeting.days.join(", ")} · {row.proposed_meeting.start}–{row.proposed_meeting.end} · Reason: {row.proposed_meeting.reason} · Evidence claim: {row.proposed_meeting.evidence_reference}. Original values are retained in source details.</p>}</div>)}
    <ul className="space-y-2 text-sm">{value.findings.map((finding,index)=><li key={index} className={finding.severity==="blocker"?"text-red-900":"text-amber-950"}><strong>{finding.severity.toUpperCase()} · {finding.code}</strong> · {finding.field}{finding.source_row!==null&&<> · Source row {finding.source_row}</>}<p>{finding.explanation}</p><p>Action: {finding.action}{finding.related_rows.length>0&&<> · Related source rows: {finding.related_rows.join(", ")}</>}</p></li>)}</ul>
  </section>;
}
