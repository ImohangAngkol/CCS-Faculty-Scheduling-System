import {present, submission} from './model.mjs';
let context = null, csrf = null, runId = new URL(location.href).searchParams.get('run');
let pending = new URL(location.href).searchParams.get('request'), busy = false, terminal = false;
const element = id => document.getElementById(id);
function controls() {
  element('start').disabled = busy || !context || Boolean(pending);
  element('refresh').disabled = busy || !(runId || pending);
  element('context').disabled = busy;
  element('new').disabled = busy || !terminal;
}
async function request(path, body) {
  const response = await fetch(path, {method: body ? 'POST' : 'GET', credentials: 'same-origin',
    headers: body ? {'Content-Type': 'application/json', 'X-CSRF-Token': csrf ?? ''} : {},
    body: body ? JSON.stringify(body) : undefined, cache: 'no-store'});
  const value = await response.json();
  if (!response.ok && !value.contract) throw new Error(value.detail?.code ?? 'Request unavailable.');
  return value;
}
async function guarded(work) {
  if (busy) return;
  busy = true; controls();
  try { await work(); } catch (error) { element('status').textContent = error.message; }
  finally { busy = false; controls(); }
}
function render(run) {
  const view = present(run);
  runId = run.run_id;
  terminal = run.terminal === true;
  const url = new URL(location.href); url.searchParams.set('run', runId); history.replaceState(null, '', url);
  element('status').textContent = `${view.message} Original GA fitness: ${view.fitness ?? 'unavailable'}.`;
  element('result').textContent = JSON.stringify(run, null, 2);
  // No automatic duplicate start, including after a recorded terminal failure.
}
element('login').addEventListener('submit', event => {
  event.preventDefault();
  guarded(async () => {
    const login = await request('/api/auth/login', {username: element('username').value, password: element('password').value});
    csrf = login.csrf_token; element('password').value = '';
    element('status').textContent = 'Signed in. Refresh the server context before starting.';
  });
});
element('context').addEventListener('click', () => guarded(async () => {
  const next = await request('/api/prototype/scheduling/context');
  submission(next, crypto.randomUUID()); context = next;
  element('context-view').textContent = JSON.stringify(next, null, 2);
  element('status').textContent = 'Server term and minimum revision loaded. Eligibility capacity alone does not prove feasibility.';
}));
element('start').addEventListener('click', () => guarded(async () => {
  pending = crypto.randomUUID();
  const url = new URL(location.href); url.searchParams.set('request', pending); history.replaceState(null, '', url);
  render(await request('/api/prototype/scheduling/runs', submission(context, pending)));
}));
element('new').addEventListener('click', () => {
  if (busy || !terminal) return;
  runId = null; pending = null; context = null; terminal = false;
  const url = new URL(location.href); url.searchParams.delete('run'); url.searchParams.delete('request'); history.replaceState(null, '', url);
  element('status').textContent = 'New request selected. Refresh context first; the previous record remains preserved.';
  controls();
});
element('refresh').addEventListener('click', () => guarded(async () => {
  render(await request(runId ? `/api/prototype/scheduling/runs/${encodeURIComponent(runId)}` :
    `/api/prototype/scheduling/requests/${encodeURIComponent(pending)}`));
}));
controls();
