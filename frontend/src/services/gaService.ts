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
// STREAM EVENT TYPES
// ============================================================

type GALogEvent = {
  type: "log";
  message: string;
};


type GAResultEvent = {
  type: "result";
  data: GARunData;
};


type GAErrorEvent = {
  type: "error";
  message: string;
};


type GADoneEvent = {
  type: "done";
};


type GAStreamEvent =
  | GALogEvent
  | GAResultEvent
  | GAErrorEvent
  | GADoneEvent;


// ============================================================
// LIVE GA STREAM
// ============================================================

export async function runGeneticAlgorithmStream(
  populationSize: number,
  generations: number,
  freshChromosomes: number,
  onLog:
    (message: string) => void,
  baselineMode:
    BaselineMode = "fresh"
): Promise<GARunData> {

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
      `${API_BASE_URL}/api/ga/stream?${params}`,
      {
        method: "POST",

        headers: {
          Accept:
            "text/event-stream",
        },
      }
    );


  if (!response.ok) {

    const errorBody =
      await response.text();


    throw new Error(
      `GA streaming request failed: ` +
      `${response.status} ` +
      `${errorBody}`
    );

  }


  if (!response.body) {

    throw new Error(
      "The backend did not return a readable stream."
    );

  }


  const reader =
    response.body.getReader();


  const decoder =
    new TextDecoder();


  let buffer = "";


  let finalResult:
    GARunData | null = null;


  function processEvent(
    eventBlock: string
  ) {

    const lines =
      eventBlock.split("\n");


    const dataLines =
      lines.filter(
        (line) =>
          line.startsWith(
            "data:"
          )
      );


    if (
      dataLines.length === 0
    ) {
      return;
    }


    const jsonText =
      dataLines
        .map(
          (line) =>
            line
              .slice(5)
              .trim()
        )
        .join("");


    if (!jsonText) {
      return;
    }


    const event =
      JSON.parse(
        jsonText
      ) as GAStreamEvent;


    if (
      event.type ===
      "log"
    ) {

      onLog(
        event.message
      );

      return;

    }


    if (
      event.type ===
      "result"
    ) {

      finalResult =
        event.data;

      return;

    }


    if (
      event.type ===
      "error"
    ) {

      throw new Error(
        event.message
      );

    }

  }


  while (true) {

    const {
      value,
      done,
    } =
      await reader.read();


    if (value) {

      buffer +=
        decoder.decode(
          value,
          {
            stream: true,
          }
        );

    }


    let boundary =
      buffer.indexOf(
        "\n\n"
      );


    while (
      boundary !== -1
    ) {

      const eventBlock =
        buffer.slice(
          0,
          boundary
        );


      buffer =
        buffer.slice(
          boundary + 2
        );


      processEvent(
        eventBlock
      );


      boundary =
        buffer.indexOf(
          "\n\n"
        );

    }


    if (done) {
      break;
    }

  }


  if (
    buffer.trim()
  ) {

    processEvent(
      buffer
    );

  }


  if (!finalResult) {

    throw new Error(
      "GA stream ended without returning a result."
    );

  }


  return finalResult;
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