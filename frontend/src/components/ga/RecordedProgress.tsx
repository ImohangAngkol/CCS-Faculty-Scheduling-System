import {useEffect, useState} from "react";
import {getHistoryGenerations} from "../../services/gaHistory";
import type {HistoryRow} from "../../services/gaHistory";
import ConvergenceChart from "./ConvergenceChart";

/** Load preceding pages so pagination never resets an improvement baseline. */
export default function RecordedProgress({runId, rows, offset, refresh}: {runId: string; rows: HistoryRow[]; offset: number; refresh: number}) {
  const key = `${runId}-${offset}-${refresh}`;
  const [prefix, setPrefix] = useState<{key: string; rows: HistoryRow[]; error?: string} | null>(null);
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const preceding: HistoryRow[] = [];
        for (let start = 0; start < offset; start += 50) {
          const page = await getHistoryGenerations(runId, start);
          if (cancelled) return;
          if (page.offset !== start || page.items.length !== 50) throw new Error("Incomplete starting observations.");
          preceding.push(...page.items);
        }
        if (!cancelled) setPrefix({key, rows: preceding});
      } catch {
        if (!cancelled) setPrefix({key, rows: [], error: "Starting observations unavailable. Retry the history/analysis refresh; no page-local baseline was substituted."});
      }
    }
    void load(); return () => {cancelled = true;};
  }, [runId, offset, key]);
  if (prefix?.key === key && prefix.error) return <p role="alert">{prefix.error}</p>;
  return <ConvergenceChart key={runId} history={rows.map(row => ({...row.metrics, run_id: runId}))}
    baselineHistory={[...(prefix?.key === key ? prefix.rows : []), ...rows].map(row => ({...row.metrics, run_id: runId}))}
    loading={offset > 0 && prefix?.key !== key}/>;
}
