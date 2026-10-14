import type { GenerationMetrics } from "./gaMonitoring";
import type { ScheduleEntry } from "../types/ga";

export type CandidateKind = "generation_best" | "best_ever";
export type HistoryRow = {
  generation: number; timestamp: string; metrics: GenerationMetrics;
  generation_best_id: string; best_ever_id: string; snapshot_bytes: number;
  capture_elapsed_ms: number; validation_elapsed_ms: number;
};
export type HistoryRun = {
  run_id: string; state: string; created_at: string; ended_at: string | null;
  generations_recorded: number; latest: HistoryRow | null;
  errors: {generation: number | null; code: string}[]; skipped_generations: number[];
  history_error: string | null; bytes_written: number;
};
export type HistoryPage = {schema_version: 1; run: HistoryRun; items: HistoryRow[]; total: number; offset: number; limit: number};
export type Workload = {faculty: string; teaching_units: number; required_teaching_load: number; difference: number;
  fulfillment_percent: number | null; preparations: number; assigned_subjects: string[]};
export type CandidateAnalysis = {schema_version: 1; run_id: string; generation: number; chromosome_id: string; timestamp: string;
  fitness: number; fitness_breakdown: Record<string, number> | null; breakdown_unavailable_reason: string | null;
  breakdown_timestamp?: string | null;
  preference_unavailable_reason: string; workload: Workload[]; validation: {status: string; validated_at: string}};
export type HistoricalSchedule = {schema_version: 1; run_id: string; generation: number; chromosome_id: string;
  schedule: ScheduleEntry[]; current_inputs_match: boolean; validation: {status: string}};
export type HistoryComparison = {schema_version: 1; run_id: string; left: number; right: number; candidate: CandidateKind;
  identical_chromosomes: boolean; improvement: Record<"generation_best_fitness" | "best_ever_fitness" | "average_fitness", number>;
  left_metrics: GenerationMetrics; right_metrics: GenerationMetrics;
  changes: {subject: string; section: string; component: string; fields: string[]; offering_change: string;
    before: ScheduleEntry[]; after: ScheduleEntry[]}[];
  left_workload: Workload[]; right_workload: Workload[]; preference_unavailable_reason: string;
  left_fitness_breakdown?: Record<string, number> | null; right_fitness_breakdown?: Record<string, number> | null};
export type RunPage = {schema_version: 1; items: HistoryRun[]; total: number; offset: number; limit: number;
  errors: {code: string; message: string}[]};
const BASE = `${API_BASE}/api/ga/runs`;
export function runPath(runId: string): string {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(runId)) throw new Error("Invalid historical run identity.");
  return `${BASE}/${runId}`;
}
export function validateHistory<T>(body: T, runId?: string, generation?: number): T {
  const data = body as {schema_version?: number; run_id?: string; generation?: number; run?: {run_id: string}};
  if (!data || data.schema_version !== 1 || (runId && (data.run_id ?? data.run?.run_id) !== runId)
    || (generation !== undefined && data.generation !== generation)) throw new Error("Historical response identity or schema mismatch.");
  return body;
}
export class HistoryRequestError extends Error {
  code: string; httpStatus: number;
  constructor(operation: string, message: string, code: string, httpStatus: number) {
    super(`${operation}: ${message} (${code})`);
    this.name = "HistoryRequestError"; this.code = code; this.httpStatus = httpStatus;
  }
}
function operationLabel(path: string) {
  if (path.includes("/export")) return "History export";
  if (path.includes("/compare") || path.includes("/fitness-comparison")) return "Generation comparison";
  if (path.includes("/analysis") || path.includes("/fitness-analysis")) return "Fitness analysis";
  if (path.includes("/schedule")) return "Schedule inspection";
  if (path.includes("/generations")) return "Generation listing";
  return "Run listing";
}
async function request(path: string, signal = AbortSignal.timeout(30000)): Promise<Response> {
  const operation = operationLabel(path);
  try {
    const response = await fetch(path, {signal});
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new HistoryRequestError(operation,
        body?.detail?.message ?? (typeof body?.detail === "string" ? body.detail : `History request failed (${response.status}).`),
        body?.detail?.code ?? "GA_HISTORY_REQUEST_FAILED", response.status);
    }
    return response;
  } catch (error) {
    if (error instanceof Error && ["TimeoutError", "AbortError"].includes(error.name)) throw new HistoryRequestError(operation, "Request timed out. Check the backend and retry; no optimization was started.", "GA_HISTORY_TIMEOUT", 0);
    if (error instanceof TypeError) throw new HistoryRequestError(operation, "Backend unavailable. Check port 8000 and retry; no optimization was started.", "GA_HISTORY_UNAVAILABLE", 0);
    throw error;
  }
}
async function json<T>(path: string, runId?: string, generation?: number): Promise<T> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let response: Response | undefined;
  try {
    return await Promise.race([
      (async () => {
        response = await request(path, controller.signal);
        return validateHistory(await response.json() as T, runId, generation);
      })(),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => {
          reject(new HistoryRequestError(operationLabel(path), "Request or response timed out. Check the backend and retry; no optimization was started.", "GA_HISTORY_TIMEOUT", 0));
          controller.abort();
        }, 30000);
      }),
    ]);
  } catch (error) {
    if (error instanceof HistoryRequestError) throw error;
    if (error instanceof Error && ["TimeoutError", "AbortError"].includes(error.name)) {
      throw new HistoryRequestError(operationLabel(path), "Response timed out. Retry when the backend is available.", "GA_HISTORY_TIMEOUT", 0);
    }
    throw new HistoryRequestError(operationLabel(path), "Backend response could not be validated. Retry and check backend logs.", "GA_HISTORY_RESPONSE_INVALID", response?.status ?? 0);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}
export const getHistoryRuns = (offset = 0) => json<RunPage>(`${BASE}?offset=${offset}&limit=20`);
export const getHistoryGenerations = async (id: string, offset = 0) => json<HistoryPage>(`${runPath(id)}/generations?offset=${offset}&limit=50`, id);
export const getHistoricalSchedule = async (id: string, generation: number, candidate: CandidateKind) =>
  json<HistoricalSchedule>(`${runPath(id)}/generations/${generation}/schedule?candidate=${candidate}`, id, generation);
export const getHistoricalAnalysis = async (id: string, generation: number, candidate: CandidateKind) =>
  json<CandidateAnalysis>(`${runPath(id)}/generations/${generation}/analysis?candidate=${candidate}`, id, generation);
export const compareGenerations = async (id: string, left: number, right: number, candidate: CandidateKind) =>
  json<HistoryComparison>(`${runPath(id)}/compare?left=${left}&right=${right}&candidate=${candidate}`, id);
export async function downloadHistory(id: string, suffix: string) {
  const response = await request(`${runPath(id)}/${suffix}`);
  const blob = await response.blob();
  const name = response.headers.get("content-disposition")?.match(/filename="([a-zA-Z0-9_.-]+)"/)?.[1] ?? `run-${id}-history.json`;
  const url = URL.createObjectURL(blob), anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function improvementLabel(value: number) {
  return value > 0 ? `${value.toLocaleString()} lower (improved)` : value < 0 ? `${Math.abs(value).toLocaleString()} higher (worse)` : "Unchanged";
}
export { json as readHistoryJSON, request as requestHistory };
import {API_BASE, apiFetch as fetch} from "./apiSession.ts";
