/** Descriptive display rules only. Never changes scoring or academic policy. */
export type Highlight = "ordinary" | "satisfaction" | "preparations" | "deviation";
export function barAppearance(n: number | null, kind: Highlight, base: string, reference: number | null = null) {
  if (n === null || !Number.isFinite(n)) return {fill: base, status: "Unavailable"};
  if (kind === "satisfaction" && n < 40) return {fill: "#9a3412", status: "Low satisfaction (below descriptive 40% threshold)"};
  if (kind === "preparations" && reference !== null && Number.isFinite(reference) && n > reference)
    return {fill: "#9a3412", status: "Above captured preparation reference"};
  if (kind === "deviation") return n > 0 ? {fill: "#9a3412", status: "Above captured faculty average"}
    : n < 0 ? {fill: "#0369a1", status: "Below captured faculty average"} : {fill: "#475569", status: "At captured faculty average"};
  return {fill: base, status: "Recorded value"};
}
export function chartNumber(v: unknown): number | null {return typeof v === "number" && Number.isFinite(v) ? v : null;}
