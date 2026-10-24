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

test("D14 actual HTTP/Edge whole system journey using actual constrained generation and fictional institutional providers",{timeout:150000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),"d14-live-browser-"));let browser,vite,socket,origin,sequence=0,version,faultOwned=false;
  const pending=new Map(),errors=[],scenarios=[],captures=[];
  const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error("Browser command timeout: "+method));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const value=await command("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});if(value.exceptionDetails)throw new Error(value.exceptionDetails.exception?.description??value.exceptionDetails.text);return value.result.value;};
  const text=value=>eventually(()=>evaluate(`document.querySelector('main')?.textContent.includes(${JSON.stringify(value)})`),"Missing live UI text: "+value);
  const click=async value=>{
    await eventually(()=>evaluate(`[...document.querySelectorAll('button')].some(e=>e.textContent===${JSON.stringify(value)}&&!e.disabled)`),"Enabled button missing: "+value);
    return evaluate(`[...document.querySelectorAll('button')].find(e=>e.textContent===${JSON.stringify(value)}).click();true`);
  };
  const input=(selector,value)=>evaluate(`{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));}true`);
  const check=async(id,title,action)=>{
    await t.test(id+" "+title,async()=>{const started_at=now();try{await action();scenarios.push({id,title,started_at,finished_at:now(),result:"PASS"});}catch(error){scenarios.push({id,title,started_at,finished_at:now(),result:"FAIL",error:error.message});throw error;}});
    console.log(JSON.stringify({scenario:id,result:scenarios.at(-1)?.result}));
    if(scenarios.at(-1)?.result==='FAIL')throw new Error('Dependent journey stopped after '+id);
  };
  const screenshot=async name=>{
    if(!process.env.D14_SCREENSHOT_DIR)return;
    const destination=resolve(process.env.D14_SCREENSHOT_DIR),allowed=resolve(root,"../docs/screenshots/dashboard-d14"),child=relative(allowed,destination);
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
    const select=(selector,value)=>evaluate(`{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('change',{bubbles:true}));}true`);
    const createFaculty=async desiredDay=>{
      await command('Page.navigate',{url:origin+'/faculty/adjustments'});await text('Your current assignments');
      const data=(await api('/api/adjustment-requests/assignments')).data;
      const row=data.assignments.find(m=>m.component==='Laboratory');assert.ok(row);
      let chosen;
      outer:for(const day of [desiredDay,...['F','S','TH','T','W','M'].filter(d=>d!==desiredDay)])for(const [start,end]of [['07:30','10:30'],['10:30','13:30'],['13:00','16:00'],['16:00','19:00']]){
        const body={schedule_id:data.schedule_id,revision:data.revision,assignment_id:row.id,academic_year:data.academic_year,term:data.term,proposal:{day,start,end,room_id:row.room_id},justification:'Fictional D14 generated timetable adjustment.'};
        const reply=await api('/api/adjustment-requests/preview',body);if(reply.status===200&&reply.data.validation.outcome==='VALID_PROPOSAL'){chosen=body;break outer;}
      }
      assert.ok(chosen,'No valid controlled adjustment found');if(!firstProposal)firstProposal=chosen;
      await select('[aria-label="Adjustment assignment"]',row.id);await select('[aria-label="Proposed day"]',chosen.proposal.day);
      await input('[aria-label="Proposed start"]',chosen.proposal.start);await input('[aria-label="Proposed end"]',chosen.proposal.end);
      await textarea('[aria-label="Adjustment justification"]',chosen.justification);
      await click('Validate proposal');await text('Valid proposal within checked constraints');await click('Save draft request');await text('Draft created.');await click('Submit for Chair review');await click('Confirm submission');await text('Request submitted.');
      const result=await api('/api/adjustment-requests');return result.data.items.find(r=>r.content.input.proposal.day===chosen.proposal.day&&r.content.input.proposal.start===chosen.proposal.start&&r.status==='SUBMITTED').id;
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
    let first,rejected,trustRequest,beforeSchedule,originalRevision,firstProposal,runId,originalGenerated;
    await check('D14-L01','anonymous application API and route deny access',async()=>{
      await command('Page.navigate',{url:origin+'/schedule-applications'});await text('Sign in');assert.equal((await api('/api/schedule-applications')).status,401);
    });
    await check('D14-I01','real faculty preference write and full reload preserve Compact / Very High',async()=>{
      await loginFaculty(0);await command('Page.navigate',{url:origin+'/faculty/preferences'});await text('Schedule Style');
      await evaluate(`document.querySelector('input[name="schedule-style"][value="Compact"]').click();true`);
      await eventually(()=>evaluate(`[...document.querySelectorAll('label')].some(e=>e.textContent.startsWith('Schedule style importance'))`),'Importance missing');
      await evaluate(`{const e=[...document.querySelectorAll('label')].find(e=>e.textContent.startsWith('Schedule style importance')).querySelector('select');Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(e,'5');e.dispatchEvent(new Event('change',{bubbles:true}));}true`);
      await click('Save Preferences');await text('Saved');await command('Page.reload');await text('Schedule Style');
      const saved=(await api('/preferences/0')).data;assert.equal(saved.gap_preference,'Compact');assert.equal(saved.gap_importance,5);assert.equal(saved.use_gap_preference,true);
      await screenshot('D14-I01-real-preference-persistence');await click('Sign out');
    });
    await check('D14-I02','administrator catalog and durable fictional GEC confirmation history use real APIs',async()=>{
      await loginAdmin();await command('Page.navigate',{url:origin+'/admin/subjects'});await text('Subject');await text('SYN101');
      await command('Page.navigate',{url:origin+'/admin/external-schedules'});await text('GEC confirmation and revision history');
      await eventually(()=>evaluate(`document.querySelector('[aria-label="GEC ledger record"]')?.options.length>1`),'Confirmation history missing');
      await select('[aria-label="GEC ledger record"]',config.recordId);await text('Status CONFIRMED');await text('NOT RECHECKED');await text('Durable revisions and confirmation decisions are managed separately');assert.equal(await evaluate(`document.querySelector('main').textContent.includes('Nothing here is saved, confirmed')`),false);
      await evaluate(`document.querySelector('[aria-label="Durable GEC confirmation ledger"]').scrollIntoView();true`);await screenshot('D14-I02-real-confirmed-ledger');
    });
    await check('D14-I03','real UI starts original constrained engine against this exact confirmed ledger',async()=>{
      await command('Page.navigate',{url:origin+'/admin/generate'});await text('Confirmed GEC constraints');await input('[aria-label="V2 academic year"]','2026-2027');await input('[aria-label="V2 term"]','Fictional first term');await click('Check confirmed constraints');await text('1 fixed weekly commitments');
      await input('[aria-label="V2 population"]','2');await input('[aria-label="V2 generations"]','1');await click('Start constrained V2');await text('V2: COMPLETED');runId=await evaluate(`new URLSearchParams(location.search).get('v2run')`);assert.match(runId,/^[a-f0-9-]{36}$/);
      const result=await api('/api/ga/v2/runs/'+runId);assert.equal(result.status,200);assert.equal(result.data.result.revisions[0].revision_id,config.revisionId);originalGenerated=JSON.stringify(result.data.result);
    });
    await check('D14-I04','real generated timetable and original fitness precede explicit fictional publication designation',async()=>{
      await command('Page.navigate',{url:origin+'/admin/schedules?v2run='+runId});await text('V2 constrained schedule');await text('SYN101');await screenshot('D14-I04-actual-constrained-proposal');
      await command('Page.navigate',{url:origin+'/admin/analysis?v2run='+runId});await text('Original fitness evaluation');await text('Generation 1');await screenshot('D14-I04-actual-fitness-analysis');
      assert.equal(basename(config.publishFile),'d14-explicit-publication.json');await writeFile(config.publishFile,JSON.stringify({run_id:runId}),{flag:'wx'});await click('Sign out');
    });
    await check('D14-L02','faculty submits proposed change against explicit fictional published source',async()=>{
      await loginFaculty(0);beforeSchedule=(await api('/api/schedules/me')).data;assert.equal(beforeSchedule.schema_version,2);originalRevision=beforeSchedule.source.revision;first=await createFaculty('F');assert.equal((await api('/api/schedule-applications')).status,403);
    });
    await check('D14-L03','Chair approval remains pending and does not grant publishing',async()=>{
      await click('Sign out');await loginAdmin();await openChair();await openFirst();await textarea('[aria-label="Decision explanation"]','Fictional Chair authorizes the proposal, not publication.');await click('Approve pending application');await click('Confirm decision');await text('APPROVED_PENDING_APPLICATION');assert.equal((await api('/api/schedule-applications')).status,403);
    });
    await check('D14-L04','independent scheduler previews before/after and complete rules without writing versions',async()=>{
      await click('Sign out');await loginPublisher();await openApplications();await openApplication();await text('Fresh complete-schedule validation: VALID');await text('Before');await text('After authorized adjustment');await text('Preview has written no version.');assert.equal((await api('/api/schedule-applications/versions')).data.versions.length,0);await screenshot('D14-L04-validated-application-preview');
    });
    await check('D14-L05','injected persistence failure rolls back version, head and application together',async()=>{
      assert.ok(isAbsolute(config.faultFile)&&basename(config.faultFile)==='d14-fault.marker');await writeFile(config.faultFile,'rollback',{flag:'wx'});faultOwned=true;await click('Apply adjustment');await text('Commit this approved change');await click('Confirm application');await text('APPLICATION_CONCURRENT_UPDATE');const v=await api('/api/schedule-applications/versions');assert.equal(v.data.versions.length,0);assert.equal(v.data.current_version_id,null);await screenshot('D14-L05-rollback-blocked');await rm(config.faultFile);faultOwned=false;
    });
    await check('D14-L06','recovery publishes one new version after explicit confirmation',async()=>{
      await click('Refresh applications');await text('Approved requests');await openApplication();await click('Apply adjustment');await click('Confirm application');await text('Adjustment applied to a new published version.');await text('Application APPLIED');const v=(await api('/api/schedule-applications/versions')).data;assert.equal(v.versions.length,2);assert.equal(v.versions[0].revision,originalRevision);assert.equal(v.versions[1].meetings.find(m=>m.id===firstProposal.assignment_id).day,firstProposal.proposal.day);assert.equal(v.versions[0].meetings.filter((m,i)=>JSON.stringify(m)!==JSON.stringify(v.versions[1].meetings[i])).length,1);assert.equal(v.current_version_id,v.versions[1].id);await screenshot('D14-L06-applied-version-history');
    });
    await check('D14-L07','faculty sees APPLIED audit and new published timetable after refresh',async()=>{
      await click('Sign out');await loginFaculty(0);await command('Page.navigate',{url:origin+'/faculty/adjustments'});await text('APPLIED');await evaluate("document.querySelector('[aria-label=\"My request history\"] button').click();true");await text('Adjustment APPLIED');await text('Published version 2');await command('Page.navigate',{url:origin+'/faculty/schedule'});await text('Published schedule with authorized post-GA changes');await text('Published version 2');const own=(await api('/api/schedules/me')).data;assert.ok(own.assignments.some(m=>m.type==='Laboratory'&&m.day===firstProposal.proposal.day&&m.start===firstProposal.proposal.start));assert.equal(own.assignments.length,beforeSchedule.assignments.length);assert.equal(own.source.post_ga_changes,true);await screenshot('D14-L07-faculty-published-timetable');
    });
    await check('D14-L08','another faculty identity cannot read private request or application history',async()=>{
      await click('Sign out');await loginFaculty(1);assert.equal((await api('/api/adjustment-requests/'+first)).status,404);assert.equal((await api('/api/schedule-applications/'+first+'/history')).status,403);assert.ok((await api('/api/schedules/me')).data.assignments.every(r=>r.subject==='SYN202'));
    });
    await check('D14-L09','rejected request cannot be applied through the real API',async()=>{
      await click('Sign out');await loginFaculty(0);rejected=await createFaculty('TH');await click('Sign out');await loginAdmin();assert.equal((await chairDecision(rejected,'reject')).status,200);await click('Sign out');await loginPublisher();assert.equal((await api('/api/schedule-applications/'+rejected+'/preview')).status,409);
    });
    await check('D14-L10','new request uses current published revision and receives a new approval',async()=>{
      await click('Sign out');await loginFaculty(0);trustRequest=await createFaculty('W');const r=(await api('/api/adjustment-requests/'+trustRequest)).data;assert.notEqual(r.content.input.revision,originalRevision);await click('Sign out');await loginAdmin();assert.equal((await chairDecision(trustRequest)).status,200);await click('Sign out');await loginPublisher();
    });
    await check('D14-L11','injected current GEC trust loss blocks application while retaining current version',async()=>{
      await writeFile(config.faultFile,'trust',{flag:'wx'});faultOwned=true;await openApplications();await openApplication(false);await text('FICTIONAL_GEC_TRUST_UNAVAILABLE');assert.equal(await evaluate("[...document.querySelectorAll('button')].some(b=>b.textContent==='Apply adjustment')"),false);assert.equal((await api('/api/schedule-applications/versions')).data.versions.length,2);await screenshot('D14-L11-trust-unavailable-blocked');await rm(config.faultFile);faultOwned=false;
    });
    await check('D14-L12','concurrent HTTP application attempts retain one final publication',async()=>{
      const p=(await api('/api/schedule-applications/'+trustRequest+'/preview')).data;const responses=await Promise.all([1,2].map(()=>api('/api/schedule-applications/'+trustRequest+'/apply',{...p.command,operation_id:crypto.randomUUID()})));assert.deepEqual(responses.map(r=>r.status).sort(),[200,409]);assert.equal((await api('/api/schedule-applications/'+trustRequest+'/history')).data.applications.length,1);assert.equal((await api('/api/schedule-applications/versions')).data.versions.length,3);
    });
    await check('D14-L13','mobile retained published versions are read-only and contained',async()=>{
      await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});await openApplications();await evaluate("document.querySelector('input[type=checkbox]').click();true");await openApplication();await text('Published version history');assert.equal(JSON.stringify((await api('/api/ga/v2/runs/'+runId)).data.result),originalGenerated);assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);await evaluate("document.querySelector('details').open=true;document.querySelector('details').scrollIntoView();true");await screenshot('D14-L13-mobile-preserved-version');
    });
    await check('D14-L14','ordinary authenticated account has no publication controls or cached private review',async()=>{
      await click('Sign out');await loginFaculty(1);await command('Page.navigate',{url:origin+'/schedule-applications'});await text('Schedule application blocked');await text('APPLICATION_AUTHORITY_REQUIRED');assert.equal(await evaluate("document.querySelector('[aria-label=\"Application review\"]')===null"),true);await click('Retry loading');await text('APPLICATION_AUTHORITY_REQUIRED');
    });
    await check('D14-I05','bound faculty without assignments receives an honest empty published timetable',async()=>{
      await click('Sign out');await loginFaculty(2);await command('Page.navigate',{url:origin+'/faculty/schedule'});await text('No assignments in this published schedule');assert.equal((await api('/api/schedules/me')).data.assignments.length,0);await screenshot('D14-I05-empty-published-timetable');
    });
    await check('D14-I06','stopping only the owned backend clears the portal and exposes session retry',async()=>{
      assert.equal(basename(config.stopFile),'d14-http.stop');await writeFile(config.stopFile,'',{flag:'wx'});
      await eventually(async()=>{try{await fetch(config.backend+'/api/auth/me');return false;}catch{return true;}},'Owned HTTP fixture did not stop');
      await command('Page.navigate',{url:origin+'/faculty/schedule'});await eventually(()=>evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Retry session check')`),'Session retry missing after real connection refusal');
      assert.equal(await evaluate(`document.querySelector('[aria-label="Weekly timetable"]')===null`),true);await screenshot('D14-I06-owned-backend-unavailable');
    });
    assert.deepEqual(errors,[]);
  }finally{
    if(faultOwned)await rm(config.faultFile);
    if(process.env.D14_SCREENSHOT_DIR){await mkdir(resolve(process.env.D14_SCREENSHOT_DIR),{recursive:true});await writeFile(join(resolve(process.env.D14_SCREENSHOT_DIR),"browser-results.json"),JSON.stringify(sanitizeTree({scope:"Actual Edge -> FastAPI HTTP -> owned SQLite; real authentication, original GA execution, actual D8-D10 ledger revalidation, Chair decisions and application transactions. Independent publisher, Chair, evidence issuer, confirmer, catalog and capacity providers are explicitly fictional; source publication is an explicit owned test handoff, not a production promotion feature. The initial GEC confirmation is created through the real API by fixture setup. Storage and trust faults are fixture injections. No PostgreSQL or institutional approval.",browser:version?.product,node:process.version,scenarios,captures,runtime_errors:errors}),null,2),{flag:"wx"});}
    for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error("Live browser closing"));}socket?.close();
    if(browser&&browser.exitCode===null)spawnSync("taskkill",["/PID",String(browser.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await vite?.close();
    const target=resolve(profile),parent=resolve(tmpdir());assert.ok(target.startsWith(parent+sep)&&basename(target).startsWith("d14-live-browser-"));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200});
  }
});
