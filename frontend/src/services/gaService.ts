import type {
  GARunData,
  GARunResponse,
} from "../types/ga";


const API_BASE_URL =
  "http://127.0.0.1:8000";


// ============================================================
// NORMAL GA REQUEST
//
// Keep this because other parts of the frontend may use it.
// ============================================================

export async function runGeneticAlgorithm(
  populationSize = 10,
  generations = 2,
  freshChromosomes = 2
): Promise<GARunResponse> {

  const params =
    new URLSearchParams({
      population_size:
        String(populationSize),

      generations:
        String(generations),

      fresh_chromosomes:
        String(freshChromosomes),
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
// LIVE STREAMING GA REQUEST
// ============================================================

export async function runGeneticAlgorithmStream(
  populationSize: number,
  generations: number,
  freshChromosomes: number,
  onLog: (message: string) => void
): Promise<GARunData> {

  const params =
    new URLSearchParams({
      population_size:
        String(populationSize),

      generations:
        String(generations),

      fresh_chromosomes:
        String(freshChromosomes),
    });


  const response =
    await fetch(
      `${API_BASE_URL}/api/ga/stream?${params}`,
      {
        method: "POST",

        headers: {
          Accept: "text/event-stream",
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


  // ==========================================================
  // PROCESS ONE SSE EVENT
  // ==========================================================

  function processEvent(
    eventBlock: string
  ) {

    const lines =
      eventBlock.split("\n");


    const dataLines =
      lines.filter(
        (line) =>
          line.startsWith("data:")
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


    if (event.type === "log") {

      onLog(
        event.message
      );

      return;
    }


    if (
      event.type === "result"
    ) {

      finalResult =
        event.data;

      return;
    }


    if (
      event.type === "error"
    ) {

      throw new Error(
        event.message
      );
    }

  }


  // ==========================================================
  // READ STREAM
  // ==========================================================

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


    // SSE events are separated by a blank line.
    let boundary =
      buffer.indexOf("\n\n");


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


  // Process any remaining data.
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