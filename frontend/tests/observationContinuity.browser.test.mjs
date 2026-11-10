// Real Edge/React, intercepted fictional HTTP only. No live API/GA acceptance.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {driver,pause,until} from './researchConsole.driver.mjs';
import {observation,missing,run,other,safety2} from './observationContinuity.fixtures.mjs';
test('U5PD freshness and continuity',{timeout:240000},async t=>{
 const evidence=process.env.U5PD_EVIDENCE,d=await driver(evidence),scenarios=[],memory=[];let mode={},release=true;
 const api=process.env.VITE_API_URL??'http://localhost:57999';
 const check=async(name,action)=>{let failure;await t.test(name,async()=>{try{await action();scenarios.push({name,status:'PASS'});}catch(e){failure=e;scenarios.push({name,status:'FAIL',message:e.message});throw e;}});if(failure)throw failure;};
 const count=()=>d.requests.filter(r=>r.path==='/api/research/observations/runs/'+run).length;
 const text=()=>d.evaluate('document.body.textContent');
 const sample=async label=>{const result=await d.command('Performance.getMetrics');const metrics=Object.fromEntries(result.metrics.filter(m=>['JSHeapUsedSize','JSHeapTotalSize','Documents','Nodes','JSEventListeners'].includes(m.name)).map(m=>[m.name,m.value]));memory.push({label,...metrics,...await d.command('Memory.getDOMCounters')});};
 d.handlers.set('Fetch.requestPaused',async({requestId,request})=>{
  const m={...mode},path=new URL(request.url).pathname;let status=200,value;
  if(path==='/api/auth/me'){status=m.anonymous?401:200;value=m.anonymous?{detail:'Authentication required'}:{user:{id:'fictional-u5pd',username:'research@fictional.invalid',role:'admin',is_active:true,faculty_id:null,faculty:null},csrf_token:'fictional-'+'not-a-credential',expires_at:'2099-01-01T00:00:00Z'};}
  else if(path.endsWith('/capabilities'))value={...safety2,scope:'FICTIONAL_RESEARCH_ONLY',available:true,message:'Fictional readonly continuity',maximum_page_size:64,maximum_run_page_size:10};
  else if(path.endsWith('/runs')){if(m.holdList)await until(()=>release,'Release fictional list');status=m.listError?503:200;value=status!==200?{detail:'Fictional connection failure'}:{...safety2,items:m.empty?[]:[observation().overview,missing().overview],total:m.empty?0:2,offset:0,next_offset:null};}
  else if(path.includes('/runs/')){
   if(m.holdOther&&path.endsWith(other))await until(()=>release,'Release old run');
   value=path.endsWith(other)?missing():observation(m.state??'FRESH');
   if(m.nearStale){const f=value.overview.freshness;f.age_seconds=29.9;f.last_verified_observation_at=f.server_verified_at-29.9;}
   if(m.skew){const f=value.overview.freshness;f.age_seconds=-1;f.last_verified_observation_at=f.server_verified_at+1;f.reason='WITHIN_CLOCK_SKEW_TOLERANCE';}
   if(m.unsafe)value.overview.reason='<img src=x onerror="window.__u5pdInjected=true">';
   status=m.denied?403:m.detailError?503:200;if(status!==200)value={detail:'Fictional read rejected'};
  }else{status=404;value={detail:'No fictional handler'};}
  try{await d.command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:d.origin},{name:'Access-Control-Allow-Credentials',value:'true'}],body:Buffer.from(JSON.stringify(value)).toString('base64')});}catch(e){if(!/Invalid InterceptionId/i.test(e.message))d.errors.push('Unexpected fulfillment failure');}
 });
 try{
  await d.command('Performance.enable');await d.command('Fetch.enable',{patterns:[{urlPattern:api+'/*',requestStage:'Request'}]});
  await check('U5PD-B01 loading and empty',async()=>{mode={holdList:true,empty:true};release=false;await d.navigate();await d.text('Loading research observations');release=true;await d.text('No research runs in your authorized scope.');await sample('initial-empty');});
  await check('U5PD-B02 fresh source and distinct retrieval clocks',async()=>{mode={};await d.click('Refresh run history');await d.text(run);await d.select(run);await d.text('Observation freshness: FRESH');await d.text('Last successful retrieval (browser clock)');await d.text('Last verified observation (server source time)');await d.text('Worker health is not established');await d.capture('B02-fresh-observations');});
  await check('U5PD-B03 stale does not imply terminated',async()=>{mode={state:'STALE'};await d.click('Refresh selected observations');await d.text('Observation freshness: STALE');await d.text('State: RUNNING');await d.text('worker termination is not inferred');await d.capture('B03-stale-not-terminated');});
  await check('U5PD-B04 temporary HTTP failure retains exact historical chart',async()=>{mode={detailError:true};await d.click('Refresh selected observations');await d.text('Run observations unavailable');await d.text('Historical observations retained');await d.text('Exact recorded best-ever penalties');assert.equal(await d.evaluate(`[...document.querySelectorAll('table')].find(t=>t.caption?.textContent.startsWith('Exact recorded')).querySelector('tbody td:nth-child(2)').textContent`),'0');await d.capture('B04-history-retained-on-error');});
  await check('U5PD-B05 retry restores connection without deleting history',async()=>{mode={};await d.click('Retry loading');await until(async()=>!(await text()).includes('Run observations unavailable'),'Retry recovery');await d.text('Observation freshness: FRESH');});
  await check('U5PD-B06 future source timestamp is UNKNOWN',async()=>{mode={state:'UNKNOWN'};await d.click('Refresh selected observations');await d.text('FUTURE_OBSERVATION');await d.text('Observation freshness: UNKNOWN');});
  await check('U5PD-B07 source ages to stale without HTTP',async()=>{mode={nearStale:true};const before=count();await d.click('Refresh selected observations');await until(()=>count()>before,'Age fixture retrieved');await d.text('BROWSER_AGE_SINCE_SERVER_VERIFICATION');await d.text('Observation freshness: STALE');});
  await check('U5PD-B08 old durable terminal is not live telemetry',async()=>{mode={state:'TERMINAL'};await d.click('Refresh selected observations');await d.text('Observation freshness: TERMINAL');await d.text('historical telemetry is not a live heartbeat');await sample('terminal-history');});
  await check('U5PD-B09 tolerated clock skew remains explicit',async()=>{mode={skew:true};await d.click('Refresh selected observations');await d.text('WITHIN_CLOCK_SKEW_TOLERANCE');});
  await check('U5PD-B10 list outage preserves selected detail',async()=>{mode={listError:true};await d.click('Refresh run history');await d.text('Research source unavailable');await d.text('Previously retrieved run history retained');await d.text('Run overview');mode={};await d.click('Retry loading');await until(async()=>!(await text()).includes('Research source unavailable'),'List recovery');});
  await check('U5PD-B11 old run completion cannot replace new selection',async()=>{mode={holdOther:true};release=false;await d.select(other);await d.text('Loading selected run');mode={};await d.select(run);await d.text('Exact recorded best-ever penalties');release=true;await pause(100);assert.equal(await d.evaluate(`document.querySelector('[aria-label="Selected research run"]').textContent.includes(${JSON.stringify(other)})`),false);});
  await check('U5PD-B12 actual reload preserves run UUID selection only',async()=>{const mark=crypto.randomUUID();await d.command('Page.addScriptToEvaluateOnNewDocument',{source:'window.__u5pdReload='+JSON.stringify(mark)});await d.command('Page.reload');await until(()=>d.evaluate('window.__u5pdReload==='+JSON.stringify(mark)),'Fresh reload');await d.text('Exact recorded best-ever penalties');assert.equal(await d.evaluate(`new URL(location.href).searchParams.get('run')`),run);});
  await check('U5PD-B13 automatic polling stops after six refreshes',async()=>{mode={};const before=count();await d.click('Refresh selected observations');const end=Date.now()+75000;while(count()<before+7&&Date.now()<end)await pause(200);assert.equal(count(),before+7);await sample('seven-bounded-reads');await pause(10500);assert.equal(count(),before+7);});
  await check('U5PD-B14 switching cancels pending polling',async()=>{mode={};await d.click('Refresh selected observations');await d.text('Observation freshness: FRESH');await d.select(other);await d.text('Generation-level fitness history unavailable');const before=d.requests.length;await pause(10500);assert.equal(d.requests.length,before);});
  await check('U5PD-B15 authoritative denial clears cache; unsafe text stays text',async()=>{mode={unsafe:true};await d.select(run);await d.text('<img src=x');assert.equal(await d.evaluate('Boolean(window.__u5pdInjected)'),false);mode={denied:true};await d.click('Refresh selected observations');await d.text('Cached observations cleared');assert.equal(await d.evaluate(`Boolean(document.querySelector('[aria-label="Selected research run"]'))`),false);});
  await check('U5PD-B16 no controls, GET-only and anonymous denial',async()=>{assert.ok(d.requests.every(r=>r.method==='GET'));assert.equal(await d.evaluate(`[...document.querySelectorAll('button')].some(b=>/^(Start|Pause|Resume|Stop|Restore|Promote|Approve|Apply)( |$)/i.test(b.textContent))`),false);await sample('before-anonymous');mode={anonymous:true};await d.navigate();await until(()=>d.evaluate(`Boolean(document.querySelector('input[type=password]'))`),'Sign-in required');});
  assert.deepEqual(d.errors,[]);
 }finally{release=true;if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({scope:'Actual Edge/React with fictional intercepted HTTP; no live FastAPI or worker claim',scenarios,requests:d.requests,runtime_errors:d.errors,memory_samples:memory,memory_scope:'CDP JS heap and DOM counters only, NOT browser process working set/private commit or proof of leak-free long-duration behavior; no forced GC'},null,2),{flag:'wx'});await d.close();}
});
