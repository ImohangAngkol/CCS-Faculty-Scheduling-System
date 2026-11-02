/** Presentation only. Existence, timestamps and fitness values cannot prove compatibility. */
export const compatibilityNotice = "Current engine and fitness-policy compatibility is not exposed by this API. Records remain available in the Historical Archive; none are classified as current.";

// Deliberately fail closed until a server-owned compatibility contract is available.
// Do not accept version strings or a client-supplied 'compatible' flag as proof.
export function isVerifiedCurrent(_record: unknown): boolean {
  void _record;
  return false;
}
export function evaluationRecords<T>(records: readonly T[], view: "current" | "archive"): T[] {
  return records.filter(record => view === "archive" ? !isVerifiedCurrent(record) : isVerifiedCurrent(record));
}
export function penaltyLabel(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString() : "—";
}

export const fitnessSeries = [
  {key: "generation_best_fitness", label: "Generation best", color: "#0f766e"},
  {key: "best_ever_fitness", label: "Best ever", color: "#b45309"},
  {key: "average_fitness", label: "Average", color: "#64748b"},
] as const;
export type PenaltyKey = typeof fitnessSeries[number]["key"];
export type PenaltyPoint = {generation: number; run_id?: string; input_fingerprint?: string; configuration_fingerprint?: string; engine_fingerprint?: string; fitness_policy_id?: string; metrics_comparable?: boolean} & Partial<Record<PenaltyKey, number | null>>;
export type ChartMode = "improvement" | "raw";
const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

/** Reject mixed identities/configurations rather than draw a misleading comparison. */
export function progressSeries(history: readonly PenaltyPoint[], baselineHistory: readonly PenaltyPoint[] = history) {
  const combined = [...baselineHistory, ...history];
  if (combined.some(point => point.metrics_comparable === false)) throw new Error("Observations are not comparable within this evaluation.");
  for (const key of ["run_id", "input_fingerprint", "configuration_fingerprint", "engine_fingerprint", "fitness_policy_id"] as const) {
    const identities = combined.map(point => point[key]);
    if (new Set(identities.filter(value => value !== undefined)).size > 1 || (identities.some(value => value !== undefined) && identities.some(value => value === undefined)))
      throw new Error("Cannot compare unrelated runs or incompatible evaluation inputs.");
  }
  if ([history, baselineHistory].some(points => points.some((point, index) => !Number.isInteger(point.generation) || point.generation < 0 || (index > 0 && point.generation <= points[index - 1].generation))))
    throw new Error("Generation observations must be ordered and unique.");
  return fitnessSeries.map(series => {
    const baseline = baselineHistory.find(point => valid(point[series.key]))?.[series.key];
    return {...series, points: history.map(point => {
      const raw = point[series.key];
      const penalty = valid(raw) ? raw : null;
      const reduction = penalty !== null && valid(baseline) ? baseline - penalty : null;
      return {generation: point.generation, penalty, reduction,
        percent: reduction !== null && valid(baseline) && baseline > 0 ? reduction / baseline * 100 : null};
    })};
  });
}
