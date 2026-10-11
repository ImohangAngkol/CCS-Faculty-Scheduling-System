import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import WeeklySchedule, { formatFacultyName } from "../../components/schedule/WeeklySchedule";
import { ConvergenceChart } from "../../components/ga/LiveGAMonitor";
import { compareGenerations, downloadHistory, getHistoricalAnalysis, getHistoricalSchedule, getHistoryGenerations,
  getHistoryRuns, improvementLabel } from "../../services/gaHistory";
import type { CandidateAnalysis, CandidateKind, HistoricalSchedule, HistoryComparison, HistoryPage, RunPage, Workload } from "../../services/gaHistory";
import type { ScheduleEntry } from "../../types/ga";

const box = "rounded-xl border border-slate-200 bg-white p-5 shadow-sm";
const button = "rounded-lg border border-teal-700 px-3 py-2 text-sm font-medium text-teal-800 disabled:opacity-40";
const number = (value: number) => value.toLocaleString(undefined, {maximumFractionDigits: 2});
const errorMessage = (reason: unknown) => reason instanceof Error ? reason.message : "History is unavailable. Check the backend and retry.";
function instructorLabel(code: string, rows: ScheduleEntry[]) {
  if (!code.startsWith("external:")) return formatFacultyName(code);
  const entry = rows.find(row => row.faculty === code) as (ScheduleEntry & {faculty_name?: string}) | undefined;
  return entry?.faculty_name ? `${entry.faculty_name} · Preassigned Instructor` : "Preassigned Instructor";
}

export default function GenerationHistory() {
  const [params, setParams] = useSearchParams();
  const runId = params.get("run") ?? "";
  const [runs, setRuns] = useState<RunPage | null>(null);
  const [runOffset, setRunOffset] = useState(0);
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [page, setPage] = useState<{key: string; value: HistoryPage} | null>(null);
  const [generation, setGeneration] = useState<number | null>(null);
  const [kind, setKind] = useState<CandidateKind>("generation_best");
  const [inspection, setInspection] = useState<{key: string; schedule: HistoricalSchedule; analysis: CandidateAnalysis} | null>(null);
  const [faculty, setFaculty] = useState("All");
  const [error, setError] = useState<{key: string; message: string} | null>(null);
  const [actionError, setActionError] = useState("");
  const [left, setLeft] = useState(0), [right, setRight] = useState(1);
  const [comparison, setComparison] = useState<{key: string; data: HistoryComparison} | null>(null);
  const [busy, setBusy] = useState(false);
  const runsKey = `runs-${runOffset}-${refresh}`, pageKey = `${runId}-${offset}-${refresh}`;
  const viewKey = `${runId}-${generation}-${kind}`;
  const compareKey = `${runId}-${left}-${right}-${kind}`;
  useEffect(() => {
    let cancelled = false;
    getHistoryRuns(runOffset).then(value => {if (!cancelled) {setRuns(value); setError(current => current?.key === runsKey ? null : current);}})
      .catch(reason => {if (!cancelled) setError({key: runsKey, message: errorMessage(reason)});});
    return () => {cancelled = true;};
  }, [runOffset, refresh, runsKey]);
  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    getHistoryGenerations(runId, offset).then(value => {if (!cancelled) {setPage({key: pageKey, value}); setError(current => current?.key === pageKey ? null : current);}})
      .catch(reason => {if (!cancelled) setError({key: pageKey, message: errorMessage(reason)});});
    return () => {cancelled = true;};
  }, [runId, offset, refresh, pageKey]);
  useEffect(() => {
    if (!runId || generation === null) return;
    let cancelled = false;
    Promise.all([getHistoricalSchedule(runId, generation, kind), getHistoricalAnalysis(runId, generation, kind)])
      .then(([schedule, analysis]) => {if (!cancelled) {setInspection({key: viewKey, schedule, analysis}); setError(current => current?.key === viewKey ? null : current);}})
      .catch(reason => {if (!cancelled) setError({key: viewKey, message: errorMessage(reason)});});
    return () => {cancelled = true;};
  }, [runId, generation, kind, viewKey, refresh]);
  const currentPage = page?.key === pageKey ? page.value : null;
  const view = inspection?.key === viewKey ? inspection : null;
  const diff = comparison?.key === compareKey ? comparison.data : null;
  const visibleError = error && [runsKey, pageKey, viewKey].includes(error.key) ? error.message : "";
  async function exportFile(suffix: string) {
    setActionError(""); setBusy(true);
    try {await downloadHistory(runId, suffix);} catch (reason) {setActionError(errorMessage(reason));}
    finally {setBusy(false);}
  }
  async function compare() {
    setBusy(true); setActionError("");
    try {setComparison({key: compareKey, data: await compareGenerations(runId, left, right, kind)});}
    catch (reason) {setActionError(errorMessage(reason));}
    finally {setBusy(false);}
  }
  const entries = view?.schedule.schedule ?? [];
  const facultyCodes = [...new Set(entries.map(row => row.faculty))].sort();
  const filtered = faculty === "All" ? entries : entries.filter(row => row.faculty === faculty);
  return <div className="space-y-5" data-testid="generation-history">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold text-slate-900">Generation History</h1>
      <p className="mt-1 text-sm text-slate-600">Inspect saved schedule candidates. Lower penalty is better. Viewing history does not change an optimization run.</p></div>
      <button className={button} onClick={() => {setError(null); setRefresh(value => value + 1);}}>Refresh history</button></div>
    {(visibleError || actionError) && <p role="alert" className="rounded-lg bg-red-50 p-4 text-sm text-red-800">{visibleError || actionError}</p>}
    <section className={box} aria-label="Historical runs">
      <label className="text-sm font-medium">Historical run <select aria-label="Historical run" className="ml-3 max-w-full rounded border p-2" value={runId} onChange={event => {
        setParams(event.target.value ? {run: event.target.value} : {}); setOffset(0); setGeneration(null); setFaculty("All"); setActionError(""); setError(null);
      }}><option value="">Choose a run</option>{runId && !runs?.items.some(run => run.run_id === runId) && <option value={runId}>{runId}</option>}
        {runs?.items.map(run => <option key={run.run_id} value={run.run_id}>{new Date(run.created_at).toLocaleString()} · {run.state} · {run.run_id}</option>)}</select></label>
      {!runs && !visibleError && <p role="status" className="mt-3 text-sm">Loading historical runs…</p>}
      {runs?.total === 0 && <p className="mt-3 text-sm text-slate-500">No generation history has been recorded yet. Existing checkpoints and Saved Best are separate artifacts.</p>}
      {runs?.errors.map((item, index) => <p role="alert" key={index} className="mt-2 text-sm text-amber-800">{item.message} ({item.code})</p>)}
      {runs && runs.total > 20 && <div className="mt-3 flex gap-2"><button className={button} disabled={!runOffset} onClick={() => setRunOffset(value => Math.max(0, value - 20))}>Previous runs</button><button className={button} disabled={runOffset + 20 >= runs.total} onClick={() => setRunOffset(value => value + 20)}>Next runs</button></div>}
    </section>
    {runId && !currentPage && !visibleError && <p role="status">Loading recorded generations…</p>}
    {currentPage && <>
      <section className={box} aria-label="Run history summary"><div className="flex flex-wrap items-center justify-between gap-3"><div>
        <h2 className="font-semibold">{currentPage.run.state} · {currentPage.total} generations recorded</h2><p className="mt-1 break-all text-xs text-slate-500">Run {runId}</p>
        <p className="mt-1 text-xs text-slate-500">Started {new Date(currentPage.run.created_at).toLocaleString()}{currentPage.run.ended_at && ` · Ended ${new Date(currentPage.run.ended_at).toLocaleString()}`}</p>
      </div><button className={button} disabled={busy || !currentPage.total} onClick={() => void exportFile("history/export")}>Download fitness history CSV</button></div>
        {currentPage.run.latest && <div className="mt-4 grid gap-3 sm:grid-cols-3">{[["Best-ever penalty", currentPage.run.latest.metrics.best_ever_fitness], ["Generation-best penalty", currentPage.run.latest.metrics.generation_best_fitness], ["Population average", currentPage.run.latest.metrics.average_fitness]].map(([label, value]) => <p key={label} className="rounded-lg bg-teal-50 p-3 text-sm"><span>{label}</span><strong className="ml-3 text-teal-900">{number(Number(value))}</strong></p>)}</div>}
        {currentPage.run.errors.length > 0 && <p role="alert" className="mt-3 text-sm text-amber-900">Some snapshots could not be recorded: {currentPage.run.errors.map(item => `Generation ${item.generation ?? "unknown"}: ${item.code}`).join("; ")}. Existing records were preserved.</p>}
        {currentPage.run.history_error && <p role="alert" className="mt-2 text-sm text-amber-900">History storage warning: {currentPage.run.history_error}</p>}
        {currentPage.run.skipped_generations.length > 0 && <p className="mt-2 text-sm text-slate-500">Configured sampling omitted {currentPage.run.skipped_generations.length} generations.</p>}
      </section>
      <section className={box}><p className="mb-3 text-xs text-slate-500">Graph shows recorded generations on this page ({currentPage.items[0]?.generation ?? "none"}–{currentPage.items.at(-1)?.generation ?? "none"}).</p>
        <ConvergenceChart history={currentPage.items.map(row => row.metrics)} />
        <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50"><tr>{["Generation", "Timestamp", "Best", "Best ever", "Average", "Population", "Accepted candidates", "Inspect"].map(label => <th key={label} className="p-2">{label}</th>)}</tr></thead>
          <tbody>{currentPage.items.map(row => <tr key={row.generation} className="border-t"><td className="p-2">{row.generation}</td><td>{new Date(row.timestamp).toLocaleString()}</td><td>{number(row.metrics.generation_best_fitness)}</td><td>{number(row.metrics.best_ever_fitness)}</td><td>{number(row.metrics.average_fitness)}</td><td>{row.metrics.population_actual} / {row.metrics.population_requested}</td><td>{row.metrics.accepted_new_chromosomes_total}</td><td className="p-2"><button className={button} aria-label={`Inspect generation ${row.generation}`} onClick={() => {setGeneration(row.generation); setRight(row.generation); setError(null); setFaculty("All");}}>Inspect</button></td></tr>)}</tbody></table></div>
        {!currentPage.total && <p className="mt-3 text-sm text-slate-500">No completed generations were recorded for this run.</p>}
        <div className="mt-4 flex items-center gap-3"><button className={button} disabled={!offset} onClick={() => setOffset(value => Math.max(0, value - 50))}>Previous generations</button><span className="text-xs text-slate-500">{offset + (currentPage.total ? 1 : 0)}–{Math.min(offset + 50, currentPage.total)} of {currentPage.total}</span><button className={button} disabled={offset + 50 >= currentPage.total} onClick={() => setOffset(value => value + 50)}>Next generations</button></div>
      </section>
      {generation !== null && <section className={box} aria-label="Historical schedule candidate"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold">Generation {generation} · Schedule candidate</h2>
        <label className="text-sm">Candidate <select aria-label="Candidate kind" className="ml-2 rounded border p-2" value={kind} onChange={event => {setKind(event.target.value as CandidateKind); setError(null);}}><option value="generation_best">Generation best</option><option value="best_ever">Best ever at this generation</option></select></label></div>
        {!view && !visibleError && <p role="status" className="mt-3">Loading validated historical candidate…</p>}
        {view && <><p className="mt-3 text-sm font-semibold text-teal-900">Overall penalty: {number(view.analysis.fitness)} · Hard constraints passed at capture</p><p className="mt-1 break-all text-xs text-slate-500">Candidate {view.analysis.chromosome_id} · Captured {new Date(view.analysis.timestamp).toLocaleString()}</p>
          {!view.schedule.current_inputs_match && <p role="alert" className="mt-3 text-sm text-amber-800">Scheduling inputs have changed. This is the original validated observation; schedule exports require restoration of the run's inputs.</p>}
          <div className="mt-4 flex flex-wrap gap-2"><button className={button} disabled={busy || !view.schedule.current_inputs_match} onClick={() => void exportFile(`generations/${generation}/export?candidate=${kind}&format=json`)}>Download candidate JSON</button><button className={button} disabled={busy || !view.schedule.current_inputs_match} onClick={() => void exportFile(`generations/${generation}/export?candidate=${kind}&format=csv`)}>Download schedule CSV</button></div>
          <div className="mt-5 text-sm"><h3 className="font-semibold">Available penalty breakdown</h3>{view.analysis.fitness_breakdown ? <dl className="mt-2 grid gap-2 sm:grid-cols-2">{Object.entries(view.analysis.fitness_breakdown).map(([name, value]) => <div key={name} className="flex justify-between rounded bg-slate-50 p-2"><dt>{name.replaceAll("_", " ")}</dt><dd>{number(value)}</dd></div>)}</dl> : <p className="mt-1 text-slate-500">{view.analysis.breakdown_unavailable_reason}</p>}<p className="mt-2 text-xs text-slate-500">{view.analysis.preference_unavailable_reason}</p></div>
          <h3 className="mb-2 mt-5 text-sm font-semibold">Faculty workload · original teaching targets</h3><WorkloadTable rows={view.analysis.workload} />
          {view.analysis.breakdown_timestamp && <p className="mt-2 text-xs text-slate-500">Penalty breakdown recorded at {new Date(view.analysis.breakdown_timestamp).toLocaleString()} under this run's original inputs.</p>}
          <p className="mt-2 text-xs text-slate-500">Preassigned external instructors are shown in the schedule and excluded from normal faculty workload scoring.</p>
          <label className="mt-5 block text-sm">Calendar faculty <select aria-label="Calendar faculty" className="ml-2 rounded border p-2" value={faculty} onChange={event => setFaculty(event.target.value)}><option value="All">All instructors</option>{facultyCodes.map(code => <option key={code} value={code}>{instructorLabel(code, entries)}</option>)}</select></label>
          <div className="mt-3"><WeeklySchedule entries={filtered.map(row => ({...row, faculty: instructorLabel(row.faculty, entries)}))} viewMode="faculty" /></div><ScheduleTable rows={filtered} />
        </>}
      </section>}
      <section className={box} aria-label="Generation comparison"><h2 className="text-lg font-semibold">Compare two generations from this run</h2><p className="mt-1 text-xs text-slate-500">Positive reduction means improvement. Average, generation-best and best-ever are compared separately. Current candidate selection: {kind === "best_ever" ? "Best ever" : "Generation best"}.</p>
        <div className="mt-4 flex flex-wrap items-end gap-3">{[["Earlier generation", left, setLeft], ["Later generation", right, setRight]].map(([label, value, setter]) => <label key={String(label)} className="text-sm">{String(label)}<input aria-label={String(label)} className="ml-2 w-20 rounded border p-2" type="number" min="0" step="1" value={Number(value)} onChange={event => (setter as (value: number) => void)(Math.max(0, Number(event.target.value)))} /></label>)}<button className={button} disabled={busy || !Number.isInteger(left) || !Number.isInteger(right)} onClick={() => void compare()}>Compare generations</button></div>
        {diff && <div className="mt-4 space-y-3"><p className="text-sm font-semibold">{diff.identical_chromosomes ? "Identical schedule candidates — no assignment changes." : `${diff.changes.length} subject/section components changed.`}</p>
          <div className="grid gap-2 text-sm sm:grid-cols-3">{Object.entries(diff.improvement).map(([name, value]) => <p key={name} className="rounded bg-teal-50 p-3">{name.replaceAll("_", " ")}<strong className="mt-1 block text-teal-900">{improvementLabel(value)}</strong></p>)}</div>
          <p className="text-sm">Accepted candidates: {diff.left_metrics.accepted_new_chromosomes_total} → {diff.right_metrics.accepted_new_chromosomes_total}</p>
          {(diff.left_fitness_breakdown || diff.right_fitness_breakdown) && <div className="overflow-x-auto"><h3 className="mb-2 text-sm font-semibold">Available penalty contributions</h3><table className="w-full text-left text-sm"><thead><tr><th>Constraint</th><th>Earlier</th><th>Later</th><th>Reduction</th></tr></thead><tbody>{[...new Set([...Object.keys(diff.left_fitness_breakdown ?? {}), ...Object.keys(diff.right_fitness_breakdown ?? {})])].map(name => {
            const before = diff.left_fitness_breakdown?.[name], after = diff.right_fitness_breakdown?.[name];
            return <tr key={name} className="border-t"><td className="py-2">{name.replaceAll("_", " ")}</td><td>{before === undefined ? "Not captured" : number(before)}</td><td>{after === undefined ? "Not captured" : number(after)}</td><td>{before === undefined || after === undefined ? "Not available" : improvementLabel(before - after)}</td></tr>;
          })}</tbody></table></div>}
          {diff.changes.map(change => <details key={`${change.subject}-${change.section}-${change.component}`} className="rounded border p-3 text-sm"><summary className="cursor-pointer font-medium">{change.subject} · {change.section} · {change.component}: {change.offering_change} ({change.fields.join(", ")})</summary><h4 className="mt-2 font-medium">Before</h4><ScheduleTable rows={change.before} /><h4 className="mt-3 font-medium">After</h4><ScheduleTable rows={change.after} /></details>)}
          <details className="text-sm"><summary className="cursor-pointer font-medium">Compare original faculty workloads</summary><h4 className="mt-2">Generation {left}</h4><WorkloadTable rows={diff.left_workload} /><h4 className="mt-3">Generation {right}</h4><WorkloadTable rows={diff.right_workload} /></details>
          <p className="text-xs text-slate-500">{diff.preference_unavailable_reason}</p><button className={button} disabled={busy} onClick={() => void exportFile(`compare/export?left=${left}&right=${right}&candidate=${kind}`)}>Download comparison JSON</button>
        </div>}
      </section>
    </>}
  </div>;
}

function WorkloadTable({rows}: {rows: Workload[]}) {
  return <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{["Faculty", "Target", "Actual", "Difference", "Fulfillment", "Preparations", "Assigned subjects"].map(label => <th key={label} className="p-2">{label}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.faculty} className="border-t"><td className="p-2">{row.faculty}</td><td>{number(row.required_teaching_load)}</td><td>{number(row.teaching_units)}</td><td>{number(row.difference)}</td><td>{row.fulfillment_percent === null ? "No teaching target" : `${number(row.fulfillment_percent)}%`}</td><td>{row.preparations}</td><td>{row.assigned_subjects.join(", ")}</td></tr>)}</tbody></table></div>;
}
function ScheduleTable({rows}: {rows: ScheduleEntry[]}) {
  return <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{["Subject", "Title", "Section", "Component", "Faculty", "Room", "Day", "Time"].map(label => <th key={label} className="p-2">{label}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index} className="border-t"><td className="p-2">{row.subject}</td><td>{row.title}</td><td>{row.section}</td><td>{row.type}</td><td>{instructorLabel(row.faculty, rows)}</td><td>{row.room}</td><td>{row.day}</td><td>{row.start}–{row.end}</td></tr>)}</tbody></table></div>;
}
