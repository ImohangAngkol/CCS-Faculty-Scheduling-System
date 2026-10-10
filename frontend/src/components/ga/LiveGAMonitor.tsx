import type { GAExecutionStatus, GenerationMetrics } from "../../services/gaMonitoring";

const format = (value: number | undefined) => value === undefined ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
export default function LiveGAMonitor({ status, history, elapsedSeconds, population, limit }: {
  status: GAExecutionStatus; history: GenerationMetrics[]; elapsedSeconds: number; population: number; limit: number;
}) {
  const current = history.at(-1);
  const label = { IDLE: "Ready", CONNECTING: "Connecting", RUNNING: current ? "Optimizing schedules" : "Preparing initial schedules", COMPLETED: "Completed", FAILED: "Failed", DISCONNECTED: "Monitoring disconnected", REJECTED: "Execution request rejected" }[status];
  return <section data-testid="live-ga-monitor" className="overflow-hidden rounded-xl border border-purple-200 bg-white shadow-sm" aria-label="Live schedule optimization">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-purple-100 bg-purple-50 px-6 py-4">
      <div><h2 className="text-lg font-semibold text-purple-950">Schedule optimization</h2><p role="status" aria-live="polite" className="text-sm text-purple-800">{label}</p></div>
      <p className="text-sm text-slate-600">Elapsed <strong data-testid="ga-elapsed" className="ml-1 text-purple-950">{Math.floor(elapsedSeconds / 60)}m {elapsedSeconds % 60}s</strong></p>
    </div>
    <div className="grid gap-6 p-6 sm:grid-cols-2">
      <div><h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Progress</h3><dl className="space-y-2 text-sm">
        <Metric label="Generation" testId="ga-generation" value={current ? `${current.generation} / ${current.generation_limit}` : `Preparing / ${limit}`} />
        <Metric label="Population · actual / requested" testId="ga-population" value={`${current?.population_actual ?? "—"} / ${current?.population_requested ?? population}`} />
        <Metric label="Accepted new candidates" testId="ga-accepted" value={format(current?.accepted_new_chromosomes_total)} />
      </dl><p className="mt-3 text-xs text-slate-500">Accepted initial schedules, crossover/mutation results and immigrants. Retained candidates and baseline seeds are excluded.</p></div>
      <div><h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Overall penalty · lower is better</h3><dl className="space-y-2 text-sm">
        <Metric label="Best ever" testId="ga-best-ever" value={format(current?.best_ever_fitness)} />
        <Metric label="Current generation best" testId="ga-generation-best" value={format(current?.generation_best_fitness)} />
        <Metric label="Population average" testId="ga-average" value={format(current?.average_fitness)} />
      </dl></div>
    </div>
    {status === "DISCONNECTED" && <p role="alert" className="mx-6 mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">The server may still be running. Losing this connection does not stop the optimization.</p>}
    <div className="border-t border-slate-100 p-6"><ConvergenceChart history={history} /></div>
  </section>;
}
function Metric({ label, value, testId }: { label: string; value: string; testId: string }) {
  return <div className="flex justify-between gap-3"><dt className="text-slate-600">{label}</dt><dd data-testid={testId} className="font-semibold tabular-nums text-purple-950">{value}</dd></div>;
}
export function ConvergenceChart({ history }: { history: GenerationMetrics[] }) {
  if (!history.length) return <p className="rounded-lg bg-slate-50 p-5 text-sm text-slate-500">The convergence graph will appear when the initial population is ready.</p>;
  const series = [
    { key: "generation_best_fitness", label: "Generation best", color: "#7c3aed" },
    { key: "best_ever_fitness", label: "Best ever", color: "#f97316" },
    { key: "average_fitness", label: "Average", color: "#64748b" },
  ] as const;
  const values = history.flatMap(point => series.map(line => point[line.key]));
  const low = Math.min(...values), high = Math.max(...values), span = Math.max(1, high - low);
  const lastGeneration = Math.max(1, history.at(-1)!.generation);
  const x = (generation: number) => 80 + generation / lastGeneration * 690;
  const y = (fitness: number) => 230 - (fitness - low) / span * 185;
  return <div data-testid="ga-convergence" data-points={history.length}>
    <h3 className="text-sm font-semibold text-slate-900">Convergence · lower penalty is better</h3>
    <div className="mt-2 flex flex-wrap gap-4 text-xs">{series.map(line => <span key={line.key} style={{ color: line.color }}>{line.label}</span>)}</div>
    <svg viewBox="0 0 800 290" className="mt-2 w-full" role="img" aria-label={`Fitness convergence through generation ${history.at(-1)!.generation}`}>
      {[0, 0.5, 1].map(fraction => <g key={fraction}><line x1="80" x2="770" y1={45 + fraction * 185} y2={45 + fraction * 185} stroke="#e2e8f0" /><text x="70" y={49 + fraction * 185} textAnchor="end" fontSize="12" fill="#64748b">{format(high - fraction * (high - low))}</text></g>)}
      <line x1="80" x2="770" y1="230" y2="230" stroke="#94a3b8" />
      {series.map(line => <g key={line.key}><polyline fill="none" stroke={line.color} strokeWidth="2.5" points={history.map(point => `${x(point.generation)},${y(point[line.key])}`).join(" ")} />{history.map(point => <circle key={point.generation} cx={x(point.generation)} cy={y(point[line.key])} r="3" fill={line.color}><title>{`Generation ${point.generation} · ${line.label}: ${format(point[line.key])}`}</title></circle>)}</g>)}
      {[0, history.at(-1)!.generation].filter((value, index, all) => all.indexOf(value) === index).map(generation => <text key={generation} x={x(generation)} y="249" textAnchor="middle" fontSize="12" fill="#64748b">{generation}</text>)}
      <text x="420" y="277" textAnchor="middle" fontSize="12" fill="#64748b">Generation</text><text x="16" y="135" textAnchor="middle" transform="rotate(-90 16 135)" fontSize="12" fill="#64748b">Penalty</text>
    </svg>
    <details className="text-xs text-slate-600"><summary className="cursor-pointer">View exact generation values</summary><div className="mt-2 max-h-48 overflow-auto"><table className="w-full text-right"><thead><tr><th className="text-left">Generation</th>{series.map(line => <th key={line.key}>{line.label}</th>)}</tr></thead><tbody>{history.map(point => <tr key={point.generation}><td className="text-left">{point.generation}</td>{series.map(line => <td key={line.key}>{format(point[line.key])}</td>)}</tr>)}</tbody></table></div></details>
  </div>;
}
