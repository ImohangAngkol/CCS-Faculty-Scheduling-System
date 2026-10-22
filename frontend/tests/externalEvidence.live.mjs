import {sanitizeTree,sanitizeText} from './evidencePrivacy.mjs';
// Real React/Edge rendering with a synthetic HTTP API, not backend authorization.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer as httpServer} from 'node:http';
import {createServer as viteServer} from 'vite';
import {spawn,spawnSync} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve, join, relative, isAbsolute, basename, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {account} from './dashboardD1.fixtures.mjs';
import {metadata, inputs, makeSource, makeProjection} from './externalReview.fixtures.mjs';
import {createHash} from 'node:crypto';
import {makeHandoff} from './externalHandoff.fixtures.mjs';
import {makeAssessment,completeMetadata} from './externalReadiness.fixtures.mjs';
import {handoffIdentity,HANDOFF_LABEL} from '../src/api/externalSchedules.ts';

const privateConfig=JSON.parse(await new Promise(resolve=>{let value='';process.stdin.setEncoding('utf8');process.stdin.on('data',chunk=>value+=chunk);process.stdin.on('end',()=>resolve(value));}));
const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const localTime = () => new Date(Date.now()+8*3600000).toISOString().replace('Z', '+08:00');
async function eventually(action, message) {
  const end = Date.now()+15000;
  while (Date.now()<end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}

test('D8 live browser-to-FastAPI smoke with synthetic academic data', {timeout: 150000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d8-browser-'));
  let mode = {}, hold, origin, browser, vite, socket, sequence = 0;
  let fileBytesMatched=false, currentSource=makeSource();
  const malicious='<img src=x onerror="window.__importExecuted=true"><script>window.__importExecuted=true</script>';
  const fixtureInputs=[{...inputs[0],title:'Fictional external course',sections:['SYN-A'],room:'',instructor:'',start:'09:00',end:'10:00',days:['M'],notes:'Fictional source text only'}];
  const pending = new Map(), errors = [], requests = [], scenarios = [], captures = [];
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
  const go = async (settings = {}, path = '/admin/external-schedules') => {mode = settings; await command('Page.navigate', {url: origin+path});};
  const click = label => evaluate(`[...document.querySelectorAll('main button')].find(el=>el.textContent===${JSON.stringify(label)}).click();true`);
  const check = (id, title, action) => t.test(id+' '+title, async () => {
    const started_at = localTime();
    try {await action(); scenarios.push({id, title, started_at, finished_at: localTime(), result: 'PASS'});}
    catch (error) {scenarios.push({id, title, started_at, finished_at: localTime(), result: 'FAIL', error: error.message}); throw error;}
  });
  const screenshot = async name => {
    if (!process.env.D8_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D8_SCREENSHOT_DIR), allowed = resolve(root, '../docs/screenshots/dashboard-d8');
    const child = relative(allowed, directory);
    assert.ok(child && !child.startsWith('..') && !isAbsolute(child));
    await mkdir(directory, {recursive: true});
    const {data} = await command('Page.captureScreenshot', {format: 'png', captureBeyondViewport: false});
    await writeFile(join(directory, name+'.png'), Buffer.from(data, 'base64'), {flag: 'wx'});
    captures.push({name: name+'.png', captured_at: localTime(), url: await evaluate('location.href'), viewport: await evaluate('({width:innerWidth,height:innerHeight})')});
  };
  let version;
  try {

    vite = await viteServer({root, envDir: false, configFile: join(root, 'vite.config.ts'),
      server: {host: 'localhost', port: privateConfig.frontendPort, strictPort: true}, logLevel: 'error',
      define: {'import.meta.env.VITE_API_URL': JSON.stringify(privateConfig.backend)}});
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
    socket.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.method==='Network.requestWillBeSent'){const req=message.params.request;requests.push({method:req.method,path:new URL(req.url).pathname});}});await command('Network.enable');await command('Runtime.enable');await command('Page.enable');version=await command('Browser.getVersion');
    console.log('Owned browser:',version.product);
    await command('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false});

    const setSelect=async(label,value)=>evaluate("var el=[...document.querySelectorAll('section[aria-label=\"Calendar review\"] label')].find(el=>el.textContent.startsWith("+JSON.stringify(label)+")).querySelector('select');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(el,"+JSON.stringify(value)+");el.dispatchEvent(new Event('change',{bubbles:true}));true");
    const map=async(label,value)=>evaluate("var el=document.querySelector('select[aria-label=\""+label+"\"]');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(el,"+JSON.stringify(value)+");el.dispatchEvent(new Event('change',{bubbles:true}));true");
    const selectFile=async(filename='fictional.csv')=>{const {root:documentRoot}=await command('DOM.getDocument');const {nodeId}=await command('DOM.querySelector',{nodeId:documentRoot.nodeId,selector:'input[type=file]'});await command('DOM.setFileInputFiles',{nodeId,files:[join(profile,filename)]});};
    const upload=async(filename='fictional.csv')=>{await selectFile(filename);await click('Preview selected file');};
    const calendar=()=>evaluate("!!document.querySelector('[data-testid=external-review-calendar]')");
    const ready=()=>eventually(calendar,'Calendar projection did not load');
    const reviewText=()=>evaluate("document.querySelector('section[aria-label=\"Calendar review\"]')?.textContent??''");
    const findings=()=>evaluate("document.querySelector('[aria-label=\"Reconciled discrepancies\"]')?.textContent??''");
    const chooseRow=async n=>setSelect('Original source row',String(n));
    const fields=Object.keys(inputs[0]),cell=value=>'"'+String(Array.isArray(value)?value.join('|'):value).replaceAll('"','""')+'"';
    await writeFile(join(profile,'fictional.csv'),[fields.join(','),...fixtureInputs.map(input=>fields.map(k=>cell(input[k])).join(','))].join('\n')+'\n');
    const handoff=()=>evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"] article')?.textContent??''");
    const outputReady=()=>eventually(async()=>(await handoff()).includes('Preview identity: d5-'),'Complete handoff did not load');
    const prepared=()=>evaluate("!!document.querySelector('section[aria-label=\"Validated review handoff\"] article')");
    const handoffPosts=()=>requests.filter(r=>r.method==='POST'&&r.path==='/api/external-schedules/handoff').length;
    const installPrintSpy=()=>evaluate(`window.__printSnapshots=[];window.print=()=>{const root=document.querySelector('.external-handoff-print-root');window.__printSnapshots.push({text:root.textContent,rows:root.querySelectorAll('.handoff-row').length,rootDisplay:getComputedStyle(root).display,appDisplay:getComputedStyle(document.querySelector('#root')).display,overflow:root.scrollWidth>innerWidth,notes:root.querySelector('.handoff-notes')?.textContent});};true`);
    const setValue=(label,value)=>evaluate("var el=document.querySelector('[aria-label=\"'+"+JSON.stringify(label)+"+'\"]');var proto=el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(el,"+JSON.stringify(value)+");el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}));true");
    const fillComplete=async()=>{
      for(const [label,value] of Object.entries({'Originating college / department':'Fictional College','Source document / reference':'Fictional memo','Source revision (when available)':'Example 1','Source evidence reference (claim)':'Fictional evidence','Academic year (YYYY-YYYY)':'2026-2027','Academic term':'Fictional first term','Effective start date':'2026-08-03','Effective end date':'2026-12-18','Timezone (explicit Asia/Manila)':'Asia/Manila','Weekly recurrence':'weekly','Calendar exceptions':'none_reported','Title completion row 2':'Fictional completed title','Meeting evidence row 2':'Fictional row evidence','Component row 2':'external_meeting','Sharing row 2':'single_section','room applicability row 2':'not_applicable','instructor applicability row 2':'not_applicable'}))await setValue(label,value);
    };
    const assess=async()=>{await click('Check readiness');await text('Assessment freshness: Current server assessment');};
    const assessmentText=()=>evaluate("document.querySelector('section[aria-label=\"Readiness assessment\"]')?.textContent??''");
    const xlsx=spawnSync(resolve(root,'../.venv/Scripts/python.exe'),['-B','-c',"import base64,io;from openpyxl import Workbook;w=Workbook();w.active.append(['supplier','subject_code','title','sections','days','start','end','source_reference']);w.active.append(['Fictional College','SYN-GEC101','Fictional external course','SYN-A','M','09:00','10:00','Fictional memo']);b=io.BytesIO();w.save(b);print(base64.b64encode(b.getvalue()).decode())"],{windowsHide:true,encoding:'utf8'});assert.equal(xlsx.status,0);await writeFile(join(profile,'fictional.xlsx'),Buffer.from(xlsx.stdout.trim(),'base64'));
    await writeFile(join(profile,'legacy.csv'),'Year Level,Section,Course Number,Schedule\n1,SYN-A,SYN-GEC101,7:30AM - 9:00AM TTF\n');
    await check('D8-L01','real React login authenticates against live FastAPI and isolated SQLite',async()=>{
      await go({},'/login');await text('Sign in with your administrator');
      await evaluate("var u=document.querySelector('input[autocomplete=username]'),p=document.querySelector('input[type=password]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(u,'admin@example.invalid');u.dispatchEvent(new Event('input',{bubbles:true}));Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(p,"+JSON.stringify(privateConfig.password)+");p.dispatchEvent(new Event('input',{bubbles:true}));true");await click('Sign in');await eventually(()=>evaluate("location.pathname.startsWith('/admin')"),'Real login did not finish');assert.equal(await evaluate("!!document.querySelector('input[type=password]')"),false);
    });
    await check('D8-L02','real canonical import supplies session-bound preview and calendar',async()=>{await go();await text('Manual intake');await upload();await ready();await text('Complete metadata and check readiness');});
    await check('D8-L03','live policy assesses entered metadata as BLOCKED without institutional verification',async()=>{await fillComplete();await assess();const value=await assessmentText();assert.ok(value.includes('BLOCKED'));assert.ok(value.includes('AUTHORITATIVE_VERIFICATION_REQUIRED'));assert.ok(value.includes('Evidence outcome: PROVIDER_UNAVAILABLE'));await evaluate("document.querySelector('[aria-label=\"Readiness assessment\"]').scrollIntoView();true");await screenshot('D8-L03-live-fastapi-blocked');});
    await check('D8-L04','live handoff revalidates and includes original source and assessment',async()=>{await click('Prepare validated review');await outputReady();const value=await handoff();assert.ok(value.includes('CONFIRMATION-READINESS REVIEW ONLY'));assert.ok(value.includes('BLOCKED'));assert.ok(value.includes('Source row 2'));assert.ok(value.includes('EVIDENCE VERIFICATION REVIEW'));});
    await check('D8-L05','live metadata edit invalidates assessment and prevents cached handoff output',async()=>{await setValue('Academic term','Changed fictional term');assert.equal(await assessmentText(),'');assert.equal(await prepared(),false);await click('Prepare validated review');await text('Handoff unavailable');await click('Check readiness');await text('Assessment freshness: Current server assessment');});
    assert.deepEqual(errors,[]);
    const posts=requests.filter(r=>r.method==='POST');assert.ok(posts.length>0);assert.ok(posts.every(r=>['/api/auth/login','/api/external-schedules/preview-file','/api/external-schedules/review','/api/external-schedules/readiness','/api/external-schedules/readiness/invalidate','/api/external-schedules/handoff'].includes(r.path)));
    if(process.env.D8_SCREENSHOT_DIR)await mkdir(resolve(process.env.D8_SCREENSHOT_DIR),{recursive:true});
    if(process.env.D8_SCREENSHOT_DIR)await writeFile(join(resolve(process.env.D8_SCREENSHOT_DIR),'browser-results.json'),JSON.stringify(sanitizeTree({browser:version.product,user_agent:version.userAgent,node:process.version,
      scope:'Actual React/Edge -> real Uvicorn/FastAPI HTTP -> isolated SQLite password/session storage and fictional metadata. Default authority provider unavailable; BLOCKED only. No PostgreSQL or institutional records. No native printing or READY authority claim.',scenarios,captures,runtime_errors:errors,preview_and_review_posts:posts.length,activation_or_GA_mutations:0,live_http_backend:true}),null,2)+'\n',{flag:'wx'});
  } finally {
    socket?.close();for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error('Browser closed'));}
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('dashboard-d8-browser-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
