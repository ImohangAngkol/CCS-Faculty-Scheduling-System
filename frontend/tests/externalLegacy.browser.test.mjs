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
import {handoffIdentity,HANDOFF_LABEL} from '../src/api/externalSchedules.ts';

const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const localTime = () => new Date(Date.now()+8*3600000).toISOString().replace('Z', '+08:00');
async function eventually(action, message) {
  const end = Date.now()+15000;
  while (Date.now()<end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}

test('D6 legacy intake browser acceptance with synthetic HTTP responses', {timeout: 150000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d6-browser-'));
  let mode = {}, hold, origin, browser, vite, socket, sequence = 0;
  let fileBytesMatched=false, currentSource=makeSource();
  const malicious='<img src=x onerror="window.__importExecuted=true"><script>window.__importExecuted=true</script>';
  const fixtureInputs=inputs.map((r,i)=>({...r,supplier:'',title:'',source_reference:'',academic_term:'',room:'',instructor:'',sections:['Imported section'],days:i<2?['M']:[],start:i<2?'07:30':'',end:i<2?'09:00':''}));
  const legacyOriginals=fixtureInputs.map((r,i)=>({source_row:i+2,year_level:'1',section:'Imported section',course_number:r.subject_code,schedule:i<2?'7:30AM - 9:00AM M':i===2?'7:30AM - 9:00AM TTF':malicious,parse_state:i<2?'parsed':i===2?'ambiguous':'invalid',discrepancies:[{code:i<2?'LEGACY_INCOMPLETE_METADATA':i===2?'LEGACY_AMBIGUOUS_DAYS':'LEGACY_INVALID_SCHEDULE',severity:i===3?'error':'review',field:'Schedule',message:'Fictional legacy finding; not confirmed.',related_rows:[]}]}));
  function projection(source,mappings=[]) {
    const value=makeProjection(source,mappings);value.legacy=source.legacy;
    value.rows.forEach((r,i)=>{r.calendar_supported=i<2;r.status='invalid';r.discrepancies.push(...source.legacy.rows[i].discrepancies);});
    return value;
  }
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
        if(settings.importError)return reply(422,{detail:{code:'INVALID_LEGACY_COLUMNS',message:'Fictional malformed header; no rows accepted'}});
        const body=JSON.parse(raw.toString());const bytes=Buffer.from(body.content_base64,'base64');
        assert.equal(new URL(request.url,'http://localhost').searchParams.get('import_format'),'legacy_gec');
        fileBytesMatched=bytes.equals(await readFile(join(profile,'fictional.csv')));
        currentSource=makeSource(fixtureInputs.map(r=>({...r,...body.metadata})));currentSource.source_sha256=createHash('sha256').update(bytes).digest('hex');
        currentSource.legacy={adapter_version:'d6.1',metadata_origin:'administrator_supplied_unverified',metadata:body.metadata,rows:structuredClone(legacyOriginals)};
        currentSource.rows.forEach((r,i)=>{r.status='invalid';r.discrepancies.push(...legacyOriginals[i].discrepancies);});
        return reply(200,currentSource);
      }
      if(path==='/api/external-schedules/handoff'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.handoffStatus)return reply(settings.handoffStatus,{detail:{code:'PREVIEW_REFERENCES_CHANGED',message:'Synthetic stale handoff reference'}});
        assert.equal(body.review_token,currentSource.review_token);
        const result=await makeHandoff(currentSource,body.mappings);result.review=projection(currentSource,body.mappings);result.preview_id=await handoffIdentity(result.review);
        if(settings.tampered){result.review.legacy.rows[0].schedule='tampered';result.preview_id=await handoffIdentity(result.review);}
        return reply(200,result);
      }
      if(path==='/api/external-schedules/review'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.reviewStatus)return reply(settings.reviewStatus,{detail:{code:'PREVIEW_REFERENCES_CHANGED',message:'Synthetic stale reference inventory'}});
        assert.equal(body.review_token,currentSource.review_token);
        return reply(200,projection(currentSource,body.mappings));
      }
    }
    return reply(404,{detail:'Not a D6 fixture endpoint'});
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
    if (!process.env.D6_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D6_SCREENSHOT_DIR), allowed = resolve(root, '../docs/screenshots/dashboard-d6');
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
    await writeFile(join(profile,'fictional.csv'),'Year Level,Section,Course Number,Schedule\n'+legacyOriginals.map(r=>['1','Imported section',r.course_number,r.schedule].map(v=>'"'+v.replaceAll('"','""')+'"').join(',')).join('\n')+'\n');
    const selectFormat=()=>evaluate("var e=[...document.querySelectorAll('main label')].find(l=>l.textContent.startsWith('Import format')).querySelector('select');e.value='legacy_gec';e.dispatchEvent(new Event('change',{bubbles:true}));true");
    const fillMetadata=async(name,value)=>evaluate("var e=document.querySelector('fieldset input[data-unused]')||[...document.querySelectorAll('fieldset label')].find(l=>l.textContent.includes("+JSON.stringify(name)+")).querySelector('input');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,"+JSON.stringify(value)+");e.dispatchEvent(new Event('input',{bubbles:true}));true");
    const handoff=()=>evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"] article')?.textContent??''");
    const outputReady=()=>eventually(async()=>(await handoff()).includes('Preview identity: d5-'),'Complete handoff did not load');
    const prepared=()=>evaluate("!!document.querySelector('section[aria-label=\"Validated review handoff\"] article')");
    const handoffPosts=()=>requests.filter(r=>r.method==='POST'&&r.path==='/api/external-schedules/handoff').length;
    const installPrintSpy=()=>evaluate(`window.__printSnapshots=[];window.print=()=>{const root=document.querySelector('.external-handoff-print-root');window.__printSnapshots.push({text:root.textContent,rows:root.querySelectorAll('.handoff-row').length,rootDisplay:getComputedStyle(root).display,appDisplay:getComputedStyle(document.querySelector('#root')).display,overflow:root.scrollWidth>innerWidth,notes:root.querySelector('.handoff-notes')?.textContent});};true`);
    await check('D6-B01','canonical remains default and legacy requires explicit selection',async()=>{
      await go();await text('Manual intake');assert.equal(await evaluate("[...document.querySelectorAll('main label')].find(l=>l.textContent.startsWith('Import format')).querySelector('select').value"),'canonical');await selectFormat();await text('Legacy metadata mapping');
    });
    await check('D6-B02','missing metadata prompts and fictional template are available',async()=>{
      await text('administrator-supplied (unverified)');assert.ok(await evaluate("!!document.querySelector('a[href=\"/templates/external-gec-legacy-fictional.csv\"]')"));await text('Blank supplier/source reference');
    });
    await check('D6-B03','legacy upload retains exact file hash and all original rows',async()=>{
      await upload();await ready();await text('Original source row 5');await text(currentSource.source_sha256);await text('LEGACY_INVALID_SCHEDULE');assert.equal(currentSource.rows.length,4);assert.ok(fileBytesMatched);
    });
    await check('D6-B04','ambiguous and invalid schedules stay visible outside the calendar',async()=>{
      await text('LEGACY_AMBIGUOUS_DAYS');assert.equal(await evaluate("document.querySelectorAll('[data-testid=external-review-calendar] .fc-event').length"),2);await evaluate("document.querySelector('[aria-label=\"Legacy source provenance\"]').scrollIntoView();true");await screenshot('D6-B04-originals-and-parsing');
    });
    await check('D6-B05','explicit section mapping reuses D4 and identifies overlaps',async()=>{
      await chooseRow(2);await map('Map section reference 1','section-a');await click('Revalidate all resource mappings');await ready();await chooseRow(3);await map('Map section reference 1','section-a');await click('Revalidate all resource mappings');await ready();await text('SECTION_OVERLAP');
    });
    await check('D6-B06','metadata edits invalidate old output and repreview labels their origin',async()=>{
      await click('Prepare validated review');await outputReady();await fillMetadata('Supplying college','Fictional Supplying College');await text('No rows to review');assert.equal(await prepared(),false);await fillMetadata('Source reference','Fictional letter 1');await fillMetadata('Academic term','Unverified example term');await upload();await ready();await text('Fictional Supplying College');await text('Administrator-supplied preview metadata');
    });
    await check('D6-B07','D5 handoff contains complete legacy provenance including invalid rows',async()=>{
      await click('Prepare validated review');await outputReady();const value=await handoff();for(const v of ['Original source row 2','Original source row 5','Parsing: ambiguous','LEGACY_INVALID_SCHEDULE','Term unknown','Not institutional confirmation'])if(v!=='Term unknown')assert.ok(value.includes(v),v);await evaluate("document.querySelector('section[aria-label=\"Validated review handoff\"]').scrollIntoView();true");await screenshot('D6-B07-complete-legacy-handoff');
    });
    await check('D6-B08','tampered legacy originals reject even a recomputed content fingerprint',async()=>{
      mode={tampered:true};await click('Prepare validated review');await text('Handoff unavailable');assert.equal(await prepared(),false);mode={};await upload();await ready();
    });
    await check('D6-B09','stale receipt response blocks output',async()=>{
      mode={handoffStatus:409};await click('Prepare validated review');await text('Handoff unavailable');assert.equal(await prepared(),false);mode={};
    });
    await check('D6-B10','malformed import clears prior results and supports retry',async()=>{
      mode={importError:true};await upload();await text('INVALID_LEGACY_COLUMNS');assert.equal(await calendar(),false);mode={};await upload();await ready();
    });
    await check('D6-B11','legacy imported markup remains literal text',async()=>{
      await click('Prepare validated review');await outputReady();assert.ok((await handoff()).includes(malicious));assert.equal(await evaluate("document.querySelectorAll('.external-handoff-document img,.external-handoff-document script').length"),0);assert.equal(await evaluate('!!window.__importExecuted'),false);
    });
    await check('D6-B12','fresh print includes every original and metadata origin',async()=>{
      await installPrintSpy();await command('Emulation.setEmulatedMedia',{media:'print'});await click('Revalidate and print review');await eventually(()=>evaluate('window.__printSnapshots.length===1'),'Print not invoked');const value=await evaluate('window.__printSnapshots[0]');assert.equal(value.rows,4);assert.ok(value.text.includes('Original source row 5'));assert.ok(value.text.includes('administrator')||value.text.includes('Administrator'));assert.equal(value.appDisplay,'none');await command('Emulation.setEmulatedMedia',{media:''});
    });
    await check('D6-B13','mobile legacy provenance does not overflow the page',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));await evaluate("document.querySelector('[aria-label=\"Legacy source provenance\"]').scrollIntoView();true");await screenshot('D6-B13-mobile-legacy');await command('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false});
    });
    await check('D6-B14','clear and refresh discard temporary data with no confirmation actions',async()=>{
      await click('Clear temporary workspace');await text('No rows to review');await command('Page.reload');await text('No rows to review');assert.equal(await prepared(),false);assert.equal(await evaluate("[...document.querySelectorAll('main button')].some(b=>/confirm|activate|lock/i.test(b.textContent))"),false);
    });
    await check('D6-B15','anonymous and faculty routes cannot issue intake or handoff requests',async()=>{
      const before=requests.filter(r=>r.method==='POST').length;await go({anonymous:true});await eventually(()=>evaluate("location.pathname==='/login'"),'Anonymous redirect');await go({faculty:true});await eventually(()=>evaluate("document.body.textContent.includes('Access unavailable')"),'Faculty denial');assert.equal(requests.filter(r=>r.method==='POST').length,before);
    });
    assert.deepEqual(errors,[]);assert.ok(fileBytesMatched);
    const posts=requests.filter(r=>r.method==='POST');assert.ok(posts.every(r=>['/api/external-schedules/preview-file','/api/external-schedules/review','/api/external-schedules/handoff'].includes(new URL(r.path,'http://localhost').pathname)));
    if(process.env.D6_SCREENSHOT_DIR)await writeFile(join(resolve(process.env.D6_SCREENSHOT_DIR),'browser-results.json'),JSON.stringify({browser:version.product,user_agent:version.userAgent,node:process.version,
      scope:'Actual React/Edge with synthetic HTTP API; print invocation intercepted for synchronous DOM/style assertions and print-media screenshots. No physical printer, native print-dialog or PDF-layout claim.',scenarios,captures,runtime_errors:errors,preview_and_review_posts:posts.length,activation_or_GA_mutations:0,legacy_decoded_bytes_verified:fileBytesMatched},null,2)+'\n',{flag:'wx'});
  } finally {
    socket?.close();for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error('Browser closed'));}
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();api.closeAllConnections();await new Promise(resolve=>api.close(resolve));
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('dashboard-d6-browser-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
