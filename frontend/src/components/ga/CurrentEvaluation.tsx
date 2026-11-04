import {useEffect, useState} from "react";
import {Link} from "react-router-dom";
import {getCurrentEvaluation} from "../../services/currentEvaluation";
import type {CurrentEvaluation as Evaluation} from "../../services/currentEvaluation";

export default function CurrentEvaluation({mode}: {mode: "best" | "runs"}) {
  const [data, setData] = useState<Evaluation | null>(null), [error, setError] = useState("");
  const [revision, refresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    getCurrentEvaluation(controller.signal).then(value => {if (!controller.signal.aborted) {setData(value);setError("");}})
      .catch(reason => {if (!controller.signal.aborted) {setData(null);setError(reason instanceof Error ? reason.message : "Current evaluation unavailable.");}});
    return () => controller.abort();
  }, [revision]);
  const best = data?.best, count = data?.current_runs;
  return <section className="mb-6 scroll-mt-20 rounded-xl border border-teal-200 bg-white p-5 md:scroll-mt-4" aria-label="Current Evaluation">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold text-teal-900">{error ? "Current Evaluation unavailable" : !data ? "Checking Current Evaluation" : !data.coverage_complete ? "Current Evaluation review incomplete" : best ? "Current Best Recorded Chromosome" : mode === "runs" ? count ? "Current GA Runs" : "No Current GA Runs Yet" : "No Current Best Chromosome"}</h2>
      <button type="button" className="ccs-btn-secondary" onClick={() => {setData(null);setError("");refresh(value => value+1);}}>Retry current evaluation</button></div>
    {!data && !error && <p role="status" className="mt-2 text-sm">Checking server-owned implementation and result provenance...</p>}
    {error && <p role="alert" className="mt-2 text-sm text-red-800">{error}</p>}
    {data && !data.coverage_complete && <p role="alert" className="mt-2 text-sm text-amber-900">Review incomplete: {data.issues.join(", ")}. A global current count and best cannot be established.</p>}
    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
      <div><dt>Current Runs:</dt><dd className="font-semibold">{count === undefined || count === null ? "\u2014" : count}</dd></div>
      <div><dt>Current Best Fitness:</dt><dd className="text-2xl font-bold" aria-label="Current best penalty">{best ? String(best.fitness) : "\u2014"}</dd></div>
      <div><dt>Saved Chromosome:</dt><dd className="font-semibold">None</dd></div>
    </dl>
    <p className="mt-2 text-sm">Run the current Genetic Algorithm to generate recorded results. The persistent Saved Best has no verified producer identity and remains unavailable as an automatic current baseline.</p>
    {data && <><p className="mt-2 text-xs text-slate-600">Technical contract {data.contract}. {data.comparison_basis} {data.current_identity.academic_context.term ? `Recorded academic context: ${data.current_identity.academic_context.academic_year} / ${data.current_identity.academic_context.term}.` : "Academic year/term unresolved."} Institutional approval is not established. Best selection uses completed, validated recorded runs only.</p>
      {data.schema_version === 2 && <p className="mt-2 text-sm text-slate-600">{data.current_identity.context_verification === "VERIFIED" ? `Server-verified scheduling scope: ${data.current_identity.academic_context.department}. Dataset: ${data.current_identity.academic_context.dataset_id}, revision ${data.current_identity.academic_context.dataset_revision}.` : "Server academic context is unavailable. Unverified runs remain outside Current Evaluation; no academic year, term or dataset is inferred."}</p>}
      {data.issues.includes("INCOMPARABLE_CONFIGURATIONS") && <p role="status" className="mt-2 text-sm text-amber-900">Different configuration fingerprints cannot supply a single current best. Inspect each original run separately.</p>}
      <details className="mt-3 text-xs text-slate-600"><summary>Current implementation provenance</summary><dl className="mt-2 space-y-2 break-all"><div><dt>Engine</dt><dd>{data.current_identity.engine_version} / {data.current_identity.engine_fingerprint}</dd></div><div><dt>Fitness policy</dt><dd>{data.current_identity.fitness_policy} / {data.current_identity.scorer_sha256}</dd></div><div><dt>Constraint contract</dt><dd>{data.current_identity.constraint_policy}</dd></div><div><dt>Input context</dt><dd>{data.current_identity.input_fingerprint}</dd></div></dl></details>
      {!!data.runs.length && <div className="mt-4 max-h-72 overflow-auto" tabIndex={0} aria-label="Recorded run compatibility table"><table className="w-full text-left text-xs"><caption className="text-left">Recorded run compatibility; original records remain in Historical Archive.</caption><thead><tr><th className="p-2">Run / generation</th><th className="p-2">Compatibility</th><th className="p-2">Reason</th><th className="p-2">Recorded history</th></tr></thead><tbody>{data.runs.map(run => <tr key={run.run_id} className="border-t"><td className="break-all p-2">{run.run_id} / {run.generation ?? "not recorded"}</td><td className="p-2 align-top">{run.classification}</td><td className="p-2 align-top">{run.reason}{run.academic_context && <p className="mt-1">Original context: {run.academic_context.academic_year} / {run.academic_context.term}; {run.academic_context.department}; {run.academic_context.dataset_id}, revision {run.academic_context.dataset_revision}.</p>}{run.provenance && <details className="mt-2 break-all"><summary>Run-start provenance</summary><p>Run start: {run.provenance.started_at}</p><p>Immutable record: {run.provenance.run_start_sha256}</p><p>Academic context: {run.provenance.context_sha256}</p><p>Configuration: {run.configuration_fingerprint}</p></details>}</td><td className="p-2 align-top"><Link className="text-teal-800 underline" to={`/admin/history?view=archive&run=${run.run_id}`}>View history</Link></td></tr>)}</tbody></table></div>}
      {best && <p className="mt-3 break-all text-sm">Best recorded source: {best.run_id}, generation {best.generation}, chromosome {best.chromosome_id}. <Link className="text-teal-800 underline" to={`/admin/history?view=archive&run=${best.run_id}`}>Inspect current best and generation history</Link></p>}</>}
    <button type="button" disabled className="ccs-btn-secondary mt-4" title="Persistent reset needs separate authorization.">Start Fresh Evaluation (not available)</button>
    <p className="mt-2 text-xs text-slate-500">No reset has occurred. Fresh population generation does not reset or delete saved records. Archive inspection does not admit a GA baseline.</p>
  </section>;
}
