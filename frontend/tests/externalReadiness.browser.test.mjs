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

const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const localTime = () => new Date(Date.now()+8*3600000).toISOString().replace('Z', '+08:00');
async function eventually(action, message) {
  const end = Date.now()+15000;
  while (Date.now()<end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}

test('D7 external review browser acceptance with synthetic HTTP responses', {timeout: 150000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d7-browser-'));
  let mode = {}, hold, origin, browser, vite, socket, sequence = 0;
  let fileBytesMatched=false, currentSource=makeSource();
  const malicious='<img src=x onerror="window.__importExecuted=true"><script>window.__importExecuted=true</script>';
  const fixtureInputs=[{...inputs[0],title:'Fictional external course',sections:['SYN-A'],room:'',instructor:'',start:'09:00',end:'10:00',days:['M'],notes:'Fictional source text only'}];
  const pending = new Map(), errors = [], requests = [], scenarios = [], captures = [];
  const api=httpServer(async(request,response)=>{
    response.setHeader('Access-Control-Allow-Origin',origin??'http://localhost');response.setHeader('Access-Control-Allow-Credentials','true');
    response.setHeader('Access-Control-Allow-Headers','Content-Type,X-CSRF-Token');response.setHeader('Access-Control-Allow-Methods','GET,POST,OPTIONS');
    response.setHeader('Content-Type','application/json');response.setHeader('Cache-Control','no-store');
    const reply=(status,body)=>{if(!response.destroyed){response.writeHead(status);response.end(JSON.stringify(body));}};
    if(request.method==='OPTIONS')return reply(200,{});
    requests.push({method:request.method,path:request.url});const settings={...mode},path=new URL(request.url,'http://localhost').pathname;
    if(path==='/api/auth/me')return settings.anonymous?reply(401,{detail:'Sign in required'}):reply(200,{user:settings.faculty?account:{...account,role:'admin',faculty_id:null,faculty:null},csrf_token:'public-d5-fixture-value',expires_at:'2099-01-01T00:00:00Z'});
    if(path==='/api/ga/status')return reply(200,{control_version:'3c.1',process_instance_id:'d5-synthetic',active_run:null,paused_runs:[]});
    if(path==='/api/ga/latest')return reply(404,{detail:'No synthetic run'});
    if(path==='/api/external-schedules/metadata')return reply(200,settings.unsupported?{...metadata,rooms:[]}:metadata);
    if(request.method==='POST'&&path.startsWith('/api/external-schedules/')){
      if(request.headers['x-csrf-token']!=='public-d5-fixture-value')return reply(403,{detail:'Synthetic CSRF missing'});
      const chunks=[];for await(const chunk of request)chunks.push(chunk);const raw=Buffer.concat(chunks);
      if(path==='/api/external-schedules/preview-file'){
        const query=new URL(request.url,'http://localhost').searchParams;let bytes=raw;const legacy=query.get('import_format')==='legacy_gec';
        if(legacy)bytes=Buffer.from(JSON.parse(raw.toString()).content_base64,'base64');
        const filename=query.get('filename');fileBytesMatched=bytes.equals(await readFile(join(profile,filename)));
        currentSource=makeSource(fixtureInputs.map(r=>({...r,...(settings.ambiguous?{days:['T','T','F']}:{}),...(legacy?{title:'',supplier:'',source_reference:''}:{})})));currentSource.source_name=filename;currentSource.source_kind=filename.endsWith('.xlsx')?'xlsx':'csv';currentSource.source_sha256=createHash('sha256').update(bytes).digest('hex');
        if(legacy)currentSource.legacy={adapter_version:'d6.1',metadata_origin:'administrator_supplied_unverified',metadata:JSON.parse(raw.toString()).metadata,rows:[{source_row:2,year_level:'1',section:'SYN-A',course_number:fixtureInputs[0].subject_code,schedule:settings.ambiguous?'7:30AM - 9:00AM TTF':'9:00AM - 10:00AM M',parse_state:settings.ambiguous?'ambiguous':'parsed',discrepancies:[]}]};
        return reply(200,currentSource);
      }
      if(path==='/api/external-schedules/readiness/invalidate')return reply(200,{status:'not_assessed',preview_only:true});
      if(path==='/api/external-schedules/readiness'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.assessmentStatus)return reply(settings.assessmentStatus,{detail:{code:'READINESS_STALE',message:'Synthetic stale preview'}});
        const result=await makeAssessment(currentSource,body.mappings,body.metadata,settings);
        if(settings.tampered)result.findings[0].action='Tampered finding';
        return reply(200,result);
      }
      if(path==='/api/external-schedules/handoff'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.handoffStatus)return reply(settings.handoffStatus,{detail:{code:'PREVIEW_REFERENCES_CHANGED',message:'Synthetic stale handoff reference'}});
        assert.equal(body.review_token,currentSource.review_token);
        const result=await makeHandoff(currentSource,body.mappings);
        if(currentSource.legacy)result.review.legacy=currentSource.legacy;
        if(body.metadata){result.readiness=await makeAssessment(currentSource,body.mappings,body.metadata,settings);result.readiness.assessment_receipt=null;result.preview_id=await handoffIdentity({review:result.review,readiness:result.readiness});}else result.preview_id=await handoffIdentity(result.review);
        if(settings.tampered)result.review.rows.pop();
        return reply(200,result);
      }
      if(path==='/api/external-schedules/review'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.reviewStatus)return reply(settings.reviewStatus,{detail:{code:'PREVIEW_REFERENCES_CHANGED',message:'Synthetic stale reference inventory'}});
        assert.equal(body.review_token,currentSource.review_token);
        const value=makeProjection(currentSource,body.mappings,settings);if(currentSource.legacy)value.legacy=currentSource.legacy;return reply(200,value);
      }
    }
    return reply(404,{detail:'Not a D7 fixture endpoint'});
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
  const go = async (settings = {}, path = '/admin/external-schedules') => {mode = settings; await command('Page.navigate', {url: origin+path});};
  const click = label => evaluate(`[...document.querySelectorAll('main button')].find(el=>el.textContent===${JSON.stringify(label)}).click();true`);
  const check = (id, title, action) => t.test(id+' '+title, async () => {
    const started_at = localTime();
    try {await action(); scenarios.push({id, title, started_at, finished_at: localTime(), result: 'PASS'});}
    catch (error) {scenarios.push({id, title, started_at, finished_at: localTime(), result: 'FAIL', error: error.message}); throw error;}
  });
  const screenshot = async name => {
    if (!process.env.D7_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D7_SCREENSHOT_DIR), allowed = resolve(root, '../docs/screenshots/dashboard-d7');
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
    await check('D7-B01','canonical CSV mounts metadata and original calendar without an assessment',async()=>{await go();await text('Manual intake');await upload();await ready();await text('Complete metadata and check readiness');assert.equal(await assessmentText(),'');await text('Not yet assessed');});
    await check('D7-B02','missing metadata gives actionable BLOCKED findings',async()=>{mode={missing:true};await assess();assert.ok((await assessmentText()).includes('MISSING_TERM'));await text('Obtain authorized source evidence');});
    await check('D7-B03','completion is explicitly administrator-provided and unverified',async()=>{await fillComplete();assert.equal(await assessmentText(),'');mode={};await assess();assert.ok((await assessmentText()).includes('AUTHORITATIVE_VERIFICATION_REQUIRED'));assert.ok((await assessmentText()).includes('BLOCKED'));await evaluate("document.querySelector('[aria-label=\"Readiness assessment\"]').scrollIntoView();true");await screenshot('D7-B03-completed-but-unverified');});
    await check('D7-B04','fictional trusted verifier READY never implies confirmation',async()=>{mode={ready:true};await assess();const value=await assessmentText();assert.ok(value.includes('READY'));assert.ok(value.includes('0 blockers'));assert.ok(value.includes('eligible for subsequent institutional confirmation review only'));await evaluate("document.querySelector('[aria-label=\"Readiness assessment\"]').scrollIntoView();true");await screenshot('D7-B04-fictional-ready');});
    await check('D7-B05','metadata edit invalidates READY and preserves unfinished fields',async()=>{await setValue('Academic term','Changed fictional term');assert.equal(await assessmentText(),'');await text('inputs changed');assert.equal(await evaluate("document.querySelector('[aria-label=\"Academic year (YYYY-YYYY)\"]').value"),'2026-2027');await assess();});
    await check('D7-B06','D4 mapping edits invalidate readiness and retain completion',async()=>{await chooseRow(2);await map('Map section reference 1','section-b');assert.equal(await assessmentText(),'');await click('Revalidate all resource mappings');await ready();assert.equal(await evaluate("document.querySelector('[aria-label=\"Academic term\"]').value"),'Changed fictional term');await assess();});
    await check('D7-B07','proposed meeting corrections retain original source and update candidate calendar',async()=>{await evaluate("document.querySelector('[aria-label=\"Propose meeting correction row 2\"]').click();true");for(const [key,value] of Object.entries({days:'T',start:'10:00',end:'11:00',reason:'Fictional supplier clarification',evidence_reference:'Fictional revised memo'}))await setValue('Proposed '+key+' row 2',value);await assess();assert.ok((await assessmentText()).includes('Proposed meeting: T'));assert.ok(await evaluate("document.querySelector('[aria-label=\"Review source row 2 SYN-GEC101\"]').title.includes('10:00')"));await text('Original day / time / status');});
    await check('D7-B08','D5 complete handoff includes current assessment and immutable source hash',async()=>{await click('Prepare validated review');await outputReady();const value=await handoff();assert.ok(value.includes('CONFIRMATION-READINESS REVIEW ONLY'));assert.ok(value.includes(currentSource.source_sha256));assert.ok(value.includes('Fictional supplier clarification'));await evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"]').scrollIntoView();true");await screenshot('D7-B08-assessed-handoff');});
    await check('D7-B09','print revalidates and includes readiness with complete original rows',async()=>{await installPrintSpy();await command('Emulation.setEmulatedMedia',{media:'print'});await click('Revalidate and print review');await eventually(()=>evaluate('window.__printSnapshots.length===1'),'Print not invoked');const value=await evaluate('window.__printSnapshots[0]');assert.ok(value.text.includes('CONFIRMATION-READINESS REVIEW ONLY'));assert.equal(value.rows,1);assert.equal(value.appDisplay,'none');await command('Emulation.setEmulatedMedia',{media:''});});
    await check('D7-B10','stale handoff discards assessment and never prints cached READY',async()=>{mode={ready:true,handoffStatus:409};await click('Revalidate and print review');await text('Handoff unavailable');assert.equal(await assessmentText(),'');assert.equal(await evaluate('window.__printSnapshots.length'),1);});
    await check('D7-B11','tampered assessment findings are rejected',async()=>{mode={tampered:true};await click('Check readiness');await text('Readiness unavailable');assert.equal(await assessmentText(),'');});
    await check('D7-B12','permission and stale assessment errors preserve editable metadata',async()=>{for(const status of [403,409,503]){mode={assessmentStatus:status};await click('Check readiness');await text('Readiness unavailable');assert.equal(await assessmentText(),'');assert.equal(await evaluate("document.querySelector('[aria-label=\"Academic year (YYYY-YYYY)\"]').value"),'2026-2027');}mode={};});
    await check('D7-B13','canonical XLSX uses the same readiness flow',async()=>{await go();await text('Manual intake');await upload('fictional.xlsx');await ready();assert.equal(currentSource.source_kind,'xlsx');await fillComplete();mode={ready:true};await assess();assert.ok((await assessmentText()).includes('READY'));});
    await check('D7-B14','legacy CSV retains ambiguous originals and editable clarification metadata',async()=>{await go({ambiguous:true});await text('Manual intake');await evaluate("var e=[...document.querySelectorAll('main label')].find(l=>l.textContent.startsWith('Import format')).querySelector('select');e.value='legacy_gec';e.dispatchEvent(new Event('change',{bubbles:true}));true");await upload('legacy.csv');await ready();await text('7:30AM - 9:00AM TTF');await fillComplete();mode={};await assess();assert.ok((await assessmentText()).includes('BLOCKED'));});
    await check('D7-B15','unknown room and faculty applicability remain explicit',async()=>{await setValue('room applicability row 2','unknown');await setValue('instructor applicability row 2','unknown');await assess();assert.ok((await assessmentText()).includes('BLOCKED'));assert.equal(await evaluate("document.querySelector('[aria-label=\"room applicability row 2\"]').value"),'unknown');});
    await check('D7-B16','mobile completion and assessment stay within viewport',async()=>{await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));await evaluate("document.querySelector('[aria-label=\"Metadata completion\"]').scrollIntoView();true");await screenshot('D7-B16-mobile-completion');await command('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false});});
    await check('D7-B17','clear during delayed assessment cannot restore stale output',async()=>{let release;hold=new Promise(resolve=>release=resolve);await click('Check readiness');await text('Assessing current source');await click('Clear temporary workspace');hold=null;release();await text('No rows to review');await pause(100);assert.equal(await assessmentText(),'');});
    await check('D7-B18','anonymous and faculty routes issue no readiness actions',async()=>{const count=requests.filter(r=>r.path.includes('/readiness')).length;await go({anonymous:true});await eventually(()=>evaluate("location.pathname==='/login'"),'Anonymous redirect');await go({faculty:true});await eventually(()=>evaluate("document.body.textContent.includes('Access unavailable')"),'Faculty denial');assert.equal(requests.filter(r=>r.path.includes('/readiness')).length,count);});
    assert.deepEqual(errors,[]);assert.ok(fileBytesMatched);
    const posts=requests.filter(r=>r.method==='POST');assert.ok(posts.every(r=>['/api/external-schedules/preview-file','/api/external-schedules/review','/api/external-schedules/handoff','/api/external-schedules/readiness','/api/external-schedules/readiness/invalidate'].includes(new URL(r.path,'http://localhost').pathname)));
    if(process.env.D7_SCREENSHOT_DIR)await writeFile(join(resolve(process.env.D7_SCREENSHOT_DIR),'browser-results.json'),JSON.stringify({browser:version.product,user_agent:version.userAgent,node:process.version,
      scope:'Actual React/Edge with synthetic HTTP API; print invocation intercepted for synchronous DOM/style assertions and print-media screenshots. No physical printer, native print-dialog or PDF-layout claim.',scenarios,captures,runtime_errors:errors,preview_and_review_posts:posts.length,activation_or_GA_mutations:0,csv_raw_bytes_verified:fileBytesMatched},null,2)+'\n',{flag:'wx'});
  } finally {
    socket?.close();for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error('Browser closed'));}
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();api.closeAllConnections();await new Promise(resolve=>api.close(resolve));
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('dashboard-d7-browser-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
