import {weightCommand, freezeCommand, neutralPreference} from './model.mjs';
const el = id => document.getElementById(id);
let csrf = null, busy = false, weights = null, preference = null, selected = null;
let preparation = new URL(location.href).searchParams.get('preparation');
function controls() {
  for (const button of document.querySelectorAll('button')) button.disabled = busy;
  for (const input of document.querySelectorAll('input, textarea')) input.disabled = busy;
  el('save-preference').disabled = busy || !preference;
  el('approve-weights').disabled = busy || !weights;
  el('prepare').disabled = busy || !selected;
  el('reload-prepared').disabled = busy || !preparation;
}
async function api(path, method = 'GET', body) {
  const reply = await fetch(path, {method, credentials: 'same-origin', cache: 'no-store',
    headers: body ? {'Content-Type': 'application/json', 'X-CSRF-Token': csrf ?? ''} : {},
    body: body ? JSON.stringify(body) : undefined});
  const value = await reply.json();
  if (!reply.ok) throw new Error(value.detail?.code ?? 'Request rejected. Check authentication, explicit scope and revision; reload before retrying.');
  return value;
}
async function perform(action) {
  if (busy) return;
  busy = true; controls();
  try {
    const result = await action();
    el('result').textContent = JSON.stringify(result, null, 2);
    el('status').textContent = 'Recorded response loaded. Preparation is not execution or institutional approval.';
  } catch (error) { el('status').textContent = error.message; }
  finally { busy = false; controls(); }
}
el('login').addEventListener('submit', event => {
  event.preventDefault();
  perform(async () => {
    const result = await api('/api/auth/login', 'POST', {username: el('username').value, password: el('password').value});
    csrf = result.csrf_token; el('password').value = '';
    weights = null; preference = null; selected = null;
    return {signed_in: true, account_role: result.user.role, scope_authority: 'Checked separately on every operation'};
  });
});
el('load-preference').addEventListener('click', () => perform(async () => {
  const code = el('faculty').value;
  const next = await api(`/api/prototype/inputs/preferences/${encodeURIComponent(code)}`);
  if (el('faculty').value !== code) throw new Error('Faculty selection changed. Reload your preference.');
  preference = next;
  const body = {...(preference.preference.body ?? neutralPreference())}; delete body.faculty_code;
  el('preference').value = JSON.stringify(body, null, 2);
  return preference;
}));
el('faculty').addEventListener('input', () => {
  preference = null; el('preference').value = ''; controls();
});
el('save-preference').addEventListener('click', () => perform(async () => {
  const response = await api(`/api/prototype/inputs/preferences/${encodeURIComponent(preference.faculty_code)}`, 'PUT',
    {request_id: crypto.randomUUID(), expected_revision: preference.preference.revision, preference: JSON.parse(el('preference').value)});
  preference.preference = response; selected = null;
  return response;
}));
el('load-weights').addEventListener('click', () => perform(async () => {
  weights = await api('/api/prototype/inputs/weights');
  el('weights').value = JSON.stringify(weights.configurable_penalties, null, 2);
  return weights;
}));
el('approve-weights').addEventListener('click', () => perform(async () => {
  const response = await api('/api/prototype/inputs/weights/approve', 'POST', weightCommand(weights, el('weights').value, crypto.randomUUID()));
  weights.policy = response; selected = null;
  return response;
}));
el('selection').addEventListener('click', () => perform(async () => {
  selected = await api('/api/prototype/inputs/selection'); return selected;
}));
function remember(value) {
  preparation = value.preparation_id;
  const url = new URL(location.href); url.searchParams.set('preparation', preparation); history.replaceState(null, '', url);
  return value;
}
el('prepare').addEventListener('click', () => perform(async () => remember(await api('/api/prototype/inputs/prepare', 'POST', freezeCommand(selected, crypto.randomUUID())))));
el('reload-prepared').addEventListener('click', () => perform(async () => remember(await api(`/api/prototype/inputs/prepared/${encodeURIComponent(preparation)}`))));
controls();
