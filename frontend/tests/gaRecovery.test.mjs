import { test } from "node:test";
import assert from "node:assert/strict";
import { controlError, readRunReference, RUN_REFERENCE_KEY } from "../src/services/gaRecovery.ts";

test("refresh remembers only a server run/process reference, not a population", () => {
  const reference = {run_id:"server-run",process_instance_id:"server-process"};
  assert.deepEqual(readRunReference({getItem: key => key === RUN_REFERENCE_KEY ? JSON.stringify(reference) : null}), reference);
  for (const value of [null, "broken", '{}', '{"run_id":3}', '{"run_id":"old"}']) assert.equal(readRunReference({getItem: () => value}), null);
});
test("missing route Not Found explains a stale or wrong backend, never cancellation", () => {
  const error = controlError(404, {detail:"Not Found"}, "http://127.0.0.1:8000/api/ga/runs/server-run/stop");
  assert.equal(error.code, "GA_CONTROL_ROUTE_MISSING");
  assert.match(error.message, /endpoint is missing/);
  assert.match(error.message, /Restart the correct backend/);
  assert.match(error.message, /No stop was acknowledged/);
});
test("unknown run and changed process remain distinguishable", () => {
  for (const [httpStatus, code] of [[404,"GA_UNKNOWN_RUN"], [409,"GA_PROCESS_CHANGED"]]) {
    const error = controlError(httpStatus, {detail:{code,message:"The current process does not own this run; no cancellation occurred."}}, "control-url");
    assert.equal(error.code, code);
    assert.equal(error.httpStatus, httpStatus);
    assert.match(error.message, /no cancellation occurred/);
  }
});
test("unreadable control responses include URL and status", () => {
  const error = controlError(500, null, "control-url");
  assert.match(error.message, /500/);
  assert.match(error.message, /control-url/);
  assert.match(error.message, /no stop was acknowledged/);
});
