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
import {metadata,schedule,analysis,result,report} from './evaluationCoverage.fixtures.mjs';

test('U3 current evaluation, coverage and workload rendering with fictional APIs', {timeout:180000}, async t => {
  const profile = await mkdtemp(join(tmpdir(),'dashboard-u3-'));
  let vite, browser, socket, sequence=0, mode={}, browserVersion;
  const pending=new Map(), handlers=new Map(), scenarios=[], captures=[], requests=[], errors=[];
  const evidence=process.env.U3_EVIDENCE_DIR;
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
    if(name.includes('workload'))await evaluate(`document.querySelector('.workload-chart').scrollIntoView({block:'center'})`);
    await evaluate('document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))');
    const image=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(join(evidence,name+'.png'),Buffer.from(image.data,'base64'),{flag:'wx'});
    captures.push({file:name+'.png',observed_at:new Date().toISOString(),viewport:await evaluate(`({width:innerWidth,height:innerHeight})`),scope:'Fictional API responses intercepted in Edge. Actual React DOM; no live FastAPI acceptance.'});
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
      const url=new URL(request.url),path=url.pathname;requests.push({path,method:request.method});let status=200,body;
      if(path==='/api/auth/me'){
        status=mode.anonymous?401:200;
        body=mode.anonymous?{detail:'Authentication required'}:{user:{id:'fictional-admin',username:'admin@fictional.invalid',role:mode.role??'admin',is_active:true,faculty_id:null,faculty:null},csrf_token:'fictional-test-only',expires_at:'2099-01-01T00:00:00Z'};
      }else if(path==='/api/ga/status')body={control_version:'3c.1',pause_resume_version:'3d.1',process_instance_id:'fictional-process',active_run:null,paused_runs:[]};
      else if(path==='/api/ga/latest')body={status:'success',data:result(mode.empty)};
      else if(path==='/api/chromosomes/best')body={status:'success',data:{exists:true,fitness:mode.savedZero?0:810,created_at:'2026-01-01T00:00:00Z'}};
      else if(path==='/api/ga/runs')body={schema_version:1,items:[],total:0,offset:0,limit:20,errors:[]};
      else if(path==='/api/ga/fitness-analysis/latest')body=report(mode);
      else if(path==='/api/faculty/'||path==='/api/faculty'){status=mode.rosterError?503:200;body=mode.rosterError?{detail:'Fictional metadata unavailable'}:{data:metadata};}
      else{status=404;body={detail:'No fictional handler'};}
      await command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:origin},{name:'Access-Control-Allow-Credentials',value:'true'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});
    });
    await command('Fetch.enable',{patterns:[{urlPattern:`${process.env.VITE_API_URL??'http://localhost:8000'}/*`,requestStage:'Request'}]});
    const resize=(width,height)=>command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await resize(1280,960);
    async function go(path,settings={}){mode=settings;await command('Page.navigate',{url:origin+path});}
    const text=label=>eventually(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(label)})`),`Missing text: ${label}`);
    const click=label=>evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)}).click()`);
    async function select(selector,value){await evaluate(`var el=document.querySelector(${JSON.stringify(selector)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('change',{bubbles:true}))`);}
    const scheduleReady=()=>eventually(()=>evaluate(`document.querySelector('select[aria-label="Schedule faculty"]')?.options.length===5`),'Roster selector ready');
    const chartReady=()=>eventually(()=>evaluate(`document.querySelectorAll('.workload-chart-row').length>0`),'Workload chart ready');
    await check('U3-B01 current saved page has zero verified runs, no saved chromosome and no historical penalty',async()=>{
      await go('/admin/chromosomes');await text('Current Runs:');await text('Saved Chromosome:');
      assert.equal(await evaluate(`document.body.textContent.includes('810')`),false);
      assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),'—');
      assert.ok(await evaluate(`[...document.querySelectorAll('dt')].some(el=>el.textContent==='Current Runs:'&&el.nextElementSibling.textContent==='0')`));
      await capture('U3-B01-current-evaluation');
    });
    await check('U3-B02 explicit archive preserves the original fitness and existing download/inspection actions',async()=>{
      await click('Historical Archive');await text('Archived penalty (compatibility unverified)');await text('810');
      assert.ok(await evaluate(`!!document.querySelector('a[href$="/best/download"]')&&[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='View Results Only')`));
      assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Baseline unavailable')).disabled`));
      await click('Current Evaluation');assert.equal(await evaluate(`document.body.textContent.includes('810')`),false);
    });
    await check('U3-B03 zero archived penalty remains a true zero and does not become a current result',async()=>{
      await go('/admin/chromosomes?view=archive',{savedZero:true});await text('Archived penalty (compatibility unverified)');
      assert.ok(await evaluate(`document.querySelector('.text-3xl').textContent.trim()==='0'`));
      await click('Current Evaluation');assert.equal(await evaluate(`document.querySelector('[aria-label="Current best penalty"]').textContent`),'—');
    });
    await check('U3-B04 fresh-evaluation action is visibly unavailable and cannot reset or write records',async()=>{
      assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Start Fresh Evaluation')).disabled`));
      await click('Start Fresh Evaluation (not available)');assert.ok(requests.every(row=>row.method==='GET'));
      await text('No reset has occurred.');
    });
    await check('U3-B05 selector includes zero-assignment faculty from captured analysis missing from metadata',async()=>{
      await go('/admin/schedules');await scheduleReady();
      assert.deepEqual(await evaluate(`[...document.querySelector('select[aria-label="Schedule faculty"]').options].map(el=>el.value)`),['All','0','1','2','10']);
      assert.ok(await evaluate(`document.querySelector('option[value="2"]').textContent.includes('No assigned subjects')`));
      await text('1 available faculty without displayed assignments');
    });
    await check('U3-B06 selecting unassigned faculty shows an honest empty timetable without invented rows',async()=>{
      await select('select[aria-label="Schedule faculty"]','2');await text('Faculty 2: No assigned subjects');
      assert.equal(await evaluate(`document.querySelectorAll('tbody tr').length`),1);
      await capture('U3-B06-unassigned-faculty');
    });
    await check('U3-B07 roster retry is actionable and fallback report members stay available',async()=>{
      await go('/admin/schedules',{rosterError:true});await text('Faculty metadata unavailable.');await scheduleReady();
      mode.rosterError=false;await click('Retry roster');await eventually(()=>evaluate(`!document.body.textContent.includes('Faculty metadata unavailable.')`),'Roster retry');
      assert.equal(await evaluate(`document.querySelector('select[aria-label="Schedule faculty"]').options.length`),5);
    });
    await check('U3-B08 loaded empty schedule retains cohort choices and zero-assignment messaging',async()=>{
      await go('/admin/schedules',{empty:true});await scheduleReady();await text('4 available faculty without displayed assignments');
      assert.equal(await evaluate(`document.body.textContent.includes('No schedule generated yet')`),false);
      await select('select[aria-label="Schedule faculty"]','2');await text('Faculty 2: No assigned subjects');
    });
    await check('U3-B09 workload graphic is above the retained table, naturally sorted and exact for zero/overload',async()=>{
      await go('/admin/analysis');await chartReady();
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('.workload-chart-row strong')].map(el=>el.textContent)`),['Faculty 0','Faculty 1','Faculty 2','Faculty 10']);
      assert.ok(await evaluate(`var rows=[...document.querySelectorAll('.workload-chart-row')],zero=rows.find(el=>el.textContent.includes('Faculty 2')),over=rows.find(el=>el.textContent.includes('Faculty 10'));zero.title.includes('actual 0; target 24')&&zero.querySelector('.workload-actual').style.width==='0%'&&over.title.includes('actual 36; target 18')&&over.querySelector('.workload-actual').style.width==='100%'`));
      assert.ok(await evaluate(`var chart=document.querySelector('.workload-chart'),table=chart.parentElement.querySelector('table');!!table&&(chart.compareDocumentPosition(table)&4)!==0`));
      await capture('U3-B09-workload-comparison');
    });
    await check('U3-B10 workload and faculty filters affect chart and table consistently',async()=>{
      await select('select[aria-label="Workload filter"]','overload');
      assert.equal(await evaluate(`document.querySelectorAll('.workload-chart-row').length`),1);
      assert.equal(await evaluate(`document.querySelector('.workload-chart-row strong').textContent`),'Faculty 10');
      await select('select[aria-label="Workload filter"]','all');await select('select[aria-label="Analysis faculty"]','Faculty 2');
      assert.equal(await evaluate(`document.querySelectorAll('.workload-chart-row').length`),1);await text('Zero teaching units');
    });
    await check('U3-B11 unavailable targets stay unknown instead of using current metadata/defaults',async()=>{
      await go('/admin/analysis',{missingTarget:true});await chartReady();
      assert.ok(await evaluate(`[...document.querySelectorAll('.workload-chart-row')].find(el=>el.textContent.includes('Faculty 2')).title.includes('actual 0; target Not captured')`));
      await text('Target not captured');
    });
    await check('U3-B12 many faculty remain keyboard reachable in the bounded chart list',async()=>{
      await go('/admin/analysis',{many:true});await chartReady();assert.equal(await evaluate(`document.querySelectorAll('.workload-chart-row').length`),35);
      await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await command('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
      await evaluate(`[...document.querySelectorAll('.workload-chart-row')].at(-1).focus()`);
      assert.ok(await evaluate(`document.querySelector('.workload-chart-list').scrollTop>0&&getComputedStyle(document.activeElement).outlineStyle!=='none'`));
    });
    await check('U3-B13 recorded above-ceiling values are visible and warned about, never clipped into a valid result',async()=>{
      await go('/admin/analysis',{aboveCeiling:true});await chartReady();await text('Recorded actual exceeds the current 40-unit ceiling');
      assert.ok(await evaluate(`[...document.querySelectorAll('.workload-chart-row')].find(el=>el.textContent.includes('Faculty 10')).title.includes('actual 45; target 18')`));
    });
    await check('U3-B14 mobile workload stays readable with exact numbers and no horizontal page overflow',async()=>{
      await resize(390,844);await go('/admin/analysis');await chartReady();
      const geometry=await evaluate(`({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,chart:document.querySelector('.workload-chart').getBoundingClientRect().width,overflow:[...document.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>({tag:el.tagName,classes:el.className,right:el.getBoundingClientRect().right}))})`);
      assert.ok(geometry.scrollWidth<=geometry.width,JSON.stringify(geometry));await capture('U3-B14-mobile-workload');await resize(1280,960);
    });
    await check('U3-B15 existing account role restrictions remain in place',async()=>{
      await go('/admin/chromosomes',{anonymous:true});await eventually(()=>evaluate(`location.pathname==='/login'`),'Anonymous redirect');
      await go('/admin/analysis',{role:'faculty'});await text('Access unavailable');
      assert.equal(await evaluate(`document.querySelector('.workload-chart')!==null`),false);
    });
    assert.deepEqual(errors,[]);assert.ok(requests.every(row=>row.method==='GET'));
    assert.equal(schedule.length,22);assert.equal(analysis.find(row=>row.Faculty_Code===2).Teaching_Load,0);
  }finally{
    if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({browser:browserVersion?.product,node:process.version,scope:'Actual headless Edge React DOM with fictional intercepted read-only APIs. No FastAPI, GA generation, database, reset or institutional authority.',scenarios,captures,requests,runtime_errors:errors},null,2)+'\n',{flag:'wx'});
    socket?.close();for(const item of pending.values())item.reject(new Error('Browser closed'));
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&target.split(sep).at(-1).startsWith('dashboard-u3-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
