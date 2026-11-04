import {useEffect, useState} from "react";
import {getSourceQualification} from "../../services/sourceQualification";
import type {SourceQualification as Qualification} from "../../services/sourceQualification";

const explanation: Record<string, string> = {
  INSTITUTIONAL_SOURCE_NOT_CONFIGURED: "Institutional source authority, ownership, approval, dataset identity, revision and effective period are not configured.",
  RUN_CONSUMPTION_BINDING_UNAVAILABLE: "No run-bound evidence proves which loaded models the optimizer consumed.",
  FULL_TRANSFORMED_MODEL_MAPPING_UNVERIFIED: "Transformed faculty, preferences, availability and other runtime inputs are not fully mapped to an approved dataset.",
  SOURCE_SET_UNSTABLE_OR_UNREADABLE: "Source files changed during inspection or could not be read. Retry the observation.",
};
export default function SourceQualification() {
  const [data, setData] = useState<Qualification | null>(null), [error, setError] = useState("");
  const [revision, refresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    getSourceQualification(controller.signal).then(value => {if (!controller.signal.aborted) {setData(value);setError("");}})
      .catch(reason => {if (!controller.signal.aborted) {setData(null);setError(reason instanceof Error ? reason.message : "Source qualification unavailable.");}});
    return () => controller.abort();
  }, [revision]);
  return <aside className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm" aria-label="Academic source qualification">
    <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-teal-900">Academic source qualification</h3>
      <button type="button" className="ccs-btn-secondary" onClick={() => {setData(null);setError("");refresh(value => value+1);}}>Retry source inspection</button></div>
    {!data && !error && <p role="status">Inspecting source qualification...</p>}
    {error && <p role="alert">{error}</p>}
    {data && <><p className="mt-2 font-semibold">BLOCKED — institutional approval is not established.</p>
      <p>Academic year, term, department, dataset identity and revision remain unverified. No values are inferred from filenames or dates.</p>
      <ul className="mt-2 list-disc pl-5">{data.reasons.map(reason => <li key={reason}>{explanation[reason]}</li>)}</ul>
      <details className="mt-2"><summary>Partial cached-table inspection</summary>
        <p className="mt-2">MATCH means a cached table equals the file observed now. It does not prove complete optimizer inputs, institutional authority or CURRENT eligibility.</p>
        <ul className="mt-2 space-y-1">{data.cached_tables.map(row => <li key={row.source}>{row.source.replaceAll("_", " ")}: <strong>{row.status}</strong>{row.row_count !== undefined ? ` (${row.row_count} source rows)` : ""}</li>)}</ul>
        {!data.cached_tables.length && <p>No source tables could be inspected.</p>}
        <p>File set stable during observation: {data.file_set_stable_during_inspection ? "yes" : "not verified"}.</p>
      </details>
      <p className="mt-2">This inspection does not approve data, change compatibility classifications, activate a provider or promote Saved Best.</p></>}
  </aside>;
}
