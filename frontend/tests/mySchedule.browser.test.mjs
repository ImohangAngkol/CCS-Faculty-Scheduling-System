// Real React/Edge rendering with a synthetic HTTP API, not backend authorization.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer as httpServer} from 'node:http';
import {createServer as viteServer} from 'vite';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve, join, relative, isAbsolute, basename, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {account} from './dashboardD1.fixtures.mjs';
import {binding, proposal, missing, empty} from './mySchedule.fixtures.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const localTime = () => new Date(Date.now()+8*3600000).toISOString().replace('Z', '+08:00');
async function eventually(action, message) {
  const end = Date.now()+15000;
  while (Date.now()<end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}

test('D2 own timetable browser acceptance with synthetic HTTP responses', {timeout: 150000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d2-browser-'));
  let mode = {}, hold, origin, browser, vite, socket, sequence = 0;
  const pending = new Map(), errors = [], requests = [], scenarios = [], captures = [];
  const api = httpServer(async (request, response) => {
    response.setHeader('Access-Control-Allow-Origin', origin ?? 'http://localhost');
    response.setHeader('Access-Control-Allow-Credentials', 'true');
    response.setHeader('Content-Type', 'application/json');
    response.setHeader('Cache-Control', 'no-store');
    requests.push({method: request.method, path: request.url});
    const settings = {...mode};
    const reply = (status, body) => {if (!response.destroyed) {response.writeHead(status); response.end(JSON.stringify(body));}};
    if (request.method !== 'GET') return reply(405, {detail: 'Read-only fixture'});
    if (request.url === '/api/auth/me') {
      if (settings.anonymous) return reply(401, {detail: 'Authentication required'});
      const user = settings.admin ? {...account, role: 'admin', faculty_id: null, faculty: null}
        : settings.unbound ? {...account, faculty: null} : account;
      return reply(200, {user, csrf_token: 'public-d2-fixture-value', expires_at: '2099-01-01T00:00:00Z'});
    }
    if (request.url === '/api/schedules/me') {
      if (hold) await hold;
      if (settings.status) return reply(settings.status, {detail: {code: 'SYNTHETIC_SOURCE_STATUS', message: 'Synthetic failure'}});
      const data = settings.missing ? missing : settings.empty ? empty : settings.wrong
        ? {...proposal, faculty_code: 1, assignments: [{...proposal.assignments[0], subject: 'SYN-PRIVATE'}]}
        : settings.unknownRoom ? {...proposal, assignments: [{...proposal.assignments[0], room: null, title: null}]} : proposal;
      return reply(200, data);
    }
    return reply(404, {detail: 'Not a D2 fixture endpoint'});
  });
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence, timer = setTimeout(() => {pending.delete(id); reject(new Error('Browser command timeout: '+method));}, 15000);
    pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, method, params}));
  });
  const evaluate = async expression => {
    const result = await command('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
    return result.result.value;
  };
  const text = value => eventually(() => evaluate(`document.querySelector('main')?.textContent.includes(${JSON.stringify(value)})`), 'Missing page text: '+value);
  const go = async (settings = {}, path = '/faculty/schedule') => {mode = settings; await command('Page.navigate', {url: origin+path});};
  const click = label => evaluate(`[...document.querySelectorAll('main button')].find(el=>el.textContent===${JSON.stringify(label)}).click();true`);
  const check = (id, title, action) => t.test(id+' '+title, async () => {
    const started_at = localTime();
    try {await action(); scenarios.push({id, title, started_at, finished_at: localTime(), result: 'PASS'});}
    catch (error) {scenarios.push({id, title, started_at, finished_at: localTime(), result: 'FAIL', error: error.message}); throw error;}
  });
  const screenshot = async name => {
    if (!process.env.D2_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D2_SCREENSHOT_DIR), allowed = resolve(root, '../docs/screenshots/dashboard-d2');
    const child = relative(allowed, directory);
    assert.ok(child && !child.startsWith('..') && !isAbsolute(child));
    await mkdir(directory, {recursive: true});
    const {data} = await command('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
    await writeFile(join(directory, name+'.png'), Buffer.from(data, 'base64'), {flag: 'wx'});
    captures.push({name: name+'.png', captured_at: localTime(), url: await evaluate('location.href'), viewport: await evaluate('({width:innerWidth,height:innerHeight})')});
  };
  let version;
  try {
    await new Promise(resolve => api.listen(0, '127.0.0.1', resolve));
    vite = await viteServer({root, envDir: false, configFile: join(root, 'vite.config.ts'),
      server: {host: 'localhost', port: 0, strictPort: true}, logLevel: 'error',
      define: {'import.meta.env.VITE_API_URL': JSON.stringify(`http://127.0.0.1:${api.address().port}`)}});
    await vite.listen(); origin = vite.resolvedUrls.local[0].replace(/\/$/, '');
    browser = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {windowsHide: true, stdio: 'ignore'});
    let launchError; browser.on('error', error => launchError = error);
    let port;
    await eventually(async () => {if (launchError) throw launchError; port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]; return /^\d+$/.test(port);}, 'Owned Edge did not start');
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket = new WebSocket(targets.find(target=>target.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
    socket.addEventListener('message', event => {
      const message=JSON.parse(event.data), entry=pending.get(message.id);
      if (entry) {pending.delete(message.id);clearTimeout(entry.timer);message.error?entry.reject(new Error(message.error.message)):entry.resolve(message.result);}
      if (message.method==='Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    });
    await command('Runtime.enable');await command('Page.enable');version=await command('Browser.getVersion');
    console.log('Owned browser:',version.product);
    await command('Emulation.setDeviceMetricsOverride',{width:1366,height:1100,deviceScaleFactor:1,mobile:false});

    await check('D2-B01','loading, own lecture/lab timetable and proposal provenance',async()=>{
      let release;hold=new Promise(resolve=>release=resolve);
      await go();await text('Loading your timetable');hold=null;release();await text('Assignment details');
      await text('SYN101');await text('SYN LEC');await text('SYN LAB');await text('Lecture');await text('Laboratory');
      await text('GA-generated proposal');await text('freshness was not recorded');
      assert.equal(await evaluate(`document.querySelectorAll('main input,main select,main textarea,main form').length`),0);
      assert.equal(await evaluate(`document.querySelector('main').textContent.includes('SYN202')`),false);
      await screenshot('D2-B01-own-proposal-timetable');
    });
    await check('D2-B02','refresh retains source and only own rows',async()=>{
      await click('Refresh timetable');await text('Assignment details');await command('Page.reload');await text('Assignment details');
      assert.equal(await evaluate(`document.querySelectorAll('section[aria-labelledby="assignment-details"] article').length`),2);
    });
    await check('D2-B03','missing completed source is distinct from an empty own schedule',async()=>{
      await go({missing:true});await text('No GA proposal available');
      await go({empty:true});await text('No assignments in this proposal');await text('compatible with loaded');
      await screenshot('D2-B03-no-own-assignments');
    });
    await check('D2-B04','unavailable source clears old rows and supports retry',async()=>{
      await go({status:503});await text('Timetable unavailable');
      assert.equal(await evaluate(`document.querySelectorAll('main article').length`),0);
      mode.status=undefined;await click('Retry loading');await text('Assignment details');
    });
    await check('D2-B05','stale proposal shows review status and refresh recovers',async()=>{
      await go({status:409});await text('Proposal source requires review');
      assert.equal(await evaluate(`document.querySelectorAll('main article').length`),0);
      await screenshot('D2-B05-stale-source');
      mode.status=undefined;await click('Refresh timetable');await text('Assignment details');
    });
    await check('D2-B06','permission denial never displays assignments',async()=>{
      await go({status:403});await text('Schedule access unavailable');await text('do not have permission');
      assert.equal(await evaluate(`document.querySelectorAll('main article').length`),0);
    });
    await check('D2-B07','missing binding performs no timetable request',async()=>{
      const before=requests.filter(r=>r.path==='/api/schedules/me').length;
      await go({unbound:true});await text('Faculty binding unavailable');await pause(100);
      assert.equal(requests.filter(r=>r.path==='/api/schedules/me').length,before);
    });
    await check('D2-B08','mismatched server identity is rejected before rendering its rows',async()=>{
      await go({wrong:true});await text('does not match your account');
      assert.equal(await evaluate(`document.querySelector('main').textContent.includes('SYN-PRIVATE')`),false);
    });
    await check('D2-B09','anonymous and wrong-role routes do not fetch the timetable',async()=>{
      const before=requests.filter(r=>r.path==='/api/schedules/me').length;
      await go({anonymous:true});await eventually(()=>evaluate(`location.pathname==='/login'`),'Anonymous redirect missing');
      await go({admin:true});await eventually(()=>evaluate(`document.body.textContent.includes('Access unavailable')`),'Role denial missing');
      assert.equal(requests.filter(r=>r.path==='/api/schedules/me').length,before);
    });
    await check('D2-B10','expired synthetic session redirects to login',async()=>{
      await go({status:401});await eventually(()=>evaluate(`location.pathname==='/login'`),'Session expiry redirect missing');
    });
    await check('D2-B11','unknown source title and room are not fabricated',async()=>{
      await go({unknownRoom:true});await text('Subject name not recorded');await text('Not recorded');
    });
    await check('D2-B12','mobile timetable remains contained and assignment details readable',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
      await go();await text('Assignment details');assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));
      await evaluate(`document.querySelector('section[aria-labelledby="assignment-details"]').scrollIntoView();true`);
      await screenshot('D2-B12-mobile-assignment-details');
    });
    await check('D2-B13','leaving during a delayed read cannot inject stale assignments',async()=>{
      let release;hold=new Promise(resolve=>release=resolve);await go();await text('Loading your timetable');
      await evaluate(`document.querySelector('a[href="/faculty"]').click();true`);await text('Faculty Dashboard');
      hold=null;release();await pause(150);assert.equal(await evaluate(`document.querySelector('main').textContent.includes('SYN101')`),false);
    });
    assert.deepEqual(errors,[]);
    assert.ok(requests.every(r=>r.method==='GET'));
    assert.ok(requests.every(r=>['/api/auth/me','/api/schedules/me'].includes(r.path)));
    if(process.env.D2_SCREENSHOT_DIR) await writeFile(join(resolve(process.env.D2_SCREENSHOT_DIR),'browser-results.json'),JSON.stringify({browser:version.product,user_agent:version.userAgent,node:process.version,
      scope:'Actual Edge/React DOM with synthetic HTTP responses, not FastAPI authorization or PostgreSQL acceptance',scenarios,captures,runtime_errors:errors,mutation_requests:0,faculty_selector_requests:0,administrator_result_requests:0},null,2)+'\n',{flag:'wx'});
  } finally {
    socket?.close();for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error('Browser closed'));}
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();api.closeAllConnections();await new Promise(resolve=>api.close(resolve));
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('dashboard-d2-browser-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
