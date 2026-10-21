import {useEffect, useRef, useState} from "react";
import {createPortal, flushSync} from "react-dom";
import {HANDOFF_LABEL, prepareExternalHandoff} from "../../api/externalSchedules";
import type {ExternalPreview, ResourceResolution, ReviewHandoff, RowMapping} from "../../api/externalSchedules";
import {metadataError} from "../../services/dashboardMetadata";
import "./externalHandoff.css";

const resourceLabels = {resolved: "Resolved", unresolved: "Unresolved", ambiguous: "Ambiguous", unsupported: "Unsupported", missing_optional: "Missing optional resource"};
const statuses = {draft: "Draft", tentative: "Tentative", needs_review: "Needs review", invalid: "Invalid"};

function Resource({name, value}: {name: string; value: ResourceResolution}) {
  return <li><strong>{name}:</strong> Original: {value.original || "(not supplied)"} → {resourceLabels[value.state]}
    {value.id !== null && <> · {value.label} · ID: {value.id} · {value.method === "explicit" ? "Explicit preview mapping" : "Recognized source key"}</>}
    {value.candidate_ids.length > 0 && <> · Candidate IDs (not selected): {value.candidate_ids.join(", ")}</>}
  </li>;
}

export function ExternalHandoffDocument({value}: {value: ReviewHandoff}) {
  const review = value.review;
  return <article className="external-handoff-document" aria-label="Complete review handoff">
    <header>
      <h3>{HANDOFF_LABEL}</h3>
      <p>CCS External/GEC schedule review handoff · All {review.rows.length} original source rows included, including invalid rows.</p>
      <p>Revalidated at: {value.revalidated_at} (validation timestamp, not an academic date).</p>
      <p className="handoff-fingerprint">Preview identity: {value.preview_id}</p>
      <p>Source: {review.source_kind} · {review.source_name ?? "Manual input"}</p>
      <p className="handoff-fingerprint">Source SHA-256: {review.source_sha256 ?? "Not available — manual input has no uploaded-file hash"}</p>
      <p className="handoff-fingerprint">Reference inventory digest: {review.reference_digest}</p>
      <p>Parser {review.source_parser_version} · Review {review.projection_version} · Handoff {value.handoff_version}</p>
      <p className="handoff-warning">Academic terms/dates remain unverified. Printing, exporting or reviewing does not approve a schedule. No commitments are permanently stored, confirmed, locked or supplied to the GA. This is a snapshot of validation at the time above; later source/reference changes require a new review.</p>
      <p>{review.rows.filter(row => row.status === "invalid").length} invalid row(s) · {review.rows.filter(row => row.status === "needs_review").length} row(s) needing review. No filtered or valid-only subset is used.</p>
    </header>
    {review.rows.map(row => <section key={row.source_row} className="handoff-row" aria-label={"Handoff source row " + row.source_row}>
      <h4>Source row {row.source_row} · {row.original.subject_code || "Missing subject code"} · {row.original.title || "Missing title"}</h4>
      <p className="handoff-row-label">{HANDOFF_LABEL}</p>
      <dl>
        <div><dt>Supplying college/department</dt><dd>{row.original.supplier || "Missing supplier"}</dd></div>
        <div><dt>Academic term (unverified)</dt><dd>{row.original.academic_term || "Term unknown"}</dd></div>
        <div><dt>Original day and time</dt><dd>{row.original.days.join(", ") || "Missing days"} · {row.original.start || "Missing start"}–{row.original.end || "Missing end"}</dd></div>
        <div><dt>Intake intent / review finding</dt><dd>{statuses[row.original.status]} / {statuses[row.status]} · {row.calendar_supported ? "Plottable weekly pattern" : "Not plotted: invalid or unsupported pattern"}</dd></div>
        <div><dt>Source reference</dt><dd>{row.original.source_reference || "Not supplied"}</dd></div>
        <div><dt>Original notes</dt><dd className="handoff-notes">{row.original.notes || "Not supplied"}</dd></div>
      </dl>
      <ul className="handoff-resources">
        {row.sections.length ? row.sections.map((item, index) => <Resource key={index} name={"CCS section reference " + (index + 1)} value={item} />) : <li>CCS section: missing references; unresolved.</li>}
        <Resource name="Room (optional)" value={row.room} />
        <Resource name="Faculty/instructor (optional)" value={row.instructor} />
      </ul>
      <h5>Discrepancies ({row.discrepancies.length})</h5>
      {row.discrepancies.length ? <ul className="handoff-discrepancies">{row.discrepancies.map((issue, index) => <li key={index}>
        <strong>{issue.severity === "error" ? "ERROR" : "REVIEW"}: {issue.code}</strong> · {issue.field} · {issue.message}
        {issue.related_rows.length > 0 && <> · Related source rows: {issue.related_rows.join(", ")}</>}
      </li>)}</ul> : <p>No discrepancies reported by this preview validator; this is not approval or a guarantee of institutional constraint coverage.</p>}
    </section>)}
    <footer>End of complete review · {review.rows.length} source rows · {HANDOFF_LABEL}</footer>
  </article>;
}

export default function ExternalScheduleHandoff({source, mappings, onInvalid}: {source: ExternalPreview; mappings: RowMapping[]; onInvalid: () => void}) {
  const [result, setResult] = useState<ReviewHandoff>();
  const [printSnapshot, setPrintSnapshot] = useState<ReviewHandoff>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  async function prepare(print = false) {
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    setResult(undefined); setError(""); setBusy(true);
    try {
      const data = await prepareExternalHandoff(source, mappings, controller.signal);
      if (controller.signal.aborted) return;
      if (print) {
        // Native print captures a synchronous, fully rendered snapshot. Ordinary
        // Ctrl+P has only a blocked-output notice, never an old validated copy.
        flushSync(() => {setResult(data); setPrintSnapshot(data);});
        try {window.print();}
        finally {flushSync(() => setPrintSnapshot(undefined));}
      } else setResult(data);
    } catch (reason) {
      if (!controller.signal.aborted) {
        setResult(undefined); onInvalid();
        setError(metadataError(reason, "Handoff unavailable. Re-preview the source if it is stale, then retry. Nothing was printed or approved."));
      }
    } finally {if (!controller.signal.aborted) setBusy(false);}
  }
  return <section className="min-w-0 space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4" aria-label="Validated review handoff">
    <h2 className="text-xl font-semibold text-teal-900">Validated review handoff</h2>
    <p className="text-sm">Prepare a complete, temporary review snapshot. Both preparation and printing revalidate the current signed source and all resource mappings on the server. Calendar filters never omit handoff rows.</p>
    <p className="text-sm font-semibold">{HANDOFF_LABEL}</p>
    <div className="flex flex-wrap gap-3">
      <button type="button" className="ccs-btn-secondary" disabled={busy} onClick={() => prepare()}>Prepare validated review</button>
      <button type="button" className="ccs-btn-primary" disabled={busy || !result} onClick={() => prepare(true)}>Revalidate and print review</button>
    </div>
    {busy && <p role="status">Revalidating the complete handoff…</p>}
    {error && <div role="alert" className="break-words text-sm text-red-900"><h3 className="font-semibold">Handoff unavailable</h3><p>{error}</p></div>}
    {!result && !busy && !error && <p className="text-sm">No handoff prepared. All invalid rows and unresolved references will remain visible.</p>}
    {result && <ExternalHandoffDocument value={result} />}
    {createPortal(<div className="external-handoff-print-root">{printSnapshot ? <ExternalHandoffDocument value={printSnapshot} /> : <div><h1>{HANDOFF_LABEL}</h1><p>No freshly revalidated print snapshot. Return to the administrator page and use Revalidate and print review. This page is not a schedule approval.</p></div>}</div>, document.body)}
  </section>;
}
