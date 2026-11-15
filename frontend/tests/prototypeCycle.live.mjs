// Genuine TCP/FastAPI/SQLite and recorded original GA; not browser acceptance.
import assert from 'node:assert/strict';
import {createHash, randomUUID} from 'node:crypto';
import {generatedView, decisionFor} from '../src/prototypeCycle/model.mjs';
let wire = ''; for await (const part of process.stdin) wire += part;
const input = JSON.parse(wire);
assert.equal(new URL(input.base).hostname, '127.0.0.1');
let cookie = '', csrf = '';
const scenarios = [], exports = {};
async function request(path, body, secure = true) {
  return fetch(input.base+path, {method: body ? 'POST' : 'GET', signal: AbortSignal.timeout(10000),
    headers: {Origin: input.base, 'Content-Type': 'application/json', ...(cookie ? {Cookie: cookie} : {}),
      ...(secure && csrf ? {'X-CSRF-Token': csrf} : {})}, body: body ? JSON.stringify(body) : undefined});
}
async function get(path) { const response = await request(path); assert.equal(response.status, 200); return response.json(); }
async function check(name, action) { await action(); scenarios.push({name, status: 'PASS'}); }
async function login(name) {
  const response = await request('/api/auth/login', {username: name+'@fictional.invalid', password: input.password});
  assert.equal(response.status, 200); cookie = response.headers.get('set-cookie').split(';')[0]; csrf = (await response.json()).csrf_token;
}
try {
  await check('anonymous recorded-run access denied', async () => assert.equal((await request('/api/prototype/cycle/runs')).status, 401));
  await check('real scheduler login', () => login('scheduler'));
  let run;
  await check('genuinely generated assignments match durable original result exactly', async () => {
    run = await get('/api/prototype/cycle/runs/'+input.first); assert.deepEqual(run.result, input.expected);
    const view = generatedView(run); assert.equal(view.fitness, input.expected.original_result.best_fitness);
    assert.equal(view.feasible, true); assert.equal(run.native_verified, false);
  });
  await check('same frozen context comparison preserves minimization and ties', async () => {
    const result = await get('/api/prototype/cycle/compare/'+input.first+'/'+input.second);
    assert.equal(result.classification, 'SAME_FROZEN_EVALUATION'); assert.equal(result.tie, true); assert.equal(result.best_saved, false);
  });
  await check('original research history JSON export exact', async () => {
    const response = await request('/api/prototype/cycle/runs/'+input.first+'/export/json');
    assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual((await response.json()).result, input.expected);
  });
  await check('original research CSV and text downloads real and bounded', async () => {
    for (const kind of ['csv', 'txt']) {
      const response = await request('/api/prototype/cycle/runs/'+input.first+'/export/'+kind);
      assert.equal(response.status, 200); assert.match(response.headers.get('content-disposition'), /attachment/);
      const raw = await response.text(); assert.ok(raw.includes(input.first)); assert.ok(Buffer.byteLength(raw) <= 256*1024);
      exports[kind] = createHash('sha256').update(raw).digest('hex');
    }
  });
  if (!input.reopened) {
    const body = decisionFor(run, 'APPROVE', 'Fictional Chair reviewed the generated assignments and workload.', randomUUID());
    await check('scheduler cannot grant own Chair approval', async () => assert.equal((await request('/api/prototype/cycle/runs/'+input.first+'/decision', body)).status, 403));
    await login('faculty');
    await check('no timetable fabricated before prototype approval', async () => assert.equal((await get('/api/prototype/cycle/timetable/2')).state, 'NO_APPROVED_PROTOTYPE_SCHEDULE'));
    await check('cross-faculty timetable denied', async () => assert.equal((await request('/api/prototype/cycle/timetable/1')).status, 403));
    await login('chair');
    await check('Chair decision requires real CSRF', async () => assert.equal((await request('/api/prototype/cycle/runs/'+input.first+'/decision', body, false)).status, 403));
    await check('real Chair approval creates immutable prototype version', async () => {
      const response = await request('/api/prototype/cycle/runs/'+input.first+'/decision', body); assert.equal(response.status, 200);
      assert.equal((await response.json()).institutional_approval, false);
      const versions = await get('/api/prototype/cycle/versions'); assert.equal(versions.length, 1);
      assert.deepEqual(versions[0].candidate, input.expected); assert.equal(versions[0].institutional_publication, false);
    });
    await check('stale duplicate decision cannot overwrite approved version', async () => {
      const response = await request('/api/prototype/cycle/runs/'+input.first+'/decision', {...body, request_id: randomUUID(), decision: 'REJECT'});
      assert.equal(response.status, 409); assert.equal((await get('/api/prototype/cycle/versions')).length, 1);
    });
    await check('revision request records history without fabricating a revised assignment', async () => {
      const second = await get('/api/prototype/cycle/runs/'+input.second);
      const response = await request('/api/prototype/cycle/runs/'+input.second+'/decision', decisionFor(second, 'REQUEST_REVISION', 'Please submit a new independently generated fictional revision.', randomUUID()));
      assert.equal(response.status, 200); assert.equal((await response.json()).decision, 'REQUEST_REVISION');
    });
  }
  await login('chair');
  await check('approved prototype JSON CSV and text exported from recorded version', async () => {
    for (const kind of ['json', 'csv', 'txt']) {
      const response = await request('/api/prototype/cycle/versions/1/export/'+kind); assert.equal(response.status, 200);
      const raw = await response.text(); assert.ok(raw.includes(input.first));
      exports['approved_'+kind] = createHash('sha256').update(raw).digest('hex');
    }
  });
  await login('faculty');
  await check(input.reopened ? 'listener restart preserves approved timetable and workload' : 'faculty refresh reads applied prototype version', async () => {
    const timetable = await get('/api/prototype/cycle/timetable/2'); assert.equal(timetable.version, 1);
    assert.equal(timetable.workload.assigned_units, 3); assert.ok(timetable.schedule.length > 0);
    assert.ok(timetable.schedule.every(row => row.faculty === '2')); assert.equal(timetable.institutional_promotion, false);
  });
  await check('real review frontend assets served', async () => {
    assert.equal((await request('/prototype/cycle')).status, 200);
    assert.match(await (await request('/prototype/cycle/console.mjs')).text(), /decisionFor/);
  });
  await check('logout revokes actual session', async () => {
    assert.equal((await request('/api/auth/logout', {})).status, 204); assert.equal((await request('/api/prototype/cycle/runs')).status, 401);
  });
  await login('unscoped');
  await check('unscoped admin cannot read approved research realm', async () => assert.equal((await request('/api/prototype/cycle/versions')).status, 403));
  console.log(JSON.stringify({scope: 'REAL_NODE_HTTP_FRONTEND_MODEL_GENUINE_RECORDED_GA_NO_BROWSER_NO_NATIVE', reopened: input.reopened, scenarios,
    export_sha256: exports, actual_original_fitness: input.expected.original_result.best_fitness, mocked_HTTP_responses: 0}));
} catch (error) { console.error('Cycle HTTP acceptance failed: '+error.message); process.exitCode = 1; }
finally { input.password = ''; cookie = ''; csrf = ''; }
