import {useId} from "react";
import {workloadPresentation} from "../../services/workloadPresentation";
import type {WorkloadObservation} from "../../services/workloadPresentation";
import "./workloadChart.css";
const exact = (value: number | null) => value === null ? "Not captured" : String(value);

export default function WorkloadChart({rows}: {rows: readonly WorkloadObservation[]}) {
  const title = useId();
  const view = workloadPresentation(rows);
  return <figure aria-labelledby={title} className="workload-chart">
    <figcaption id={title} className="font-semibold text-teal-900">Teaching workload: target and actual</figcaption>
    <p className="mt-1 text-xs text-slate-600">Recorded teaching units only. Teal: actual; gold outline: target. Scale: 0–{view.maximum} units. A baseline marker denotes zero. Missing targets are not replaced with current settings.</p>
    {!view.rows.length ? <p role="status" className="mt-3 text-sm text-slate-500">No workload observations match this view.</p> : <ul className="workload-chart-list" aria-label="Recorded faculty workload comparisons">
      {view.rows.map((row, index) => {
        const label = `${row.observation.faculty}: actual ${exact(row.actual)}; target ${exact(row.target)} teaching units; ${row.status}${row.actual === 0 ? "; zero teaching units" : ""}${row.inconsistent ? "; recorded status differs from these values" : ""}`;
        return <li key={`${row.observation.faculty}-${index}`} tabIndex={0} aria-label={label} title={label} className="workload-chart-row">
          <div className="flex flex-wrap justify-between gap-2 text-sm"><strong className="break-words">{row.observation.faculty}</strong><span>{row.status}{row.actual === 0 ? " · Zero teaching units" : ""}</span></div>
          <div className="workload-track-row"><span>Actual</span><div className="workload-track" aria-hidden="true">{row.actualWidth !== null && <span className={`workload-actual${row.actual === 0 ? " workload-zero" : ""}`} style={{width: `${row.actualWidth}%`}}/>}</div><span className="tabular-nums">{exact(row.actual)}</span></div>
          <div className="workload-track-row"><span>Target</span><div className="workload-track" aria-hidden="true">{row.targetWidth !== null && <span className={`workload-target${row.target === 0 ? " workload-zero" : ""}`} style={{width: `${row.targetWidth}%`}}/>}</div><span className="tabular-nums">{exact(row.target)}</span></div>
          {row.inconsistent && <p className="mt-1 text-xs text-amber-900">Recorded status differs from the displayed values; inspect the detailed record.</p>}
          {row.actual !== null && row.actual > 40 && <p className="mt-1 text-xs text-red-800">Recorded actual exceeds the current 40-unit ceiling; display is not a feasibility validation.</p>}
        </li>;
      })}
    </ul>}
  </figure>;
}
