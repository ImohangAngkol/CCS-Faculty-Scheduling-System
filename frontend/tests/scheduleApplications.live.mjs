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

test("D13 actual HTTP/Edge faculty request lifecycle with fictional schedule source",{timeout:150000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),"d13-live-browser-"));let browser,vite,socket,origin,sequence=0,version,faultOwned=false;
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
    if(!process.env.D13_SCREENSHOT_DIR)return;
    const destination=resolve(process.env.D13_SCREENSHOT_DIR),allowed=resolve(root,"../docs/screenshots/dashboard-d13"),child=relative(allowed,destination);
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
    socket.addEventListener("message",event=>{const value=JSON.parse(event.data),entry=pending.get(value.id);if(entry){pending.delete(value.id);clearTimeout(entry.timer);value.error?entry.reject(new Error(value.error.message)):entry.resolve(value.result);}if(value.method==="Runtime.exceptionThrown")errors.push(value.params.exceptionDetails.exception?.description??value.params.exceptionDetails.text);});
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
      await textarea('[aria-label="Adjustment justification"]','Fictional request <img src=x onerror=window.__d13Injected=1> for Chair review.');
      await click('Validate proposal');await text('Valid proposal within checked constraints');await click('Save draft request');await text('Draft created.');await click('Submit for Chair review');await click('Confirm submission');await text('Request submitted.');
      const result=await api('/api/adjustment-requests');return result.data.items.find(r=>r.content.input.proposal.day===day).id;
    };
    const loginPublisher=async()=>{
      await command('Page.navigate',{url:origin+'/login'});await eventually(()=>evaluate("Boolean(document.querySelector('input[type=password]'))"),'Login missing');await input('input[autocomplete=username]','scheduler@example.invalid');await input('input[type=password]',config.password);await evaluate("document.querySelector('form').requestSubmit();true");await eventually(()=>evaluate("location.pathname==='/admin'"),'Publisher login failed');
    };
    const openApplications=async()=>{await command('Page.navigate',{url:origin+'/schedule-applications'});await text('Approved requests');};
    const openApplication=async(expectReview=true)=>{await eventually(()=>evaluate("[...document.querySelectorAll('main button')].some(b=>b.textContent.includes('SYN101 / SYN-A'))"),'Application missing');await evaluate("[...document.querySelectorAll('main button')].find(b=>b.textContent.includes('SYN101 / SYN-A')).click();true");if(expectReview)await text('Application:');};
    const chairDecision=async(id,action='approve')=>{
      const result=await api('/api/chair-reviews/'+id),r=result.data.request;
      return api('/api/chair-reviews/'+id+'/'+action,{operation_id:crypto.randomUUID(),expected_version:r.version,explanation:'Fictional independent Chair decision for application testing.',content_digest:r.content_digest,schedule_revision:r.content.input.revision,constraint_digest:r.content.review.constraint_digest});
    };
    let first,rejected,trustRequest,concurrent,beforeSchedule,originalRevision;
    await check('D13-L01','anonymous application API and route deny access',async()=>{
      await command('Page.navigate',{url:origin+'/schedule-applications'});await text('Sign in');assert.equal((await api('/api/schedule-applications')).status,401);
    });
    await check('D13-L02','faculty submits proposed change against explicit fictional published source',async()=>{
      await loginFaculty(0);beforeSchedule=(await api('/api/schedules/me')).data;assert.equal(beforeSchedule.schema_version,2);originalRevision=beforeSchedule.source.revision;first=await createFaculty('F');assert.equal((await api('/api/schedule-applications')).status,403);
    });
    await check('D13-L03','Chair approval remains pending and does not grant publishing',async()=>{
      await click('Sign out');await loginAdmin();await openChair();await openFirst();await textarea('[aria-label="Decision explanation"]','Fictional Chair authorizes the proposal, not publication.');await click('Approve pending application');await click('Confirm decision');await text('APPROVED_PENDING_APPLICATION');assert.equal((await api('/api/schedule-applications')).status,403);
    });
    await check('D13-L04','independent scheduler previews before/after and complete rules without writing versions',async()=>{
      await click('Sign out');await loginPublisher();await openApplications();await openApplication();await text('Fresh complete-schedule validation: VALID');await text('Before');await text('After authorized adjustment');await text('Preview has written no version.');assert.equal((await api('/api/schedule-applications/versions')).data.versions.length,0);await screenshot('D13-L04-validated-application-preview');
    });
    await check('D13-L05','injected persistence failure rolls back version, head and application together',async()=>{
      assert.ok(isAbsolute(config.faultFile)&&basename(config.faultFile)==='d13-fault.marker');await writeFile(config.faultFile,'rollback',{flag:'wx'});faultOwned=true;await click('Apply adjustment');await text('Commit this approved change');await click('Confirm application');await text('APPLICATION_CONCURRENT_UPDATE');const v=await api('/api/schedule-applications/versions');assert.equal(v.data.versions.length,0);assert.equal(v.data.current_version_id,null);await screenshot('D13-L05-rollback-blocked');await rm(config.faultFile);faultOwned=false;
    });
    await check('D13-L06','recovery publishes one new version after explicit confirmation',async()=>{
      await click('Refresh applications');await text('Approved requests');await openApplication();await click('Apply adjustment');await click('Confirm application');await text('Adjustment applied to a new published version.');await text('Application APPLIED');const v=(await api('/api/schedule-applications/versions')).data;assert.equal(v.versions.length,2);assert.equal(v.versions[0].revision,originalRevision);assert.equal(v.versions[0].meetings[0].day,'M');assert.equal(v.versions[1].meetings[0].day,'F');assert.equal(v.current_version_id,v.versions[1].id);await screenshot('D13-L06-applied-version-history');
    });
    await check('D13-L07','faculty sees APPLIED audit and new published timetable after refresh',async()=>{
      await click('Sign out');await loginFaculty(0);await command('Page.navigate',{url:origin+'/faculty/adjustments'});await text('APPLIED');await evaluate("document.querySelector('[aria-label=\"My request history\"] button').click();true");await text('Adjustment APPLIED');await text('Published version 2');await command('Page.navigate',{url:origin+'/faculty/schedule'});await text('Published schedule with authorized post-GA changes');await text('Published version 2');const own=(await api('/api/schedules/me')).data;assert.equal(own.assignments[0].day,'F');assert.equal(own.assignments.length,2);assert.equal(own.source.post_ga_changes,true);await screenshot('D13-L07-faculty-published-timetable');
    });
    await check('D13-L08','another faculty identity cannot read private request or application history',async()=>{
      await click('Sign out');await loginFaculty(1);assert.equal((await api('/api/adjustment-requests/'+first)).status,404);assert.equal((await api('/api/schedule-applications/'+first+'/history')).status,403);assert.deepEqual((await api('/api/schedules/me')).data.assignments.map(r=>r.subject),['SYN202']);
    });
    await check('D13-L09','rejected request cannot be applied through the real API',async()=>{
      await click('Sign out');await loginFaculty(0);rejected=await createFaculty('TH');await click('Sign out');await loginAdmin();assert.equal((await chairDecision(rejected,'reject')).status,200);await click('Sign out');await loginPublisher();assert.equal((await api('/api/schedule-applications/'+rejected+'/preview')).status,409);
    });
    await check('D13-L10','new request uses current published revision and receives a new approval',async()=>{
      await click('Sign out');await loginFaculty(0);trustRequest=await createFaculty('W');const r=(await api('/api/adjustment-requests/'+trustRequest)).data;assert.notEqual(r.content.input.revision,originalRevision);await click('Sign out');await loginAdmin();assert.equal((await chairDecision(trustRequest)).status,200);await click('Sign out');await loginPublisher();
    });
    await check('D13-L11','injected current GEC trust loss blocks application while retaining current version',async()=>{
      await writeFile(config.faultFile,'trust',{flag:'wx'});faultOwned=true;await openApplications();await openApplication(false);await text('FICTIONAL_GEC_TRUST_UNAVAILABLE');assert.equal(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent==='Apply adjustment')"),false);assert.equal((await api('/api/schedule-applications/versions')).data.versions.length,2);await screenshot('D13-L11-trust-unavailable-blocked');await rm(config.faultFile);faultOwned=false;
    });
    await check('D13-L12','concurrent HTTP application attempts retain one final publication',async()=>{
      const p=(await api('/api/schedule-applications/'+trustRequest+'/preview')).data;const responses=await Promise.all([1,2].map(()=>api('/api/schedule-applications/'+trustRequest+'/apply',{...p.command,operation_id:crypto.randomUUID()})));assert.deepEqual(responses.map(r=>r.status).sort(),[200,409]);assert.equal((await api('/api/schedule-applications/'+trustRequest+'/history')).data.applications.length,1);assert.equal((await api('/api/schedule-applications/versions')).data.versions.length,3);
    });
    await check('D13-L13','mobile retained published versions are read-only and contained',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await openApplications();await evaluate("document.querySelector('input[type=checkbox]').click();true");await openApplication();await text('Published version history');assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await evaluate("document.querySelector('details').open=true;document.querySelector('details').scrollIntoView();true");await screenshot('D13-L13-mobile-preserved-version');
    });
    await check('D13-L14','ordinary authenticated account has no publication controls or cached private review',async()=>{
      await click('Sign out');await loginFaculty(1);await command('Page.navigate',{url:origin+'/schedule-applications'});await text('Schedule application blocked');await text('APPLICATION_AUTHORITY_REQUIRED');assert.equal(await evaluate("document.querySelector('[aria-label=\"Application review\"]')===null"),true);await click('Retry loading');await text('APPLICATION_AUTHORITY_REQUIRED');
    });
    assert.deepEqual(errors,[]);
  }finally{
    if(faultOwned)await rm(config.faultFile);
    if(process.env.D13_SCREENSHOT_DIR){await mkdir(resolve(process.env.D13_SCREENSHOT_DIR),{recursive:true});await writeFile(join(resolve(process.env.D13_SCREENSHOT_DIR),"browser-results.json"),JSON.stringify(sanitizeTree({scope:"Actual Edge -> FastAPI HTTP -> owned SQLite; real authentication, Chair decisions and application transactions. Independent publisher, Chair, published-source, capacity and trust providers are explicitly fictional. Storage and trust faults are fixture injections; real D8-D10 verification is exercised separately by backend tests. No PostgreSQL or institutional approval.",browser:version?.product,node:process.version,scenarios,captures,runtime_errors:errors}),null,2),{flag:"wx"});}
    for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error("Live browser closing"));}socket?.close();
    if(browser&&browser.exitCode===null)spawnSync("taskkill",["/PID",String(browser.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await vite?.close();
    const target=resolve(profile),parent=resolve(tmpdir());assert.ok(target.startsWith(parent+sep)&&basename(target).startsWith("d13-live-browser-"));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200});
  }
});
