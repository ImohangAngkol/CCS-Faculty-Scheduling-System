import { test } from "node:test";
import assert from "node:assert/strict";
import { readGAStream, GAStreamError } from "../src/services/gaMonitoring.ts";

const metric = generation => ({ status: "RUNNING", generation, generation_limit: 3,
  population_requested: 10, population_actual: 8, generation_best_fitness: 100 - generation,
  best_ever_fitness: 100 - generation, average_fitness: 150, worst_fitness: 200,
  best_ever_improvement: generation ? 1 : 0, generations_without_improvement: 0,
  elapsed_ms: generation * 1000, generation_elapsed_ms: 1000,
  accepted_new_chromosomes_total: 8 + generation * 3, baseline_chromosomes: 0,
  fitness_evaluations_total: null, input_fingerprint: "inputs", configuration_fingerprint: "config",
  metrics_comparable: true, validation_status: "passed" });
const result = { best_fitness: 98, fitness_breakdown: {}, generations_completed: 2, population_size: 10, history: [], schedule: [] };
const event = (type, sequence, data) => ({ schema_version: 1, run_id: "run-1", sequence, type, timestamp: "2026-10-10T03:00:00Z", data });
function frames(events, newline = "\n") { return events.map(item => `data: ${JSON.stringify(item)}${newline}${newline}`).join(""); }
function source(text, chunk = 1) {
  const bytes = new TextEncoder().encode(text); let offset = 0, cancelled = false;
  return { get cancelled() { return cancelled; }, stream: new ReadableStream({
    pull(controller) { if (offset < bytes.length) { controller.enqueue(bytes.slice(offset, offset += chunk)); } else controller.close(); },
    cancel() { cancelled = true; },
  }) };
}
test("single-byte UTF-8 and CRLF chunks deliver progress before result and clean up", async () => {
  const logs = [], events = [];
  const input = source(frames([event("run_created", 1, {}), event("log", 2, { message: "Preparing… 教" }), event("initial_population_ready", 3, metric(0)), event("generation_completed", 4, metric(1)), event("result", 5, result), event("done", 6, { status: "COMPLETED" })], "\r\n"));
  assert.deepEqual(await readGAStream(input.stream, log => logs.push(log), item => events.push(item)), result);
  assert.deepEqual(logs, ["Preparing… 教"]);
  assert.deepEqual(events.map(item => item.type), ["run_created", "log", "initial_population_ready", "generation_completed", "result", "done"]);
  assert.equal(events[2].data.population_actual, 8);
  assert.equal(input.stream.locked, false); assert.equal(input.cancelled, true);
});
test("multiple events per chunk, heartbeat comments and multiline JSON", async () => {
  const text = ': heartbeat\r\n\r\nevent: result\r\ndata: {"type":"result",\r\ndata: "data":' + JSON.stringify(result) + '}\r\n\r\ndata: {"type":"done"}\r\n\r\n';
  assert.deepEqual(await readGAStream(source(text, 99999).stream, () => {}), result);
});
test("duplicate and stale sequences ignored; unknown events are forward compatible", async () => {
  const seen = [];
  const events = [event("initial_population_ready", 3, metric(0)), event("initial_population_ready", 3, metric(0)), event("generation_completed", 2, metric(1)), event("future", 4, {}), event("generation_completed", 5, metric(1)), event("result", 6, result), event("done", 7, { status: "COMPLETED" })];
  await readGAStream(source(frames(events), 99999).stream, () => {}, item => seen.push(item.sequence));
  assert.deepEqual(seen, [3, 5, 6, 7]);
});
test("premature EOF is disconnected, never stopped or completed", async () => {
  for (const events of [[event("run_started", 1, {})], [event("result", 1, result)]]) {
    const input = source(frames(events));
    await assert.rejects(readGAStream(input.stream, () => {}), error => error instanceof GAStreamError && error.status === "DISCONNECTED");
    assert.equal(input.stream.locked, false);
  }
});
test("explicit server error is failed and reader is cancelled", async () => {
  const input = source(frames([event("error", 1, { message: "Publication rejected", status: "FAILED" })]));
  await assert.rejects(readGAStream(input.stream, () => {}), error => error.status === "FAILED" && error.message === "Publication rejected");
  assert.equal(input.cancelled, true); assert.equal(input.stream.locked, false);
});
test("legacy log, result and done contracts remain supported", async () => {
  const logs = [];
  assert.deepEqual(await readGAStream(source(frames([{ type: "log", message: "legacy" }, { type: "result", data: result }, { type: "done" }])).stream, line => logs.push(line)), result);
  assert.deepEqual(logs, ["legacy"]);
});
test("invalid metrics, envelope, run identity and malformed data fail safely", async () => {
  for (const items of [
    [event("initial_population_ready", 1, { ...metric(0), average_fitness: null })],
    [event("initial_population_ready", 1, { ...metric(0), metrics_comparable: false })],
    [{ ...event("run_started", 1, {}), schema_version: 2 }],
    [event("run_started", 1, {}), { ...event("result", 2, result), run_id: "other" }],
    [event("done", 1, { status: "COMPLETED" })],
  ]) await assert.rejects(readGAStream(source(frames(items)).stream, () => {}), GAStreamError);
  await assert.rejects(readGAStream(source("data: broken\n\n").stream, () => {}), GAStreamError);
});
