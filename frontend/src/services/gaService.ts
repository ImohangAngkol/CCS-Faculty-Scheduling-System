import { GAStreamError, readGAStream, GA_RUN_STATES } from "./gaMonitoring";
import type { GAMonitoringEvent } from "./gaMonitoring";
import type { GARunState } from "./gaMonitoring";
import { validateRunLogs } from "./gaLogs";
import type { RunLogs } from "./gaLogs";
import { controlError, GAControlError, readGAJSON, readGAControlJSON } from "./gaRecovery";
import type { BackendStatus, RunSnapshot, CheckpointStatus } from "./gaRecovery";
import type {
  BaselineMode,
  GARunData,
  GARunResponse,
} from "../types/ga";


const API_BASE_URL =
  "http://127.0.0.1:8000";


// ============================================================
// NORMAL GA RUN
// ============================================================

export async function runGeneticAlgorithm(
  populationSize = 10,
  generations = 2,
  freshChromosomes = 2,
  baselineMode:
    BaselineMode = "fresh"
): Promise<{ status: string; data: GARunData | null }> {

  const params =
    new URLSearchParams({

      population_size:
        String(
          populationSize
        ),

      generations:
        String(
          generations
        ),

      fresh_chromosomes:
        String(
          freshChromosomes
        ),

      baseline_mode:
        baselineMode,

    });


  const response =
    await fetch(
      `${API_BASE_URL}/api/ga/run?${params}`,
      {
        method: "POST",
      }
    );


  if (!response.ok) {

    const errorBody =
      await response.text();


    throw new Error(
      `GA request failed: ` +
      `${response.status} ` +
      `${errorBody}`
    );

  }


  return response.json();
}


// ============================================================
// LATEST COMPLETED GA RESULT
// ============================================================

export async function getLatestGAResult():
  Promise<GARunData | null> {
  const {response, body} = await readGAJSON<GARunResponse>(`${API_BASE_URL}/api/ga/latest`, {}, 120000);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      "Failed to restore the latest generated schedule."
    );
  }

  return body?.data ?? null;
}


// Structured events extend the existing POST SSE contract.
export async function runGeneticAlgorithmStream(
  populationSize: number, generations: number, freshChromosomes: number,
  onLog: (message: string, event?: GAMonitoringEvent) => void, baselineMode: BaselineMode = "fresh",
  onEvent?: (event: GAMonitoringEvent) => void,
  processInstanceId?: string,
): Promise<GARunData | null> {
  const params = new URLSearchParams({ population_size: String(populationSize),
    generations: String(generations), fresh_chromosomes: String(freshChromosomes), baseline_mode: baselineMode });
  const response = await fetch(`${API_BASE_URL}/api/ga/stream?${params}`, {
    method: "POST", headers: { Accept: "text/event-stream", ...(processInstanceId ? { "X-GA-Process-ID": processInstanceId } : {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new GAStreamError(controlError(response.status, body, `${API_BASE_URL}/api/ga/stream`).message, "REJECTED");
  }
  if (!response.body) throw new GAStreamError("Live monitoring is unavailable. The server may still be running.");
  return readGAStream(response.body, onLog, onEvent);
}

export async function stopGARun(runId: string, processInstanceId?: string): Promise<{ run_id: string; state: GARunState; accepted: boolean }> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}/stop`;
  const {response, body} = await readGAControlJSON<{run_id:string;process_instance_id?:string;state:GARunState;accepted:boolean}>(url, { method: "POST", headers: processInstanceId ? { "X-GA-Process-ID": processInstanceId } : {} });
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.run_id !== runId || (processInstanceId !== undefined && body.process_instance_id !== undefined && body.process_instance_id !== processInstanceId)
      || typeof body.accepted !== "boolean" || !GA_RUN_STATES.includes(body.state)) {
    throw new Error("Invalid stop acknowledgement. The server may still be running.");
  }
  return body;
}

function validateSnapshot(snapshot: RunSnapshot, processId: string) {
  const invalid = () => new GAControlError("Run recovery returned incomplete metrics or a different backend identity. Check the backend instance on port 8000 and refresh to retry; no population was restarted.", "GA_RECOVERY_INVALID", 0);
  if (!snapshot || typeof snapshot.run_id !== "string" || snapshot.process_instance_id !== processId
      || ![...GA_RUN_STATES, "INTERRUPTED"].includes(snapshot.state)
      || typeof snapshot.execution_active !== "boolean" || !snapshot.configuration
      || !Number.isFinite(snapshot.elapsed_ms)) throw invalid();
  const history = snapshot.progress_history ?? [];
  if (!Array.isArray(history)) throw invalid();
  const metrics = [...history, ...(snapshot.latest_progress ? [snapshot.latest_progress] : [])];
  for (const point of metrics) {
    if (!point || point.validation_status !== "passed" || point.metrics_comparable !== true
        || ![point.generation, point.generation_limit, point.population_actual, point.population_requested,
          point.best_ever_fitness, point.generation_best_fitness, point.average_fitness,
          point.accepted_new_chromosomes_total].every(Number.isFinite)) throw invalid();
  }
  if (snapshot.state === "PAUSED" && (!snapshot.checkpoint || !history.length || !snapshot.latest_progress
      || snapshot.latest_completed_generation !== snapshot.latest_progress.generation
      || history.at(-1)?.generation !== snapshot.latest_completed_generation)) throw invalid();
}

export async function getGABackendStatus(): Promise<BackendStatus> {
  const url = `${API_BASE_URL}/api/ga/status`;
  const {response, body} = await readGAJSON<BackendStatus>(url);
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.control_version !== "3c.1" || typeof body.process_instance_id !== "string") {
    throw new GAControlError(`The backend at ${API_BASE_URL} does not advertise Phase 3C.1 control support. Restart the updated backend with one worker before starting another run.`, "GA_CONTROL_UNSUPPORTED", response.status);
  }
  if (body.active_run) validateSnapshot(body.active_run, body.process_instance_id);
  if (body.paused_runs !== undefined && !Array.isArray(body.paused_runs)) throw new GAControlError("Invalid paused-run discovery response. Refresh the correct backend to retry.", "GA_RECOVERY_INVALID", response.status);
  for (const run of body.paused_runs ?? []) validateSnapshot(run, body.process_instance_id);
  return body;
}

export async function getGARunState(runId: string, processInstanceId: string): Promise<RunSnapshot> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}`;
  const {response, body} = await readGAJSON<RunSnapshot>(url, { headers: { "X-GA-Process-ID": processInstanceId } });
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.run_id !== runId || body.process_instance_id !== processInstanceId || ![...GA_RUN_STATES, "INTERRUPTED"].includes(body.state)) {
    throw new GAControlError("The backend returned a different run or process identity. No stop was acknowledged.", "GA_RUN_IDENTITY_MISMATCH", response.status);
  }
  validateSnapshot(body, processInstanceId);
  return body;
}

export async function getGARunLogs(runId: string, processId: string, afterSequence: number): Promise<RunLogs> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}/logs?after_sequence=${afterSequence}`;
  const {response, body} = await readGAJSON<RunLogs>(url, {headers: {"X-GA-Process-ID": processId}});
  if (!response.ok) throw controlError(response.status, body, url);
  return validateRunLogs(body!, runId, processId);
}

export async function controlGARun(runId: string, processInstanceId: string, action: "pause" | "resume"): Promise<RunSnapshot & {accepted: boolean}> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}/${action}`;
  const {response, body} = await readGAControlJSON<RunSnapshot & {state:GARunState;accepted:boolean}>(url, {method:"POST", headers:{"X-GA-Process-ID":processInstanceId}});
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.run_id !== runId || body.process_instance_id !== processInstanceId
      || typeof body.accepted !== "boolean" || !GA_RUN_STATES.includes(body.state)) throw new Error("Invalid GA control acknowledgement.");
  return body;
}

export async function getGACheckpointStatus(runId: string, processInstanceId: string): Promise<CheckpointStatus> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}/checkpoint-status`;
  const {response, body} = await readGAJSON<CheckpointStatus>(url, { headers: { "X-GA-Process-ID": processInstanceId } }, 120000);
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.run_id !== runId || body.process_instance_id !== processInstanceId
      || ![...GA_RUN_STATES, "INTERRUPTED"].includes(body.state) || typeof body.resumable !== "boolean") {
    throw new GAControlError("The checkpoint response could not be validated; resume is unavailable.", "GA_CHECKPOINT_STATUS_INVALID", response.status);
  }
  return body;
}

export async function getGARunResult(runId: string): Promise<GARunData> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}/result`;
  const {response, body} = await readGAJSON<{data: GARunData}>(url, {}, 120000);
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.data?.run_id !== runId || !["STOPPED", "COMPLETED"].includes(String(body.data.status))) throw new Error("Recovered result belongs to another run.");
  return body.data;
}


// ============================================================
// UPLOAD CHROMOSOME
// ============================================================

export async function uploadBaselineChromosome(
  payload: unknown
) {

  const response =
    await fetch(
      `${API_BASE_URL}/api/chromosomes/upload`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body:
          JSON.stringify(
            payload
          ),
      }
    );


  if (!response.ok) {

    const error =
      await response
        .json()
        .catch(
          () => null
        );


    throw new Error(
      error?.detail ??
      "Failed to upload chromosome."
    );

  }


  return response.json();
}


// ============================================================
// SAVED BEST STATUS
// ============================================================

export async function getSavedBestStatus() {

  const response =
    await fetch(
      `${API_BASE_URL}/api/chromosomes/best`
    );


  if (!response.ok) {

    throw new Error(
      "Failed to check saved best chromosome."
    );

  }


  return response.json();
}


// ============================================================
// SAVED BEST DOWNLOAD
// ============================================================

export function getSavedBestDownloadUrl() {

  return (
    `${API_BASE_URL}` +
    `/api/chromosomes/best/download`
  );

}


// ============================================================
// ANALYZE SAVED BEST ONLY
//
// DOES NOT RUN GENETIC ALGORITHM
// ============================================================

export async function analyzeSavedBestChromosome():
  Promise<GARunResponse> {

  const response =
    await fetch(
      `${API_BASE_URL}/api/chromosomes/best/analyze`,
      {
        method: "POST",
      }
    );


  if (!response.ok) {

    const error =
      await response
        .json()
        .catch(
          () => null
        );


    throw new Error(
      error?.detail ??
      "Failed to analyze saved chromosome."
    );

  }


  return response.json();
}


// ============================================================
// ANALYZE UPLOADED CHROMOSOME ONLY
//
// DOES NOT RUN GENETIC ALGORITHM
// ============================================================

export async function analyzeUploadedChromosome():
  Promise<GARunResponse> {

  const response =
    await fetch(
      `${API_BASE_URL}/api/chromosomes/uploaded/analyze`,
      {
        method: "POST",
      }
    );


  if (!response.ok) {

    const error =
      await response
        .json()
        .catch(
          () => null
        );


    throw new Error(
      error?.detail ??
      "Failed to analyze uploaded chromosome."
    );

  }


  return response.json();
}
