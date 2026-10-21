// Real Edge rendering and interaction, served by Vite + a synthetic HTTP API.
// No FastAPI, identity database, institutional files or GA execution is involved.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer as httpServer} from 'node:http';
import {createServer as viteServer} from 'vite';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve, join, relative, isAbsolute, basename, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {account, binding, faculty, subjects} from './dashboardD1.fixtures.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(action, message, timeout = 15000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}
const localTime = () => new Date(Date.now() + 8 * 3600000).toISOString().replace('Z', '+08:00');

test('D1 rendered dashboard acceptance with synthetic HTTP responses', {timeout: 180000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d1-browser-'));
  let mode = {}, origin, holdCatalog, holdProfile, socket, browser, vite, sequence = 0;
  const pending = new Map(), errors = [], requests = [], scenarios = [], captures = [];
  const api = httpServer(async (request, response) => {
    response.setHeader('Access-Control-Allow-Origin', origin ?? 'http://localhost');
    response.setHeader('Access-Control-Allow-Credentials', 'true');
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-CSRF-Token');
    response.setHeader('Content-Type', 'application/json');
    response.setHeader('Cache-Control', 'no-store');
    if (request.method === 'OPTIONS') {response.writeHead(204); response.end(); return;}
    requests.push({method: request.method, path: request.url});
    const snapshot = {...mode};
    const reply = (status, body) => {if (!response.destroyed) {response.writeHead(status); response.end(JSON.stringify(body));}};
    if (request.method !== 'GET') return reply(405, {detail: 'Read-only D1 fixture'});
    if (request.url === '/api/auth/me') {
      if (snapshot.anonymous) return reply(401, {detail: 'Sign in required'});
      const user = snapshot.role === 'admin' ? {...account, role: 'admin', faculty_id: null, faculty: null}
        : snapshot.unbound ? {...account, faculty: null} : account;
      return reply(200, {user, csrf_token: 'public-d1-fixture-value', expires_at: '2099-01-01T00:00:00Z'});
    }
    if (request.url === '/api/subjects/available') {
      if (holdCatalog) await holdCatalog;
      return reply(snapshot.catalogStatus ?? 200, snapshot.catalogStatus ? {detail: 'Synthetic rejection'} : {data: snapshot.emptyCatalog ? [] : subjects});
    }
    if (request.url === '/api/faculty/' + binding.faculty_id) {
      if (holdProfile) await holdProfile;
      const data = snapshot.wrongIdentity ? {...faculty, faculty_id: 'other', name: 'Do not expose this profile'}
        : snapshot.emptyAcademic ? {...faculty, seniority_level: null, specializations: [], eligible_subject_codes: []} : faculty;
      return reply(snapshot.profileStatus ?? 200, snapshot.profileStatus ? {detail: 'Synthetic rejection'} : {data});
    }
    if (request.url === '/api/ga/status') return reply(200, {control_version: '3c.1', process_instance_id: 'd1-synthetic-process', active_run: null, paused_runs: []});
    if (request.url === '/api/ga/latest') return reply(404, {detail: 'No synthetic run'});
    if (request.url === '/api/schedules/me') return reply(200, {schema_version: 1, availability: 'missing', faculty_id: binding.faculty_id, faculty_code: binding.faculty_code,
      source: {kind: 'latest_completed_ga_result', label: 'GA-generated proposal', compatibility: 'not_available', freshness: 'not_recorded', saved_at: null}, assignments: []});
    return reply(404, {detail: 'Not a D1 fixture endpoint'});
  });
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error('Browser command timeout: ' + method));}, 15000);
    pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, method, params}));
  });
  const evaluate = async expression => {
    const result = await command('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
    return result.result.value;
  };
  const text = value => eventually(() => evaluate(`document.querySelector('main')?.textContent.includes(${JSON.stringify(value)})`), 'Missing page text: ' + value);
  const go = async (path, settings = {}) => {
    mode = settings;
    await command('Page.navigate', {url: origin + path});
  };
  const retry = () => evaluate(`[...document.querySelectorAll('main button')].find(el => el.textContent==='Retry loading').click();true`);
  const check = async (id, title, action) => t.test(id + ' ' + title, async () => {
    const started_at = localTime();
    try {await action(); scenarios.push({id, title, started_at, finished_at: localTime(), result: 'PASS'});}
    catch (error) {scenarios.push({id, title, started_at, finished_at: localTime(), result: 'FAIL', error: error.message}); throw error;}
  });
  const screenshot = async name => {
    if (!process.env.D1_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D1_SCREENSHOT_DIR);
    const allowed = resolve(root, '../docs/screenshots/dashboard-d1');
    const child = relative(allowed, directory);
    assert.ok(child && !child.startsWith('..') && !isAbsolute(child), 'New D1 screenshot directory required');
    await mkdir(directory, {recursive: true});
    const {data} = await command('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
    await writeFile(join(directory, name + '.png'), Buffer.from(data, 'base64'), {flag: 'wx'});
    captures.push({name: name + '.png', captured_at: localTime(), url: await evaluate('location.href'), viewport: await evaluate('({width:innerWidth,height:innerHeight})')});
  };
  let version;
  try {
    await new Promise(resolve => api.listen(0, '127.0.0.1', resolve));
    const backend = `http://127.0.0.1:${api.address().port}`;
    vite = await viteServer({root, envDir: false, configFile: join(root, 'vite.config.ts'),
      server: {host: 'localhost', port: 0, strictPort: true},
      define: {'import.meta.env.VITE_API_URL': JSON.stringify(backend)}, logLevel: 'error'});
    await vite.listen(); origin = vite.resolvedUrls.local[0].replace(/\/$/, '');
    const executable = process.env.PREFERENCE_TEST_BROWSER ?? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
    browser = spawn(executable, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {windowsHide: true, stdio: 'ignore'});
    let launchError; browser.on('error', error => launchError = error);
    let port;
    await eventually(async () => {if (launchError) throw launchError; port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; return /^\d+$/.test(port);}, 'Owned Edge browser did not start');
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {socket.addEventListener('open', resolve, {once: true}); socket.addEventListener('error', reject, {once: true});});
    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data), entry = pending.get(message.id);
      if (entry) {pending.delete(message.id); clearTimeout(entry.timer); message.error ? entry.reject(new Error(message.error.message)) : entry.resolve(message.result);}
      if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    });
    version = await command('Browser.getVersion');
    console.log('Owned browser:', version.product);
    await command('Runtime.enable'); await command('Page.enable');
    await command('Emulation.setDeviceMetricsOverride', {width: 1366, height: 1000, deviceScaleFactor: 1, mobile: false});

    await check('D1-B01', 'catalog loading, real component details and unsupported metadata', async () => {
      let release; holdCatalog = new Promise(resolve => release = resolve);
      await go('/admin/subjects', {role: 'admin'}); await text('Loading subject catalog');
      holdCatalog = null; release(); await text('Synthetic Computing');
      await evaluate(`document.querySelector('main details summary').click();true`);
      await text('90 minutes each'); await text('180 minutes each');
      await evaluate(`document.querySelectorAll('main details summary')[1].click();true`);
      await text('No duration has been inferred');
      assert.equal(await evaluate(`document.querySelectorAll('main input:not([type=search]), main form').length`), 0);
      await screenshot('D1-B01-subject-catalog');
    });
    await check('D1-B02', 'code/title search, no matches and clear', async () => {
      const search = async value => evaluate(`var input=document.querySelector('#catalog-search');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,${JSON.stringify(value)});input.dispatchEvent(new Event('input',{bubbles:true}));true`);
      await search('syn101'); await text('Showing 1 of 2 subjects');
      await search('SEMINAR'); await text('Synthetic Seminar');
      assert.equal(await evaluate(`document.querySelectorAll('main article').length`), 1);
      await search('no match'); await text('No matching subjects');
      await search(''); await text('Showing 2 of 2 subjects');
    });
    await check('D1-B03', 'genuine empty catalog', async () => {await go('/admin/subjects', {role: 'admin', emptyCatalog: true}); await text('No subjects available');});
    await check('D1-B04', 'catalog error and successful retry', async () => {
      await go('/admin/subjects', {role: 'admin', catalogStatus: 503}); await text('temporarily unavailable');
      mode.catalogStatus = undefined; await retry(); await text('Synthetic Computing');
    });
    await check('D1-B05', 'catalog metadata denial is actionable', async () => {await go('/admin/subjects', {role: 'admin', catalogStatus: 403}); await text('do not have permission');});
    await check('D1-B06', 'faculty welcome, honest feature status and navigation', async () => {
      await go('/faculty'); await text('Welcome, Synthetic Lecturer.'); await text('Read only');
      for (const path of ['preferences', 'schedule', 'profile']) assert.ok(await evaluate(`!!document.querySelector('main a[href="/faculty/${path}"]')`));
      await screenshot('D1-B06-faculty-dashboard');
      await evaluate(`document.querySelector('main a[href="/faculty/schedule"]').click();true`); await text('No GA proposal available');
      await go('/faculty'); await text('Faculty Dashboard');
      await evaluate(`document.querySelector('main a[href="/faculty/profile"]').click();true`); await text('Synthetic computing domain');
    });
    await check('D1-B07', 'profile loading, identity and read-only academic details survive refresh', async () => {
      let release; holdProfile = new Promise(resolve => release = resolve);
      await go('/faculty/profile'); await text('Loading faculty metadata'); holdProfile = null; release();
      await text('Synthetic computing domain'); await text('Account information'); await text('Faculty information');
      assert.equal(await evaluate(`document.querySelectorAll('main input, main textarea, main form').length`), 0);
      await command('Page.reload'); await text('Synthetic computing domain');
      await screenshot('D1-B07-faculty-profile');
    });
    await check('D1-B08', 'empty academic fields remain honest unknowns', async () => {await go('/faculty/profile', {emptyAcademic: true}); await text('None recorded'); await text('Not provided');});
    await check('D1-B09', 'missing metadata preserves account binding', async () => {await go('/faculty/profile', {profileStatus: 404}); await text('Faculty metadata not found'); await text(binding.display_code);});
    await check('D1-B10', 'mismatched identity is never rendered', async () => {
      await go('/faculty/profile', {wrongIdentity: true}); await text('does not match your account binding');
      assert.equal(await evaluate(`document.querySelector('main').textContent.includes('Do not expose this profile')`), false);
    });
    await check('D1-B11', 'profile service failure and retry', async () => {
      await go('/faculty/profile', {profileStatus: 503}); await text('temporarily unavailable');
      mode.profileStatus = undefined; await retry(); await text('Synthetic computing domain');
    });
    await check('D1-B12', 'missing binding makes no faculty lookup', async () => {
      const before = requests.filter(item => item.path.startsWith('/api/faculty/')).length;
      await go('/faculty/profile', {unbound: true}); await text('No faculty record has been selected');
      await pause(150); assert.equal(requests.filter(item => item.path.startsWith('/api/faculty/')).length, before);
    });
    await check('D1-B13', 'role-denied routes never mount protected metadata pages', async () => {
      const before = requests.length;
      await go('/admin/subjects'); await eventually(() => evaluate(`document.body.textContent.includes('Access unavailable')`), 'Faculty admin denial missing');
      await go('/faculty/profile', {role: 'admin'}); await eventually(() => evaluate(`document.body.textContent.includes('Access unavailable')`), 'Admin faculty portal denial missing');
      assert.ok(!requests.slice(before).some(item => item.path.startsWith('/api/faculty/') || item.path === '/api/subjects/available'));
    });
    await check('D1-B14', 'anonymous access redirects and metadata 401 expires the session', async () => {
      for (const path of ['/admin/subjects', '/faculty/profile', '/faculty']) {
        await go(path, {anonymous: true}); await eventually(() => evaluate(`location.pathname==='/login'`), 'Anonymous redirect missing');
      }
      await go('/faculty/profile', {profileStatus: 401}); await eventually(() => evaluate(`location.pathname==='/login'`), 'Expired session redirect missing');
    });
    await check('D1-B15', 'mobile catalog, dashboard and profile fit the viewport', async () => {
      await command('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: false});
      for (const [path, settings, ready] of [['/admin/subjects', {role: 'admin'}, 'Synthetic Computing'], ['/faculty', {}, 'Welcome, Synthetic Lecturer.'], ['/faculty/profile', {}, 'Synthetic computing domain']]) {
        await go(path, settings); await text(ready);
        assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth'), path + ' overflows the mobile viewport');
      }
      await screenshot('D1-B15-mobile-profile');
    });
    await check('D1-B16', 'metadata denial does not expose academic details', async () => {
      await go('/faculty/profile', {profileStatus: 403}); await text('do not have permission');
      assert.equal(await evaluate(`document.querySelector('main').textContent.includes('Synthetic computing domain')`), false);
    });
    assert.deepEqual(errors, []);
    assert.ok(requests.every(item => item.method === 'GET'), 'D1 must issue no mutation requests');
    if (process.env.D1_SCREENSHOT_DIR) {
      await writeFile(join(resolve(process.env.D1_SCREENSHOT_DIR), 'browser-results.json'), JSON.stringify({
        browser: version.product, user_agent: version.userAgent, node: process.version,
        scope: 'Actual React DOM in headless Edge; synthetic HTTP API, no FastAPI/PostgreSQL or persisted workflow verification',
        scenarios, captures, runtime_errors: errors, mutation_requests: 0,
      }, null, 2) + '\n', {flag: 'wx'});
    }
  } finally {
    holdCatalog = null; holdProfile = null;
    socket?.close(); for (const entry of pending.values()) {clearTimeout(entry.timer); entry.reject(new Error('Browser closed'));}
    if (browser && browser.exitCode === null) {
      browser.kill(); await Promise.race([pause(3000), new Promise(resolve => browser.once('exit', resolve))]);
    }
    await vite?.close(); api.closeAllConnections(); await new Promise(resolve => api.close(resolve));
    const target = resolve(profile);
    assert.ok(target.startsWith(resolve(tmpdir()) + sep) && basename(target).startsWith('dashboard-d1-browser-'));
    await rm(target, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
});
