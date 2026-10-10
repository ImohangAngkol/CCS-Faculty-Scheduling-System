import type { GARunData } from "../types/ga";

export type GenerationMetrics = {
  status: "RUNNING";
  generation: number;
  generation_limit: number;
  population_requested: number;
  population_actual: number;
  generation_best_fitness: number;
  best_ever_fitness: number;
  average_fitness: number;
  worst_fitness: number;
  best_ever_improvement: number;
  generations_without_improvement: number;
  elapsed_ms: number;
  generation_elapsed_ms: number;
  accepted_new_chromosomes_total: number;
  baseline_chromosomes: number;
  fitness_evaluations_total: null;
  input_fingerprint: string;
  configuration_fingerprint: string;
  metrics_comparable: boolean;
  validation_status: "passed";
};
export type GARunState = "CREATED" | "INITIALIZING" | "RUNNING" | "STOP_REQUESTED" | "STOPPING" | "STOPPED" | "COMPLETED" | "FAILED";
export type GAExecutionStatus = "IDLE" | "CONNECTING" | "RECOVERING" | "INTERRUPTED" | GARunState | "DISCONNECTED" | "REJECTED";
export type GAMonitoringEvent = {
  schema_version: 1; run_id: string; sequence: number; timestamp: string;
} & (
  | { type: "initial_population_ready" | "generation_completed"; data: GenerationMetrics }
  | { type: "run_created" | "run_started" | "run_state_changed" | "log" | "error" | "done"; data: Record<string, unknown> }
  | { type: "result"; data: GARunData }
);

export class GAStreamError extends Error {
  status: GAExecutionStatus;
  constructor(message: string, status: GAExecutionStatus = "DISCONNECTED") {
    super(message); this.name = "GAStreamError"; this.status = status;
  }
}

/** Incremental SSE decoding, including UTF-8, CR/LF framing and multiline data. */
export async function readGAStream(
  stream: ReadableStream<Uint8Array>, onLog: (message: string) => void,
  onEvent?: (event: GAMonitoringEvent) => void,
): Promise<GARunData | null> {
  const reader = stream.getReader(), decoder = new TextDecoder();
  let buffer = "", lines: string[] = [], result: GARunData | null = null;
  let runId: string | null = null, sequence = 0, terminal = false, stopped = false;
  const known = new Set(["run_created", "run_started", "run_state_changed", "initial_population_ready", "generation_completed", "log", "result", "error", "done"]);
  function dispatch() {
    const data = lines.filter(line => line.startsWith("data:")).map(line => line.slice(5).replace(/^ /, "")).join("\n");
    lines = [];
    if (!data) return;
    const event = JSON.parse(data);
    if (!known.has(event.type)) return;
    if (event.schema_version !== undefined) {
      if (event.schema_version !== 1 || typeof event.run_id !== "string" || !Number.isInteger(event.sequence) || event.sequence < 1 || typeof event.timestamp !== "string" || !event.data || typeof event.data !== "object") {
        throw new GAStreamError("Invalid GA monitoring event.");
      }
      if (runId && event.run_id !== runId) throw new GAStreamError("GA stream changed run identity.");
      runId = event.run_id;
      if (event.sequence <= sequence) return; // Ignore duplicate/stale delivery.
      sequence = event.sequence; // Gaps are allowed: console logs are best effort.
      if (event.type === "run_state_changed" && !["CREATED", "INITIALIZING", "RUNNING", "STOP_REQUESTED", "STOPPING", "STOPPED", "COMPLETED", "FAILED"].includes(event.data.status)) {
        throw new GAStreamError("Invalid GA lifecycle state.");
      }
      if (event.type === "run_state_changed" && event.data.status === "STOPPED") stopped = true;
      if (stopped && event.data.status === "COMPLETED") throw new GAStreamError("GA completion contradicts its acknowledged stop.");
      if (event.type === "initial_population_ready" || event.type === "generation_completed") {
        const metric = event.data;
        for (const key of ["generation", "generation_limit", "population_requested", "population_actual", "generation_best_fitness", "best_ever_fitness", "average_fitness", "worst_fitness", "elapsed_ms", "accepted_new_chromosomes_total"]) {
          if (!Number.isFinite(metric[key])) throw new GAStreamError("Invalid GA progress metrics.");
        }
        if (metric.validation_status !== "passed" || metric.metrics_comparable !== true) throw new GAStreamError("GA metrics failed validation or comparability checks.");
      }
      onEvent?.(event as GAMonitoringEvent);
    }
    if (event.type === "log") onLog(event.message ?? event.data.message);
    if (event.type === "error") throw new GAStreamError(event.message ?? event.data.message, "FAILED");
    if (event.type === "result") {
      const value = event.data;
      if (!value || !Number.isFinite(value.best_fitness) || !Array.isArray(value.schedule) || !Array.isArray(value.history) || !value.fitness_breakdown || !Number.isInteger(value.generations_completed) || !Number.isInteger(value.population_size)) {
        throw new GAStreamError("Invalid GA result payload.");
      }
      result = value;
    }
    if (event.type === "done") {
      if (event.data?.status === "FAILED") throw new GAStreamError("GA execution failed.", "FAILED");
      if (event.data?.status === "STOPPED") {
        if (result ? result.status !== "STOPPED" || event.data.has_result === false : event.data.has_result !== false) {
          throw new GAStreamError("Stopped GA stream is missing its preserved result.");
        }
        terminal = true;
        return;
      }
      if (result?.status === "STOPPED") throw new GAStreamError("Stopped result received a contradictory terminal status.");
      if (!result) throw new GAStreamError("GA stream ended without a valid result.");
      terminal = true;
    }
  }
  function consume(eof = false) {
    while (!terminal) {
      const index = buffer.search(/[\r\n]/);
      if (index < 0 || (!eof && buffer[index] === "\r" && index === buffer.length - 1)) break;
      const line = buffer.slice(0, index);
      const width = buffer[index] === "\r" && buffer[index + 1] === "\n" ? 2 : 1;
      buffer = buffer.slice(index + width);
      if (line === "") dispatch(); else lines.push(line);
    }
    if (eof && !terminal) {
      if (buffer) lines.push(buffer);
      buffer = ""; dispatch();
    }
  }
  try {
    while (!terminal) {
      const chunk = await reader.read();
      buffer += decoder.decode(chunk.value, { stream: !chunk.done });
      consume(chunk.done);
      if (chunk.done) break;
    }
    if (!terminal) throw new GAStreamError("Live monitoring disconnected. The server may still be running; this did not stop the GA.");
    return result;
  } catch (error) {
    if (error instanceof GAStreamError) throw error;
    throw new GAStreamError("Live monitoring disconnected or received malformed data. The server may still be running; this did not stop the GA.");
  } finally {
    try { await reader.cancel(); } catch { /* Transport already closed. */ }
    reader.releaseLock();
  }
}
