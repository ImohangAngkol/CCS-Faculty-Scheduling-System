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
import {metadata, row, preview, issue} from './externalSchedules.fixtures.mjs';
import {createHash} from 'node:crypto';

const root = fileURLToPath(new URL('../', import.meta.url));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const localTime = () => new Date(Date.now()+8*3600000).toISOString().replace('Z', '+08:00');
async function eventually(action, message) {
  const end = Date.now()+15000;
  while (Date.now()<end) {try {if (await action()) return;} catch {} await pause(60);}
  throw new Error(message);
}

test('D3 external intake browser acceptance with synthetic HTTP responses', {timeout: 150000}, async t => {
  const profile = await mkdtemp(join(tmpdir(), 'dashboard-d3-browser-'));
  let mode = {}, hold, origin, browser, vite, socket, sequence = 0;
  let fileBytesMatched=false;
  const pending = new Map(), errors = [], requests = [], scenarios = [], captures = [];
  const api = httpServer(async (request, response) => {
    response.setHeader('Access-Control-Allow-Origin',origin??'http://localhost');
    response.setHeader('Access-Control-Allow-Credentials','true');
    response.setHeader('Access-Control-Allow-Headers','Content-Type,X-CSRF-Token');
    response.setHeader('Access-Control-Allow-Methods','GET,POST,OPTIONS');
    response.setHeader('Content-Type','application/json');response.setHeader('Cache-Control','no-store');
    const reply=(status,body)=>{if(!response.destroyed){response.writeHead(status);response.end(JSON.stringify(body));}};
    if(request.method==='OPTIONS')return reply(200,{});
    requests.push({method:request.method,path:request.url});const settings={...mode};
    const path=new URL(request.url,'http://localhost').pathname;
    if(path==='/api/auth/me')return settings.anonymous?reply(401,{detail:'Sign in required'}):reply(200,{user:settings.faculty?account:{...account,role:'admin',faculty_id:null,faculty:null},csrf_token:'public-d3-fixture-value',expires_at:'2099-01-01T00:00:00Z'});
    if(path==='/api/ga/status')return reply(200,{control_version:'3c.1',process_instance_id:'d3-synthetic',active_run:null,paused_runs:[]});
    if(path==='/api/ga/latest')return reply(404,{detail:'No synthetic run'});
    if(path==='/api/external-schedules/metadata'){
      if(hold&&settings.holdMetadata)await hold;
      return settings.metadataStatus?reply(settings.metadataStatus,{detail:'Synthetic metadata failure'}):reply(200,metadata);
    }
    if(request.method==='POST'&&['/api/external-schedules/preview','/api/external-schedules/preview-file'].includes(path)){
      if(request.headers['x-csrf-token']!=='public-d3-fixture-value')return reply(403,{detail:'Missing synthetic CSRF'});
      const chunks=[];for await(const chunk of request)chunks.push(chunk);const raw=Buffer.concat(chunks);
      if(hold)await hold;
      if(settings.previewStatus)return reply(settings.previewStatus,{detail:{code:'UNSAFE_WORKBOOK',message:'Synthetic parser rejection; no subset accepted.'}});
      const rows=path.endsWith('/preview')?JSON.parse(raw.toString()).rows:[row];
      let issues=[issue('TERM_UNKNOWN'),issue('SUBJECT_NOT_IN_CATALOG','review','subject_code')];
      if(settings.invalid)issues.push(issue('REQUIRED_FIELD','error','sections'));
      if(settings.duplicates)issues.push(issue('DUPLICATE_ENTRY','error','row',[2]),issue('SECTION_OVERLAP','error','sections',[2]));
      if(settings.unresolved)issues.push(issue('UNRESOLVED_SECTION','review','sections'),issue('UNRESOLVED_ROOM','review','room'),issue('UNRESOLVED_INSTRUCTOR','review','instructor'));
      const result=preview(rows,path.endsWith('/preview')?'manual':'csv',issues);
      if(path.endsWith('/preview-file')){fileBytesMatched=raw.equals(await readFile(join(profile,'fictional.csv')));result.source_sha256=createHash('sha256').update(raw).digest('hex');}
      return reply(200,result);
    }
    return reply(404,{detail:'Not a D3 fixture endpoint'});
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
    if (!process.env.D3_SCREENSHOT_DIR) return;
    const directory = resolve(process.env.D3_SCREENSHOT_DIR), allowed = resolve(root, '../docs/screenshots/dashboard-d3');
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

    const field=async(name,value)=>evaluate("var input=document.querySelector('input[name=\""+name+"\"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,"+JSON.stringify(value)+");input.dispatchEvent(new Event('input',{bubbles:true}));true");
    const fill=async(values=row)=>{
      for(const [name,value] of Object.entries(values))if(!['days','status'].includes(name))await field(name,Array.isArray(value)?value.join('|'):value);
      await evaluate("var label=[...document.querySelectorAll('fieldset label')].find(el=>el.textContent==='Monday');if(!label.querySelector('input').checked)label.querySelector('input').click();true");
    };
    const draft=async(values=row)=>{await fill(values);await click('Add draft row');await text('Unvalidated temporary drafts');};
    const selectFile=async(name)=>{const {root:documentRoot}=await command('DOM.getDocument');const {nodeId}=await command('DOM.querySelector',{nodeId:documentRoot.nodeId,selector:'input[type=file]'});await command('DOM.setFileInputFiles',{nodeId,files:[join(profile,name)]});};
    const tableText=()=>evaluate("document.querySelector('tbody')?.textContent??''");
    await writeFile(join(profile,'fictional.csv'),'supplier,subject_code,title,sections,days,start,end,source_reference\nFictional College,SYN-GEC101,Fictional Seminar,SYN-A,M,09:00,10:00,Fictional memo\n');
    await writeFile(join(profile,'unsupported.xls'),'Fictional plain text, not Excel');
    await check('D3-B01','metadata loading, honest empty state and no confirm/lock actions',async()=>{
      let release;hold=new Promise(resolve=>release=resolve);await go({holdMetadata:true});await text('Loading reference metadata');hold=null;release();await text('Manual intake');await text('No rows to review');
      assert.equal(await evaluate("[...document.querySelectorAll('main button')].some(el=>/confirm|lock|activate/i.test(el.textContent))"),false);
    });
    await check('D3-B02','manual draft entry, multiple fields, source notes and local edit',async()=>{
      await draft();assert.ok((await tableText()).includes('Fictional Seminar'));
      await click('Edit row');await field('notes','Fictional revised note');await click('Update draft row');await text('Fictional revised note');
      await evaluate("document.querySelector('main').scrollIntoView();true");await screenshot('D3-B02-manual-intake');
    });
    await check('D3-B03','server review findings are shown without persisted or active claims',async()=>{
      await click('Review manual drafts');await text('TERM_UNKNOWN');await text('Needs review');await text('Not persisted');await text('Not activated');
      await evaluate("document.querySelector('section[aria-labelledby=review-table]').scrollIntoView();true");await screenshot('D3-B03-review-findings');
    });
    await check('D3-B04','invalid rows show required-field discrepancies with edit and re-review',async()=>{
      mode={invalid:true};await click('Edit row');await field('sections','');await click('Update draft row');await click('Review manual drafts');await text('REQUIRED_FIELD');assert.ok((await tableText()).includes('Invalid'));
      mode={};await click('Edit row');await field('sections','SYN-A');await click('Update draft row');await click('Review manual drafts');await text('TERM_UNKNOWN');assert.equal((await tableText()).includes('REQUIRED_FIELD'),false);
    });
    await check('D3-B05','duplicate and section conflict rows retain related source references',async()=>{
      mode={duplicates:true};await draft();await click('Review manual drafts');await text('DUPLICATE_ENTRY');await text('SECTION_OVERLAP');await text('Related source rows: 2');
    });
    await check('D3-B06','actual CSV selection uploads raw bytes and displays source hash/row',async()=>{
      await go();await text('Manual intake');await selectFile('fictional.csv');await click('Preview selected file');await text('Source SHA-256');await text('fictional.csv');await text('TERM_UNKNOWN');assert.ok(fileBytesMatched);
      assert.ok((await tableText()).includes('Fictional Seminar'));await evaluate("document.querySelector('section[aria-label=\"Preview provenance\"]').scrollIntoView();true");await screenshot('D3-B06-csv-preview');
    });
    await check('D3-B07','unsafe-file rejection clears prior preview and supports retry',async()=>{
      mode={previewStatus:422};await click('Preview selected file');await text('Preview failed');await text('UNSAFE_WORKBOOK');assert.equal(await evaluate("!!document.querySelector('section[aria-label=\"Preview provenance\"]')"),false);
      mode={};await click('Preview selected file');await text('Source SHA-256');
    });
    await check('D3-B08','unsupported extension is rejected before upload',async()=>{
      const before=requests.filter(r=>r.path.startsWith('/api/external-schedules/preview-file')).length;
      await selectFile('unsupported.xls');await click('Preview selected file');await text('Choose a CSV or XLSX');
      assert.equal(requests.filter(r=>r.path.startsWith('/api/external-schedules/preview-file')).length,before);
    });
    await check('D3-B09','metadata unavailability retries without fabricating references',async()=>{
      await go({metadataStatus:503});await text('Reference metadata unavailable');mode={};await click('Retry loading');await text('Manual intake');
    });
    await check('D3-B10','permission-denied preview never claims acceptance',async()=>{
      await draft();mode={previewStatus:403};await click('Review manual drafts');await text('You do not have permission');assert.equal(await evaluate("!!document.querySelector('section[aria-label=\"Preview provenance\"]')"),false);
    });
    await check('D3-B11','anonymous and faculty routes do not fetch administrator preview metadata',async()=>{
      let before=requests.filter(r=>r.path.includes('/api/external-schedules')).length;
      await go({anonymous:true});await eventually(()=>evaluate("location.pathname==='/login'"),'Anonymous redirect');assert.equal(requests.filter(r=>r.path.includes('/api/external-schedules')).length,before);
      await go({faculty:true});await eventually(()=>evaluate("document.body.textContent.includes('Access unavailable')"),'Role denial');assert.equal(requests.filter(r=>r.path.includes('/api/external-schedules')).length,before);
    });
    await check('D3-B12','mobile intake form and review table stay within viewport',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await go();await text('Manual intake');await draft();
      assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));await evaluate("document.querySelector('main').scrollIntoView();true");await screenshot('D3-B12-mobile-intake');
      await command('Emulation.setDeviceMetricsOverride',{width:1600,height:1200,deviceScaleFactor:1,mobile:false});
    });
    await check('D3-B13','refresh discards temporary work and template is explicitly fictional',async()=>{
      await command('Page.reload');await text('No rows to review');const response=await fetch(origin+'/templates/external-gec-fictional.csv');assert.equal(response.status,200);assert.match(await response.text(),/Fictional College/);
      assert.equal(await evaluate("Object.keys(localStorage).some(k=>/external|intake/i.test(k))"),false);
    });
    await check('D3-B14','clearing during a delayed preview prevents stale results reappearing',async()=>{
      await draft();let release;hold=new Promise(resolve=>release=resolve);await click('Review manual drafts');await text('Validating preview');await click('Clear temporary workspace');await text('No rows to review');hold=null;release();await pause(200);assert.equal(await evaluate("!!document.querySelector('section[aria-label=\"Preview provenance\"]')"),false);
    });
    await check('D3-B15','unresolved section room and instructor findings remain explicit',async()=>{
      mode={unresolved:true};await draft({...row,sections:['Fictional unknown'],room:'Fictional unknown',instructor:'Fictional unknown'});await click('Review manual drafts');await text('UNRESOLVED_SECTION');await text('UNRESOLVED_ROOM');await text('UNRESOLVED_INSTRUCTOR');
    });
    assert.deepEqual(errors,[]);
    const posts=requests.filter(r=>r.method==='POST');assert.ok(posts.every(r=>r.path.startsWith('/api/external-schedules/preview')));
    if(process.env.D3_SCREENSHOT_DIR)await writeFile(join(resolve(process.env.D3_SCREENSHOT_DIR),'browser-results.json'),JSON.stringify({browser:version.product,user_agent:version.userAgent,node:process.version,
      scope:'Actual React/Edge with synthetic HTTP responses; no FastAPI authorization or XLSX parser claim',scenarios,captures,runtime_errors:errors,preview_post_requests:posts.length,activation_or_GA_mutations:0,csv_raw_bytes_verified:fileBytesMatched},null,2)+'\n',{flag:'wx'});
  } finally {
    socket?.close();for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error('Browser closed'));}
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();api.closeAllConnections();await new Promise(resolve=>api.close(resolve));
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('dashboard-d3-browser-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
