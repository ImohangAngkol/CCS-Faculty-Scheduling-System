import type { GARunState, GenerationMetrics } from "./gaMonitoring";

export type RunReference = { run_id: string; process_instance_id: string };
export type RunSnapshot = RunReference & {
  state: GARunState; execution_active: boolean; accepting_stop: boolean;
  configuration: { population_size?: number; generations?: number; fresh_chromosomes?: number };
  latest_progress: GenerationMetrics | null; latest_completed_generation: number | null;
  elapsed_ms: number; terminal_error: string | null; result_reference: string | null;
};
export type BackendStatus = {
  control_version: "3c.1"; process_instance_id: string; active_run: RunSnapshot | null;
};
export const RUN_REFERENCE_KEY = "ga.active-run.v1";

export function readRunReference(storage: Pick<Storage, "getItem">): RunReference | null {
  try {
    const value = JSON.parse(storage.getItem(RUN_REFERENCE_KEY) ?? "null");
    return value && typeof value.run_id === "string" && typeof value.process_instance_id === "string" ? value : null;
  } catch { return null; }
}

export class GAControlError extends Error {
  code: string;
  httpStatus: number;
  constructor(message: string, code: string, httpStatus: number) {
    super(message); this.name = "GAControlError"; this.code = code; this.httpStatus = httpStatus;
  }
}

export function controlError(httpStatus: number, body: unknown, url: string): GAControlError {
  const detail = (body as { detail?: string | { code?: string; message?: string } } | null)?.detail;
  if (httpStatus === 404 && (detail === "Not Found" || !detail)) {
    return new GAControlError(`The GA control endpoint is missing at ${url}. The running backend lacks this route. Restart the correct backend with one worker. No stop was acknowledged.`, "GA_CONTROL_ROUTE_MISSING", 404);
  }
  const message = typeof detail === "string" ? detail : detail?.message;
  const code = typeof detail === "object" ? detail?.code : undefined;
  return new GAControlError(message ?? `GA control request failed (${httpStatus}) at ${url}; no stop was acknowledged.`, code ?? "GA_CONTROL_REQUEST_FAILED", httpStatus);
}
