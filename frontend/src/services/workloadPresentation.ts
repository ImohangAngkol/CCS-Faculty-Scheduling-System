import {facultyOrder} from "../components/schedule/scheduleOrder.ts";
export type WorkloadObservation = {faculty: string; teaching_units: number | null; required_teaching_load: number | null; workload_status?: string};
const units = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0;

/** Read recorded numbers only. No current workload settings, defaults or scoring. */
export function workloadPresentation<T extends WorkloadObservation>(rows: readonly T[]) {
  const sorted = [...rows].sort((a, b) => facultyOrder(a.faculty, b.faculty));
  const maximum = Math.max(1, ...sorted.flatMap(row => [row.teaching_units, row.required_teaching_load].filter(units)));
  return {maximum, rows: sorted.map(row => {
    const actual = units(row.teaching_units) ? row.teaching_units : null;
    const target = units(row.required_teaching_load) ? row.required_teaching_load : null;
    const status = actual === null ? "Actual not captured" : target === null ? "Target not captured" : actual < target ? "Underload" : actual > target ? "Overload" : "Balanced (at target)";
    const expected = actual === null || target === null ? "unavailable" : actual < target ? "underload" : actual > target ? "overload" : "on_target";
    const inconsistent = row.workload_status !== undefined && row.workload_status !== expected;
    return {observation: row, actual, target, status, inconsistent,
      actualWidth: actual === null ? null : actual / maximum * 100,
      targetWidth: target === null ? null : target / maximum * 100};
  })};
}
