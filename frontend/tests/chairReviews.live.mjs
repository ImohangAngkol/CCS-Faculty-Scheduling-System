// Actual Edge -> owned FastAPI/SQLite V2 integration. Private login via stdin.
import {test} from "node:test";
import assert from "node:assert/strict";
import {createServer as viteServer} from "vite";
import {spawn,spawnSync} from "node:child_process";
import {mkdtemp,readFile,mkdir,writeFile,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {resolve,join,relative,isAbsolute,basename,sep} from "node:path";
import {fileURLToPath} from "node:url";
import {sanitizeTree} from "./evidencePrivacy.mjs";

const config=JSON.parse(await new Promise(resolve=>{let raw="";process.stdin.setEncoding("utf8");process.stdin.on("data",chunk=>raw+=chunk);process.stdin.on("end",()=>resolve(raw));}));
const root=fileURLToPath(new URL("../",import.meta.url));
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const now=()=>new Date(Date.now()+8*3600000).toISOString().replace("Z","+08:00");
async function eventually(action,message){const end=Date.now()+30000;while(Date.now()<end){try{if(await action())return;}catch{}await pause(60);}throw new Error(message);}

test("D12 actual HTTP/Edge faculty request lifecycle with fictional schedule source",{timeout:150000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),"d12-live-browser-"));let browser,vite,socket,origin,sequence=0,version,faultOwned=false;
  const pending=new Map(),errors=[],scenarios=[],captures=[];
  const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error("Browser command timeout: "+method));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const value=await command("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});if(value.exceptionDetails)throw new Error(value.exceptionDetails.text);return value.result.value;};
  const text=value=>eventually(()=>evaluate(`document.querySelector('main')?.textContent.includes(${JSON.stringify(value)})`),"Missing live UI text: "+value);
  const click=async value=>{
    await eventually(()=>evaluate(`[...document.querySelectorAll('button')].some(e=>e.textContent===${JSON.stringify(value)}&&!e.disabled)`),"Enabled button missing: "+value);
    return evaluate(`[...document.querySelectorAll('button')].find(e=>e.textContent===${JSON.stringify(value)}).click();true`);
  };
  const input=(selector,value)=>evaluate(`{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));}true`);
  const check=(id,title,action)=>t.test(id+" "+title,async()=>{const started_at=now();try{await action();scenarios.push({id,title,started_at,finished_at:now(),result:"PASS"});}catch(error){scenarios.push({id,title,started_at,finished_at:now(),result:"FAIL",error:error.message});throw error;}});
  const screenshot=async name=>{
    if(!process.env.D12_SCREENSHOT_DIR)return;
    const destination=resolve(process.env.D12_SCREENSHOT_DIR),allowed=resolve(root,"../docs/screenshots/dashboard-d12"),child=relative(allowed,destination);
    assert.ok(child&&!child.startsWith("..")&&!isAbsolute(child));await mkdir(destination,{recursive:true});
    await command("Page.bringToFront");await evaluate("document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))");
    const {data}=await command("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});await writeFile(join(destination,name+".png"),Buffer.from(data,"base64"),{flag:"wx"});
    captures.push({name:name+".png",captured_at:now(),url:await evaluate("location.origin+location.pathname"),query_omitted:true,viewport:await evaluate("({width:innerWidth,height:innerHeight})")});
  };
  try{
    vite=await viteServer({root,envDir:false,configFile:join(root,"vite.config.ts"),server:{host:"localhost",port:config.frontendPort,strictPort:true},logLevel:"error",define:{"import.meta.env.VITE_API_URL":JSON.stringify(config.backend)}});await vite.listen();origin=vite.resolvedUrls.local[0].replace(/\/$/,"");
    browser=spawn("C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--remote-debugging-port=0",`--user-data-dir=${profile}`,"about:blank"],{windowsHide:true,stdio:"ignore"});
    let port,launchError;browser.on("error",error=>launchError=error);
    await eventually(async()=>{if(launchError)throw launchError;port=(await readFile(join(profile,"DevToolsActivePort"),"utf8")).split("\n")[0];return /^\d+$/.test(port);},"Owned live Edge did not start");
    const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(targets.find(t=>t.type==="page").webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true});});
    socket.addEventListener("message",event=>{const value=JSON.parse(event.data),entry=pending.get(value.id);if(entry){pending.delete(value.id);clearTimeout(entry.timer);value.error?entry.reject(new Error(value.error.message)):entry.resolve(value.result);}if(value.method==="Runtime.exceptionThrown")errors.push(value.params.exceptionDetails.text);});
    await command("Runtime.enable");await command("Page.enable");version=await command("Browser.getVersion");await command("Emulation.setDeviceMetricsOverride",{width:1366,height:1100,deviceScaleFactor:1,mobile:false});
    const loginFaculty=async number=>{
      await command("Page.navigate",{url:origin+"/login"});await eventually(()=>evaluate("Boolean(document.querySelector('input[type=password]'))"),"Login form missing");
      await input('input[autocomplete=username]',`faculty${number}@example.invalid`);await input('input[type=password]',config.password);await evaluate("document.querySelector('form').requestSubmit();true");await eventually(()=>evaluate("location.pathname==='/faculty'"),"Faculty login failed");
    };
    const loginAdmin=async()=>{
      await command("Page.navigate",{url:origin+"/login"});await eventually(()=>evaluate("Boolean(document.querySelector('input[type=password]'))"),"Login form missing");
      await input('input[autocomplete=username]','admin@example.invalid');await input('input[type=password]',config.password);await evaluate("document.querySelector('form').requestSubmit();true");await eventually(()=>evaluate("location.pathname==='/admin'"),"Chair account login failed");
    };
    const textarea=(selector,value)=>evaluate(`{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));}true`);
    const api=(path,body)=>evaluate(`(async()=>{const token=(await (await fetch(${JSON.stringify(config.backend+"/api/auth/me")},{credentials:'include'})).json()).csrf_token;const r=await fetch(${JSON.stringify(config.backend)}+${JSON.stringify(path)},{credentials:'include',${body?`method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:${JSON.stringify(JSON.stringify(body))}`:"method:'GET'"}});return {status:r.status,data:await r.json()};})()`);
    const openChair=async()=>{await command("Page.navigate",{url:origin+"/chair/requests"});await text("Department-scoped queue");};
    const openFirst=async()=>{await eventually(()=>evaluate("[...document.querySelectorAll('main button')].some(e=>e.textContent.includes('SYN101 / SYN-A'))"),"Chair request missing");await evaluate("[...document.querySelectorAll('main button')].find(e=>e.textContent.includes('SYN101 / SYN-A')).click();true");await text("Request review:");};
    const createFaculty=async day=>{
      await command("Page.navigate",{url:origin+"/faculty/adjustments"});await text("Your current assignments");
      await evaluate(`{const e=document.querySelector('[aria-label="Adjustment assignment"]');e.selectedIndex=1;e.dispatchEvent(new Event('change',{bubbles:true}));}true`);
      await evaluate(`{const e=document.querySelector('[aria-label="Proposed day"]');e.value=${JSON.stringify(day)};e.dispatchEvent(new Event('change',{bubbles:true}));}true`);
      await textarea('[aria-label="Adjustment justification"]','Fictional request <img src=x onerror=window.__d12Injected=1> for Chair review.');
      await click('Validate proposal');await text('Valid proposal within checked constraints');await click('Save draft request');await text('Draft created.');await click('Submit for Chair review');await click('Confirm submission');await text('Request submitted.');
      const result=await api('/api/adjustment-requests');return result.data.items.find(r=>r.content.input.proposal.day===day).id;
    };
    let first,second,stale,beforeSchedule;
    await check('D12-L01','unauthenticated Chair API and route deny access',async()=>{
      await command('Page.navigate',{url:origin+'/chair/requests'});await text('Sign in');assert.equal((await api('/api/chair-reviews')).status,401);
    });
    await check('D12-L02','bound faculty submits through real UI and cannot decide',async()=>{
      await loginFaculty(0);beforeSchedule=(await api('/api/schedules/me')).data.assignments;first=await createFaculty('TH');
      assert.equal((await api('/api/chair-reviews/'+first)).status,403);assert.equal(await evaluate('window.__d12Injected===undefined'),true);
    });
    await check('D12-L03','independent fictional Chair sees scoped queue and fresh findings',async()=>{
      await click('Sign out');await loginAdmin();await openChair();await openFirst();await text('VALID_PROPOSAL');await text('Pinned GEC constraints:');await text('Fictional request <img');assert.equal(await evaluate('window.__d12Injected===undefined'),true);await screenshot('D12-L03-scoped-review');
    });
    await check('D12-L04','approval requires explanation and explicit confirmation',async()=>{
      assert.equal(await evaluate("[...document.querySelectorAll('button')].find(b=>b.textContent==='Approve pending application').disabled"),true);
      await textarea('[aria-label="Decision explanation"]','Fictional Chair authorizes this proposal; application remains pending.');await click('Approve pending application');await text('Confirm approve?');await click('Confirm decision');await text('Final decision recorded.');await text('APPROVED_PENDING_APPLICATION');await screenshot('D12-L04-approved-pending-application');
    });
    await check('D12-L05','faculty sees durable approval without schedule mutation',async()=>{
      await click('Sign out');await loginFaculty(0);await command('Page.navigate',{url:origin+'/faculty/adjustments'});await text('APPROVED_PENDING_APPLICATION');await evaluate("document.querySelector('[aria-label=\"My request history\"] button').click();true");await text('Department Chair decision:');await text('Your teaching schedule has not changed.');assert.deepEqual((await api('/api/schedules/me')).data.assignments,beforeSchedule);assert.equal(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent==='Withdraw request')"),false);await evaluate(`[...document.querySelectorAll('[aria-label="Request details"] [role=status]')].at(-1).scrollIntoView({block:'center'});true`);await screenshot('D12-L05-faculty-approved');
    });
    await check('D12-L06','second proposal receives explained rejection',async()=>{
      second=await createFaculty('F');await click('Sign out');await loginAdmin();await openChair();await openFirst();await textarea('[aria-label="Decision explanation"]','Fictional rejection: department review requires a different proposal.');await click('Reject request');await click('Confirm decision');await text('Final decision recorded.');await text('REJECTED');await screenshot('D12-L06-rejected-history');
    });
    await check('D12-L07','faculty sees rejection and cannot replace a final decision',async()=>{
      await click('Sign out');await loginFaculty(0);const own=await api('/api/adjustment-requests/'+second);assert.equal(own.data.status,'REJECTED');assert.match(own.data.decision.explanation,/Fictional rejection/);assert.equal((await api('/api/adjustment-requests/'+second+'/withdraw',{operation_id:crypto.randomUUID(),expected_version:2})).status,409);assert.deepEqual((await api('/api/schedules/me')).data.assignments,beforeSchedule);
    });
    await check('D12-L08','stale source blocks approval while rejection remains available',async()=>{
      stale=await createFaculty('S');assert.ok(isAbsolute(config.faultFile)&&basename(config.faultFile)==='d12-stale.marker');await writeFile(config.faultFile,'fictional stale source',{flag:'wx'});faultOwned=true;
      await click('Sign out');await loginAdmin();await openChair();await openFirst();await text('STALE_SCHEDULE_REFERENCE');assert.equal(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent==='Approve pending application')"),false);await screenshot('D12-L08-stale-approval-blocked');await rm(config.faultFile);faultOwned=false;
    });
    await check('D12-L09','concurrent contradictory HTTP decisions retain exactly one final',async()=>{
      const row=(await api('/api/chair-reviews/'+stale)).data.request;
      const command={expected_version:row.version,explanation:'Fictional concurrent independent decision.',content_digest:row.content_digest,schedule_revision:row.content.input.revision,constraint_digest:row.content.review.constraint_digest};
      const responses=await Promise.all(['approve','reject'].map(action=>api('/api/chair-reviews/'+stale+'/'+action,{...command,operation_id:crypto.randomUUID()})));assert.deepEqual(responses.map(r=>r.status).sort(),[200,409]);assert.equal((await api('/api/chair-reviews/'+stale+'/history')).data.history.length,1);
    });
    await check('D12-L10','mobile decided history is available after a full reload',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await openChair();await text('No eligible requests');await evaluate("document.querySelector('input[type=checkbox]').click();true");await openFirst();await text('Decision history');assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await evaluate("document.querySelector('[aria-label=\"Chair request details\"]').scrollIntoView();true");await screenshot('D12-L10-mobile-decision');
    });
    await check('D12-L11','authenticated ordinary faculty cannot enter Chair review or obtain controls',async()=>{
      await click('Sign out');await loginFaculty(1);await command('Page.navigate',{url:origin+'/chair/requests'});await text('Chair review unavailable');await text('CHAIR_AUTHORITY_REQUIRED');assert.equal(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent==='Approve pending application'||b.textContent==='Reject request')"),false);await screenshot('D12-L11-ordinary-account-denied');
    });
    await check('D12-L12','retry rechecks authority without granting access or showing cached private rows',async()=>{
      await click('Retry loading');await text('CHAIR_AUTHORITY_REQUIRED');assert.equal(await evaluate("document.querySelector('[aria-label=\"Chair request details\"]')===null"),true);
    });
    assert.deepEqual(errors,[]);
  }finally{
    if(faultOwned)await rm(config.faultFile);
    if(process.env.D12_SCREENSHOT_DIR){await mkdir(resolve(process.env.D12_SCREENSHOT_DIR),{recursive:true});await writeFile(join(resolve(process.env.D12_SCREENSHOT_DIR),"browser-results.json"),JSON.stringify(sanitizeTree({scope:"Actual Edge -> FastAPI HTTP -> owned SQLite; real sessions/Origin/CSRF and decision transactions, explicitly fictional Chair directory, scope, guarded schedule and trusted snapshot provider. Real D8-D10 integration is tested separately by backend tests; no PostgreSQL or genuine institutional authority",browser:version?.product,node:process.version,scenarios,captures}),null,2),{flag:"wx"});}
    for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error("Live browser closing"));}socket?.close();
    if(browser&&browser.exitCode===null)spawnSync("taskkill",["/PID",String(browser.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await vite?.close();
    const target=resolve(profile),parent=resolve(tmpdir());assert.ok(target.startsWith(parent+sep)&&basename(target).startsWith("d12-live-browser-"));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200});
  }
});
