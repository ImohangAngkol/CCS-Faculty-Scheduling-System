import {generatedView, decisionFor} from './model.mjs';
const el = id => document.getElementById(id);
let csrf = null, busy = false, selected = null;
el('run').value = new URL(location.href).searchParams.get('run') ?? '';
function controls() {
  for (const item of document.querySelectorAll('button, input, textarea')) item.disabled = busy;
  const available = selected && ['COMPLETED', 'STOPPED'].includes(selected.state) && selected.generated && selected.reviews.length === 0;
  for (const name of ['approve', 'reject', 'revise']) el(name).disabled = busy || !available;
  if (available) el('approve').disabled = busy || !selected.result.qualification.fully_feasible_under_captured_policy;
  for (const name of ['json', 'csv', 'txt']) el(name).disabled = busy || !selected?.generated;
}
async function api(path, body) {
  const reply = await fetch(path, {method: body ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store',
    headers: body ? {'Content-Type': 'application/json', 'X-CSRF-Token': csrf ?? ''} : {}, body: body ? JSON.stringify(body) : undefined});
  const result = await reply.json();
  if (!reply.ok && !result.contract) throw new Error(result.detail?.code ?? 'Request unavailable. Reload and check scope/revision.');
  return result;
}
async function work(action) {
  if (busy) return;
  busy = true; controls();
  try { const result = await action(); el('result').textContent = JSON.stringify(result, null, 2); }
  catch (error) { selected = null; el('status').textContent = error.message; }
  finally { busy = false; controls(); }
}
function display(run) {
  const view = generatedView(run); selected = run; el('run').value = run.run_id;
  const url = new URL(location.href); url.searchParams.set('run', run.run_id); history.replaceState(null, '', url);
  el('status').textContent = `${view.state}. Original fitness: ${view.fitness ?? 'unavailable'}. Fully feasible: ${view.feasible}. Native/Edge acceptance remains unverified.`;
  return run;
}
el('login').addEventListener('submit', event => {
  event.preventDefault(); work(async () => {
    const result = await api('/api/auth/login', {username: el('username').value, password: el('password').value});
    csrf = result.csrf_token; el('password').value = ''; selected = null;
    el('status').textContent = 'Signed in; scope and Chair authority are checked separately.';
    return {signed_in: true};
  });
});
el('run').addEventListener('input', () => { selected = null; controls(); });
el('list').addEventListener('click', () => work(() => api('/api/prototype/cycle/runs')));
el('inspect').addEventListener('click', () => work(async () => display(await api('/api/prototype/cycle/runs/'+encodeURIComponent(el('run').value)))));
el('admit').addEventListener('click', () => work(async () => display(await api('/api/prototype/cycle/admissions',
  {request_id: crypto.randomUUID(), preparation_id: el('preparation').value}))));
el('stop').addEventListener('click', () => work(() => api('/api/prototype/cycle/runs/'+encodeURIComponent(el('run').value)+'/stop', {request_id: crypto.randomUUID()})));
for (const [name, decision] of [['approve', 'APPROVE'], ['reject', 'REJECT'], ['revise', 'REQUEST_REVISION']]) {
  el(name).addEventListener('click', () => work(async () => {
    const body = decisionFor(selected, decision, el('explanation').value, crypto.randomUUID());
    await api('/api/prototype/cycle/runs/'+encodeURIComponent(selected.run_id)+'/decision', body);
    return display(await api('/api/prototype/cycle/runs/'+encodeURIComponent(selected.run_id)));
  }));
}
el('compare').addEventListener('click', () => work(() => api('/api/prototype/cycle/compare/'+encodeURIComponent(el('run').value)+'/'+encodeURIComponent(el('other').value))));
el('versions').addEventListener('click', () => work(() => api('/api/prototype/cycle/versions')));
el('timetable').addEventListener('click', () => work(() => api('/api/prototype/cycle/timetable/'+encodeURIComponent(el('faculty').value))));
for (const kind of ['json', 'csv', 'txt']) el(kind).addEventListener('click', () => work(async () => {
  const response = await fetch('/api/prototype/cycle/runs/'+encodeURIComponent(selected.run_id)+'/export/'+kind, {credentials: 'same-origin', cache: 'no-store'});
  if (!response.ok) throw new Error('Export unavailable; no file was created.');
  const url = URL.createObjectURL(await response.blob());
  try { const link = document.createElement('a'); link.href = url; link.download = 'fictional-research.'+kind; link.click(); }
  finally { URL.revokeObjectURL(url); }
  return {downloaded: kind, institutional_publication: false};
}));
controls();
