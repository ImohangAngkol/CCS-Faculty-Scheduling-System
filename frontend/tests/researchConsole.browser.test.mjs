// Actual Edge/React with fictional intercepted HTTP, never live FastAPI.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {driver,pause,until} from './researchConsole.driver.mjs';
import {detail,run,other,safety} from './researchObservations.fixtures.mjs';
test('U5PC intercepted observation states',{timeout:180000},async t=>{
 const evidence=process.env.U5PC_EVIDENCE,d=await driver(evidence),scenarios=[];let mode={},release=true;
 const api=process.env.VITE_API_URL??'http://localhost:57999';
 const check=async(name,action)=>{let failure;await t.test(name,async()=>{try{await action();scenarios.push({name,status:'PASS'});}catch(e){failure=e;scenarios.push({name,status:'FAIL',message:e.message});throw e;}});if(failure)throw failure;};
 const body=()=>d.evaluate('document.body.textContent');
 const deniedControls=async()=>assert.equal(await d.evaluate(`[...document.querySelectorAll('button')].some(b=>/^(Start|Pause|Resume|Stop|Restore|Promote|Approve|Apply)( |$)/i.test(b.textContent))`),false);
 d.handlers.set('Fetch.requestPaused',async({requestId,request})=>{
  const m={...mode},path=new URL(request.url).pathname;let status=200,value;
  if(path==='/api/auth/me'){status=m.anonymous?401:200;value=m.anonymous?{detail:'Authentication required'}:{user:{id:'fictional-observer',username:'research@fictional.invalid',role:'admin',is_active:true,faculty_id:null,faculty:null},csrf_token:'fictional-not-a-credential',expires_at:'2099-01-01T00:00:00Z'};}
  else if(path.endsWith('/capabilities')){status=m.denied?403:200;value=m.denied?{detail:'Denied'}:{...safety,scope:'FICTIONAL_RESEARCH_ONLY',available:true,message:'Fictional read-only',maximum_page_size:64,maximum_run_page_size:10};}
  else if(path.endsWith('/runs')){if(m.holdList)await until(()=>release,'Release fictional list');value={...safety,items:m.empty?[]:[detail.overview,{...detail.overview,run_id:other,state:'CREATED',worker_state:'CREATED',best_so_far_fitness:null}],total:m.empty?0:2,offset:0,next_offset:null};}
  else if(path.includes('/runs/')){
   if(m.holdDetail)await until(()=>release,'Release fictional detail');status=m.detailError?503:200;
   value=structuredClone(detail);
   if(path.endsWith(other)){value.overview={...value.overview,run_id:other,state:'CREATED',worker_state:'CREATED',best_so_far_fitness:null,context_qualification:'UNVERIFIED_NOT_CONSUMED'};value.fitness={availability:'UNAVAILABLE_NOT_RECORDED',points:[]};}
   if(m.interrupted){value.overview.state='INTERRUPTED';value.overview.worker_state='RUNNING';value.overview.state_classification='DERIVED';value.overview.reason='EXPIRED_OWNER_LEASE';}
   if(m.active){value.overview.state='RUNNING';value.overview.worker_state='RUNNING';}
   if(m.unsafe)value.overview.reason='<img src=x onerror="window.__injected=true">';
   if(status!==200)value={detail:'Fictional unavailable'};
  }else{status=404;value={detail:'Fictional handler absent'};}
  try{await d.command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:d.origin},{name:'Access-Control-Allow-Credentials',value:'true'}],body:Buffer.from(JSON.stringify(value)).toString('base64')});}catch(e){if(!/Invalid InterceptionId/i.test(e.message))d.errors.push('Fulfillment failed');}
 });
 try{
  await d.command('Fetch.enable',{patterns:[{urlPattern:api+'/*',requestStage:'Request'}]});
  await check('U5PC-S01 loading then empty',async()=>{mode={empty:true,holdList:true};release=false;await d.navigate();await d.text('Loading research observations');release=true;await d.text('No research runs in your authorized scope.');});
  await check('U5PC-S02 access error and retry',async()=>{mode={denied:true};await d.click('Refresh run history');await d.text('Research source unavailable');mode={};await d.click('Retry loading');await d.text(run);});
  await check('U5PC-S03 zero fitness chart and provenance',async()=>{await d.select(run);await d.text('Exact recorded best-ever penalties');assert.match(await body(),/FICTIONAL-YEAR/);await d.capture('S03-recorded-zero-history');await deniedControls();});
  await check('U5PC-S04 missing generation metrics has no fabricated chart',async()=>{await d.select(other);await d.text('Generation-level fitness history unavailable');assert.equal(await d.evaluate(`Boolean(document.querySelector('table'))`),false);});
  await check('U5PC-S05 interruption derived explicitly',async()=>{mode={interrupted:true};await d.select(run);await d.text('EXPIRED_OWNER_LEASE');await d.text('(derived)');await d.capture('S05-derived-interruption');});
  await check('U5PC-S06 detail failure clears prior data and retry works',async()=>{mode={detailError:true};await d.click('Refresh selected observations');await d.text('Run observations unavailable');mode={};await d.click('Retry loading');await d.text('Exact recorded best-ever penalties');});
  await check('U5PC-S07 stale selection response cannot replace newer run',async()=>{mode={holdDetail:true};release=false;await d.select(other);await d.text('Loading selected run');mode={};await d.select(run);await d.text('Exact recorded best-ever penalties');release=true;await pause(150);assert.equal(await d.evaluate(`document.querySelector('[aria-label="Selected research run"]').textContent.includes(${JSON.stringify(other)})`),false);});
  await check('U5PC-S08 imported text is rendered as text',async()=>{mode={unsafe:true};await d.click('Refresh selected observations');await d.text('<img src=x');assert.equal(await d.evaluate('Boolean(window.__injected)'),false);assert.equal(await d.evaluate(`Boolean(document.querySelector('main img'))`),false);});
  await check('U5PC-S09 polling cancels after switching to terminal run',async()=>{mode={active:true};await d.click('Refresh selected observations');await d.text('State: RUNNING');mode={};await d.select(other);await d.text('Generation-level fitness history unavailable');const before=d.requests.length;await pause(10500);assert.equal(d.requests.length,before);});
  await check('U5PC-S10 reload requires fresh selection',async()=>{await d.navigate();await d.text('Research run history');await d.text(run);assert.equal(await d.evaluate(`Boolean(document.querySelector('[aria-label="Selected research run"]'))`),false);});
  await check('U5PC-S11 research network is GET-only, safety notices visible',async()=>{assert.ok(d.requests.length>0&&d.requests.every(r=>r.method==='GET'));await d.text('Seven-day readiness: NO-GO');await deniedControls();});
  await check('U5PC-S12 anonymous session cannot inspect console',async()=>{mode={anonymous:true};await d.navigate();await until(()=>d.evaluate(`Boolean(document.querySelector('input[type=password]'))`),'Sign-in form');assert.equal(await d.evaluate(`Boolean(document.querySelector('[aria-label="Selected research run"]'))`),false);});
  assert.deepEqual(d.errors,[]);
 }finally{release=true;if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({scope:'Actual Edge/React with intercepted fictional HTTP only; no FastAPI or worker acceptance',scenarios,requests:d.requests,runtime_errors:d.errors},null,2),{flag:'wx'});await d.close();}
});
