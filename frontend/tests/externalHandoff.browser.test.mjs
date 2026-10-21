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
import {metadata, inputs, makeSource, makeProjection} from './externalReview.fixtures.mjs';
import {createHash} from 'node:crypto';
import {makeHandoff} from './externalHandoff.fixtures.mjs';
import {HANDOFF_LABEL} from '../src/api/externalSchedules.ts';

const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const localTime = () => new Date(Date.now()+8*3600000).toISOString().replace('Z', '+08:00');
async function eventually(action, message) {
  const end = Date.now()+15000;
  while (Date.now()<end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}

test('D5 external review browser acceptance with synthetic HTTP responses', {timeout: 150000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d5-browser-'));
  let mode = {}, hold, origin, browser, vite, socket, sequence = 0;
  let fileBytesMatched=false, currentSource=makeSource();
  const malicious='<img src=x onerror="window.__importExecuted=true"><script>window.__importExecuted=true</script>';
  const fixtureInputs=inputs.map((r,i)=>i?r:{...r,notes:'Fictional caf\u00e9 \ud83e\uddea '+malicious});
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
        fileBytesMatched=raw.equals(await readFile(join(profile,'fictional.csv')));currentSource=makeSource(fixtureInputs);currentSource.source_sha256=createHash('sha256').update(raw).digest('hex');return reply(200,currentSource);
      }
      if(path==='/api/external-schedules/handoff'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.handoffStatus)return reply(settings.handoffStatus,{detail:{code:'PREVIEW_REFERENCES_CHANGED',message:'Synthetic stale handoff reference'}});
        assert.equal(body.review_token,currentSource.review_token);
        const result=await makeHandoff(currentSource,body.mappings);
        if(settings.tampered)result.review.rows.pop();
        return reply(200,result);
      }
      if(path==='/api/external-schedules/review'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.reviewStatus)return reply(settings.reviewStatus,{detail:{code:'PREVIEW_REFERENCES_CHANGED',message:'Synthetic stale reference inventory'}});
        assert.equal(body.review_token,currentSource.review_token);
        return reply(200,makeProjection(currentSource,body.mappings,settings));
      }
    }
    return reply(404,{detail:'Not a D5 fixture endpoint'});
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
    if (!process.env.D5_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D5_SCREENSHOT_DIR), allowed = resolve(root, '../docs/screenshots/dashboard-d5');
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
    const selectFile=async()=>{const {root:documentRoot}=await command('DOM.getDocument');const {nodeId}=await command('DOM.querySelector',{nodeId:documentRoot.nodeId,selector:'input[type=file]'});await command('DOM.setFileInputFiles',{nodeId,files:[join(profile,'fictional.csv')]});};
    const upload=async()=>{await selectFile();await click('Preview selected file');};
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
    await check('D5-B01','preparation waits for fresh server validation before any output',async()=>{
      await go();await text('Manual intake');await upload();await ready();await text('Validated review handoff');assert.equal(await prepared(),false);
      let release;hold=new Promise(resolve=>release=resolve);await click('Prepare validated review');await text('Revalidating the complete handoff');assert.equal(await prepared(),false);hold=null;release();await outputReady();
    });
    await check('D5-B02','calendar filters cannot omit invalid or unresolved handoff rows',async()=>{
      await setSelect('Subject filter','SYN-GEC202');await text('1 of 4 source row(s) shown');await click('Prepare validated review');await outputReady();
      assert.equal(await evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"]').querySelectorAll('.handoff-row').length"),4);
      const value=await handoff();for(const text of ['Source row 2','Source row 3','Source row 4','Source row 5','Invalid','Ambiguous','Missing optional resource','INVALID_TIME','ROOM_OVERLAP','Draft','Tentative'])assert.ok(value.includes(text),text);
      await click('Clear review filters');await evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"]').scrollIntoView();true");await screenshot('D5-B02-complete-review-handoff');
    });
    await check('D5-B03','source hash fingerprint and import provenance remain visible without a receipt',async()=>{
      const value=await handoff();assert.ok(value.includes(currentSource.source_sha256));assert.ok(value.includes('fictional.csv'));assert.ok(value.includes('Original notes'));assert.ok(value.includes('reference')||value.includes('Reference'));
      assert.equal(value.includes(currentSource.review_token),false);assert.ok(value.includes(HANDOFF_LABEL));
    });
    await check('D5-B04','explicit mapping invalidates the handoff and new output preserves source labels',async()=>{
      await chooseRow(2);await map('Map section reference 1','section-a');await map('Map instructor','faculty-a');assert.equal(await prepared(),false);
      await click('Prepare validated review');await outputReady();const value=await handoff();for(const text of ['Imported section','Explicit preview mapping','section-a','faculty-a','SECTION_OVERLAP','INSTRUCTOR_OVERLAP','ROOM_OVERLAP'])assert.ok(value.includes(text),text);
    });
    await check('D5-B05','HTML-looking imported text renders literally and cannot execute or load markup',async()=>{
      const result=await evaluate("({text:document.querySelector('section[aria-label=\"Validated review handoff\"] article').textContent,images:document.querySelectorAll('.external-handoff-document img,.external-handoff-document script').length,executed:!!window.__importExecuted})");
      assert.ok(result.text.includes(malicious));assert.equal(result.images,0);assert.equal(result.executed,false);
      await evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"] .handoff-row').scrollIntoView();true");await screenshot('D5-B05-mappings-and-safe-text');
    });
    await check('D5-B06','stale preparation discards old output and does not enable printing',async()=>{
      mode={handoffStatus:409};await click('Prepare validated review');await text('Handoff unavailable');assert.equal(await prepared(),false);
      assert.equal(await evaluate("[...document.querySelectorAll('main button')].find(b=>b.textContent==='Revalidate and print review').disabled"),true);mode={};await upload();await ready();
    });
    await check('D5-B07','tampered or truncated review response is rejected with no partial output',async()=>{
      mode={tampered:true};await click('Prepare validated review');await text('Handoff unavailable');assert.equal(await prepared(),false);mode={};await click('Prepare validated review');await outputReady();
    });
    await check('D5-B08','print revalidates again and a stale print attempt never invokes printing',async()=>{
      await installPrintSpy();mode={handoffStatus:409};const before=handoffPosts();await click('Revalidate and print review');await text('Handoff unavailable');assert.equal(handoffPosts(),before+1);assert.equal(await evaluate('window.__printSnapshots.length'),0);mode={};await click('Prepare validated review');await outputReady();
    });
    await check('D5-B09','print-media layout contains the freshly revalidated complete batch only',async()=>{
      await command('Emulation.setEmulatedMedia',{media:'print'});const before=handoffPosts();await click('Revalidate and print review');
      await eventually(()=>evaluate('window.__printSnapshots.length===1'),'Print interception not called');assert.equal(handoffPosts(),before+1);
      const value=await evaluate('window.__printSnapshots[0]');assert.equal(value.rows,4);assert.equal(value.rootDisplay,'block');assert.equal(value.appDisplay,'none');assert.equal(value.overflow,false);assert.ok(value.text.includes('Source row 5'));assert.ok(value.text.includes('INVALID_TIME'));assert.ok(value.notes.includes(malicious));
      assert.equal(value.text.includes(currentSource.review_token),false);await command('Emulation.setEmulatedMedia',{media:''});
    });
    await check('D5-B10','ordinary browser printing cannot reuse a prior handoff snapshot',async()=>{
      await command('Emulation.setEmulatedMedia',{media:'print'});
      assert.equal(await evaluate("document.querySelector('.external-handoff-print-root').querySelectorAll('.handoff-row').length"),0);
      assert.ok(await evaluate("document.querySelector('.external-handoff-print-root').textContent.includes('No freshly revalidated print snapshot')"));
      await screenshot('D5-B10-unvalidated-print-blocked');await command('Emulation.setEmulatedMedia',{media:''});
    });
    await check('D5-B11','clear during delayed preparation cancels output and printing',async()=>{
      let release;hold=new Promise(resolve=>release=resolve);await click('Prepare validated review');await text('Revalidating the complete handoff');await click('Clear temporary workspace');hold=null;release();await text('No rows to review');await pause(100);assert.equal(await prepared(),false);assert.equal(await evaluate("!!document.querySelector('.external-handoff-print-root')"),false);
    });
    await check('D5-B12','mobile complete handoff remains readable without page overflow',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await upload();await ready();await click('Prepare validated review');await outputReady();assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));
      await evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"]').scrollIntoView();true");await screenshot('D5-B12-mobile-handoff');await command('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false});
    });
    await check('D5-B13','anonymous and faculty users cannot mount handoff or issue preview posts',async()=>{
      const before=handoffPosts();await go({anonymous:true});await eventually(()=>evaluate("location.pathname==='/login'"),'Anonymous redirect');await go({faculty:true});await eventually(()=>evaluate("document.body.textContent.includes('Access unavailable')"),'Role denial');assert.equal(handoffPosts(),before);
    });
    await check('D5-B14','printing errors discard print state and remain actionable',async()=>{
      await go();await text('Manual intake');await upload();await ready();await click('Prepare validated review');await outputReady();await evaluate("window.print=()=>{throw new Error('Synthetic print unavailable')};true");await click('Revalidate and print review');await text('Handoff unavailable');assert.equal(await prepared(),false);assert.equal(await evaluate("document.querySelector('.external-handoff-print-root').querySelectorAll('.handoff-row').length"),0);
    });
    await check('D5-B15','reload drops the handoff and no confirmation or GA mutations exist',async()=>{
      const before=handoffPosts();await command('Page.reload');await text('No rows to review');assert.equal(handoffPosts(),before);assert.equal(await prepared(),false);
      assert.equal(await evaluate("[...document.querySelectorAll('main button')].some(b=>/confirm|activate|lock/i.test(b.textContent))"),false);
    });
    assert.deepEqual(errors,[]);assert.ok(fileBytesMatched);
    const posts=requests.filter(r=>r.method==='POST');assert.ok(posts.every(r=>['/api/external-schedules/preview-file','/api/external-schedules/review','/api/external-schedules/handoff'].includes(new URL(r.path,'http://localhost').pathname)));
    if(process.env.D5_SCREENSHOT_DIR)await writeFile(join(resolve(process.env.D5_SCREENSHOT_DIR),'browser-results.json'),JSON.stringify({browser:version.product,user_agent:version.userAgent,node:process.version,
      scope:'Actual React/Edge with synthetic HTTP API; print invocation intercepted for synchronous DOM/style assertions and print-media screenshots. No physical printer, native print-dialog or PDF-layout claim.',scenarios,captures,runtime_errors:errors,preview_and_review_posts:posts.length,activation_or_GA_mutations:0,csv_raw_bytes_verified:fileBytesMatched},null,2)+'\n',{flag:'wx'});
  } finally {
    socket?.close();for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error('Browser closed'));}
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();api.closeAllConnections();await new Promise(resolve=>api.close(resolve));
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('dashboard-d5-browser-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
