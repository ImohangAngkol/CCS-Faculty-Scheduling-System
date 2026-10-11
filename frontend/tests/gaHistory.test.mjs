import {test} from "node:test";
import assert from "node:assert/strict";
import {runPath, validateHistory, improvementLabel, getHistoryGenerations, compareGenerations, getHistoricalSchedule, getHistoricalAnalysis} from "../src/services/gaHistory.ts";

const id = "00000000-0000-4000-8000-000000000001";
test("history paths reject unsafe identities", () => {
  assert.ok(runPath(id).endsWith(id));
  for (const value of ["../private", "run-id", id.toUpperCase().replace("00000001", "abcdefAB")]) assert.throws(() => runPath(value));
});
test("invalid URL run identity rejects asynchronously so recovery settles into an error", async () => {
  await assert.rejects(getHistoryGenerations("../private"), /Invalid historical run identity/);
});
test("history contracts reject wrong schemas, runs and generations", () => {
  assert.equal(validateHistory({schema_version: 1, run_id: id, generation: 4}, id, 4).generation, 4);
  assert.throws(() => validateHistory({schema_version: 2, run_id: id}, id));
  assert.throws(() => validateHistory({schema_version: 1, run_id: "another"}, id));
  assert.throws(() => validateHistory({schema_version: 1, run_id: id, generation: 0}, id, 4));
});
test("penalty reduction is positive, deterioration negative, equal unchanged", () => {
  assert.match(improvementLabel(10), /lower.*improved/);
  assert.match(improvementLabel(-5), /higher.*worse/);
  assert.equal(improvementLabel(0), "Unchanged");
});
test("inspection and comparison issue GET only and preserve server data", async () => {
  const before = globalThis.fetch, requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({url, options});
    return Response.json({schema_version: 1, run_id: id, generation: 4, run: {run_id: id}, items: [], total: 5});
  };
  try {
    const page = await getHistoryGenerations(id, 50);
    assert.equal(page.total, 5);
    await getHistoricalSchedule(id, 4, "best_ever");
    await compareGenerations(id, 1, 4, "generation_best");
    assert.ok(requests.every(request => !request.options.method));
    assert.ok(requests[0].url.endsWith("offset=50&limit=50"));
    assert.ok(requests[1].url.endsWith("candidate=best_ever"));
  } finally {globalThis.fetch = before;}
});
test("history API reports specific validation errors", async () => {
  const before = globalThis.fetch;
  globalThis.fetch = async () => Response.json({detail: {message: "Original inputs are unavailable."}}, {status: 409});
  try {await assert.rejects(getHistoricalSchedule(id, 4, "generation_best"), /Original inputs/);}
  finally {globalThis.fetch = before;}
});

test("history distinguishes unavailable backend, timeout, incompatible inputs and corrupt history", async () => {
  const before = globalThis.fetch;
  try {
    for (const [code, status] of [["GA_HISTORY_CORRUPT",422],["GA_HISTORY_INPUT_CHANGED",409]]) {
      globalThis.fetch = async () => Response.json({detail:{code,message:"Validation rejected"}}, {status});
      await assert.rejects(getHistoricalAnalysis(id,0,"generation_best"), error => error.code===code && error.httpStatus===status && error.message.includes("Fitness analysis:"));
    }
    globalThis.fetch = async () => {throw new TypeError("Failed to fetch");};
    await assert.rejects(getHistoricalSchedule(id,0,"generation_best"), error=>error.code==="GA_HISTORY_UNAVAILABLE");
    globalThis.fetch = async () => {throw new DOMException("Timed out", "TimeoutError");};
    await assert.rejects(getHistoricalSchedule(id,0,"generation_best"), error=>error.code==="GA_HISTORY_TIMEOUT");
    globalThis.fetch = async () => new Response("not JSON");
    await assert.rejects(getHistoricalSchedule(id,0,"generation_best"), error=>error.code==="GA_HISTORY_RESPONSE_INVALID");
  } finally {globalThis.fetch=before;}
});

test("a stalled history JSON body settles into a timeout without reporting corruption", async () => {
  const beforeFetch=globalThis.fetch, beforeTimeout=globalThis.setTimeout;
  let signal;
  globalThis.setTimeout=(callback,delay,...args)=>beforeTimeout(callback,delay===30000?25:delay,...args);
  globalThis.fetch=async (_url,options)=>{
    signal=options.signal;
    return {ok:true,status:200,json:()=>new Promise(()=>{})};
  };
  try {
    await assert.rejects(getHistoricalAnalysis(id,0,"generation_best"), error=>error.code==="GA_HISTORY_TIMEOUT" && error.message.includes("Fitness analysis:"));
    assert.equal(signal.aborted,true);
  } finally {globalThis.fetch=beforeFetch;globalThis.setTimeout=beforeTimeout;}
});
