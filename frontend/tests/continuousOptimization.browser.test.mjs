import {readinessFixture} from './continuousOptimization.fixtures.mjs';
import {runContinuousScenarios} from './continuousOptimization.scenarios.mjs';
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
import {snapshot,runId,processId,logs as fixtureLogs} from './continuousOptimizationRun.fixtures.mjs';

test('U5F readiness and existing fixed lifecycle with fictional HTTP', {timeout:180000}, async t => {
  const profile = await mkdtemp(join(tmpdir(),'u5f-browser-'));
  let vite, browser, socket, sequence=0, mode={}, browserVersion, cancelledOldDocumentRequests=0, confirmations=0;
  const pending=new Map(), handlers=new Map(), scenarios=[], captures=[], requests=[], errors=[];
  const evidence=process.env.U5F_EVIDENCE_DIR;
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
    const selector = name.includes('fixed') ? '[data-testid="live-ga-monitor"]' : '[aria-label="Optimization mode"]';
    await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'start'})`);
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
    await command('Runtime.enable');await command('Page.enable');await command('Emulation.setFocusEmulationEnabled',{enabled:true});
    handlers.set('Runtime.exceptionThrown',()=>errors.push('Unexpected browser runtime exception'));

    handlers.set('Page.javascriptDialogOpening',()=>{confirmations++;void command('Page.handleJavaScriptDialog',{accept:!mode.cancelConfirm});});
    handlers.set('Fetch.requestPaused',async({requestId,request})=>{
      const requestMode=mode,url=new URL(request.url),path=url.pathname;requests.push({path,method:request.method});let status=200,body;
      if(request.method==='OPTIONS'){status=204;body={};}
      else if(path==='/api/auth/me'){status=mode.anonymous?401:200;body=mode.anonymous?{detail:'Authentication required'}:{user:{id:'fictional-admin',username:'admin@fictional.invalid',role:mode.role??'admin',is_active:true,faculty_id:null,faculty:null},csrf_token:'fictional-test-only',expires_at:'2099-01-01T00:00:00Z'};}
      else if(path==='/api/ga/continuous/readiness'){
        if(mode.readinessHold)await eventually(()=>!mode.readinessHold,'Fictional readiness release');
        status=mode.readinessError?503:200;body=mode.readinessError?{detail:'Fictional readiness unavailable'}:readinessFixture();
        if(mode.forgedReadiness)body.executable=true;
      }
      else if(path==='/api/ga/latest'){status=404;body={detail:'No fictional saved result'};}
      else if(path==='/api/chromosomes/best')body={status:'success',data:{exists:false,fitness:null,created_at:null}};
      else if(path==='/api/ga/status'){if(mode.discoveryDelay)await pause(300);body={control_version:'3c.1',pause_resume_version:'3d.1',process_instance_id:processId,active_run:mode.idle?null:snapshot(mode),paused_runs:[]};}
      else if(path===`/api/ga/runs/${runId}/checkpoint-status`)body={run_id:runId,process_instance_id:processId,state:'PAUSED',resumable:!mode.invalidCheckpoint,error:mode.invalidCheckpoint?'Fictional checkpoint mismatch':undefined};
      else if(path===`/api/ga/runs/${runId}/logs`){
        const snap=snapshot(mode),all=(mode.logs??fixtureLogs).map((message,index)=>({sequence:index+1,message,timestamp:'2026-11-03T01:00:00Z',line_truncated:false}));
        const cursor=Number(url.searchParams.get('after_sequence')??0),entries=all.filter(row=>row.sequence>cursor).slice(0,200),latest=all.length,next=entries.at(-1)?.sequence??Math.min(cursor,latest);
        body={run_id:runId,process_instance_id:processId,log_epoch:'fictional-live-console',state:snap.state,execution_active:snap.execution_active,entries,latest_sequence:latest,next_sequence:next,has_more:next<latest,earlier_logs_truncated:!!mode.truncated,cursor_reset:cursor>latest};
      }else if(request.method==='POST'&&path===`/api/ga/runs/${runId}/pause`){await eventually(()=>!mode.holdPause,'Fictional pause acknowledgement');mode.state='PAUSE_REQUESTED';body={...snapshot(mode),accepted:true};}
      else if(request.method==='POST'&&path===`/api/ga/runs/${runId}/resume`){mode.state='RESUMING';body={...snapshot(mode),accepted:true};}
      else if(request.method==='POST'&&path===`/api/ga/runs/${runId}/stop`){mode.state='STOP_REQUESTED';body={...snapshot(mode),accepted:true};}
      else if(path===`/api/ga/runs/${runId}`){status=mode.stateError?503:200;body=mode.stateError?{detail:{code:'GA_RECOVERY_UNAVAILABLE',message:'Fictional state unavailable'}}:snapshot(mode);}
      else{status=404;body={detail:'No fictional handler'};}
      try {await command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:origin},{name:'Access-Control-Allow-Credentials',value:'true'},{name:'Access-Control-Allow-Methods',value:'GET, POST, OPTIONS'},{name:'Access-Control-Allow-Headers',value:'Content-Type, X-CSRF-Token, X-GA-Process-ID'}],body:Buffer.from(status===204?'':JSON.stringify(body)).toString('base64')});}
      catch(error){if(error.message==='Invalid InterceptionId.'&&requestMode!==mode)cancelledOldDocumentRequests++;else errors.push('CDP fulfillment: '+error.message);}
    });
    await command('Fetch.enable',{patterns:[{urlPattern:`${process.env.VITE_API_URL??'http://localhost:8000'}/*`,requestStage:'Request'}]});
    await command('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:join(profile,'downloads')});
    const resize=(width,height)=>command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});await resize(1366,1000);
    async function go(settings={}){mode=settings;const previous=await evaluate('performance.timeOrigin');await command('Page.navigate',{url:origin+'/admin/generate'});await eventually(()=>evaluate(`performance.timeOrigin!==${previous}&&document.readyState==='complete'`),'Fresh document');}
    const text=label=>eventually(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(label)})`),`Missing text: ${label}`);
    const click=label=>evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)}).click()`);
    const badge=label=>eventually(()=>evaluate(`document.querySelector('[data-testid="ga-lifecycle-badge"]')?.textContent===${JSON.stringify(label)}`),`Lifecycle ${label}`);
    const metricText=id=>evaluate(`document.querySelector('[data-testid=${JSON.stringify(id)}]')?.textContent`);
    const consoleReady=()=>eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]')?.textContent.includes('Repeated fictional output')`),'Console hydration');
    async function select(selector,value){await evaluate(`var el=document.querySelector(${JSON.stringify(selector)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('change',{bubbles:true}));`);}

    await runContinuousScenarios({check,go,text,click,capture,command,evaluate,eventually,resize,requests,mode:()=>mode,runId,confirmations:()=>confirmations});
    assert.deepEqual(errors,[]);
  }finally{
    if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({browser:browserVersion?.product,node:process.version,scope:'Actual Edge React and existing GAContext with intercepted fictional HTTP. Control acknowledgements are synthetic; no live FastAPI, GA worker, database or institutional acceptance.',scenarios,captures,requests,confirmations,cancelled_old_document_requests:cancelledOldDocumentRequests,runtime_errors:errors},null,2)+'\n',{flag:'wx'});
    socket?.close();for(const item of pending.values())item.reject(new Error('Browser closed'));
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&target.split(sep).at(-1).startsWith('u5f-browser-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
