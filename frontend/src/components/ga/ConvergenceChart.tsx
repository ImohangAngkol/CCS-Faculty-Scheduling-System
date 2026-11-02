import {useState} from "react";
import {progressSeries} from "../../services/resultPresentation";
import type {ChartMode, PenaltyPoint} from "../../services/resultPresentation";

const format = (value: number | null) => value === null ? "—" : value.toLocaleString(undefined, {maximumFractionDigits: 2});

export default function ConvergenceChart({history, baselineHistory = history, loading = false}: {
  history: readonly PenaltyPoint[]; baselineHistory?: readonly PenaltyPoint[]; loading?: boolean;
}) {
  const [mode, setMode] = useState<ChartMode>("improvement");
  if (loading) return <p role="status">Loading this run's starting observations…</p>;
  if (!history.length) return <p role="status" className="rounded-lg bg-slate-50 p-5 text-sm text-slate-500">Optimization Progress will appear when the initial population is ready.</p>;
  let lines;
  try {lines = progressSeries(history, baselineHistory);} catch (error) {
    return <p role="alert">{error instanceof Error ? error.message : "Incompatible chart observations."}</p>;
  }
  const value = (point: typeof lines[number]["points"][number]) => mode === "raw" ? point.penalty : point.reduction;
  const values = lines.flatMap(line => line.points.flatMap(point => value(point) === null ? [] : [value(point)!]));
  const low = Math.min(0, ...values), high = Math.max(0, ...values), span = Math.max(1, high - low);
  const first = history[0].generation, last = history.at(-1)!.generation;
  const x = (generation: number) => 85 + (generation - first) / Math.max(1, last - first) * 680;
  const y = (score: number) => 230 - (score - low) / span * 185;
  const describe = (point: typeof lines[number]["points"][number]) => `Generation ${point.generation} · Original penalty: ${format(point.penalty)} · Absolute improvement: ${format(point.reduction)} · Percentage improvement: ${point.percent === null ? "Unavailable (zero, negative or invalid starting penalty)" : `${format(point.percent)}%`}`;
  return <div data-testid="ga-convergence" data-points={history.length}>
    <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold text-slate-900">{mode === "improvement" ? "Optimization Progress" : "Raw Fitness Penalty"}</h3>
      <label className="text-sm">Chart mode <select aria-label="Chart mode" className="ml-2 rounded border p-2" value={mode} onChange={event => setMode(event.target.value as ChartMode)}><option value="improvement">Optimization Improvement</option><option value="raw">Raw Fitness Penalty</option></select></label></div>
    <p className="mt-2 text-sm text-slate-600">{mode === "improvement" ? "Higher improvement indicates a greater reduction in scheduling penalties." : "Lower penalty is better. Original recorded penalty values are unchanged."}</p>
    <p className="mt-1 text-xs text-slate-500">Each series uses its first valid observation in this run. Percentage improvement is unavailable for zero or invalid starting penalties.</p>
    {!values.length ? <p role="status">No valid observations for this chart mode.</p> : <>
      <div className="mt-3 flex flex-wrap gap-4 text-xs">{lines.map(line => <span key={line.key} style={{color: line.color}}>{line.label}</span>)}</div>
      <svg viewBox="0 0 800 290" className="mt-2 w-full" role="img" aria-label={`${mode === "improvement" ? "Optimization Progress" : "Raw Fitness Penalty"} through generation ${last}`}>
        <title>{mode === "improvement" ? "Penalty reduction from the start of the same run" : "Recorded penalties, lower is better"}</title>
        {[0, 0.5, 1].map(fraction => <g key={fraction}><line x1="85" x2="765" y1={45 + fraction * 185} y2={45 + fraction * 185} stroke="#e2e8f0"/><text x="75" y={49 + fraction * 185} textAnchor="end" fontSize="12" fill="#64748b">{format(low + span - fraction * span)}</text></g>)}
        {lines.map(line => <g key={line.key}><path fill="none" stroke={line.color} strokeWidth="2.5" d={line.points.map((point, index) => value(point) === null ? "" : `${index === 0 || value(line.points[index - 1]) === null ? "M" : "L"}${x(point.generation)},${y(value(point)!)}`).join(" ")}/>{line.points.map(point => value(point) === null ? null : <circle key={point.generation} cx={x(point.generation)} cy={y(value(point)!)} r="3" fill={line.color} tabIndex={0} aria-label={`${line.label} · ${describe(point)}`}><title>{line.label} · {describe(point)}</title></circle>)}</g>)}
        {[first, last].filter((v, i, all) => all.indexOf(v) === i).map(generation => <text key={generation} x={x(generation)} y="249" textAnchor="middle" fontSize="12" fill="#64748b">{generation}</text>)}
        <text x="420" y="277" textAnchor="middle" fontSize="12" fill="#64748b">Generation</text><text x="16" y="135" textAnchor="middle" transform="rotate(-90 16 135)" fontSize="12" fill="#64748b">{mode === "improvement" ? "Penalty Reduction" : "Penalty"}</text>
      </svg></>}
    <details className="mt-2 text-xs text-slate-600"><summary className="cursor-pointer">View exact generation values</summary><div className="mt-2 max-h-64 overflow-auto"><table className="w-full text-right"><caption className="text-left">Original penalties and same-run improvement; no values are clamped.</caption><thead><tr>{["Generation", "Series", "Original penalty", "Absolute improvement", "Percentage improvement"].map(label => <th className="p-2" key={label}>{label}</th>)}</tr></thead><tbody>{lines.flatMap(line => line.points.map(point => <tr key={`${line.key}-${point.generation}`}><td>{point.generation}</td><td>{line.label}</td><td>{format(point.penalty)}</td><td>{format(point.reduction)}</td><td>{point.percent === null ? "—" : `${format(point.percent)}%`}</td></tr>))}</tbody></table></div></details>
  </div>;
}
