import {changeFor, validateView} from './model.mjs';

const el = id => document.getElementById(id);
let epoch = 0, state = null, csrf = '';
const fields = new Map();
const node = (tag, text) => { const element = document.createElement(tag); element.textContent = text; return element; };

function clear() {
  state = null; fields.clear(); el('rows').replaceChildren(); el('save').disabled = true;
  el('provenance').textContent = ''; el('assessment').textContent = 'No qualified input assessment loaded.';
}
async function request(path, options = {}) {
  const reply = await fetch(path, {...options, credentials: 'same-origin', signal: AbortSignal.timeout(10000),
    headers: {'Content-Type': 'application/json', ...(csrf ? {'X-CSRF-Token': csrf} : {}), ...options.headers}});
  const data = reply.status === 204 ? null : await reply.json();
  if (!reply.ok) throw new Error(data?.detail?.code ?? `HTTP ${reply.status}: request rejected.`);
  return data;
}
function render(data) {
  state = validateView(data); fields.clear(); el('rows').replaceChildren();
  for (const row of state.faculty) {
    const tr = document.createElement('tr');
    tr.append(node('th', `Faculty ${row.faculty_code}`), node('td', row.soft_target_teaching_units),
      node('td', row.maximum_teaching_units), node('td', row.eligible_units));
    const td = document.createElement('td'), input = document.createElement('input');
    input.type = 'number'; input.min = '0'; input.max = String(row.maximum_teaching_units); input.step = '1';
    input.value = row.minimum_teaching_units === null ? '' : String(row.minimum_teaching_units);
    input.setAttribute('aria-label', `Faculty ${row.faculty_code} explicit minimum units`);
    input.disabled = !state.can_configure; td.append(input); tr.append(td);
    tr.append(node('td', row.proven_shortfall ? `Infeasible: at least ${row.proven_shortfall} units short` :
      row.minimum_teaching_units === null ? 'Minimum unspecified' : 'Not proven infeasible'));
    el('rows').append(tr); fields.set(row.faculty_code, input);
  }
  el('save').disabled = !state.can_configure;
  el('assessment').textContent = state.preflight === 'MINIMUM_WORKLOAD_INFEASIBLE' ?
    'MINIMUM_WORKLOAD_INFEASIBLE: an explicit minimum exceeds eligible offering units. No GA was started.' :
    'NOT_PROVEN_INFEASIBLE: an upper-bound check is not proof of a feasible schedule. No GA was started.';
  el('scope').textContent = `${state.scope.academic_year} / ${state.scope.term} / ${state.scope.catalog_revision}`;
  el('provenance').textContent = `Prototype policy revision ${state.policy.revision}\nPolicy: ${state.policy.digest}\nCaptured input bundle: ${state.bundle_fingerprint}\nCapture: ${state.input_capture_verification}; optimizer consumption: ${state.optimizer_consumption}`;
}
async function reload() {
  const key = ++epoch; el('error').textContent = ''; el('save').disabled = true;
  el('message').textContent = 'Loading stored policy and input qualification…';
  try {
    const me = await request('/api/auth/me'); if (key !== epoch) return;
    csrf = me.csrf_token;
    const data = await request('/api/prototype/workload'); if (key !== epoch) return;
    render(data); el('message').textContent = 'Stored prototype policy loaded.';
  } catch (error) { if (key === epoch) { clear(); el('message').textContent = ''; el('error').textContent = error.message; } }
}
el('login').onsubmit = async event => {
  event.preventDefault(); const key = ++epoch; clear(); el('error').textContent = '';
  const password = el('password').value; el('password').value = '';
  try {
    await request('/api/auth/login', {method: 'POST', body: JSON.stringify({username: el('username').value, password})});
    if (key === epoch) await reload();
  } catch (error) { if (key === epoch) el('error').textContent = error.message; }
};
el('reload').onclick = () => void reload();
el('save').onclick = async () => {
  if (!state) return;
  let change;
  try { change = changeFor(state, new Map([...fields].map(([code, input]) => [code, input.value]))); }
  catch (error) { el('error').textContent = error.message; return; }
  const key = ++epoch; el('save').disabled = true; el('error').textContent = ''; el('message').textContent = 'Saving explicit prototype minimums…';
  try {
    const data = await request('/api/prototype/workload', {method: 'PUT', body: JSON.stringify(change)});
    if (key !== epoch) return; render(data); el('message').textContent = 'Prototype policy revision saved. This is not institutional approval.';
  } catch (error) {
    if (key === epoch) { clear(); el('message').textContent = ''; el('error').textContent = `${error.message} Save outcome may be uncertain; reload server state before retrying.`; }
  }
};
el('logout').onclick = async () => {
  const key = ++epoch;
  try { await request('/api/auth/logout', {method: 'POST'}); }
  catch (error) { if (key === epoch) el('error').textContent = error.message; }
  if (key === epoch) { csrf = ''; clear(); el('message').textContent = 'Local view cleared. Verify sign-out if the connection failed.'; }
};
window.addEventListener('pagehide', () => { epoch++; csrf = ''; clear(); });
void reload();
