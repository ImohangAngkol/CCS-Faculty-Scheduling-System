import { GAStreamError, readGAStream } from "./gaMonitoring";
import type { GAMonitoringEvent } from "./gaMonitoring";
import type { GARunState } from "./gaMonitoring";
import { controlError, GAControlError } from "./gaRecovery";
import type { BackendStatus, RunSnapshot } from "./gaRecovery";
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

  const response =
    await fetch(
      `${API_BASE_URL}/api/ga/latest`
    );

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      "Failed to restore the latest generated schedule."
    );
  }

  const payload =
    await response.json() as GARunResponse;

  return payload.data;
}


// Structured events extend the existing POST SSE contract.
export async function runGeneticAlgorithmStream(
  populationSize: number, generations: number, freshChromosomes: number,
  onLog: (message: string) => void, baselineMode: BaselineMode = "fresh",
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
  const response = await fetch(url, { method: "POST", headers: processInstanceId ? { "X-GA-Process-ID": processInstanceId } : {} });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.run_id !== runId || typeof body.accepted !== "boolean" || !["CREATED", "INITIALIZING", "RUNNING", "STOP_REQUESTED", "STOPPING", "STOPPED", "COMPLETED", "FAILED"].includes(body.state)) {
    throw new Error("Invalid stop acknowledgement. The server may still be running.");
  }
  return body;
}

export async function getGABackendStatus(): Promise<BackendStatus> {
  const url = `${API_BASE_URL}/api/ga/status`;
  const response = await fetch(url);
  const body = await response.json().catch(() => null);
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.control_version !== "3c.1" || typeof body.process_instance_id !== "string") {
    throw new GAControlError(`The backend at ${API_BASE_URL} does not advertise Phase 3C.1 control support. Restart the updated backend with one worker before starting another run.`, "GA_CONTROL_UNSUPPORTED", response.status);
  }
  return body;
}

export async function getGARunState(runId: string, processInstanceId: string): Promise<RunSnapshot> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}`;
  const response = await fetch(url, { headers: { "X-GA-Process-ID": processInstanceId } });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.run_id !== runId || body.process_instance_id !== processInstanceId || !["CREATED", "INITIALIZING", "RUNNING", "STOP_REQUESTED", "STOPPING", "STOPPED", "COMPLETED", "FAILED"].includes(body.state)) {
    throw new GAControlError("The backend returned a different run or process identity. No stop was acknowledged.", "GA_RUN_IDENTITY_MISMATCH", response.status);
  }
  return body;
}

export async function getGARunResult(runId: string): Promise<GARunData> {
  const url = `${API_BASE_URL}/api/ga/runs/${encodeURIComponent(runId)}/result`;
  const response = await fetch(url);
  const body = await response.json().catch(() => null);
  if (!response.ok) throw controlError(response.status, body, url);
  if (body?.data?.run_id !== runId || !["STOPPED", "COMPLETED"].includes(body.data.status)) throw new Error("Recovered result belongs to another run.");
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
