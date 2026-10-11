// Invoked by the isolated pytest HTTP fixture, never against institutional data.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, basename, sep} from 'node:path';

const backend = process.env.GA_RECOVERY_TEST_URL;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(check, message, timeout = 90000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    try { const value = await check(); if (value) return value; } catch { /* Pending server/browser startup. */ }
    await sleep(100);
  }
  throw new Error(message);
}

test('real FastAPI: start, pause, acknowledge, refresh, hydrate and resume the same population', {skip: !backend, timeout:240000}, async () => {
  assert.match(backend, /^http:\/\/127\.0\.0\.1:\d+$/);
  const profile = await mkdtemp(join(tmpdir(), 'ga-paused-recovery-'));
  const vite = spawn(process.execPath, ['node_modules/vite/bin/vite.js','--host','localhost','--port','5173','--strictPort'], {cwd:new URL('../',import.meta.url),windowsHide:true,stdio:'pipe'});
  const executable = process.env.PREFERENCE_TEST_BROWSER ?? (process.platform==='win32' ? 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' : 'chromium');
  const edge = spawn(executable, ['--headless=new','--disable-gpu','--disable-extensions','--disable-background-networking','--disable-sync','--no-first-run','--no-default-browser-check','--remote-debugging-port=9228',`--user-data-dir=${profile}`,'about:blank'], {windowsHide:true,stdio:'pipe'});
  let socket, sequence=0;
  const pending=new Map();
  let startupError;
  for (const child of [vite,edge]) { child.on('error', error=>startupError=error); child.stdout?.resume(); child.stderr?.resume(); }
  try {
    await eventually(async()=>{if(startupError) throw startupError;return (await fetch('http://localhost:5173',{signal:AbortSignal.timeout(2000)})).ok;},'Vite did not start',15000);
    const targets=await eventually(async()=>(await fetch('http://127.0.0.1:9228/json/list',{signal:AbortSignal.timeout(2000)})).json(),'Browser did not start',15000);
    socket=new WebSocket(targets.find(target=>target.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
    socket.addEventListener('message',event=>{
      const message=JSON.parse(event.data), entry=pending.get(message.id);
      if(entry) {pending.delete(message.id);clearTimeout(entry.timer); if(message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result);}
    });
    const command=(method,params={})=>new Promise((resolve,reject)=>{
      const id=++sequence, timer=setTimeout(()=>{pending.delete(id);reject(new Error(`Browser command timed out: ${method}`));},10000);
      pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));
    });
    const evaluate=async expression=>{
      const value=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
      if(value.exceptionDetails) throw new Error(value.exceptionDetails.text);
      return value.result.value;
    };
    await command('Runtime.enable');await command('Page.enable');
    await command('Page.addScriptToEvaluateOnNewDocument',{source:`
      const transport=window.fetch.bind(window);
      window.testRequests=[];
      window.fetch=(input,options)=>{
        const url=String(input);window.testRequests.push({url,method:options?.method??'GET'});
        if(url.startsWith('http://127.0.0.1:8000')) {
          if(sessionStorage.getItem('delayLatest')==='true' && url.endsWith('/api/ga/latest')) return new Promise(()=>{});
          return transport(url.replace('http://127.0.0.1:8000',${JSON.stringify(backend)}),options);
        }
        return transport(input,options);
      };
    `});
    await command('Page.navigate',{url:'http://localhost:5173/admin/generate'});
    const button=label=>`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)} && !button.disabled)`;
    await eventually(()=>evaluate(`!!(${button('Generate Schedule')})`),'Start button not ready',15000);
    await evaluate(`${button('Generate Schedule')}.click();true`);
    await eventually(()=>evaluate(`!!(${button('Pause Generation')})`),'Pause unavailable');
    await evaluate(`${button('Pause Generation')}.click();true`);
    await eventually(()=>evaluate(`!!(${button('Resume Generation')})`),'Backend never acknowledged a verified paused checkpoint');
    const runId=await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`);
    const state=await (await fetch(`${backend}/api/ga/runs/${runId}`)).json();
    assert.equal(state.state,'PAUSED');assert.equal(state.execution_active,false);
    assert.equal(state.configuration.population_size,10);assert.equal(state.configuration.generations,2);
    await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]')?.textContent.includes('GENETIC ALGORITHM PAUSED')`),'Initial paused console output missing');
    assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent`),'PAUSED');
    await evaluate(`sessionStorage.setItem('delayLatest','true');window.oldDocument=true;true`);
    await command('Page.reload');
    await eventually(()=>evaluate(`!window.oldDocument && !!(${button('Resume Generation')})`),'Refresh failed to discover the durable paused run');
    const expected={
      'ga-run-id':runId,'ga-generation':`${state.latest_completed_generation} / 2`,
      'ga-population':`${state.latest_progress.population_actual} / 10`,
      'ga-best-ever':state.latest_progress.best_ever_fitness.toLocaleString(),
      'ga-generation-best':state.latest_progress.generation_best_fitness.toLocaleString(),
      'ga-average':state.latest_progress.average_fitness.toLocaleString(undefined,{maximumFractionDigits:2}),
      'ga-accepted':state.latest_progress.accepted_new_chromosomes_total.toLocaleString(),
      'ga-elapsed':`${Math.floor(state.elapsed_ms/60000)}m ${Math.floor(state.elapsed_ms/1000)%60}s`,
    };
    for(const [id,value] of Object.entries(expected)) assert.equal(await evaluate(`document.querySelector('[data-testid="${id}"]').textContent`),value,id);
    assert.equal(await evaluate(`Number(document.querySelector('[data-testid="ga-convergence"]').dataset.points)`),state.progress_history.length);
    assert.equal(await evaluate(`window.testRequests.filter(request=>request.method==='POST').length`),0);
    await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]')?.textContent.includes('GENETIC ALGORITHM PAUSED')`),'Refresh did not recover available paused logs');
    await evaluate(`${button('Resume Generation')}.click();true`);
    await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-generation"]')?.textContent==='2 / 2' && document.querySelector('[data-testid="live-ga-monitor"]')?.textContent.includes('Completed')`),'Resume did not continue to generation 2');
    assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`),runId);
    assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`),'3');
    await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]')?.textContent.includes('GENETIC ALGORITHM RESUMING') && document.querySelector('[data-testid="ga-console-output"]')?.textContent.includes('GENETIC ALGORITHM COMPLETED')`),'Resumed console logs did not reconnect');
    assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent`),'COMPLETED');
    assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.split('GENETIC ALGORITHM RESUMING').length-1`),1);
    assert.deepEqual(await evaluate(`window.testRequests.filter(request=>request.method==='POST').map(request=>request.url.split('/').at(-1))`),['resume']);
  } finally {
    socket?.close();for(const entry of pending.values())clearTimeout(entry.timer);
    edge.kill();vite.kill();
    await Promise.race([sleep(3000),Promise.all([edge,vite].map(child=>new Promise(resolve=>child.exitCode!==null||child.signalCode!==null ? resolve() : child.once('exit',resolve))))]);
    const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&basename(target).startsWith('ga-paused-recovery-'));
    await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
