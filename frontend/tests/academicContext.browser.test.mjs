import {academicFixture as evaluationFixture} from './academicContext.fixtures.mjs';
// Actual Edge + React DOM, with CDP-intercepted fictional API responses only.
// No FastAPI, GA execution, PostgreSQL, real credentials or institutional authority.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, sep} from 'node:path';

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(action, label, timeout = 15000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {try {const result = await action(); if (result) return result;} catch {} await pause(50);}
  throw new Error(label);
}
const id = '00000000-0000-4000-8000-000000000601';
const metrics = (generation, best) => ({status:'RUNNING',generation,generation_limit:51,population_requested:4,population_actual:4,
  generation_best_fitness:best,best_ever_fitness:Math.min(100,best),average_fitness:best+50,worst_fitness:best+100,
  accepted_new_chromosomes_total:4,elapsed_ms:1000,input_fingerprint:'fictional-input',configuration_fingerprint:'fictional-configuration'});
const schedule = [
  {faculty:'10',subject:'FIC10',section:'FIC1',type:'Lecture',day:'Monday',start:'08:00',end:'09:00',room:'Fictional1',title:'Fictional course'},
  {faculty:'2',subject:'FIC10',section:'FIC1',type:'Lecture',day:'Tuesday',start:'08:00',end:'09:00',room:'Fictional1',title:'Fictional course'},
  {faculty:'2',subject:'FIC2',section:'FIC1',type:'Laboratory',day:'Wednesday',start:'08:00',end:'09:00',room:'Fictional2',title:'Fictional course'},
  {faculty:'2',subject:'FIC2',section:'FIC1',type:'Lecture',day:'Thursday',start:'08:00',end:'09:00',room:'Fictional1',title:'Fictional course'},
];
const historyRows = Array.from({length:51},(_,generation)=>({generation,timestamp:'2026-01-01T00:00:00Z',metrics:metrics(generation,generation===50?90:generation===1?110:100)}));
const run = {run_id:id,state:'PAUSED',created_at:'2026-01-01T00:00:00Z',ended_at:null,generations_recorded:51,latest:historyRows.at(-1),errors:[],skipped_generations:[],history_error:null,bytes_written:0};

test('U5B current evaluation with fictional intercepted responses', {timeout:180000}, async t => {
  const profile = await mkdtemp(join(tmpdir(),'dashboard-u5b-'));
  let vite, browser, socket, sequence=0, mode={}, browserVersion, cancelledOldDocumentRequests=0, cancelledVerifiedNetworkRequests=0;
  const cancelledNetwork = new Set();
  const pending=new Map(), handlers=new Map(), scenarios=[], captures=[], requests=[], errors=[];
  const evidence=process.env.U5B_EVIDENCE_DIR;
  function command(method,params={}) {
    return new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(new Error(`CDP timeout: ${method}`));},method==='Page.captureScreenshot'?30000:10000);
      pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});socket.send(JSON.stringify({id,method,params}));});
  }
  async function evaluate(expression) {
    const response=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(response.exceptionDetails)throw new Error(response.exceptionDetails.text);
    return response.result.value;
  }
  async function capture(name) {
    if(!evidence)return;
    await command('Page.bringToFront');
    if(name.startsWith('U5B-'))await evaluate(`document.querySelector('section[aria-label="Current Evaluation"]').scrollIntoView({block:'start'})`);
    if(name.includes('optimization'))await evaluate(`document.querySelector('[data-testid="ga-convergence"]').scrollIntoView({block:'center'})`);
    if(name.includes('sorted'))await evaluate(`document.querySelector('table').scrollIntoView({block:'center'})`);
    await evaluate('document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))');
    const image=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(join(evidence,name+'.png'),Buffer.from(image.data,'base64'),{flag:'wx'});
    captures.push({file:name+'.png',observed_at:new Date().toISOString(),viewport:{width:1280,height:960},scope:'Fictional API responses intercepted in Edge. Actual React DOM; no live FastAPI acceptance.'});
  }
  async function check(name, action){
    let failure;
    await t.test(name,async()=>{try {await action();scenarios.push({name,status:'PASS'});} catch(error){failure=error;scenarios.push({name,status:'FAIL',message:error.message});throw error;}});
    if(failure)throw new Error(`Browser scenario stopped: ${name}`);
  }
  try {
    vite=await createServer({server:{host:'localhost',port:0,strictPort:true},logLevel:'error'});await vite.listen();
    const origin=`http://localhost:${vite.httpServer.address().port}`;
    browser=spawn(process.env.PREFERENCE_TEST_BROWSER??'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
    const port=await eventually(async()=>(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0],'Edge startup');
    const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket=new WebSocket(targets.find(target=>target.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve);socket.addEventListener('error',reject);});
    socket.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.id){const entry=pending.get(message.id);pending.delete(message.id);if(message.error)entry?.reject(new Error(message.error.message));else entry?.resolve(message.result);}else handlers.get(message.method)?.(message.params);});
    browserVersion=await command('Browser.getVersion');
    await command('Runtime.enable');await command('Page.enable');await command('Network.enable');
    handlers.set('Network.loadingFailed',event=>{if(event.canceled)cancelledNetwork.add(event.requestId);});
    handlers.set('Runtime.exceptionThrown',()=>errors.push('Unexpected browser runtime exception'));
    handlers.set('Fetch.requestPaused',async({requestId,request,networkId})=>{
      const requestMode=mode,url=new URL(request.url),path=url.pathname;requests.push({path,method:request.method});
      let status=200,body;
      if(path==='/api/auth/me'){
        if(mode.anonymous){status=401;body={detail:'Authentication required'};}
        else body={user:{id:'fictional-admin',username:'admin@fictional.invalid',role:mode.role??'admin',is_active:true,faculty_id:null,faculty:null},csrf_token:'fictional-test-only',expires_at:'2099-01-01T00:00:00Z'};
      }else if(path==='/api/ga/current-evaluation'){
        if(mode.hold)await eventually(()=>!mode.hold,'Controlled fictional projection release');
        status=mode.error?503:200;body=mode.error?{detail:'Fictional projection unavailable'}:evaluationFixture(mode.projection??'current');
        if(mode.tampered)body.best={...body.best,fitness:0};
      }
      else if(path==='/api/ga/status')body={control_version:'3c.1',pause_resume_version:'3d.1',process_instance_id:'fictional-process',active_run:null,paused_runs:[]};
      else if(path==='/api/ga/latest')body={status:'success',data:{best_fitness:100,schedule,history:[],fitness_breakdown:{},population_size:4,generations_completed:1}};
      else if(path==='/api/chromosomes/best'){
        status=mode.savedError?503:200;body=mode.savedError?{detail:'Synthetic unavailable'}:{status:'success',data:{exists:!mode.noSaved,fitness:mode.noSaved?null:810,created_at:'2026-01-01T00:00:00Z'}};
      }else if(path==='/api/ga/runs'){
        status=mode.historyError?503:200;body=mode.historyError?{detail:{message:'Synthetic history unavailable',code:'GA_HISTORY_UNAVAILABLE'}}:{schema_version:1,items:[run],total:1,offset:0,limit:20,errors:[]};
      }else if(path.endsWith('/generations')){
        const offset=Number(url.searchParams.get('offset')??0);body={schema_version:1,run,items:historyRows.slice(offset,offset+50),total:51,offset,limit:50};
      }else if(path==='/api/faculty/'||path==='/api/faculty')body={data:[]};
      else {status=404;body={detail:'No fictional handler for this route'};}
      try {await command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:origin},{name:'Access-Control-Allow-Credentials',value:'true'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});}
      catch(error){
        if(error.message==='Invalid InterceptionId.'&&requestMode!==mode)cancelledOldDocumentRequests++;
        else if(error.message==='Invalid InterceptionId.'&&networkId){
          try{await eventually(()=>cancelledNetwork.has(networkId),'Verified cancelled request',1000);cancelledVerifiedNetworkRequests++;}
          catch{errors.push('CDP fulfillment without confirmed cancellation: '+error.message);}
        }else errors.push('CDP fulfillment: '+error.message);
      }
    });
    // Exact API origin: a wildcard /api/ path also intercepts Vite's /src/api/*.ts modules.
    await command('Fetch.enable',{patterns:[{urlPattern:`${process.env.VITE_API_URL ?? 'http://localhost:8000'}/*`,requestStage:'Request'}]});
    await command('Emulation.setDeviceMetricsOverride',{width:1280,height:960,deviceScaleFactor:1,mobile:false});
    async function go(path,settings={}){mode=settings;const previous=await evaluate('performance.timeOrigin');await command('Page.navigate',{url:origin+path});await eventually(()=>evaluate(`performance.timeOrigin!==${previous}&&document.readyState==='complete'`),'Fresh document');}
    const text=label=>eventually(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(label)})`),`Missing text: ${label}`);
    const click=label=>evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)}).click()`);
    await check('U5B-B01 current candidate shows exact fitness and recorded history identity',async()=>{
      await go('/admin/chromosomes');await text('Current Best Recorded Chromosome');
      assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),'12.3456789');
      assert.ok(await evaluate(`[...document.querySelectorAll('dt')].some(el=>el.textContent==='Current Runs:'&&el.nextElementSibling.textContent==='1')`));
      await capture('U5B-B01-current-best');
    });
    await check('U5B-B02 implementation provenance remains separate from academic approval',async()=>{
      await evaluate(`document.querySelector('section[aria-label="Current Evaluation"] summary').click()`);
      await text('preference-policy-2');await text('Server-verified scheduling scope: Fictional Department');await text('fictional-dataset, revision fictional-revision.1');await text('FICTIONAL-YEAR / FICTIONAL-TERM');await text('Institutional approval is not established');await capture('U5B-B02-provenance');
    });
    await check('U5B-B03 zero current runs has dash fitness and no saved chromosome',async()=>{
      await go('/admin/chromosomes',{projection:'empty'});await text('No Current Best Chromosome');
      assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),String.fromCharCode(8212));
      assert.ok(await evaluate(`[...document.querySelectorAll('dt')].some(el=>el.textContent==='Current Runs:'&&el.nextElementSibling.textContent==='0')`));
    });
    await check('U5B-B04 legacy policy cannot supply a current penalty',async()=>{await go('/admin/chromosomes',{projection:'legacy'});await text('LEGACY_INCOMPATIBLE');await text('ACADEMIC_CONTEXT_CHANGED');assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),String.fromCharCode(8212));});
    await check('U5B-B05 absent historical provenance remains unknown',async()=>{await go('/admin/history',{projection:'unknown'});await text('UNKNOWN_COMPATIBILITY');await text('RUN_START_PROVENANCE_NOT_CAPTURED');await capture('U5B-B05-unknown');});
    await check('U5B-B06 unavailable projection is retryable and never zero-fills a count',async()=>{
      await go('/admin/chromosomes',{error:true});await text('Current Evaluation unavailable');
      assert.ok(await evaluate(`[...document.querySelectorAll('dt')].some(el=>el.textContent==='Current Runs:'&&el.nextElementSibling.textContent===String.fromCharCode(8212))`));
      mode.error=false;await click('Retry current evaluation');await text('Current Best Recorded Chromosome');
    });
    await check('U5B-B07 a tampered response candidate is rejected',async()=>{await go('/admin/chromosomes',{tampered:true});await text('Current evaluation provenance is invalid or unsupported');assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),String.fromCharCode(8212));});
    await check('U5B-B08 partial archive inspection makes no global best claim',async()=>{await go('/admin/chromosomes',{projection:'incomplete'});await text('Review incomplete: ARCHIVED_RECORD_UNREADABLE');assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),String.fromCharCode(8212));});
    await check('U5B-B09 a real measured zero stays zero',async()=>{await go('/admin/chromosomes',{projection:'zero'});await text('Current Best Recorded Chromosome');assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),'0');});
    await check('U5B-B10 current history links inspect the identified run without mixing runs',async()=>{
      await go('/admin/history');await text('Current Best Recorded Chromosome');
      await evaluate(`[...document.querySelectorAll('a')].find(el=>el.textContent==='Inspect current best and generation history').click()`);
      await text('generations recorded');assert.ok(await evaluate(`location.search.includes('run=${id}')&&!!document.querySelector('select[aria-label="Historical run"]')`));
    });
    await check('U5B-B11 archive saved-best penalty remains unchanged and its baseline stays blocked',async()=>{
      await go('/admin/chromosomes?view=archive');await text('Archived penalty (compatibility unverified)');await text('810');
      assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(el=>el.textContent.includes('Baseline unavailable')).disabled`));
      assert.ok(await evaluate(`!!document.querySelector('a[href$="/best/download"]')`));
    });
    await check('U5B-B12 loading and route cleanup do not invent current results',async()=>{
      await go('/admin/chromosomes',{hold:true});await text('Checking Current Evaluation');
      assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),String.fromCharCode(8212));
      mode.hold=false;await text('Current Best Recorded Chromosome');
    });
    await check('U5B-B13 mobile current provenance wraps without page overflow',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await go('/admin/chromosomes');await text('Current Best Recorded Chromosome');
      assert.ok(await evaluate(`document.documentElement.scrollWidth<=innerWidth`));await capture('U5B-B13-mobile');
    });
    await check('U5B-B14 faculty and anonymous routes cannot expose current evaluation',async()=>{
      await go('/admin/chromosomes',{role:'faculty'});await text('Access unavailable');
      await go('/admin/history',{anonymous:true});await eventually(()=>evaluate(`location.pathname==='/login'`),'Anonymous redirect');
    });
    await check('U5B-B15 missing server context is explicit and cannot create current results',async()=>{
      await go('/admin/chromosomes',{projection:'unavailable'});await text('Server academic context is unavailable');await text('no academic year, term or dataset is inferred');
      assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),String.fromCharCode(8212));await capture('U5B-B15-unavailable-context');
    });
    await check('U5B-B16 the actual contract uses CURRENT with a verified dataset and original history link',async()=>{
      await go('/admin/history');await text('Current Best Recorded Chromosome');await text('ga-result-compatibility-v2');
      assert.ok(await evaluate(`[...document.querySelectorAll('tbody tr')].some(row=>row.textContent.includes('CURRENT')&&!row.textContent.includes('CURRENT_COMPATIBLE'))`));
      assert.ok(await evaluate(`!![...document.querySelectorAll('a')].find(el=>el.textContent==='Inspect current best and generation history')`));
    });
    await check('U5B-B17 immutable run-start and configuration identities are accessible',async()=>{
      await evaluate(`[...document.querySelectorAll('summary')].find(el=>el.textContent==='Run-start provenance').click()`);
      await text('Run start: 2026-11-04T00:00:00+08:00');await text('Configuration:');await text('Original context: FICTIONAL-YEAR / FICTIONAL-TERM');await capture('U5B-B17-run-start-provenance');
    });
    assert.deepEqual(errors,[]);assert.ok(requests.every(r=>r.method==='GET'),'Presentation must not mutate APIs');
  } finally {
    if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({browser:browserVersion?.product,node:process.version,scope:'Actual headless Edge React DOM; CDP-intercepted fictional API responses. No FastAPI, GA generation or database acceptance.',scenarios,captures,requests,cancelled_old_document_requests:cancelledOldDocumentRequests,cancelled_verified_network_requests:cancelledVerifiedNetworkRequests,runtime_errors:errors},null,2)+'\n',{flag:'wx'});
    socket?.close();for(const item of pending.values())item.reject(new Error('Browser closed'));
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&target.split(sep).at(-1).startsWith('dashboard-u5b-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
