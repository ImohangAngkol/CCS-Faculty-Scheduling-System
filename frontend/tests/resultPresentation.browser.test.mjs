import {evaluationFixture} from './currentEvaluation.fixtures.mjs';
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
const id = '00000000-0000-4000-8000-000000000001';
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

test('U1 rendered results presentation with fictional intercepted responses', {timeout:180000}, async t => {
  const profile = await mkdtemp(join(tmpdir(),'dashboard-u1-'));
  let vite, browser, socket, sequence=0, mode={}, browserVersion;
  const pending=new Map(), handlers=new Map(), scenarios=[], captures=[], requests=[], errors=[];
  const evidence=process.env.U1_EVIDENCE_DIR;
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
    await command('Runtime.enable');await command('Page.enable');
    handlers.set('Runtime.exceptionThrown',()=>errors.push('Unexpected browser runtime exception'));
    handlers.set('Fetch.requestPaused',async({requestId,request})=>{
      const url=new URL(request.url),path=url.pathname;requests.push({path,method:request.method});
      let status=200,body;
      if(path==='/api/auth/me'){
        if(mode.anonymous){status=401;body={detail:'Authentication required'};}
        else body={user:{id:'fictional-admin',username:'admin@fictional.invalid',role:mode.role??'admin',is_active:true,faculty_id:null,faculty:null},csrf_token:'fictional-test-only',expires_at:'2099-01-01T00:00:00Z'};
      }else if(path==='/api/ga/current-evaluation')body=evaluationFixture('empty');
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
      await command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:origin},{name:'Access-Control-Allow-Credentials',value:'true'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});
    });
    // Exact API origin: a wildcard /api/ path also intercepts Vite's /src/api/*.ts modules.
    await command('Fetch.enable',{patterns:[{urlPattern:`${process.env.VITE_API_URL ?? 'http://localhost:8000'}/*`,requestStage:'Request'}]});
    await command('Emulation.setDeviceMetricsOverride',{width:1280,height:960,deviceScaleFactor:1,mobile:false});
    async function go(path,settings={}){mode=settings;await command('Page.navigate',{url:origin+path});}
    const text=label=>eventually(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(label)})`),`Missing text: ${label}`);
    const click=label=>evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)}).click()`);
    await check('U1-B01 current saved empty state retains archive/download and blocks unverified baseline',async()=>{
      await go('/admin/chromosomes?view=archive');await text('Archived penalty (compatibility unverified)');
      assert.ok(await evaluate(`document.body.textContent.includes('Historical Archive') && [...document.querySelectorAll('button')].find(b=>b.textContent.includes('Baseline unavailable')).disabled`));
      assert.ok(await evaluate(`!!document.querySelector('a[href$="/best/download"]') && document.body.textContent.includes('810')`));
      await capture('U1-B01-saved-archive');
    });
    await check('U1-B02 empty archive retains upload without inventing a saved penalty',async()=>{await go('/admin/chromosomes?view=archive',{noSaved:true});await text('No saved best chromosome exists yet');assert.equal(await evaluate(`document.body.textContent.includes('Archived penalty (compatibility unverified)')`),false);assert.ok(await evaluate(`!!document.querySelector('input[type="file"]')`));});
    await check('U1-B03 saved status error is actionable and never becomes current',async()=>{await go('/admin/chromosomes',{savedError:true});await text('Saved chromosome status unavailable');await text('No Current Best Chromosome');});
    await check('U1-B04 stored saved preference does not auto-select legacy baseline',async()=>{
      await evaluate(`sessionStorage.setItem('gaPreferredBaseline','saved')`);await go('/admin/generate');await text('Saved Best');
      assert.equal(await evaluate(`[...document.querySelectorAll('input[name="baselineMode"]')].find(r=>r.checked).closest('label').textContent.includes('Fresh')`),true);
      assert.equal(await evaluate(`[...document.querySelectorAll('input[name="baselineMode"]')][1].disabled`),true);
    });
    await check('U1-B05 history defaults to empty Current Evaluation, not completed/recent status',async()=>{await go('/admin/history');await text('No Current GA Runs Yet');assert.equal(await evaluate(`!!document.querySelector('select[aria-label="Historical run"]')`),false);});
    await check('U1-B06 archive remains selectable with original state and identity',async()=>{
      await click('Historical Archive');await text('Historical run');await eventually(()=>evaluate(`document.querySelector('select[aria-label="Historical run"]').options.length===2`),'Archive options');
      assert.ok(await evaluate(`document.querySelector('select[aria-label="Historical run"]').textContent.includes('PAUSED')`));
      await evaluate(`var select=document.querySelector('select[aria-label="Historical run"]');select.value='${id}';select.dispatchEvent(new Event('change',{bubbles:true}))`);await text('51 generations recorded');
    });
    await check('U1-B07 improvement preserves deterioration and independent series',async()=>{
      await eventually(()=>evaluate(`!!document.querySelector('[data-testid="ga-convergence"]')`),'Chart');
      assert.ok(await evaluate(`document.querySelector('select[aria-label="Chart mode"]').value==='improvement' && !!document.querySelector('circle[aria-label*="Absolute improvement: -10"]')`));
      await capture('U1-B07-optimization-progress');
    });
    await check('U1-B08 chart toggles raw penalty without changing exact observations',async()=>{
      await evaluate(`var select=document.querySelector('select[aria-label="Chart mode"]');select.value='raw';select.dispatchEvent(new Event('change',{bubbles:true}))`);await text('Original recorded penalty values are unchanged.');
      assert.ok(await evaluate(`!!document.querySelector('circle[aria-label*="Original penalty: 110"]')`));
    });
    await check('U1-B09 next page retains generation-zero baseline instead of rebasing',async()=>{await click('Next generations');await text('50');await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-convergence"]')?.dataset.points==='1'`),'Next chart page');assert.ok(await evaluate(`!!document.querySelector('circle[aria-label*="Absolute improvement: 10"]')`));});
    await check('U1-B10 schedule ordering preserves all lecture/laboratory rows and filters',async()=>{
      await go('/admin/schedules');await text('FIC10');
      const rows=await evaluate(`[...document.querySelectorAll('tbody tr')].map(row=>row.textContent)`);
      assert.equal(rows.length,4);assert.ok(rows[0].includes('FIC2')&&rows[0].includes('Lecture'));assert.ok(rows[1].includes('Laboratory'));assert.ok(rows[3].includes('Faculty 10'));
      await capture('U1-B10-sorted-schedule');
      await evaluate(`var input=document.querySelector('input[placeholder="Subject, faculty, room..."]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'FIC2');input.dispatchEvent(new Event('input',{bubbles:true}))`);
      await eventually(()=>evaluate(`document.querySelectorAll('tbody tr').length===2`),'Schedule search');
    });
    await check('U1-B11 history failure remains actionable without showing current runs',async()=>{await go('/admin/history?view=archive',{historyError:true});await text('Synthetic history unavailable');await text('Refresh history');});
    await check('U1-B12 admin routes retain anonymous and faculty access protection',async()=>{
      await go('/admin/history',{anonymous:true});await eventually(()=>evaluate(`location.pathname==='/login'`),'Anonymous redirect');
      await go('/admin/chromosomes',{role:'faculty'});await eventually(()=>evaluate(`!document.body.textContent.includes('No Current Best Chromosome') && document.body.textContent.includes('Access unavailable') && document.body.textContent.includes('You do not have permission')`),'Faculty denied');
    });
    assert.deepEqual(errors,[]);assert.ok(requests.every(r=>r.method==='GET'),'Presentation must not mutate APIs');
  } finally {
    if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({browser:browserVersion?.product,node:process.version,scope:'Actual headless Edge React DOM; CDP-intercepted fictional API responses. No FastAPI, GA generation or database acceptance.',scenarios,captures,requests,runtime_errors:errors},null,2)+'\n',{flag:'wx'});
    socket?.close();for(const item of pending.values())item.reject(new Error('Browser closed'));
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&target.split(sep).at(-1).startsWith('dashboard-u1-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
