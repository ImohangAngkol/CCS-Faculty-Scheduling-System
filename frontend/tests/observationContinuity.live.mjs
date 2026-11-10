// Actual application HTTP. Private login/fault channel on stdin, no interception.
import assert from 'node:assert/strict';
import {writeFile,unlink} from 'node:fs/promises';
import {basename,dirname,join} from 'node:path';
import {driver,until} from './researchConsole.driver.mjs';
let wire='';for await(const part of process.stdin)wire+=part;const input=JSON.parse(wire);wire='';
assert.ok(basename(dirname(input.fault_path)).startsWith('ga-u5i-')&&basename(input.fault_path)==='U5PD-HTTP-FAULT');
const evidence=process.env.U5PD_EVIDENCE,scenarios=[];let d;
async function check(name,fn){try{await fn();scenarios.push({name,status:'PASS'});}catch(e){scenarios.push({name,status:'FAIL',message:e.message});throw e;}}
async function login(username){
 await until(()=>d.evaluate(`Boolean(document.querySelector('input[type=password]'))`),'Actual sign-in form');
 await d.evaluate(`(()=>{const inputs=document.querySelectorAll('input');const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;set.call(inputs[0],${JSON.stringify(username)});inputs[0].dispatchEvent(new Event('input',{bubbles:true}));set.call(inputs[1],${JSON.stringify(input.password)});inputs[1].dispatchEvent(new Event('input',{bubbles:true}));return true;})()`);
 await d.click('Sign in');await until(()=>d.evaluate(`!location.pathname.includes('/login')`),'Authenticated navigation');await d.navigate();
}
try{
 d=await driver(evidence,input.port);
 await check('U5PD-L01 real session authentication',async()=>{await d.navigate();await login(input.username);await d.text(input.runs.completed);});
 await check('U5PD-L02 genuine completed worker and confirmed terminal',async()=>{await d.select(input.runs.completed);await d.text('Observation freshness: TERMINAL');await d.text('Exact recorded best-ever penalties');await d.text('Last verified observation (server source time)');await d.text('Last successful retrieval (browser clock)');await d.capture('L02-real-terminal-history');});
 await check('U5PD-L03 browser reload restores only authorized run selection',async()=>{const mark=crypto.randomUUID();await d.command('Page.addScriptToEvaluateOnNewDocument',{source:'window.__u5pdLive='+JSON.stringify(mark)});await d.command('Page.reload');await until(()=>d.evaluate('window.__u5pdLive==='+JSON.stringify(mark)),'Actual document reload');await d.text('Exact recorded best-ever penalties');assert.equal(await d.evaluate(`new URL(location.href).searchParams.get('run')`),input.runs.completed);});
 await check('U5PD-L04 actual HTTP injected 503 retains history',async()=>{await writeFile(input.fault_path,'DETAIL',{flag:'wx'});await d.click('Refresh selected observations');await d.text('Run observations unavailable');await d.text('Historical observations retained');await d.text('Exact recorded best-ever penalties');await d.capture('L04-real-HTTP-error-retained-history');});
 await check('U5PD-L05 retry after injected fault recovers',async()=>{await unlink(input.fault_path);await d.click('Retry loading');await until(()=>d.evaluate(`!document.body.textContent.includes('Run observations unavailable')`),'HTTP recovered');await d.text('Observation freshness: TERMINAL');});
 await check('U5PD-L06 list failure leaves selected observations mounted',async()=>{await writeFile(input.fault_path,'LIST',{flag:'wx'});await d.click('Refresh run history');await d.text('Research source unavailable');await d.text('Run overview');await d.text('Previously retrieved run history retained');await unlink(input.fault_path);await d.click('Retry loading');await until(()=>d.evaluate(`!document.body.textContent.includes('Research source unavailable')`),'List recovered');});
 await check('U5PD-L07 missing metrics and injected interruption are truthful',async()=>{await d.select(input.runs.missing);await d.text('UNVERIFIED_NOT_CONSUMED');await d.text('Generation-level fitness history unavailable');await d.select(input.runs.interrupted);await d.text('Observation freshness: UNKNOWN');await d.text('EXPIRED_OWNER_LEASE');await d.text('(derived)');});
 await check('U5PD-L08 no operations and only research GETs',async()=>{assert.ok(d.requests.length&&d.requests.every(r=>r.method==='GET'));assert.equal(await d.evaluate(`[...document.querySelectorAll('button')].some(b=>/^(Start|Pause|Resume|Stop|Restore|Promote|Approve|Apply)( |$)/i.test(b.textContent))`),false);});
 await check('U5PD-L09 unscoped real administrator cannot read',async()=>{await d.click('Sign out');await login('unscoped@fictional.invalid');await d.text('Research source unavailable');assert.equal(await d.evaluate(`Boolean(document.querySelector('[aria-label="Selected research run"]'))`),false);});
 assert.deepEqual(d.errors,[]);
}catch(e){process.exitCode=1;console.error('Live continuity verification failed: '+e.message);}
finally{input.password='';try{await unlink(input.fault_path);}catch{}if(evidence)await writeFile(join(evidence,'live-browser-results.json'),JSON.stringify({scope:'Real Edge/React/FastAPI/TCP/session/private SQLite/native worker. Temporary HTTP 503 and expired owner metadata explicitly injected by test harness; not an institutional outage.',scenarios,requests:d?.requests??[],runtime_errors:d?.errors??[],HTTP_interception:false},null,2),{flag:'wx'});await d?.close();}
