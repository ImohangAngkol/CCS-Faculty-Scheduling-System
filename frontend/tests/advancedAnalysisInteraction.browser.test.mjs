import {analysisFixture,run as advancedRun} from './advancedAnalysis.fixtures.mjs';
import {qualificationFixture} from './sourceQualification.fixtures.mjs';
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

test('U5E current evaluation with fictional intercepted responses', {timeout:180000}, async t => {
  const profile = await mkdtemp(join(tmpdir(),'dashboard-u5e-'));
  let vite, browser, socket, sequence=0, mode={}, browserVersion, cancelledOldDocumentRequests=0, cancelledVerifiedNetworkRequests=0;
  const cancelledNetwork = new Set();
  const pending=new Map(), handlers=new Map(), scenarios=[], captures=[], requests=[], errors=[];
  const evidence=process.env.U5E_EVIDENCE_DIR;
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
    if(name.startsWith('U5E-'))await evaluate(`document.querySelector('[aria-label="Advanced GA analysis"]').scrollIntoView({block:'start'})`);
    if(name.includes('charts'))await evaluate(`document.querySelector('section[aria-label="Subject Preference Satisfaction"]').scrollIntoView({block:'start'})`);
    if(name.includes('heatmap'))await evaluate(`document.querySelector('[aria-label="Faculty satisfaction heatmap"]').scrollIntoView({block:'start'})`);
    if(name.includes('hours'))await evaluate(`document.querySelector('section[aria-label="Scheduled Teaching Hours per Faculty"]').scrollIntoView({block:'start'})`);
    if(name.includes('percentage-labels'))await evaluate(`document.querySelector('section[aria-label="Day Preference Satisfaction"]').scrollIntoView({block:'start'})`);
    if(name.includes('progress')||name.includes('comparison'))await evaluate(`document.querySelector('[role="tabpanel"]').scrollIntoView({block:'start'})`);
    if(name.includes('optimization'))await evaluate(`document.querySelector('[data-testid="ga-convergence"]').scrollIntoView({block:'center'})`);
    if(name.includes('sorted'))await evaluate(`document.querySelector('table').scrollIntoView({block:'center'})`);
    await evaluate('document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))');
    const image=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(join(evidence,name+'.png'),Buffer.from(image.data,'base64'),{flag:'wx'});
    captures.push({file:name+'.png',observed_at:new Date().toISOString(),viewport:await evaluate('({width:innerWidth,height:innerHeight})'),scope:'Fictional API responses intercepted in Edge. Actual React DOM; no live FastAPI acceptance.'});
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
      }else if(path==='/api/ga/advanced-analysis/runs'){
        body=analysisFixture('runs');if(mode.noRuns){body.items=[];body.total=0;}
      }else if(path.endsWith('/compare')&&path.includes('/advanced-analysis/')){
        body=analysisFixture('comparison');if(mode.compareError){status=409;body={detail:{message:'Fictional incompatible academic/input context'}};}
      }else if(path.startsWith('/api/ga/advanced-analysis/runs/')){
        if(mode.analysisHold)await eventually(()=>!mode.analysisHold,'Controlled fictional analysis release');
        const variant=mode.variant??(url.searchParams.get('generation')==='1'?'second':'current');body=analysisFixture(variant);
        body.source.candidate=url.searchParams.get('candidate')??'generation_best';
        if(mode.analysisError){status=503;body={detail:{message:'Fictional analysis unavailable'}};}
        if(mode.tamperAnalysis)body.receipt.status='VERIFIED';
      }else if(path==='/api/ga/source-qualification'){
        if(mode.sourceHold)await eventually(()=>!mode.sourceHold,'Controlled fictional inspection release');
        status=mode.sourceError?503:200;body=mode.sourceError?{detail:'Fictional unavailable'}:qualificationFixture();
        if(mode.stale)body.cached_tables[0].status='STALE_OR_DIFFERENT_CACHE';
        if(mode.invalidSource)body.eligible_for_current=true;
      }else if(path==='/api/ga/current-evaluation'){
        if(mode.hold)await eventually(()=>!mode.hold,'Controlled fictional projection release');
        status=mode.error?503:200;body=mode.error?{detail:'Fictional projection unavailable'}:evaluationFixture(mode.projection??'unavailable');
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
    await command('Emulation.setDeviceMetricsOverride',{width:1920,height:1080,deviceScaleFactor:1,mobile:false});
    async function go(path,settings={}){mode=settings;const previous=await evaluate('performance.timeOrigin');await command('Page.navigate',{url:origin+path});await eventually(()=>evaluate(`performance.timeOrigin!==${previous}&&document.readyState==='complete'`),'Fresh document');}
    const text=label=>eventually(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(label)})`),`Missing text: ${label}`);
    const click=label=>evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)}).click()`);
    const route=`/admin/analysis?view=advanced&run=${advancedRun}&generation=0`;
    const choose=(label,value)=>evaluate(`(()=>{const e=document.querySelector('select[aria-label="${label}"]');const setter=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;setter.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('change',{bubbles:true}));})()`);
    await check('U5E-B01 summary and all seven charts use one recorded chromosome',async()=>{
      await go(route);await text('Selected run summary');await text('U5D receipt: UNVERIFIED');await capture('U5E-B01-summary');
      for(const title of ['Subject Preference Satisfaction','Day Preference Satisfaction','Time Preference Satisfaction','Number of Preparations per Faculty','Teaching Load Distribution','Load Balance vs. Faculty Average','Scheduled Teaching Hours per Faculty'])assert.ok(await evaluate(`!!document.querySelector('section[aria-label=${JSON.stringify(title)}] svg')`),title);
      assert.ok(await evaluate(`document.querySelector('section[aria-label="Subject Preference Satisfaction"]').parentElement&&getComputedStyle(document.querySelector('section[aria-label="Subject Preference Satisfaction"]').parentElement).gridTemplateColumns.split(' ').length===3`));await capture('U5E-B01-charts');
    });
    await check('U5E-B02 heatmap does not turn missing preferences into zero',async()=>{
      await text('Faculty Satisfaction Heatmap');const content=await evaluate(`document.querySelector('[aria-label="Faculty satisfaction heatmap"]').textContent`);
      assert.ok(content.includes('100%')&&content.includes('Not available')&&content.includes('disabled'));await capture('U5E-B02-heatmap');
    });
    await check('U5E-B03 read-only faculty drill-down uses original preferences and assignments',async()=>{
      await click('Faculty 1: view details');await eventually(()=>evaluate(`document.querySelector('dialog').open`),'Faculty details open');
      await text('FIC101');await text('Monday');await text('09:00');
      assert.equal(await evaluate(`document.querySelectorAll('dialog input,dialog textarea,dialog select').length`),0);await capture('U5E-B03-details');await click('Close faculty details');
    });
    await check('U5E-B04 heatmap sorting has all six explicit options and nulls last',async()=>{
      assert.equal(await evaluate(`document.querySelector('select[aria-label="Faculty ordering"]').options.length`),6);
      await choose('Faculty ordering','lowest');assert.ok((await evaluate(`document.querySelector('[aria-label="Faculty satisfaction heatmap"] tbody tr').textContent`)).includes('Faculty 1'));
    });
    await check('U5E-B05 weekly hours retain lecture/laboratory duration and day legend',async()=>{
      const content=await evaluate(`document.querySelector('section[aria-label="Scheduled Teaching Hours per Faculty"]').textContent`);
      assert.ok(content.includes('mon')&&content.includes('tue'));await capture('U5E-B05-hours');
    });
    await check('U5E-B06 optimization progress displays recorded fitness, satisfaction, violations and coverage',async()=>{
      await click('Optimization Progress');await text('Recorded fitness over generations');await text('Recorded hard-constraint violations');await text('Recorded generation elapsed time');
      await evaluate(`[...document.querySelectorAll('summary')].find(e=>e.textContent==='Recorded progress coverage').click()`);await text('100%');await capture('U5E-B06-progress');
    });
    await check('U5E-B07 comparison shows negative and unchanged deltas separately from faculty outcomes',async()=>{
      await click('Chromosome Comparison');await choose('Comparison left','0');await choose('Comparison right','1');await click('Compare recorded snapshots');await text('Right minus left');await text('-100');await text('0 (unchanged)');await capture('U5E-B07-comparison');
    });
    await check('U5E-B08 incompatible comparison fails closed with retryable selection',async()=>{
      mode.compareError=true;await choose('Comparison right','0');await choose('Comparison right','1');await click('Compare recorded snapshots');await text('Fictional incompatible academic/input context');
    });
    await check('U5E-B09 generation switching clears previous metrics and updates source identity',async()=>{
      await click('Faculty Analysis');await choose('Advanced generation','1');await text('generation 1');
      await eventually(()=>evaluate(`document.querySelector('[aria-label="Faculty satisfaction heatmap"] tbody tr').textContent.includes('0%')`),'Updated day mismatch');
    });
    await check('U5E-B10 incomplete history has honest unavailable graphs and retained gaps',async()=>{
      await go(route.replace('generation=0','generation=1'),{variant:'legacy'});await text('Selected run summary');await text('No recorded applicable values');await click('Optimization Progress');await text('unavailable or incompatible; gaps were retained');
    });
    await check('U5E-B11 zero faculty has no invented results',async()=>{
      await go(route,{variant:'empty'});await text('No captured faculty');await text('No faculty were captured in this chromosome');
    });
    await check('U5E-B12 one distinct chromosome has an unavailable comparison',async()=>{
      await go(route,{variant:'one'});await text('Selected run summary');await click('Chromosome Comparison');await text('Only one distinct valid chromosome');
    });
    await check('U5E-B13 loading, error and independent retry work without starting GA',async()=>{
      await go(route,{analysisHold:true});await text('Loading candidate-bound analysis');mode.analysisHold=false;await text('Selected run summary');
      await go(route,{analysisError:true});await text('Fictional analysis unavailable');mode.analysisError=false;await click('Retry advanced analysis');await text('Selected run summary');
    });
    await check('U5E-B14 a forged verified receipt is rejected',async()=>{
      await go(route,{tamperAnalysis:true});await text('Recorded analysis identity or measurements could not be validated');assert.equal(await evaluate(`!!document.querySelector('[aria-label="GA run summary"]')`),false);
    });
    await check('U5E-B15 empty archive and faculty access restrictions remain explicit',async()=>{
      await go('/admin/analysis?view=advanced',{noRuns:true});await text('No recorded runs are available');
      await go(route,{role:'faculty'});await text('Access unavailable');await go(route,{anonymous:true});await eventually(()=>evaluate(`location.pathname==='/login'`),'Anonymous redirect');
    });
    await check('U5E-B16 mobile charts stack with no page overflow',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await go(route);await text('Selected run summary');
      assert.ok(await evaluate(`document.documentElement.scrollWidth<=innerWidth`));await capture('U5E-B16-mobile');
    });
    await check('U5E-B17 real chart-bar pointer selection opens captured faculty details',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:1920,height:1080,deviceScaleFactor:1,mobile:false});await go(route);await text('Selected run summary');
      const selector='section[aria-label="Subject Preference Satisfaction"] [role="button"]';
      await eventually(()=>evaluate(`!!document.querySelector(${JSON.stringify(selector)})`),'Clickable faculty bar');
      await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center'})`);
      const point=await evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
      await command('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});await command('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
      await eventually(()=>evaluate('document.querySelector("dialog").open'),'Bar opens faculty details');await text('Faculty 1');await capture('U5E-B17-bar-details');await click('Close faculty details');
    });
    await check('U5E-B18 chart bars support keyboard selection',async()=>{
      await evaluate(`document.querySelector('section[aria-label="Scheduled Teaching Hours per Faculty"] [role="button"]').focus()`);
      await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await command('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
      await eventually(()=>evaluate('document.querySelector("dialog").open'),'Keyboard opens faculty details');await click('Close faculty details');
    });
    await check('U5E-B19 percentage labels retain zero and explain descriptive highlighting',async()=>{
      await go(route);await text('Selected run summary');
      await eventually(()=>evaluate(`[...document.querySelectorAll('section[aria-label="Day Preference Satisfaction"] .recharts-label')].some(n=>n.textContent==='100%')`),'Rendered percentage labels');
      await choose('Advanced generation','1');await text('generation 1');
      if(evidence)await writeFile(join(evidence,'zero-label-diagnostic.json'),JSON.stringify(await evaluate(`(()=>{const e=document.querySelector('section[aria-label="Day Preference Satisfaction"]');return {scope:'Fictional chart diagnostic only',svg_text:e?.querySelector('svg')?.textContent,reference_dots:e?.querySelectorAll('.recharts-reference-dot').length,labels:[...e?.querySelectorAll('.recharts-label')??[]].map(n=>n.textContent),summary:document.querySelector('[aria-label="Best-so-far chromosome indicator"]')?.textContent,heatmap:document.querySelector('[aria-label="Faculty satisfaction heatmap"] tbody')?.textContent};})()`),null,2)+'\n',{flag:'wx'});
      await eventually(()=>evaluate(`[...document.querySelectorAll('section[aria-label="Day Preference Satisfaction"] .recharts-label')].some(n=>n.textContent==='0%')`),'Exact zero percentage label');
      await text('not a scoring threshold');await capture('U5E-B19-percentage-labels');
    });
    await check('U5E-B20 preparation reference hours totals and best-so-far are explicit',async()=>{
      await go(route);await text('Selected run summary');await text('Above the captured reference of 2');await text('Faculty 2: 1.5 h');await text('Recorded best-so-far penalty at generation 0: 10');
      await text('Selected snapshot: generation best');await choose('Advanced candidate','best_ever');await text('Selected snapshot: best ever');await capture('U5E-B20-hours-and-best');
    });
    assert.deepEqual(errors,[]);assert.ok(requests.every(r=>r.method==='GET'),'Presentation must not mutate APIs');
  } finally {
    if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({browser:browserVersion?.product,node:process.version,scope:'Actual headless Edge React DOM; CDP-intercepted fictional API responses. No FastAPI, GA generation or database acceptance.',scenarios,captures,requests,cancelled_old_document_requests:cancelledOldDocumentRequests,cancelled_verified_network_requests:cancelledVerifiedNetworkRequests,runtime_errors:errors},null,2)+'\n',{flag:'wx'});
    socket?.close();for(const item of pending.values())item.reject(new Error('Browser closed'));
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&target.split(sep).at(-1).startsWith('dashboard-u5e-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
