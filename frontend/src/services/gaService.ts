import { GAStreamError, readGAStream } from "./gaMonitoring";
import type { GAMonitoringEvent } from "./gaMonitoring";
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
): Promise<GARunResponse> {

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
): Promise<GARunData> {
  const params = new URLSearchParams({ population_size: String(populationSize),
    generations: String(generations), fresh_chromosomes: String(freshChromosomes), baseline_mode: baselineMode });
  const response = await fetch(`${API_BASE_URL}/api/ga/stream?${params}`, {
    method: "POST", headers: { Accept: "text/event-stream" },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new GAStreamError(body?.detail ?? `GA execution request rejected (${response.status}).`, "REJECTED");
  }
  if (!response.body) throw new GAStreamError("Live monitoring is unavailable. The server may still be running.");
  return readGAStream(response.body, onLog, onEvent);
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