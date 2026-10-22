import type {ExternalPreview} from "../../api/externalSchedules";

export default function LegacyScheduleProvenance({legacy, sourceRow}: {legacy: ExternalPreview["legacy"]; sourceRow?: number}) {
  if (!legacy) return null;
  const rows = sourceRow === undefined ? legacy.rows : legacy.rows.filter(row => row.source_row === sourceRow);
  return <section className="min-w-0 space-y-2 break-words rounded border border-amber-300 bg-amber-50 p-3" aria-label="Legacy source provenance">
    <h3 className="font-semibold text-teal-900">Legacy GEC source · {legacy.adapter_version}</h3>
    <p className="text-sm">Year Level is context only; it never creates a section identity. Section → existing section reconciliation; Course Number → subject code; Schedule → parsed days/start/end. Titles, faculty and rooms were not supplied or invented.</p>
    <p className="text-sm">Administrator-supplied preview metadata (unverified): Supplier: {legacy.metadata.supplier || "Missing supplier"} · Source reference: {legacy.metadata.source_reference || "Missing source reference"} · Term: {legacy.metadata.academic_term || "Term unknown"} · {legacy.metadata.status === "draft" ? "Draft" : "Tentative"}. Not institutional confirmation.</p>
    {rows.map(row => <div key={row.source_row} className="border-t border-amber-200 pt-2 text-sm">
      <strong>Original source row {row.source_row} · Parsing: {row.parse_state}</strong>
      <p className="whitespace-pre-wrap">Year Level: {row.year_level || "(blank)"} · Section: {row.section || "(blank)"} · Course Number: {row.course_number || "(blank)"} · Schedule: {row.schedule || "(blank)"}</p>
      {row.discrepancies.map((issue, index) => <p key={index}><strong>{issue.code}</strong> · {issue.message}</p>)}
    </div>)}
    <p className="text-sm font-semibold">Incomplete/unverified preview — not ready for confirmation. Original values and source rows are retained; nothing is saved or active in GA.</p>
  </section>;
}
