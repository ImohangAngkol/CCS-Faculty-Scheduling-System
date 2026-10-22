import {useEffect, useRef, useState} from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import {reviewExternal} from "../../api/externalSchedules";
import type {ExternalMetadata, ExternalPreview, ResourceResolution, ReviewMeeting, ReviewProjection, RowMapping} from "../../api/externalSchedules";
import {metadataError} from "../../services/dashboardMetadata";
import {emptyReviewFilters, filterReviewRows, hasResourceOverlap, reviewCalendarEvents} from "./externalReviewModel";
import type {ReviewFilters} from "./externalReviewModel";
import ExternalScheduleHandoff from "./ExternalScheduleHandoff";
import ExternalScheduleReadiness from "./ExternalScheduleReadiness";
import {assessReadiness, emptyCompletion, invalidateReadiness} from "../../api/externalReadiness";
import type {CompletionMetadata, ReadinessAssessment} from "../../api/externalReadiness";

const stateLabels = {resolved: "Resolved", unresolved: "Unresolved", ambiguous: "Ambiguous", unsupported: "Unsupported", missing_optional: "Missing optional resource"};
const intentLabels = {draft: "Draft", tentative: "Tentative"};
function ResourceState({value}: {value?: ResourceResolution}) {
  return <p className="mt-1 text-sm text-slate-600">{value ? stateLabels[value.state] + (value.label ? " · " + value.label : "") + (value.method === "explicit" ? " · Explicit preview mapping" : "") : "Awaiting full-batch validation"}</p>;
}

export default function ExternalScheduleReview({source, metadata}: {source: ExternalPreview; metadata: ExternalMetadata}) {
  const [projection, setProjection] = useState<ReviewProjection>();
  const [mappings, setMappings] = useState<RowMapping[]>([]);
  const [busy, setBusy] = useState(Boolean(source.review_token));
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<ReviewFilters>(emptyReviewFilters);
  const [selected, setSelected] = useState<number | null>(null);
  const pending = useRef<AbortController | null>(null);
  const [completion,setCompletion] = useState(()=>emptyCompletion(source));
  const [completionTouched,setCompletionTouched] = useState(false);
  const [assessment,setAssessment] = useState<ReadinessAssessment>();
  const [assessmentBusy,setAssessmentBusy] = useState(false);
  const [assessmentError,setAssessmentError] = useState("");
  const [freshness,setFreshness] = useState("Not yet assessed");
  const assessmentPending = useRef<AbortController | null>(null);
  const invalidations = useRef<Promise<void>>(Promise.resolve());
  useEffect(()=>()=>assessmentPending.current?.abort(),[]);
  useEffect(()=>{
    if(!assessment)return;
    const timer=setTimeout(()=>{setAssessment(undefined);setFreshness("Stale — assessment expired");},Math.min(Math.max(0,Date.parse(assessment.expires_at)-Date.now()),2147483647));
    return ()=>clearTimeout(timer);
  },[assessment]);
  function stale() {
    assessmentPending.current?.abort();setAssessment(undefined);setAssessmentBusy(false);setAssessmentError("");setFreshness("Stale — inputs changed; assess again");
    if(completionTouched) {
      invalidations.current=invalidations.current.catch(()=>{}).then(()=>invalidateReadiness(source));
      void invalidations.current.catch(reason=>setAssessmentError(metadataError(reason,"The preview may be stale. Reimport and retry.")));
    }
  }
  function complete(value:CompletionMetadata) {stale();setCompletion(value);setCompletionTouched(true);}
  async function assess() {
    assessmentPending.current?.abort();const controller=new AbortController();assessmentPending.current=controller;
    setAssessment(undefined);setAssessmentBusy(true);setAssessmentError("");setCompletionTouched(true);setFreshness("Assessing");
    try {await invalidations.current;const value=await assessReadiness(source,mappings,completion,controller.signal);if(!controller.signal.aborted){setAssessment(value);setFreshness("Current server assessment");}}
    catch(reason){if(!controller.signal.aborted){setFreshness("Unavailable / stale");setAssessmentError(metadataError(reason,"Reimport stale sources or correct completion metadata and retry."));}}
    finally{if(!controller.signal.aborted)setAssessmentBusy(false);}
  }
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    if (!source.review_token) return;
    const controller = new AbortController(); pending.current = controller;
    reviewExternal(source, [], controller.signal).then(data => {if (!controller.signal.aborted) {setProjection(data); setBusy(false);}})
      .catch(reason => {if (!controller.signal.aborted) {setError(metadataError(reason, "Review unavailable. Reload metadata and preview the source again if references changed.")); setBusy(false);}});
    return () => controller.abort();
  }, [source]);

  function mapResource(line: number, field: "sections" | "room" | "instructor", value: string, index = 0) {
    stale();
    pending.current?.abort(); setBusy(false); setProjection(undefined); setError("");
    setMappings(current => {
      const item = current.find(m => m.source_row === line) ?? {source_row: line};
      const updated = field === "sections"
        ? {...item, sections: [...(item.sections ?? []).filter(s => s.reference_index !== index), ...(value ? [{reference_index: index, target_id: value}] : [])]}
        : {...item, [field + "_id"]: value || null};
      return [...current.filter(m => m.source_row !== line), updated];
    });
  }
  async function revalidate() {
    stale();
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    setProjection(undefined); setBusy(true); setError("");
    try {const data = await reviewExternal(source, mappings, controller.signal); if (!controller.signal.aborted) setProjection(data);}
    catch (reason) {if (!controller.signal.aborted) setError(metadataError(reason, "Review unavailable. Reload metadata and preview the source again if references changed."));}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  const calendarProjection = assessment?.effective_review ?? projection;
  const visible = filterReviewRows(calendarProjection?.rows ?? [], filters);
  const detail = source.rows.find(r => r.source_row === selected) ?? source.rows.find(r => r.source_row === visible[0]?.source_row) ?? source.rows[0];
  const current = projection?.rows.find(r => r.source_row === detail?.source_row);
  const mapping = mappings.find(m => m.source_row === detail?.source_row);
  const unique = (values: string[]) => [...new Set(values)].sort();
  function filter(name: keyof ReviewFilters, value: string) {setSelected(null); setFilters({...filters, [name]: value});}
  if (!source.review_token) return <section className="rounded-xl border border-amber-200 bg-amber-50 p-4" aria-label="Calendar review"><h2 className="font-semibold">Weekly review calendar</h2><p className="mt-2 text-sm">This response has no current preview receipt. Preview the source with the current backend to enable calendar review and reconciliation.</p></section>;
  return <section className="min-w-0 space-y-4 rounded-xl border border-teal-200 bg-white p-4 sm:p-5" aria-label="Calendar review">
    <h2 className="text-xl font-semibold text-teal-900">Weekly review calendar</h2>
    <p className="text-sm text-slate-600">Read-only weekly pattern · Academic dates unverified · Draft/Tentative only · Not saved or activated. Red labels identify resource overlap findings; simultaneous rows remain separate.</p>
    {busy && <p role="status">Validating complete source and resource mappings…</p>}
    {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-900">{error}</p>}
    {!projection && !busy && !error && <p role="status" className="rounded-lg bg-amber-50 p-3">Mappings changed. Revalidate the complete batch before viewing an updated calendar.</p>}
    <ExternalScheduleReadiness source={source} resources={metadata} value={completion} onChange={complete} onAssess={assess} assessment={assessment} busy={assessmentBusy} error={assessmentError} freshness={freshness} />
    {assessment&&<p className="rounded border border-amber-300 p-3 text-sm">Calendar shows the administrator-completed candidate for readiness review. Original imported details remain below. This is not an official or activated timetable.</p>}
    <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
      <label>Review section<select className="mt-1 block w-full rounded border p-2" value={filters.section} onChange={event => filter("section", event.target.value)}><option value="">All sections</option>{metadata.sections.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}{unique((projection?.rows ?? []).flatMap(r => r.sections.filter(s => !s.id).map(s => s.original))).map(value => <option key={"source:" + value} value={"source:" + value}>Unresolved: {value || "(blank)"}</option>)}</select></label>
      <label>Supplying college filter<select className="mt-1 block w-full rounded border p-2" value={filters.supplier} onChange={event => filter("supplier", event.target.value)}><option value="">All suppliers</option>{unique(source.rows.map(r => r.input.supplier)).map(v => <option key={v} value={v}>{v || "(missing)"}</option>)}</select></label>
      <label>Subject filter<select className="mt-1 block w-full rounded border p-2" value={filters.subject} onChange={event => filter("subject", event.target.value)}><option value="">All subjects</option>{unique(source.rows.map(r => r.input.subject_code)).map(v => <option key={v} value={v}>{v || "(missing)"}</option>)}</select></label>
      <label>Draft/Tentative filter<select className="mt-1 block w-full rounded border p-2" value={filters.intent} onChange={event => filter("intent", event.target.value)}><option value="">All intake statuses</option><option value="draft">Draft</option><option value="tentative">Tentative</option></select></label>
      <label>Reference state filter<select className="mt-1 block w-full rounded border p-2" value={filters.references} onChange={event => filter("references", event.target.value)}><option value="">All reference states</option><option value="resolved">Provided resources resolved</option><option value="pending">Needs reconciliation</option><option value="ambiguous">Ambiguous</option><option value="unsupported">Unsupported</option><option value="missing_optional">Missing optional resource</option></select></label>
    </div>
    <button type="button" className="ccs-btn-secondary" onClick={() => setFilters(emptyReviewFilters)}>Clear review filters</button>
    {calendarProjection && <>
      <p className="text-sm">{visible.length} of {calendarProjection.rows.length} source row(s) shown. Filters never change full-batch validation.</p>
      <div className="min-w-0 max-w-full overflow-x-auto"><div className="min-w-[700px]" data-testid="external-review-calendar">
        <FullCalendar plugins={[timeGridPlugin]} initialView="timeGridWeek" initialDate="2000-01-03" timeZone="UTC"
          firstDay={1} hiddenDays={[0]} headerToolbar={false} dayHeaderFormat={{weekday: "long"}} height={620}
          allDaySlot={false} slotMinTime="00:00:00" slotMaxTime="24:00:00" scrollTime="07:30:00" slotDuration="00:30:00"
          editable={false} eventStartEditable={false} eventDurationEditable={false} droppable={false} selectable={false}
          slotEventOverlap={false} eventMinHeight={1} nowIndicator={false} events={reviewCalendarEvents(visible)}
          eventContent={info => {const row = info.event.extendedProps.meeting as ReviewMeeting; return <button type="button" className="h-full w-full overflow-hidden p-0.5 text-left text-[10px] leading-3" aria-label={"Review source row " + row.source_row + " " + row.original.subject_code}
            title={intentLabels[row.original.status] + " · Source row " + row.source_row + " · " + row.original.start + "–" + row.original.end + " · " + row.original.title}
            onClick={() => setSelected(row.source_row)}>
            <strong className={"block truncate " + (hasResourceOverlap(row) ? "text-red-900" : "")}>{hasResourceOverlap(row) ? "Resource overlap" : intentLabels[row.original.status]}</strong>
            <strong className="block truncate">{row.original.subject_code}</strong>
            <span className="block truncate">{row.sections.map(s => s.label ?? s.original).join(", ") || "Section unresolved"}</span>
          </button>;}} />
      </div></div>
      <div className="flex flex-wrap gap-2" aria-label="Visible source rows">{visible.map(row => <button key={row.source_row} type="button" className="ccs-btn-secondary" onClick={() => setSelected(row.source_row)}>Details: source row {row.source_row}</button>)}</div>
      {!visible.length && <p role="status">No source rows match these filters.</p>}
      {visible.filter(row => !row.calendar_supported).map(row => <p key={row.source_row} role="status" className="rounded border border-red-200 p-3 text-sm text-red-900">Source row {row.source_row} is not plotted: invalid or unsupported day/time. Its original details and discrepancies remain available.</p>)}
    </>}
    {detail && <section className="rounded-lg border border-slate-200 p-4" aria-label="Source reconciliation">
      <h3 className="font-semibold text-teal-900">Resource reconciliation · Source row {detail.source_row}</h3>
      <p className="mt-2 text-sm text-slate-600">The source selector covers the full original batch; filters affect only the calendar and visible-row list.</p>
      <label className="mt-3 block text-sm">Original source row<select className="ml-2 rounded border p-2" value={detail.source_row} onChange={event => setSelected(Number(event.target.value))}>{source.rows.map(row => <option key={row.source_row} value={row.source_row}>{row.source_row} · {row.input.subject_code}</option>)}</select></label>
      <dl className="mt-3 grid gap-2 break-words text-sm sm:grid-cols-2">
        <div><dt>Subject / title</dt><dd>{detail.input.subject_code} · {detail.input.title}</dd></div>
        <div><dt>Supplying college / term</dt><dd>{detail.input.supplier} · {detail.input.academic_term || "Term unknown"}</dd></div>
        <div><dt>Original day / time / status</dt><dd>{detail.input.days.join(", ")} · {detail.input.start}–{detail.input.end} · {intentLabels[detail.input.status]}</dd></div>
        <div><dt>Source reference / notes</dt><dd className="whitespace-pre-wrap">{detail.input.source_reference} · {detail.input.notes}</dd></div>
      </dl>
      <p className="mt-3 break-all text-xs">Original source: {source.source_name ?? "Manual input"} · SHA-256: {source.source_sha256 ?? "Not an uploaded file"}</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {detail.input.sections.map((value, index) => <label key={index} className="min-w-0 text-sm">Section reference {index + 1}: {value || "(missing)"}
          <select className="mt-1 block w-full min-w-0 max-w-full rounded border p-2" aria-label={"Map section reference " + (index+1)} value={mapping?.sections?.find(s => s.reference_index === index)?.target_id ?? ""} onChange={event => mapResource(detail.source_row, "sections", event.target.value, index)}><option value="">Recognized source key only</option>{metadata.sections.map(r => <option key={r.id} value={r.id}>{r.label} · {r.id}</option>)}</select><ResourceState value={current?.sections[index]} />
        </label>)}
        {(["room", "instructor"] as const).map(field => <label key={field} className="min-w-0 text-sm">{field === "room" ? "Room reference" : "Faculty/instructor reference"}: {detail.input[field] || "(not supplied)"}
          <select className="mt-1 block w-full min-w-0 max-w-full rounded border p-2" aria-label={"Map " + field} disabled={!metadata[field === "room" ? "rooms" : "instructors"].length} value={mapping?.[field === "room" ? "room_id" : "instructor_id"] ?? ""} onChange={event => mapResource(detail.source_row, field, event.target.value)}><option value="">No explicit mapping</option>{metadata[field === "room" ? "rooms" : "instructors"].map(r => <option key={r.id} value={r.id}>{r.label} · {r.alias ?? r.id}</option>)}</select><ResourceState value={current?.[field]} />
        </label>)}
      </div>
      <p className="mt-3 text-sm text-amber-950">Mappings select existing records for this preview only. They never rewrite source text, create an identity or reserve availability. Names alone do not select a faculty UUID.</p>
      <button type="button" className="ccs-btn-secondary mt-3" disabled={busy} onClick={revalidate}>Revalidate all resource mappings</button>
      {current && <div className="mt-4 space-y-2" aria-label="Reconciled discrepancies">{current.discrepancies.map((d,index) => <p key={index} className={d.severity === "error" ? "text-sm text-red-900" : "text-sm text-amber-950"}><strong>{d.code}</strong> · {d.field} · {d.message}{d.related_rows.length ? " · Related source rows: " + d.related_rows.join(", ") : ""}</p>)}</div>}
    </section>}
    <ExternalScheduleHandoff key={JSON.stringify([mappings,completionTouched?completion:null,assessment?.assessment_fingerprint??null])} source={source} mappings={mappings} onInvalid={() => {setProjection(undefined);setAssessment(undefined);setFreshness("Stale — revalidation failed");if(completionTouched)setAssessmentError("Handoff unavailable. Reassess current metadata and retry.");}} completion={completionTouched?completion:undefined} assessment={assessment} />
  </section>;
}
