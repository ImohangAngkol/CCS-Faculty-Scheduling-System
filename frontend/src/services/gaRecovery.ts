import type { GARunState, GenerationMetrics } from "./gaMonitoring";

export type RunReference = { run_id: string; process_instance_id: string };
export type CheckpointStatus = RunReference & {
  state: GARunState | "INTERRUPTED"; resumable: boolean; error?: string; code?: string;
};
export type RunSnapshot = RunReference & {
  state: GARunState | "INTERRUPTED"; execution_active: boolean; accepting_stop: boolean;
  accepting_pause?: boolean; accepting_resume?: boolean; checkpoint?: string | null;
  progress_history?: GenerationMetrics[];
  checkpoint_status?: CheckpointStatus;
  configuration: { population_size?: number; generations?: number; fresh_chromosomes?: number };
  latest_progress: GenerationMetrics | null; latest_completed_generation: number | null;
  elapsed_ms: number; terminal_error: string | null; result_reference: string | null;
};
export type BackendStatus = {
  control_version: "3c.1"; process_instance_id: string; active_run: RunSnapshot | null;
  pause_resume_version?: "3d.1"; paused_runs?: RunSnapshot[];
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

// Bound the request and JSON body reading, even if a transport ignores abort.
// Aborting a read never controls the GA worker.
export async function readGAJSON<T>(url: string, options: RequestInit = {}, timeoutMs = 10000): Promise<{response: Response; body: T | null}> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      (async () => {
        const response = await fetch(url, {...options, signal: controller.signal});
        const body = await response.json().catch(() => null) as T | null;
        return {response, body};
      })(),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => {
          reject(new GAControlError(`Recovery request timed out at ${url}. Check that the updated backend is running on port 8000 with one worker, then refresh to retry. No run was restarted or cancelled.`, "GA_RECOVERY_TIMEOUT", 0));
          controller.abort();
        }, timeoutMs);
      }),
    ]);
  } catch (reason) {
    if (reason instanceof GAControlError) throw reason;
    throw new GAControlError(`Recovery request failed at ${url}. ${reason instanceof Error ? reason.message : "Backend unavailable."} Check the backend on port 8000 and refresh to retry. No run was restarted or cancelled.`, "GA_RECOVERY_UNAVAILABLE", 0);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

// A timed-out POST has an unknown outcome: aborting its HTTP connection does
// not undo a server-side control action. Reconcile status rather than retrying.
export async function readGAControlJSON<T>(url: string, options: RequestInit, timeoutMs = 120000): Promise<{response: Response; body: T | null}> {
  try {
    return await readGAJSON<T>(url, options, timeoutMs);
  } catch (reason) {
    if (!(reason instanceof GAControlError)) throw reason;
    const timedOut = reason.code === "GA_RECOVERY_TIMEOUT";
    throw new GAControlError(`GA control acknowledgement ${timedOut ? "timed out" : "was unavailable"} at ${url}. The request may have reached the backend; its outcome is unknown. Check authoritative run status before retrying. Closing this request does not cancel the worker.`, timedOut ? "GA_CONTROL_ACK_TIMEOUT" : "GA_CONTROL_ACK_UNAVAILABLE", reason.httpStatus);
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
