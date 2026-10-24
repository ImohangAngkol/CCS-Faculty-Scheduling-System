import ExternalConfirmationLedger from "../../components/schedule/ExternalConfirmationLedger";
import type {ConfirmationReview} from "../../api/externalConfirmations";
import {useEffect, useRef, useState} from "react";
import type {FormEvent} from "react";
import axios from "axios";
import MetadataState from "../../components/dashboard/MetadataState";
import {emptyExternalRow, getExternalMetadata, previewFile, previewManual} from "../../api/externalSchedules";
import type {ExternalMetadata, ExternalPreview, ExternalRow, LegacyMetadata} from "../../api/externalSchedules";
import {metadataError} from "../../services/dashboardMetadata";
import ExternalScheduleReview from "../../components/schedule/ExternalScheduleReview";
import LegacyScheduleProvenance from "../../components/schedule/LegacyScheduleProvenance";

const labels = {supplier: "Supplying college / department", subject_code: "Subject code", title: "Descriptive title",
  academic_term: "Academic term (unverified)", start: "Start time", end: "End time", room: "Room (optional)",
  instructor: "Assigned instructor (optional)", source_reference: "Source reference", notes: "Notes"};
const dayLabels = [["M", "Monday"], ["T", "Tuesday"], ["W", "Wednesday"], ["TH", "Thursday"], ["F", "Friday"], ["S", "Saturday"]];
const statusLabel = {draft: "Draft", tentative: "Tentative", needs_review: "Needs review", invalid: "Invalid"};

function importError(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.status !== 401 && error.response?.status !== 403) {
    const detail = error.response?.data?.detail;
    if (detail && typeof detail.code === "string" && typeof detail.message === "string") return detail.code + ": " + detail.message;
  }
  return metadataError(error, "The preview could not be verified. Check the file or connection and retry.");
}

export default function ExternalSchedules() {
  const [confirmationReview,setConfirmationReview]=useState<ConfirmationReview>();
  const [metadata, setMetadata] = useState<ExternalMetadata>();
  const [metadataErrorText, setMetadataErrorText] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [form, setForm] = useState(emptyExternalRow);
  const [drafts, setDrafts] = useState<ExternalRow[]>([]);
  const [editing, setEditing] = useState<number | null>(null);
  const [file, setFile] = useState<File>();
  const [format, setFormat] = useState("canonical");
  const [legacyMetadata, setLegacyMetadata] = useState<LegacyMetadata>({supplier: "", source_reference: "", academic_term: "", status: "draft"});
  const [preview, setPreview] = useState<ExternalPreview>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [workspace, setWorkspace] = useState(0);
  const [previewSequence, setPreviewSequence] = useState(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getExternalMetadata(controller.signal).then(data => {if (!controller.signal.aborted) {setMetadata(data); setMetadataErrorText("");}})
      .catch(reason => {if (!controller.signal.aborted) setMetadataErrorText(metadataError(reason, "Reference metadata is unavailable. Retry loading."));});
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => () => pending.current?.abort(), []);
  function invalidate() {setConfirmationReview(undefined);pending.current?.abort(); pending.current = null; setBusy(false); setPreview(undefined); setError("");}
  function add(event: FormEvent) {
    event.preventDefault(); invalidate();
    if (editing === null && drafts.length >= 200) {setError("The manual queue is limited to 200 rows."); return;}
    setDrafts(editing === null ? [...drafts, form] : drafts.map((row, i) => i === editing ? form : row));
    setEditing(null); setForm(emptyExternalRow());
  }
  async function review(kind: "manual" | "file") {
    invalidate();
    const controller = new AbortController(); pending.current = controller; setBusy(true);
    try {
      const result = kind === "manual" ? await previewManual(drafts, controller.signal)
        : file ? await previewFile(file, controller.signal, format === "legacy_gec" ? legacyMetadata : undefined) : undefined;
      if (!controller.signal.aborted) {setPreview(result); setPreviewSequence(value => value+1);}
    } catch (reason) {if (!controller.signal.aborted) setError(importError(reason));}
    finally {if (!controller.signal.aborted) {setBusy(false); pending.current = null;}}
  }
  const rows = preview?.rows.map(row => ({...row.input, sourceRow: row.source_row, reviewStatus: row.status, issues: row.discrepancies}))
    ?? drafts.map((row, i) => ({...row, sourceRow: i+1, reviewStatus: row.status, issues: []}));
  return <div className="min-w-0 space-y-6">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5 sm:p-6">
      <p className="text-sm font-semibold text-teal-800">Administrator workspace · Preview only</p>
      <h1 className="mt-1 text-2xl font-bold text-slate-900">External/GEC Schedules</h1>
      <p className="mt-3 text-sm text-slate-700">Intake and calendar previews are temporary. Durable revisions and confirmation decisions are managed separately in the ledger below. Confirmation does not start or activate a GA run.</p>
      <p className="mt-2 text-sm text-amber-950">Temporary drafts and uploaded previews are lost when you leave or refresh this page. No verified academic term/date registry is configured.</p>
    </header>
    {!metadata && !metadataErrorText && <MetadataState title="Loading reference metadata" description="Reading the existing prototype catalog and resource labels…" />}
    {metadataErrorText && <MetadataState title="Reference metadata unavailable" description={metadataErrorText} retry={() => {setMetadataErrorText(""); setAttempt(value => value+1);}} />}
    {metadata && <>
      <section className="rounded-xl border border-slate-200 bg-white p-5" aria-labelledby="manual-intake">
        <h2 id="manual-intake" className="text-lg font-semibold text-teal-900">Manual intake</h2>
        <p className="mt-1 text-sm text-slate-600">Use current reference labels where known. Multiple sections use | separators. Unknown references remain unresolved; they are never created automatically.</p>
        <form onSubmit={add} className="mt-4 grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Object.entries(labels).map(([name, label]) => <label key={name} className="min-w-0 text-sm font-medium text-slate-700">{label}
            <input className="mt-1 block w-full min-w-0 rounded-lg border border-slate-300 p-2" name={name} value={form[name as keyof typeof labels]}
              maxLength={name === "notes" ? 1000 : name === "subject_code" ? 40 : name === "title" ? 200 : name === "source_reference" ? 250 : name === "instructor" ? 160 : 120}
              type={name === "start" || name === "end" ? "time" : "text"}
              list={name === "room" ? "external-rooms" : name === "instructor" ? "external-instructors" : name === "subject_code" ? "external-subjects" : undefined}
              onChange={event => setForm({...form, [name]: event.target.value})} />
          </label>)}
          <label className="min-w-0 text-sm font-medium text-slate-700">Affected CCS section(s)
            <input className="mt-1 block w-full min-w-0 rounded-lg border border-slate-300 p-2" name="sections" list="external-sections" maxLength={1000}
              value={form.sections.join("|")} onChange={event => setForm({...form, sections: event.target.value ? event.target.value.split("|") : []})} />
          </label>
          <label className="text-sm font-medium text-slate-700">Intake status
            <select className="mt-1 block w-full rounded-lg border border-slate-300 p-2" value={form.status} onChange={event => setForm({...form, status: event.target.value as ExternalRow["status"]})}><option value="draft">Draft</option><option value="tentative">Tentative</option></select>
          </label>
          <fieldset className="sm:col-span-2 lg:col-span-3"><legend className="text-sm font-medium text-slate-700">Day(s) of the week</legend>
            <div className="mt-2 flex flex-wrap gap-4">{dayLabels.map(([day, name]) => <label key={day} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.days.includes(day)} onChange={event => setForm({...form, days: event.target.checked ? [...form.days, day] : form.days.filter(value => value !== day)})} />{name}</label>)}</div>
          </fieldset>
          <button className="ccs-btn-primary justify-self-start" type="submit">{editing === null ? "Add draft row" : "Update draft row"}</button>
          {editing !== null && <button type="button" className="ccs-btn-secondary" onClick={() => {setEditing(null); setForm(emptyExternalRow());}}>Cancel editing</button>}
        </form>
        <datalist id="external-sections">{metadata.sections.map(row => <option key={row.id} value={row.label} />)}</datalist>
        <datalist id="external-rooms">{metadata.rooms.map(row => <option key={row.id} value={row.label} />)}</datalist>
        <datalist id="external-instructors">{metadata.instructors.map(row => <option key={row.id} value={row.label} />)}</datalist>
        <datalist id="external-subjects">{metadata.subjects.map(row => <option key={row.code} value={row.code}>{row.title}</option>)}</datalist>
        <div className="mt-4 flex flex-wrap items-center gap-3"><button type="button" className="ccs-btn-secondary" disabled={!drafts.length || busy} onClick={() => review("manual")}>Review manual drafts</button><span className="text-sm text-slate-600">{drafts.length} temporary manual row(s)</span></div>
      </section>
      <section className="rounded-xl border border-slate-200 bg-white p-5" aria-labelledby="file-intake">
        <h2 id="file-intake" className="text-lg font-semibold text-teal-900">CSV / XLSX import preview</h2>
        <p className="mt-2 text-sm text-slate-600">UTF-8 comma-separated CSV or one-sheet XLSX · 1 MiB · 200 rows · 13 columns. No formulas, macros, external links or embedded content. Use text cells or time-only start/end cells in XLSX. | separates sections and days.</p>
        <a className="mt-2 inline-block font-medium text-teal-800 underline" href="/templates/external-gec-fictional.csv" download>Download fictional CSV template</a>
        <label className="mt-4 block text-sm font-medium">Import format<select className="mt-1 block w-full max-w-md rounded border p-2" value={format} onChange={event => {invalidate(); setFormat(event.target.value);}}><option value="canonical">Canonical CSV / XLSX</option><option value="legacy_gec">Legacy GEC CSV (four columns)</option></select></label>
        {format === "legacy_gec" && <fieldset className="mt-4 space-y-3 rounded border border-amber-300 bg-amber-50 p-4"><legend className="font-semibold">Legacy metadata mapping</legend>
          <p className="text-sm">Requires exactly Year Level, Section, Course Number, Schedule. Use explicit AM/PM endpoints and compact M/T/W/TH/F/S/SAT day codes. Repeated days are ambiguous. Missing metadata stays unresolved. This adds unverified preview context only; no title, faculty, room or stable identity is inferred.</p>
          {(["supplier", "source_reference", "academic_term"] as const).map(name => <label key={name} className="block text-sm">{labels[name]} · administrator-supplied (unverified)<input className="mt-1 block w-full rounded border p-2" value={legacyMetadata[name]} maxLength={name === "source_reference" ? 250 : 120} onChange={event => {invalidate(); setLegacyMetadata({...legacyMetadata, [name]: event.target.value});}} /></label>)}
          <label className="block text-sm">Legacy intake status<select className="mt-1 block w-full rounded border p-2" value={legacyMetadata.status} onChange={event => {invalidate(); setLegacyMetadata({...legacyMetadata, status: event.target.value as LegacyMetadata["status"]});}}><option value="draft">Draft</option><option value="tentative">Tentative</option></select></label>
          <a className="inline-block text-teal-800 underline" href="/templates/external-gec-legacy-fictional.csv" download>Download fictional legacy CSV template</a>
          <p className="text-sm">Blank supplier/source reference and missing title produce Invalid findings. Supplied term text remains unverified. Correct the source or metadata and preview again; no subset is dropped.</p>
        </fieldset>}
        <div className="mt-4 flex min-w-0 flex-wrap items-center gap-3"><label className="min-w-0 text-sm">Schedule file<input key={workspace} type="file" className="mt-1 block w-full max-w-sm text-sm" accept={format === "legacy_gec" ? ".csv" : ".csv,.xlsx"} onChange={event => {invalidate(); setFile(event.target.files?.[0]);}} /></label>
          <button type="button" className="ccs-btn-secondary" disabled={!file || busy} onClick={() => review("file")}>Preview selected file</button></div>
      </section>
    </>}
    {busy && <MetadataState title="Validating preview" description="Checking all rows and references. No rows are being saved or activated." />}
    {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4"><h2 className="font-semibold text-red-900">Preview failed</h2><p className="mt-2 break-words text-sm">{error}</p><p className="mt-2 text-sm">Correct the input and retry using the review or preview button. No subset was accepted.</p></div>}
    {preview && <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm" aria-label="Preview provenance">
      <h2 className="font-semibold">Review preview · Not persisted · Not activated</h2>
      <p className="mt-1">Source: {preview.source_kind === "manual" ? "Manual drafts" : preview.source_name} · Parser {preview.parser_version}</p>
      {preview.source_sha256 && <p className="mt-1 break-all">Source SHA-256: {preview.source_sha256}</p>}
      <p className="mt-1">Term/date coverage remains unverified. Same-week overlap checks are provisional. This preview is not a constraint set or confirmation.</p>
    </section>}
    {preview?.legacy && <LegacyScheduleProvenance legacy={preview.legacy} />}
    <ExternalConfirmationLedger review={confirmationReview}/>
    {preview && metadata && <ExternalScheduleReview key={previewSequence} source={preview} metadata={metadata} onConfirmationReview={setConfirmationReview} />}
    <section className="min-w-0 rounded-xl border border-slate-200 bg-white p-5" aria-labelledby="review-table">
      <h2 id="review-table" className="text-lg font-semibold text-teal-900">Intake review</h2>
      {preview?.review_token && <p className="mt-2 text-sm text-slate-600">Original intake findings before resource reconciliation. The calendar review above shows the currently revalidated mappings; original source text below is unchanged.</p>}
      {!rows.length ? <p className="mt-3 text-sm text-slate-600">No rows to review. Add a manual draft or preview a file.</p> : <>
        <p className="mt-2 text-sm text-slate-600">{preview ? "Validated preview" : "Unvalidated temporary drafts"} · {rows.length} row(s). Draft/Tentative is the intake intent; review findings are separate.</p>
        <div className="mt-4 max-w-full overflow-x-auto"><table className="w-full min-w-[1050px] table-fixed text-left text-sm">
          <thead className="bg-teal-800 text-white"><tr>{["Source row", "Subject", "Supplier / term", "Sections", "Day / time", "Room / instructor", "Source / notes", "Status", "Discrepancies"].map(title => <th key={title} className="p-3">{title}</th>)}</tr></thead>
          <tbody>{rows.map((row, i) => <tr key={i} className="border-b border-slate-200 align-top">
            <td className="p-3">{row.sourceRow}{(!preview || preview.source_kind === "manual") && <div className="mt-2 flex flex-col gap-2"><button type="button" className="text-teal-800 underline" onClick={() => {invalidate(); setForm(drafts[i]); setEditing(i);}}>Edit row</button><button type="button" className="text-red-800 underline" onClick={() => {invalidate(); setDrafts(drafts.filter((_, n) => n !== i)); setEditing(null); setForm(emptyExternalRow());}}>Remove row</button></div>}</td>
            <td className="break-words p-3"><strong>{row.subject_code || "Missing code"}</strong><p>{row.title || "Missing title"}</p></td>
            <td className="break-words p-3">{row.supplier || "Missing supplier"}<p className="mt-1">{row.academic_term || "Term unknown"}</p></td>
            <td className="break-words p-3">{row.sections.join(", ") || "Missing sections"}</td>
            <td className="break-words p-3">{row.days.join(", ") || "Missing days"}<p>{row.start || "?"} – {row.end || "?"}</p></td>
            <td className="break-words p-3">{row.room || "Room not supplied"}<p className="mt-1">{row.instructor || "Instructor not supplied"}</p></td>
            <td className="break-words p-3">{row.source_reference || "Missing source reference"}<p className="mt-1 whitespace-pre-wrap">{row.notes}</p></td>
            <td className="p-3"><strong className={row.reviewStatus === "invalid" ? "text-red-800" : "text-amber-900"}>{statusLabel[row.reviewStatus]}</strong><p className="mt-1">{statusLabel[row.status]} intent</p></td>
            <td className="break-words p-3">{row.issues.length ? <ul className="space-y-3">{row.issues.map((issue, n) => <li key={n}><strong className={issue.severity === "error" ? "text-red-800" : "text-amber-900"}>{issue.code}</strong><p>{issue.message}</p><p>Field: {issue.field}{issue.related_rows.length ? " · Related source rows: " + issue.related_rows.join(", ") : ""}</p></li>)}</ul> : "Not validated"}</td>
          </tr>)}</tbody>
        </table></div>
      </>}
    </section>
    <button type="button" className="ccs-btn-secondary" onClick={() => {invalidate(); setDrafts([]); setForm(emptyExternalRow()); setEditing(null); setFile(undefined); setLegacyMetadata({supplier: "", source_reference: "", academic_term: "", status: "draft"}); setWorkspace(value => value+1);}}>Clear temporary workspace</button>
  </div>;
}
