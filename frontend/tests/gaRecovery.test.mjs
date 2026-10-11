import { test } from "node:test";
import assert from "node:assert/strict";
import { controlError, readRunReference, RUN_REFERENCE_KEY, readGAJSON, readGAControlJSON } from "../src/services/gaRecovery.ts";

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

test("recovery timeout bounds a stalled request and aborts only its read", async () => {
  const original = globalThis.fetch;
  let signal;
  globalThis.fetch = async (_url, options) => { signal=options.signal; return new Promise(() => {}); };
  try {
    await assert.rejects(readGAJSON('http://127.0.0.1:8000/api/ga/status', {}, 20), error => error.code==='GA_RECOVERY_TIMEOUT' && /refresh to retry/.test(error.message));
    assert.equal(signal.aborted, true);
  } finally { globalThis.fetch=original; }
});

test("recovery timeout also bounds a stalled JSON response body", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => ({json:async () => new Promise(() => {})});
  try {
    await assert.rejects(readGAJSON('checkpoint-status', {}, 20), error => error.code==='GA_RECOVERY_TIMEOUT');
  } finally { globalThis.fetch=original; }
});

test("unavailable backend errors identify the endpoint without claiming checkpoint loss", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
  try {
    await assert.rejects(readGAJSON('http://127.0.0.1:8000/api/ga/status'), error => error.code==='GA_RECOVERY_UNAVAILABLE' && /port 8000/.test(error.message) && /No run was restarted or cancelled/.test(error.message));
  } finally { globalThis.fetch=original; }
});

test("a control timeout has an unknown outcome and must never claim the worker was cancelled", async () => {
  const original = globalThis.fetch;
  let signal, calls = 0;
  globalThis.fetch = async (_url, options) => { calls++; signal=options.signal; return new Promise(() => {}); };
  try {
    await assert.rejects(readGAControlJSON('stop-url', {method:'POST'}, 20), error => error.code==='GA_CONTROL_ACK_TIMEOUT' && /outcome is unknown/.test(error.message) && /does not cancel the worker/.test(error.message));
    assert.equal(signal.aborted, true);
    assert.equal(calls, 1);
  } finally { globalThis.fetch=original; }
});

test("a lost control connection requests authoritative reconciliation without retrying the POST", async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw new TypeError('Lost acknowledgement'); };
  try {
    await assert.rejects(readGAControlJSON('resume-url', {method:'POST'}), error => error.code==='GA_CONTROL_ACK_UNAVAILABLE' && /Check authoritative run status/.test(error.message));
    assert.equal(calls, 1);
  } finally { globalThis.fetch=original; }
});
