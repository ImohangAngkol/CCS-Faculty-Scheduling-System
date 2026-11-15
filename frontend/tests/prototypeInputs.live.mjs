// Real Node TCP + frontend model; no browser and no intercepted HTTP.
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {weightCommand, freezeCommand} from '../src/prototypeInputs/model.mjs';
let wire = ''; for await (const chunk of process.stdin) wire += chunk;
const input = JSON.parse(wire);
assert.equal(new URL(input.base).hostname, '127.0.0.1');
let cookie = '', csrf = '', prepared = input.previous?.prepared ?? null;
const scenarios = [];
async function request(path, method = 'GET', body, secure = true) {
  return fetch(input.base+path, {method, signal: AbortSignal.timeout(10000),
    headers: {Origin: input.base, 'Content-Type': 'application/json', ...(cookie ? {Cookie: cookie} : {}),
      ...(secure && csrf ? {'X-CSRF-Token': csrf} : {})}, body: body === undefined ? undefined : JSON.stringify(body)});
}
async function check(name, action) { await action(); scenarios.push({name, status: 'PASS'}); }
async function login(name) {
  const reply = await request('/api/auth/login', 'POST', {username: name+'@fictional.invalid', password: input.password});
  assert.equal(reply.status, 200); cookie = reply.headers.get('set-cookie').split(';')[0]; csrf = (await reply.json()).csrf_token;
}
async function get(path) { const reply = await request(path); assert.equal(reply.status, 200); return reply.json(); }
try {
  await check('anonymous denied', async () => assert.equal((await request('/api/prototype/inputs/weights')).status, 401));
  await check('real faculty login', () => login('faculty'));
  let pref;
  await check('own preference revision readable', async () => { pref = await get('/api/prototype/inputs/preferences/2'); assert.equal(pref.preference.revision, input.reopened ? 1 : 0); });
  await check('cross faculty read denied', async () => assert.equal((await request('/api/prototype/inputs/preferences/1')).status, 403));
  let weights = await get('/api/prototype/inputs/weights');
  const command = weightCommand(weights, '{"subject_penalty":140}', randomUUID());
  await check('faculty cannot approve Chair coefficients', async () => assert.equal((await request('/api/prototype/inputs/weights/approve', 'POST', command)).status, 403));
  if (!input.reopened) {
    const change = {request_id: randomUUID(), expected_revision: 0, preference: {faculty_priority: 1, preferred_subjects: ['SYN-WA'],
      use_subject_preference: true, subject_importance: 5, use_day_preference: false, use_time_preference: false}};
    await check('CSRF rejects preference write', async () => assert.equal((await request('/api/prototype/inputs/preferences/2', 'PUT', change, false)).status, 403));
    await check('real preference save', async () => assert.equal((await request('/api/prototype/inputs/preferences/2', 'PUT', change)).status, 200));
    await check('saved preference reload', async () => assert.equal((await get('/api/prototype/inputs/preferences/2')).preference.revision, 1));
    await check('real Chair login', () => login('chair'));
    await check('Chair approves supported coefficient', async () => {
      const reply = await request('/api/prototype/inputs/weights/approve', 'POST', command); assert.equal(reply.status, 200);
      assert.equal((await reply.json()).revision, 1);
    });
    await check('Chair account alone does not grant scheduling action', async () => assert.equal((await request('/api/prototype/inputs/selection')).status, 403));
    await check('real scheduler login', () => login('scheduler'));
    let selection;
    await check('server selection pins preferences and weight revision', async () => { selection = await get('/api/prototype/inputs/selection'); assert.equal(selection.weights_revision, 1); });
    await check('real immutable preparation persisted', async () => {
      const reply = await request('/api/prototype/inputs/prepare', 'POST', freezeCommand(selection, randomUUID()));
      assert.equal(reply.status, 200); assert.equal(reply.headers.get('cache-control'), 'no-store'); prepared = await reply.json();
      assert.equal(prepared.optimizer_consumption, 'NOT_ESTABLISHED'); assert.equal(prepared.worker_started, false);
    });
    await check('preparation reload exact', async () => assert.deepEqual(await get('/api/prototype/inputs/prepared/'+prepared.preparation_id), prepared));
    await check('client authority fields rejected', async () => assert.equal((await request('/api/prototype/inputs/prepare', 'POST', {...freezeCommand(selection, randomUUID()), role: 'chair'})).status, 422));
    await login('chair'); weights = await get('/api/prototype/inputs/weights');
    await check('later coefficient revision preserves old preparation', async () => {
      assert.equal((await request('/api/prototype/inputs/weights/approve', 'POST', weightCommand(weights, '{"subject_penalty":210}', randomUUID()))).status, 200);
      await login('scheduler'); assert.deepEqual(await get('/api/prototype/inputs/prepared/'+prepared.preparation_id), prepared);
    });
  } else {
    await check('listener restart preserves new weight policy', async () => assert.equal(weights.policy.revision, 2));
    await login('scheduler');
    await check('listener and service restart preserve exact old snapshot', async () => assert.deepEqual(await get('/api/prototype/inputs/prepared/'+prepared.preparation_id), prepared));
  }
  await check('real frontend assets served', async () => {
    assert.equal((await request('/prototype/inputs')).status, 200);
    assert.match(await (await request('/prototype/inputs/console.mjs')).text(), /weightCommand/);
    assert.match(await (await request('/prototype/inputs/model.mjs')).text(), /freezeCommand/);
  });
  await check('logout invalidates real cookie', async () => {
    assert.equal((await request('/api/auth/logout', 'POST')).status, 204);
    assert.equal((await request('/api/prototype/inputs/weights')).status, 401);
  });
  await check('unscoped administrator denied', async () => { await login('unscoped'); assert.equal((await request('/api/prototype/inputs/weights')).status, 403); });
  console.log(JSON.stringify({scope: 'REAL_NODE_TCP_FRONTEND_MODEL_FASTAPI_SQLITE_NO_BROWSER_NO_GA', reopened: input.reopened, scenarios, prepared, mocked_HTTP_responses: 0}));
} catch (error) { console.error('Input preparation HTTP acceptance failed: '+error.message); process.exitCode = 1; }
finally { input.password = ''; cookie = ''; csrf = ''; }
