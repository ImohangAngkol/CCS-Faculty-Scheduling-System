// Private input arrives on stdin; never archived or printed. No interceptions.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {driver,until} from './researchConsole.driver.mjs';
let wire='';for await(const part of process.stdin)wire+=part;
const input=JSON.parse(wire);wire='';const evidence=process.env.U5PC_EVIDENCE,scenarios=[];let d;
async function check(name,action){try{await action();scenarios.push({name,status:'PASS'});}catch(e){scenarios.push({name,status:'FAIL',message:e.message});throw e;}}
try{
 d=await driver(evidence,input.port);
 await check('U5PC-L01 anonymous console redirects to sign-in',async()=>{await d.navigate();await until(()=>d.evaluate(`Boolean(document.querySelector('input[type=password]'))`),'Actual sign-in');});
 await check('U5PC-L02 actual React login with FastAPI session',async()=>{
  // React-controlled fields use native setters and real input events.
  await d.evaluate(`(()=>{const inputs=document.querySelectorAll('input');const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;set.call(inputs[0],${JSON.stringify(input.username)});inputs[0].dispatchEvent(new Event('input',{bubbles:true}));set.call(inputs[1],${JSON.stringify(input.password)});inputs[1].dispatchEvent(new Event('input',{bubbles:true}));return true;})()`);
  await d.click('Sign in');await until(()=>d.evaluate(`!location.pathname.includes('/login')`),'Authenticated navigation');input.password='';
  await d.navigate();await d.text(input.runs.completed);
 });
 await check('U5PC-L03 real completed worker provenance and zero history',async()=>{await d.select(input.runs.completed);await d.text('TRUSTED_FICTIONAL_CONSUMPTION');await d.text('Exact recorded best-ever penalties');await d.text('FICTIONAL-YEAR');assert.equal(await d.evaluate(`[...document.querySelectorAll('table')].find(t=>t.caption?.textContent.startsWith('Exact recorded')).querySelector('tbody td:nth-child(2)').textContent`),'0');await d.capture('L03-real-worker-history');});
 await check('U5PC-L04 durable worker telemetry and checkpoint metadata',async()=>{await d.text('Execution timeline');await d.text('Checkpoint metadata');await d.text('Active restoration unavailable');assert.equal(await d.evaluate(`document.querySelector('input[type=password]')!==null`),false);});
 await check('U5PC-L05 not-consumed run truthfully lacks metrics',async()=>{await d.select(input.runs.missing);await d.text('UNVERIFIED_NOT_CONSUMED');await d.text('Generation-level fitness history unavailable');assert.equal(await d.evaluate(`Boolean(document.querySelector('table'))`),false);});
 await check('U5PC-L06 injected expired owner is derived interruption',async()=>{await d.select(input.runs.interrupted);await d.text('EXPIRED_OWNER_LEASE');await d.text('(derived)');await d.capture('L06-injected-expired-owner');});
 await check('U5PC-L07 reload and fresh selection retain durable data',async()=>{await d.navigate();await d.text(input.runs.completed);assert.equal(await d.evaluate(`Boolean(document.querySelector('[aria-label="Selected research run"]'))`),false);await d.select(input.runs.completed);await d.text('Exact recorded best-ever penalties');});
 await check('U5PC-L08 research reads are GET-only and no operational controls',async()=>{assert.ok(d.requests.length>0&&d.requests.every(r=>r.method==='GET'));assert.equal(await d.evaluate(`[...document.querySelectorAll('button')].some(b=>/^(Start|Pause|Resume|Stop|Restore|Promote|Approve|Apply)( |$)/i.test(b.textContent))`),false);await d.text('Continuous Optimization: DISABLED');});
 await check('U5PC-L09 malformed and unauthorized resource probes fail',async()=>{const result=await d.evaluate(`(async()=>{const base=${JSON.stringify(process.env.VITE_API_URL)};const a=await fetch(base+'/api/research/observations/runs/not-a-uuid',{credentials:'include'});const b=await fetch(base+'/api/research/observations/runs?limit=100',{credentials:'include'});return [a.status,b.status]})()`);assert.deepEqual(result,[422,422]);});
 assert.deepEqual(d.errors,[]);
}catch(e){process.exitCode=1;console.error('Live console verification failed: '+e.message);}
finally{input.password='';if(evidence)await writeFile(join(evidence,'live-browser-results.json'),JSON.stringify({scope:'Actual Edge/React -> TCP FastAPI -> real sessions and private SQLite. Worker genuinely executed; interruption scenario uses explicitly injected expired-owner metadata.',scenarios,requests:d?.requests??[],runtime_errors:d?.errors??[],HTTP_interception:false},null,2),{flag:'wx'});await d?.close();}
