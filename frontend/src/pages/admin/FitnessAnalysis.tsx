import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import LiveGAMonitor, { ConvergenceChart } from "../../components/ga/LiveGAMonitor";
import { useGA } from "../../context/GAContext";
import { getHistoryRuns, getHistoryGenerations, improvementLabel } from "../../services/gaHistory";
import type { CandidateKind, HistoryPage, RunPage } from "../../services/gaHistory";
import { compareFitness, downloadFitnessReport, downloadLoadedEvaluation, getFitnessReport, loadedEvaluationReport, metric, statusLabel } from "../../services/fitnessReporting";
import type { FitnessReport, FitnessComparison } from "../../services/fitnessReporting";
import type { GARunData } from "../../types/ga";
import { IMPORTANCE_OPTIONS } from "../../components/faculty/preferenceModel";
import ConstrainedResultPanel from "../../components/ga/ConstrainedResultPanel";

const box = "rounded-xl border border-slate-200 bg-white p-5 shadow-sm";
const button = "rounded-lg border border-teal-700 px-3 py-2 text-sm font-medium text-teal-800 disabled:opacity-40";
const control = "ml-2 rounded-lg border border-slate-300 bg-white p-2 text-sm";
const errorText = (error: unknown) => error instanceof Error ? error.message : "Analysis unavailable. Check the backend and retry.";
const importance = (value: number | null) => IMPORTANCE_OPTIONS.find(option => option.value === value)?.label ?? "Not captured";

export default function FitnessAnalysis() {
  const [params]=useSearchParams();
  const runId=params.get("v2run");
  return runId?<ConstrainedResultPanel runId={runId} analysis/>:<LegacyFitnessAnalysis/>;
}

function LegacyFitnessAnalysis() {
  const ga = useGA();
  const [params, setParams] = useSearchParams();
  const runId = params.get("run") ?? (ga.gaData?.result_source === "loaded_chromosome" ? "loaded" : "");
  const historical = !!runId && runId !== "loaded";
  const generation = params.has("generation") ? Number(params.get("generation")) : null;
  const candidate: CandidateKind = params.get("candidate") === "best_ever" ? "best_ever" : "generation_best";
  const [runOffset, setRunOffset] = useState(0), [offset, setOffset] = useState(0), [refresh, setRefresh] = useState(0);
  const [runs, setRuns] = useState<RunPage | null>(null);
  const [page, setPage] = useState<{key: string; value: HistoryPage} | null>(null);
  const [report, setReport] = useState<{key: string; value: FitnessReport; data?: GARunData | null} | null>(null);
  const [error, setError] = useState<{key: string; text: string} | null>(null);
  const [listingError, setListingError] = useState("");
  const [faculty, setFaculty] = useState("All"), [workloadFilter, setWorkloadFilter] = useState("all");
  const [left, setLeft] = useState(0), [right, setRight] = useState(1);
  const [comparison, setComparison] = useState<{key: string; value: FitnessComparison} | null>(null);
  const [actionError, setActionError] = useState(""), [busy, setBusy] = useState(false);
  const reportKey = `${runId}-${generation}-${candidate}-${refresh}-${ga.gaData?.best_fitness ?? ""}-${ga.gaData?.run_id ?? ""}`;
  const chartRunId = historical ? runId : report?.key === reportKey ? report.value.source.run_id : null;
  const pageKey = `${chartRunId}-${offset}-${refresh}`;
  const compareKey = `${runId}-${left}-${right}-${candidate}`;
  useEffect(() => {
    let cancelled = false;
    getHistoryRuns(runOffset).then(value => { if (!cancelled) { setRuns(value); setListingError(""); } })
      .catch(reason => { if (!cancelled) setListingError(errorText(reason)); });
    return () => { cancelled = true; };
  }, [runOffset, refresh]);
  useEffect(() => {
    if (!chartRunId) return;
    let cancelled = false;
    getHistoryGenerations(chartRunId, offset).then(value => {
      if (cancelled) return;
      setPage({key: pageKey, value}); setListingError("");
      if (historical && generation === null && value.items.length) setParams(previous => { const next = new URLSearchParams(previous); next.set("run", runId); next.set("generation", String(value.items.at(-1)!.generation)); return next; });
    }).catch(reason => { if (!cancelled) setListingError(errorText(reason)); });
    return () => { cancelled = true; };
  }, [runId, chartRunId, historical, offset, refresh, generation, pageKey, setParams]);
  useEffect(() => {
    if (historical && generation === null) return;
    let cancelled = false;
    const request = runId === "loaded" ? Promise.resolve().then(() => {
      if (!ga.gaData || ga.gaData.result_source !== "loaded_chromosome") throw new Error("Loaded evaluation is no longer available. Load the saved/uploaded candidate again, or choose a recorded run.");
      return loadedEvaluationReport(ga.gaData);
    }) : getFitnessReport(runId || undefined, generation ?? undefined, candidate);
    request.then(value => {
      if (!cancelled) { setReport({key: reportKey, value, data: ga.gaData}); setError(null); }
    }).catch(reason => { if (!cancelled) setError({key: reportKey, text: errorText(reason)}); });
    return () => { cancelled = true; };
  }, [runId, historical, generation, candidate, reportKey, ga.gaData]);
  const view = report?.key === reportKey && (runId !== "loaded" || report.data === ga.gaData) ? report.value : null;
  const currentPage = page?.key === pageKey ? page.value : null;
  const currentComparison = comparison?.key === compareKey ? comparison.value : null;
  const visibleError = error?.key === reportKey ? error.text : null;
  const members = view?.faculty.filter(row => (faculty === "All" || row.faculty === faculty) && (workloadFilter === "all" || row.workload_status === workloadFilter)) ?? [];
  async function download(section: "fitness" | "workload", format: "csv" | "json") {
    setBusy(true); setActionError("");
    try {
      if (runId === "loaded" && view) await downloadLoadedEvaluation(view, section, format);
      else await downloadFitnessReport(runId || undefined, generation ?? undefined, candidate, section, format);
    }
    catch (reason) { setActionError(errorText(reason)); }
    finally { setBusy(false); }
  }
  async function compare() {
    setBusy(true); setActionError("");
    try { setComparison({key: compareKey, value: await compareFitness(runId, left, right, candidate)}); }
    catch (reason) { setActionError(errorText(reason)); }
    finally { setBusy(false); }
  }
  return <div className="space-y-6">
    {ga.executionStatus !== "IDLE" && <LiveGAMonitor onPause={ga.pauseGA} onResume={ga.resumeGA} canPause={ga.canPause} canResume={ga.canResume} controlError={ga.controlError} pausedRuns={ga.pausedRuns} onSelectPaused={id => { const run = ga.pausedRuns.find(item => item.run_id === id); if (run) ga.selectPausedRun(run); }} runId={ga.activeRunId} recoveryNotice={ga.recoveryNotice} onStop={ga.stopGA} canStop={ga.canStop} stopError={ga.stopError} status={ga.executionStatus} history={ga.progressHistory} elapsedSeconds={ga.elapsedSeconds} population={ga.populationSize} limit={ga.generations} />}
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold text-slate-900">Fitness Analysis</h1><p className="mt-1 text-sm text-slate-500">Understand workload, preferences, and recorded penalties. Lower penalty is better.</p></div><div className="flex gap-2"><Link className={button} to="/admin/history">Generation History</Link><button className={button} onClick={() => setRefresh(value => value + 1)}>Refresh analysis</button></div></div>
    <section className={box} aria-label="Analysis source"><h2 className="mb-3 font-semibold text-teal-900">Choose a recorded schedule</h2><div className="flex flex-wrap items-center gap-3">
      <label>Source<select aria-label="Analysis source" className={control} value={runId} onChange={event => { setParams({run: event.target.value}); setOffset(0); setFaculty("All"); setActionError(""); }}><option value="">Latest saved schedule</option>{(runId === "loaded" || ga.gaData?.result_source === "loaded_chromosome") && <option value="loaded">Current loaded candidate evaluation</option>}{historical && !runs?.items.some(run => run.run_id === runId) && <option value={runId}>Selected historical run</option>}{runs?.items.map(run => <option key={run.run_id} value={run.run_id}>{new Date(run.created_at).toLocaleString()} · {run.state} · {run.generations_recorded} recorded generations</option>)}</select></label>
      {historical && <><label>Generation<select aria-label="Analysis generation" className={control} value={generation ?? ""} onChange={event => setParams(previous => { const next = new URLSearchParams(previous); next.set("generation", event.target.value); return next; })}>{generation !== null && !currentPage?.items.some(row => row.generation === generation) && <option value={generation}>Generation {generation}</option>}{generation === null && <option value="">Choose a recorded generation</option>}{currentPage?.items.map(row => <option key={row.generation} value={row.generation}>Generation {row.generation}</option>)}</select></label><label>Candidate<select aria-label="Analysis candidate" className={control} value={candidate} onChange={event => setParams(previous => { const next = new URLSearchParams(previous); next.set("candidate", event.target.value); return next; })}><option value="generation_best">Best in this generation</option><option value="best_ever">Best ever at this generation</option></select></label></>}
    </div><div className="mt-3 flex gap-2"><button className={button} disabled={!runOffset} onClick={() => setRunOffset(value => Math.max(0, value - 20))}>Previous runs</button><button className={button} disabled={!runs || runOffset + 20 >= runs.total} onClick={() => setRunOffset(value => value + 20)}>More runs</button></div>{listingError && <p role="alert" className="mt-3 text-sm text-red-700">{listingError}</p>}{historical && currentPage?.total === 0 && <p className="mt-3 text-sm text-slate-500">No completed generation snapshots are available for this run.</p>}</section>
    {visibleError && <div role="alert" className="rounded-lg bg-red-50 p-4 text-red-800">{visibleError} <Link className="underline" to="/admin/generate">Generate a schedule</Link></div>}
    {!view && !visibleError && (!historical || generation !== null) && <p role="status">Loading recorded fitness analysis…</p>}
    {view && <>
      <section className={box}><div className="border-l-4 border-teal-700 pl-4"><p className="text-sm text-slate-500">Overall penalty</p><p className="mt-1 text-3xl font-bold text-[#115E59]">{metric(view.overall_penalty)}</p><p className="mt-2 text-xs text-slate-500">{view.source.generation !== null ? `Generation ${view.source.generation} · ${view.source.candidate === "best_ever" ? "Best ever" : "Generation best"}` : view.source.kind === "loaded-chromosome-evaluation" ? "Loaded candidate - original evaluation; no optimization ran" : "Saved final evaluation - generation provenance not captured"}{view.source.timestamp && ` · ${new Date(view.source.timestamp).toLocaleString()}`}</p></div><div className="mt-4 flex flex-wrap gap-2">{(["fitness", "workload"] as const).flatMap(section => (["csv", "json"] as const).map(format => <button key={`${section}-${format}`} className={button} disabled={busy} onClick={() => void download(section, format)}>Export {section === "fitness" ? "analysis" : "workload"} {format.toUpperCase()}</button>))}</div>{view.source.analysis_timestamp && <p className="mt-2 text-xs text-slate-500">Component evaluation recorded {new Date(view.source.analysis_timestamp).toLocaleString()} under original inputs.</p>}</section>
      <section className={box}><h2 className="text-lg font-semibold">Where the penalty comes from</h2><p className="mt-1 text-sm text-slate-500">{view.definitions.overall}</p>{!view.breakdown_available && <p role="status" className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">This generation recorded a total only. Component scores were not captured; they are not recalculated from today's preferences.</p>}<div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Component</th><th className="p-2">Recorded contribution</th><th className="p-2">Calculation</th></tr></thead><tbody>{view.components.map(row => <tr className="border-t" key={row.key}><td className="p-2 font-medium">{row.label}</td><td className="p-2">{metric(row.penalty)}</td><td className="p-2 text-slate-600">{row.definition}</td></tr>)}</tbody></table></div>{view.breakdown_available && <p className="mt-3 font-semibold text-teal-900">Recorded component sum: {metric(view.recorded_component_sum)} = overall penalty {metric(view.overall_penalty)}</p>}</section>
      <section className={box}><div className="flex flex-wrap gap-3"><label>Faculty<select aria-label="Analysis faculty" className={control} value={faculty} onChange={event => setFaculty(event.target.value)}><option>All</option>{view.faculty.map(row => <option key={row.faculty}>{row.faculty}</option>)}</select></label><label>Workload<select aria-label="Workload filter" className={control} value={workloadFilter} onChange={event => setWorkloadFilter(event.target.value)}><option value="all">All workloads</option><option value="underload">Under target</option><option value="on_target">At target</option><option value="overload">Above target</option><option value="unavailable">Target not captured</option></select></label></div></section>
      <section className={box}><h2 className="text-lg font-semibold">Faculty teaching workload</h2><p className="mt-1 text-sm text-slate-500">{view.definitions.target} {view.definitions.actual} Underload is soft; 40 teaching units remains a hard maximum.</p><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{["Faculty", "Target", "Actual", "Difference", "Fulfillment", "Admin release", "Research release", "Extension release", "Status", "Recorded workload penalty"].map(label => <th className="p-2" key={label}>{label}</th>)}</tr></thead><tbody>{members.map(row => <tr key={row.faculty} className="border-t"><td className="p-2 font-medium">{row.faculty}</td>{[row.required_teaching_load, row.teaching_units, row.difference].map((value, index) => <td key={index} className="p-2">{metric(value)}</td>)}<td className="p-2">{row.required_teaching_load === 0 ? "No teaching target" : metric(row.fulfillment_percent, "%")}</td>{[row.admin_load, row.research_load, row.extension_load].map((value, index) => <td key={index} className="p-2">{metric(value)}</td>)}<td className="p-2">{row.workload_status.replaceAll("_", " ")}{row.heavy_overload && " · Heavy overload warning"}{row.teaching_units !== null && row.teaching_units > 40 && " · Hard maximum violation"}</td><td className="p-2">{metric(row.workload_penalty)}{row.workload_status === "underload" && <p className="text-xs text-slate-500">{metric(row.underload_steps)} shortfall bands</p>}</td></tr>)}</tbody></table></div>{!members.length && <p className="mt-3 text-sm text-slate-500">No faculty match these filters.</p>}<p className="mt-3 text-xs text-slate-500">{view.definitions.difference} {view.definitions.fulfillment} Missing release details remain “Not captured”.</p></section>
      <section className={box}><h2 className="text-lg font-semibold">Faculty preference outcomes</h2><p className="mt-1 text-sm text-slate-500">{view.definitions.indicators} {view.definitions.priority}</p>{members.map(member => <div key={member.faculty} className="mt-5 border-t pt-4"><h3 className="font-semibold text-teal-900">{member.faculty}</h3><p className="mt-1 text-xs text-slate-500">Preparations: {metric(member.preparations)} · Recorded faculty penalty: {metric(member.total_penalty)} · Priority multiplier: {metric(member.priority_multiplier)}</p>{member.unavailable_reason && <p className="mt-2 text-sm text-amber-800">{member.unavailable_reason}</p>}{member.preferences && <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{["Preference", "Outcome", "Descriptive match", "Importance", "Recorded penalty", "Explanation"].map(label => <th className="p-2" key={label}>{label}</th>)}</tr></thead><tbody>{member.preferences.map(row => <tr key={row.key} className="border-t"><td className="p-2">{view.components.find(c => c.key === row.key)?.label ?? row.key}</td><td className="p-2">{statusLabel(row.status)}{row.affects_fitness === false && row.status !== "disabled" && <p className="text-xs text-slate-500">Informational only</p>}</td><td className="p-2">{row.satisfaction_percent === null ? statusLabel(row.status) : metric(row.satisfaction_percent, "%")}{row.total !== null && row.total > 0 && <p className="text-xs text-slate-500">{row.matched} / {row.total} fully matched</p>}{row.idle_minutes !== undefined && <p className="text-xs text-slate-500">{row.idle_minutes} idle minutes</p>}</td><td className="p-2">{importance(row.importance)}</td><td className="p-2">{metric(row.penalty)}</td><td className="p-2 text-slate-600">{row.explanation}</td></tr>)}</tbody></table></div>}{Object.keys(member.penalties).length > 0 && <details className="mt-3 text-sm"><summary className="cursor-pointer">All recorded faculty contributions</summary><dl className="mt-2 grid gap-2 sm:grid-cols-2">{view.components.map(component => <div key={component.key} className="flex justify-between rounded bg-slate-50 p-2"><dt>{component.label}</dt><dd>{metric(member.penalties[component.key])}</dd></div>)}</dl></details>}</div>)}</section>
      {view.external_instructors.length > 0 && <section className={box}><h2 className="font-semibold">Preassigned instructors</h2>{view.external_instructors.map(row => <p key={`${row.name}-${row.subject}-${row.section}`} className="mt-2 text-sm">{row.name} · {row.subject} · Section {row.section} · {row.scoring}</p>)}</section>}
      <details className={box}><summary className="cursor-pointer font-semibold">Definitions, recorded configuration, and reporting limitations</summary><dl className="mt-3 space-y-2 text-sm">{Object.entries(view.definitions).map(([name, text]) => <div key={name}><dt className="font-semibold">{name.replaceAll("_", " ")}</dt><dd className="text-slate-600">{text}</dd></div>)}</dl><ul className="mt-3 list-disc pl-5 text-sm">{view.limitations.map(text => <li key={text}>{text}</li>)}</ul>{view.fitness_configuration && <dl className="mt-4 grid gap-2 sm:grid-cols-2">{Object.entries(view.fitness_configuration).filter(([key]) => !["target_teaching_load", "load_tolerance", "regular_teaching_load", "load_balance_penalty"].includes(key)).map(([key, value]) => <div key={key} className="flex justify-between bg-slate-50 p-2 text-sm"><dt>{key.replaceAll("_", " ")}</dt><dd>{value}</dd></div>)}</dl>}</details>
    </>}
    {chartRunId && currentPage && <section className={box}><h2 className="text-lg font-semibold">Recorded convergence</h2><p className="mb-3 text-xs text-slate-500">Recorded generations on this page: {currentPage.items[0]?.generation ?? "none"}–{currentPage.items.at(-1)?.generation ?? "none"}. Lower is better.</p><ConvergenceChart history={currentPage.items.map(row => row.metrics)} /><div className="mt-3 flex gap-2"><button className={button} disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 50))}>Previous generations</button><button className={button} disabled={offset + 50 >= currentPage.total} onClick={() => setOffset(value => value + 50)}>More generations</button><Link className={button} to={`/admin/history?run=${chartRunId}`}>Inspect schedules in Generation History</Link></div></section>}
    {historical && <section className={box} aria-label="Fitness generation comparison"><h2 className="text-lg font-semibold">What changed between generations?</h2><p className="mt-1 text-sm text-slate-500">Compares the selected candidate kind using original recorded inputs. Current preferences are never substituted.</p><div className="mt-4 flex flex-wrap items-end gap-3">{[["Earlier generation", left, setLeft], ["Later generation", right, setRight]].map(([label, value, setter]) => <label key={String(label)}>{String(label)}<input aria-label={String(label)} className={`${control} w-24`} type="number" min={0} step={1} value={Number(value)} onChange={event => (setter as (value: number) => void)(Number(event.target.value))} /></label>)}<button className={button} disabled={busy || !Number.isInteger(left) || !Number.isInteger(right) || left < 0 || right < 0} onClick={() => void compare()}>Compare fitness outcomes</button></div>{currentComparison && <div className="mt-4 space-y-4"><p className="font-semibold text-teal-900">Overall penalty: {improvementLabel(currentComparison.overall_reduction)}</p><p className="text-sm text-slate-500">{currentComparison.explanation}</p><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{["Component", "Before", "After", "Change"].map(label => <th key={label} className="p-2">{label}</th>)}</tr></thead><tbody>{currentComparison.component_changes.map(row => <tr className="border-t" key={row.key}><td className="p-2">{row.label}</td><td className="p-2">{metric(row.before)}</td><td className="p-2">{metric(row.after)}</td><td className="p-2">{row.reduction === null ? "Not captured at both generations" : improvementLabel(row.reduction)}</td></tr>)}</tbody></table></div><h3 className="font-semibold">Workload and preference changes</h3>{currentComparison.faculty_changes.filter(row => faculty === "All" || faculty === row.faculty).map(row => <div key={row.faculty} className="rounded-lg bg-slate-50 p-3 text-sm"><strong>{row.faculty}</strong><p>Teaching units: {metric(row.before?.teaching_units)} → {metric(row.after?.teaching_units)} · Fulfillment: {metric(row.before?.fulfillment_percent, "%")} → {metric(row.after?.fulfillment_percent, "%")}</p>{(row.after?.preferences ?? row.before?.preferences ?? []).map(preference => <p key={preference.key}>{view?.components.find(c => c.key === preference.key)?.label ?? preference.key}: {metric(row.before?.preferences?.find(p => p.key === preference.key)?.satisfaction_percent, "%")} → {metric(row.after?.preferences?.find(p => p.key === preference.key)?.satisfaction_percent, "%")}</p>)}</div>)}<p className="text-sm">{currentComparison.assignment_changes.length} offering/component assignments changed; inspect schedules in Generation History.</p></div>}</section>}
    {actionError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-700">{actionError}</p>}
  </div>;
}
