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

const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const localTime = () => new Date(Date.now()+8*3600000).toISOString().replace('Z', '+08:00');
async function eventually(action, message) {
  const end = Date.now()+15000;
  while (Date.now()<end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}

test('D4 external review browser acceptance with synthetic HTTP responses', {timeout: 150000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d4-browser-'));
  let mode = {}, hold, origin, browser, vite, socket, sequence = 0;
  let fileBytesMatched=false, currentSource=makeSource();
  const pending = new Map(), errors = [], requests = [], scenarios = [], captures = [];
  const api=httpServer(async(request,response)=>{
    response.setHeader('Access-Control-Allow-Origin',origin??'http://localhost');response.setHeader('Access-Control-Allow-Credentials','true');
    response.setHeader('Access-Control-Allow-Headers','Content-Type,X-CSRF-Token');response.setHeader('Access-Control-Allow-Methods','GET,POST,OPTIONS');
    response.setHeader('Content-Type','application/json');response.setHeader('Cache-Control','no-store');
    const reply=(status,body)=>{if(!response.destroyed){response.writeHead(status);response.end(JSON.stringify(body));}};
    if(request.method==='OPTIONS')return reply(200,{});
    requests.push({method:request.method,path:request.url});const settings={...mode},path=new URL(request.url,'http://localhost').pathname;
    if(path==='/api/auth/me')return settings.anonymous?reply(401,{detail:'Sign in required'}):reply(200,{user:settings.faculty?account:{...account,role:'admin',faculty_id:null,faculty:null},csrf_token:'public-d4-fixture-value',expires_at:'2099-01-01T00:00:00Z'});
    if(path==='/api/ga/status')return reply(200,{control_version:'3c.1',process_instance_id:'d4-synthetic',active_run:null,paused_runs:[]});
    if(path==='/api/ga/latest')return reply(404,{detail:'No synthetic run'});
    if(path==='/api/external-schedules/metadata')return reply(200,settings.unsupported?{...metadata,rooms:[]}:metadata);
    if(request.method==='POST'&&path.startsWith('/api/external-schedules/')){
      if(request.headers['x-csrf-token']!=='public-d4-fixture-value')return reply(403,{detail:'Synthetic CSRF missing'});
      const chunks=[];for await(const chunk of request)chunks.push(chunk);const raw=Buffer.concat(chunks);
      if(path==='/api/external-schedules/preview-file'){
        fileBytesMatched=raw.equals(await readFile(join(profile,'fictional.csv')));currentSource=makeSource();currentSource.source_sha256=createHash('sha256').update(raw).digest('hex');return reply(200,currentSource);
      }
      if(path==='/api/external-schedules/review'){
        const body=JSON.parse(raw.toString());if(hold)await hold;
        if(settings.reviewStatus)return reply(settings.reviewStatus,{detail:{code:'PREVIEW_REFERENCES_CHANGED',message:'Synthetic stale reference inventory'}});
        assert.equal(body.review_token,currentSource.review_token);
        return reply(200,makeProjection(currentSource,body.mappings,settings));
      }
    }
    return reply(404,{detail:'Not a D4 fixture endpoint'});
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
    if (!process.env.D4_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D4_SCREENSHOT_DIR), allowed = resolve(root, '../docs/screenshots/dashboard-d4');
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
    await writeFile(join(profile,'fictional.csv'),[fields.join(','),...inputs.map(input=>fields.map(k=>cell(input[k])).join(','))].join('\n')+'\n');
    await check('D4-B01','signed-source review loading and weekly calendar provenance',async()=>{
      await go();await text('Manual intake');let release;hold=new Promise(resolve=>release=resolve);await upload();await text('Validating complete source');assert.equal(await calendar(),false);hold=null;release();await ready();await text('4 of 4 source row(s) shown');
      assert.equal(await evaluate("document.querySelector('main').textContent.includes('public-d4-fictional-receipt')"),false);
      assert.equal(await evaluate("document.querySelector('.fc-col-header').textContent.includes('2000')"),false);
    });
    await check('D4-B02','overlapping entries occupy separate calendar lanes with row-level details',async()=>{
      await eventually(()=>evaluate("document.querySelectorAll('.fc-timegrid-event').length===3"),'Three valid calendar events');
      const layout=await evaluate("[2,3].map(n=>document.querySelector('button[aria-label^=\"Review source row '+n+' \"]').closest('.fc-timegrid-event').getBoundingClientRect()).map(r=>({left:r.left,right:r.right,top:r.top,bottom:r.bottom}))");
      assert.ok(layout[0].top<layout[1].bottom&&layout[1].top<layout[0].bottom);assert.ok(layout[0].right<=layout[1].left+2||layout[1].right<=layout[0].left+2);
      await evaluate("document.querySelector('button[aria-label^=\"Review source row 2 \"]').click();true");await text('Source row 2');await text('Resource overlap');
      await evaluate("document.querySelector('section[aria-label=\"Calendar review\"]').scrollIntoView();true");await screenshot('D4-B02-weekly-overlap-calendar');
    });
    await check('D4-B03','section supplier subject and Draft/Tentative filters combine',async()=>{
      await setSelect('Review section','section-b');await text('1 of 4 source row(s) shown');await click('Clear review filters');
      await setSelect('Supplying college filter','Another Fictional College');await text('1 of 4 source row(s) shown');
      await setSelect('Draft/Tentative filter','draft');await text('No source rows match');await click('Clear review filters');
      await setSelect('Subject filter','SYN-GEC202');await text('1 of 4 source row(s) shown');await setSelect('Draft/Tentative filter','tentative');await text('No source rows match');await click('Clear review filters');
    });
    await check('D4-B04','reference-state filters distinguish ambiguity and missing optional resources',async()=>{
      await setSelect('Reference state filter','ambiguous');await text('1 of 4 source row(s) shown');await setSelect('Reference state filter','missing_optional');await text('2 of 4 source row(s) shown');await setSelect('Reference state filter','resolved');await text('2 of 4 source row(s) shown');await click('Clear review filters');
    });
    await check('D4-B05','explicit mappings trigger full-batch identity conflicts and preserve original text/hash',async()=>{
      await chooseRow(2);await text('Ambiguous');await map('Map section reference 1','section-a');assert.equal(await calendar(),false);
      await map('Map instructor','faculty-a');await click('Revalidate all resource mappings');await ready();
      await eventually(async()=>{const text=await findings();return text.includes('SECTION_OVERLAP')&&text.includes('INSTRUCTOR_OVERLAP')&&text.includes('ROOM_OVERLAP');},'Mapped canonical resource conflicts');
      await text('Imported section');await text('Explicit preview mapping');assert.ok((await reviewText()).includes(currentSource.source_sha256));
      await evaluate("document.querySelector('section[aria-label=\"Source reconciliation\"]').scrollIntoView();true");await screenshot('D4-B05-explicit-resource-reconciliation');
    });
    await check('D4-B06','distinct canonical mappings clear corresponding conflicts without changing source',async()=>{
      await map('Map section reference 1','section-b');await map('Map room','room-b');await map('Map instructor','faculty-b');await click('Revalidate all resource mappings');await ready();assert.equal((await findings()).includes('OVERLAP'),false);await text('Imported section');
    });
    await check('D4-B07','clearing explicit mappings restores unresolved and ambiguous source states',async()=>{
      await map('Map section reference 1','');await map('Map room','');await map('Map instructor','');await click('Revalidate all resource mappings');await ready();await text('Ambiguous');await text('Unresolved');
    });
    await check('D4-B08','invalid time rows remain selectable as details but are not plotted',async()=>{
      await chooseRow(5);await text('Source row 5 is not plotted');await eventually(async()=>(await findings()).includes('INVALID_TIME'),'Invalid time discrepancy');
      assert.equal(await evaluate("!!document.querySelector('button[aria-label^=\"Review source row 5 \"]')"),false);
      await evaluate("document.querySelector('section[aria-label=\"Source reconciliation\"]').scrollIntoView();true");await screenshot('D4-B08-invalid-source-details');
    });
    await check('D4-B09','missing optional resources can map only to listed existing records',async()=>{
      await chooseRow(4);await text('Missing optional resource');await map('Map room','room-a');await map('Map instructor','faculty-b');await click('Revalidate all resource mappings');await ready();
      const states=await evaluate("document.querySelector('section[aria-label=\"Source reconciliation\"]').textContent");assert.ok(states.includes('Explicit preview mapping'));assert.ok(states.includes('(not supplied)'));
    });
    await check('D4-B10','stale-source review removes the calendar until the source is re-previewed',async()=>{
      mode={reviewStatus:409};await click('Revalidate all resource mappings');await text('Review unavailable');assert.equal(await calendar(),false);
      mode={};await upload();await ready();await text('4 of 4 source row(s) shown');
    });
    await check('D4-B11','clearing during delayed revalidation prevents stale source projection',async()=>{
      let release;hold=new Promise(resolve=>release=resolve);await click('Revalidate all resource mappings');await text('Validating complete source');await click('Clear temporary workspace');await text('No rows to review');hold=null;release();await pause(150);assert.equal(await calendar(),false);
    });
    await check('D4-B12','mobile filters reconciliation and contained calendar remain usable',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await upload();await ready();assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));
      await evaluate("document.querySelector('section[aria-label=\"Calendar review\"]').scrollIntoView();true");await screenshot('D4-B12-mobile-review');await command('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false});
    });
    await check('D4-B13','anonymous and faculty users cannot mount administrator review',async()=>{
      const before=requests.filter(r=>r.path.includes('/api/external-schedules')).length;await go({anonymous:true});await eventually(()=>evaluate("location.pathname==='/login'"),'Anonymous redirect');
      await go({faculty:true});await eventually(()=>evaluate("document.body.textContent.includes('Access unavailable')"),'Role denial');assert.equal(requests.filter(r=>r.path.includes('/api/external-schedules')).length,before);
    });
    await check('D4-B14','unsupported resource inventory disables selection and exposes state',async()=>{
      await go({unsupported:true});await text('Manual intake');await upload();await ready();await chooseRow(2);await text('Unsupported');assert.equal(await evaluate("document.querySelector('select[aria-label=\"Map room\"]').disabled"),true);
    });
    await check('D4-B15','calendar has no drag resize confirmation or GA mutation controls',async()=>{
      assert.equal(await evaluate("document.querySelectorAll('.fc-event-resizer,.fc-event-draggable').length"),0);
      assert.equal(await evaluate("[...document.querySelectorAll('main button')].some(el=>/confirm|lock|activate/i.test(el.textContent))"),false);
      const before=requests.filter(r=>r.method==='POST').length;await command('Page.reload');await text('No rows to review');assert.equal(requests.filter(r=>r.method==='POST').length,before);
    });
    assert.deepEqual(errors,[]);assert.ok(fileBytesMatched);
    const posts=requests.filter(r=>r.method==='POST');assert.ok(posts.every(r=>['/api/external-schedules/preview-file','/api/external-schedules/review'].includes(new URL(r.path,'http://localhost').pathname)));
    if(process.env.D4_SCREENSHOT_DIR)await writeFile(join(resolve(process.env.D4_SCREENSHOT_DIR),'browser-results.json'),JSON.stringify({browser:version.product,user_agent:version.userAgent,node:process.version,
      scope:'Actual React/FullCalendar/Edge with synthetic HTTP responses; no live D4 API authorization claim',scenarios,captures,runtime_errors:errors,preview_and_review_posts:posts.length,activation_or_GA_mutations:0,csv_raw_bytes_verified:fileBytesMatched},null,2)+'\n',{flag:'wx'});
  } finally {
    socket?.close();for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error('Browser closed'));}
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();api.closeAllConnections();await new Promise(resolve=>api.close(resolve));
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('dashboard-d4-browser-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
