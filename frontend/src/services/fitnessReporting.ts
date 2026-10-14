import { readHistoryJSON, requestHistory, runPath } from "./gaHistory.ts";
import type { CandidateKind } from "./gaHistory";
import type { GARunData } from "../types/ga";

export type PreferenceIndicator = {key: string; status: string; matched: number | null; total: number | null;
  satisfaction_percent: number | null; importance: number | null; affects_fitness: boolean | null;
  penalty: number | null; explanation: string; idle_minutes?: number};
export type FacultyReport = {faculty: string; teaching_units: number | null; required_teaching_load: number | null;
  difference: number | null; fulfillment_percent: number | null; admin_load: number | null;
  research_load: number | null; extension_load: number | null; workload_status: string;
  heavy_overload: boolean | null; workload_penalty: number | null; underload_steps: number | null;
  preparations: number | null; total_penalty: number | null; priority_multiplier: number | null;
  penalties: Record<string, number>; preferences: PreferenceIndicator[] | null; unavailable_reason: string | null};
export type FitnessReport = {schema_version: 1; source: {kind: string; run_id: string | null; generation: number | null;
  candidate: CandidateKind; timestamp: string | null; analysis_timestamp?: string | null; chromosome_id: string | null; penalty_source: string | null};
  overall_penalty: number; breakdown_available: boolean; recorded_component_sum: number | null;
  components: {key: string; label: string; definition: string; penalty: number | null}[];
  faculty: FacultyReport[]; external_instructors: {name: string; subject: string; section: string; scoring: string}[];
  definitions: Record<string, string>; fitness_configuration: Record<string, number> | null; limitations: string[]};
export type FitnessComparison = {schema_version: 1; source: {run_id: string; left: number; right: number; candidate: CandidateKind};
  overall_reduction: number; component_changes: {key: string; label: string; before: number | null; after: number | null; reduction: number | null}[];
  faculty_changes: {faculty: string; before: FacultyReport | null; after: FacultyReport | null}[];
  assignment_changes: unknown[]; explanation: string};
const BASE = `${API_BASE}/api/ga`;
const validNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const componentKeys = ["subject_preference", "time_preference", "day_preference", "schedule_style", "lecture_lab_preference", "number_of_preparations", "teaching_load_balance", "daily_teaching_load"];
export function validateFitnessReport(report: FitnessReport, runId?: string, generation?: number, candidate?: CandidateKind) {
  if (report?.schema_version !== 1 || !report?.source || !validNumber(report.overall_penalty) || !Array.isArray(report.components) || !Array.isArray(report.faculty)
      || (runId && report.source.run_id !== runId) || (generation !== undefined && report.source.generation !== generation)
      || (candidate && report.source.candidate !== candidate)) throw new Error("Fitness report identity or observations could not be validated.");
  if (report.components.length !== componentKeys.length || new Set(report.components.map(row => row.key)).size !== componentKeys.length
      || report.components.some(row => !componentKeys.includes(row.key) || (row.penalty !== null && !validNumber(row.penalty)))) throw new Error("Invalid component observation.");
  if (report.breakdown_available && (report.components.some(row => row.penalty === null)
      || !validNumber(report.recorded_component_sum) || Math.abs(report.recorded_component_sum - report.overall_penalty) > 0.000001
      || Math.abs(report.components.reduce((sum, row) => sum + (row.penalty ?? 0), 0) - report.overall_penalty) > 0.000001)) throw new Error("Component penalties do not reconcile with overall penalty.");
  return report;
}
function checkedGeneration(generation: number) {
  if (!Number.isInteger(generation) || generation < 0) throw new Error("Choose a recorded generation.");
  return generation;
}
export async function getFitnessReport(runId?: string, generation?: number, candidate: CandidateKind = "generation_best") {
  const path = runId ? `${runPath(runId)}/generations/${checkedGeneration(generation!)}/fitness-analysis?candidate=${candidate}` : `${BASE}/fitness-analysis/latest`;
  return validateFitnessReport(await readHistoryJSON<FitnessReport>(path), runId, generation, runId ? candidate : undefined);
}
export async function compareFitness(runId: string, left: number, right: number, candidate: CandidateKind) {
  const report = await readHistoryJSON<FitnessComparison>(`${runPath(runId)}/fitness-comparison?left=${checkedGeneration(left)}&right=${checkedGeneration(right)}&candidate=${candidate}`);
  if (report.source?.run_id !== runId || report.source.left !== left || report.source.right !== right || report.source.candidate !== candidate
      || !validNumber(report.overall_reduction) || !Array.isArray(report.component_changes) || !Array.isArray(report.faculty_changes)) throw new Error("Comparison source could not be validated.");
  return report;
}
export async function downloadFitnessReport(runId: string | undefined, generation: number | undefined, candidate: CandidateKind, section: "fitness" | "workload", format: "json" | "csv") {
  const path = runId ? `${runPath(runId)}/generations/${checkedGeneration(generation!)}/fitness-analysis/export?candidate=${candidate}` : `${BASE}/fitness-analysis/latest/export?`;
  const response = await requestHistory(`${path}&section=${section}&format=${format}`);
  const blob = await response.blob();
  const name = response.headers.get("content-disposition")?.match(/filename="([a-zA-Z0-9_.-]+)"/)?.[1] ?? `fitness-${section}.${format}`;
  const url = URL.createObjectURL(blob), anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const metric = (value: number | null | undefined, suffix = "") => value === null || value === undefined ? "Not captured" : `${value.toLocaleString(undefined, {maximumFractionDigits: 2})}${suffix}`;
export const statusLabel = (status: string) => ({satisfied: "Satisfied", partially_satisfied: "Partially satisfied", unmet: "Unmet", disabled: "Disabled", unavailable: "Not captured", not_applicable: "No applicable comparisons"}[status] ?? status);

// Preserve the existing saved/uploaded candidate analysis workflow. These are
// already evaluated API observations in GAContext, never a new evaluation.
export function loadedEvaluationReport(data: GARunData): FitnessReport {
  const labels = ["Ranked subjects", "Preferred times", "Preferred days", "Schedule style", "Lecture / laboratory days", "Preparations", "Teaching workload", "Daily teaching time"];
  const fields = ["Subject_Penalty", "Time_Penalty", "Day_Penalty", "Schedule_Style_Penalty", "Lecture_Lab_Penalty", "Preparation_Penalty", "Load_Balance_Penalty", "Daily_Teaching_Load_Penalty"];
  function observed(row: Record<string, unknown>, key: string): number | null {
    const value = row[key];
    if (value === undefined || value === null) return null;
    if (!validNumber(value)) throw new Error(`Invalid recorded ${key}.`);
    return value;
  }
  const breakdown = data.fitness_breakdown as unknown as Record<string, unknown>;
  const components = componentKeys.map((key, index) => ({key, label: labels[index], penalty: observed(breakdown, key), definition: "Original recorded evaluation contribution. Original inputs were not stored with this loaded candidate."}));
  const available = components.every(row => row.penalty !== null);
  const faculty = (data.faculty_analysis?.faculty ?? []).filter(row => !String(row.Faculty_Code).startsWith("external:")).map(item => {
    const row = item as unknown as Record<string, unknown>;
    const penalties = Object.fromEntries(componentKeys.flatMap((key, index) => {const value = observed(row, fields[index]); return value === null ? [] : [[key, value]];}));
    const preferences = ["Subject", "Day", "Time"].map(prefix => {
      const key = `${prefix.toLowerCase()}_preference`, value = observed(row, `${prefix}_Satisfaction`);
      return {key, status: value === null ? "unavailable" : value === 100 ? "satisfied" : value === 0 ? "unmet" : "partially_satisfied",
        matched: null, total: null, satisfaction_percent: value, importance: observed(row, `${prefix}_Importance`),
        affects_fitness: null, penalty: penalties[key] ?? null, explanation: "Recorded descriptive indicator from the original load evaluation; enable flags were not captured."};
    });
    return {faculty: `Faculty ${Number.isInteger(Number(item.Faculty_Code)) ? Number(item.Faculty_Code) : item.Faculty_Code}`,
      teaching_units: observed(row, "Teaching_Load"), required_teaching_load: null, difference: null, fulfillment_percent: null,
      admin_load: null, research_load: null, extension_load: null, workload_status: "unavailable", heavy_overload: null,
      workload_penalty: penalties.teaching_load_balance ?? null, underload_steps: null,
      preparations: observed(row, "Preparations"), total_penalty: observed(row, "Total_Penalty"), priority_multiplier: observed(row, "Priority_Weight"),
      penalties, preferences, unavailable_reason: "Teaching targets, release details and original enable flags were not captured by the existing load-analysis API."};
  });
  const external = data.schedule.filter(row => row.faculty.startsWith("external:")).map(row => ({name: (row as typeof row & {faculty_name?: string}).faculty_name ?? "Preassigned Instructor", subject: row.subject, section: row.section, scoring: "Excluded from normal workload/preference scoring"}));
  return validateFitnessReport({schema_version: 1, source: {kind: "loaded-chromosome-evaluation", run_id: null, generation: null,
    candidate: "best_ever", timestamp: null, chromosome_id: null, penalty_source: "existing-load-evaluation"},
    overall_penalty: data.best_fitness, components, breakdown_available: available,
    recorded_component_sum: available ? components.reduce((sum, row) => sum + row.penalty!, 0) : null, faculty,
    external_instructors: [...new Map(external.map(row => [`${row.name}/${row.subject}/${row.section}`, row])).values()],
    definitions: {overall: "Sum of recorded evaluation contributions; lower penalty is better.", target: "Teaching target is 24 minus release units; original targets/releases were not stored here.",
      actual: "Recorded course teaching units, not contact hours.", difference: "Actual minus the original target; target unavailable.", fulfillment: "Actual divided by original target; target unavailable.",
      indicators: "Recorded descriptive percentages are separate from penalties.", priority: "Original recorded importance and priority affect preferences; no new scoring occurs."},
    fitness_configuration: null, limitations: ["This is the existing loaded-candidate evaluation, not a historical generation.", "Reloading the browser restores saved run data; load this candidate again to inspect its evaluation.", "Original missing targets/preferences are not replaced with current values."]});
}
export async function downloadLoadedEvaluation(report: FitnessReport, section: "fitness" | "workload", format: "json" | "csv") {
  validateFitnessReport(report);
  let content: string;
  if (format === "json") content = JSON.stringify({...report, report_kind: section}, null, 2);
  else {
    const safe = (value: unknown) => {
      let text = value === undefined || value === null ? "" : String(value);
      if (/^[\t\r\n]/.test(text) || /^[=+@-]/.test(text.trimStart())) text = "'" + text;
      return `"${text.replaceAll('"', '""')}"`;
    };
    const headers = ["source", "generation", "faculty", "component", "value", "definition"];
    const rows: unknown[][] = section === "workload" ? report.faculty.map(row => [report.source.kind, null, row.faculty, "teaching_units", row.teaching_units, report.definitions.actual + " " + report.definitions.target])
      : report.components.map(row => [report.source.kind, null, null, row.key, row.penalty, row.definition]);
    content = [headers, ...rows].map(row => row.map(safe).join(",")).join("\r\n");
  }
  const url = URL.createObjectURL(new Blob([content], {type: format === "json" ? "application/json" : "text/csv;charset=utf-8"}));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = `loaded-candidate-${section}.${format}`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
import {API_BASE} from "./apiSession.ts";
