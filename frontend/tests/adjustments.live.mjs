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

test("D11 actual HTTP/Edge faculty request lifecycle with fictional schedule source",{timeout:150000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),"d11-live-browser-"));let browser,vite,socket,origin,sequence=0,version,faultOwned=false;
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
    if(!process.env.D11_SCREENSHOT_DIR)return;
    const destination=resolve(process.env.D11_SCREENSHOT_DIR),allowed=resolve(root,"../docs/screenshots/dashboard-d11"),child=relative(allowed,destination);
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
    const open=async()=>{await command("Page.navigate",{url:origin+"/faculty/adjustments"});await text("Your current assignments");};
    const chooseDay=async day=>evaluate(`{const e=document.querySelector('[aria-label="Proposed day"]');e.value=${JSON.stringify(day)};e.dispatchEvent(new Event('change',{bubbles:true}));}true`);
    const setReason=async value=>evaluate(`{const e=document.querySelector('textarea');Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));}true`);
    let requestId,beforeSchedule;
    await check("D11-L01","unauthenticated real API rejects requests",async()=>{
      await command("Page.navigate",{url:origin+"/login"});await text("Sign in");
      assert.equal(await evaluate(`fetch(${JSON.stringify(config.backend+"/api/adjustment-requests")},{credentials:'include'}).then(r=>r.status)`),401);
    });
    await check("D11-L02","real bound faculty sees only own assignments and empty history",async()=>{
      await loginFaculty(0);await open();await text("No adjustment requests yet.");
      assert.equal(await evaluate("document.querySelector('main').textContent.includes('Other private synthetic assignment')"),false);
      beforeSchedule=await evaluate(`fetch(${JSON.stringify(config.backend+"/api/schedules/me")},{credentials:'include'}).then(r=>r.json()).then(v=>JSON.stringify(v.assignments))`);
      await evaluate(`{const e=document.querySelector('[aria-label="Adjustment assignment"]');e.selectedIndex=1;e.dispatchEvent(new Event('change',{bubbles:true}));}true`);
      await setReason('Fictional reason <img src=x onerror=window.__d11Injected=1> for adjustment.');
    });
    await check("D11-L03","invalid lecture duration rejected by actual API",async()=>{
      await input('[aria-label="Proposed end"]','09:30');await click("Validate proposal");await text("INVALID_TIME_OR_DURATION");await input('[aria-label="Proposed end"]','10:30');
    });
    await check("D11-L04","real room conflict remains a review discrepancy",async()=>{
      await chooseDay('T');await click("Validate proposal");await text("ROOM_CONFLICT");await text("Proposal requires authorized review");
    });
    await check("D11-L05","confirmed fictional GEC commitment conflicts explicitly",async()=>{
      await chooseDay('F');await click("Validate proposal");await text("CONFIRMED_GEC_CONFLICT");
    });
    await check("D11-L06","valid proposal renders safely and cannot imply approval",async()=>{
      await chooseDay('TH');await click("Validate proposal");await text("Valid proposal within checked constraints");
      assert.equal(await evaluate("window.__d11Injected===undefined"),true);await screenshot("D11-L06-validated-proposal");
    });
    await check("D11-L07","draft persists through real SQLite API",async()=>{
      await click("Save draft request");await text("Draft created.");
      requestId=await evaluate("fetch("+JSON.stringify(config.backend+"/api/adjustment-requests")+",{credentials:'include'}).then(r=>r.json()).then(v=>v.items[0].id)");assert.match(requestId,/^[a-f0-9-]{36}$/);
      await text("Fictional reason <img");assert.equal(await evaluate("window.__d11Injected===undefined"),true);
    });
    await check("D11-L08","explicit submission retains original schedule",async()=>{
      await click("Submit for future Chair review");await text("Submit this proposal?");await click("Confirm submission");await text("Request submitted.");
      assert.equal(await evaluate(`fetch(${JSON.stringify(config.backend+"/api/schedules/me")},{credentials:'include'}).then(r=>r.json()).then(v=>JSON.stringify(v.assignments))`),beforeSchedule);
      await evaluate(`document.querySelector('[aria-label="Request details"]').scrollIntoView();true`);await screenshot("D11-L08-submitted-history");
    });
    await check("D11-L09","submitted request survives a full dashboard reload",async()=>{
      await open();await text("SUBMITTED");await evaluate(`[...document.querySelectorAll('[aria-label="My request history"] button')][0].click();true`);await text("Request details");await text("2. SUBMITTED");
    });
    await check("D11-L10","another real faculty session cannot access private request",async()=>{
      await click("Sign out");await loginFaculty(1);await open();await text("No adjustment requests yet.");
      assert.equal(await evaluate(`fetch(${JSON.stringify(config.backend+"/api/adjustment-requests/")}+${JSON.stringify(requestId)},{credentials:'include'}).then(r=>r.status)`),404);
    });
    await check("D11-L11","unavailable source retains private history and permits withdrawal",async()=>{
      await click("Sign out");await loginFaculty(0);
      assert.ok(isAbsolute(config.faultFile)&&basename(config.faultFile)==='d11-unavailable.marker');await writeFile(config.faultFile,'fictional fixture unavailable',{flag:'wx'});faultOwned=true;
      await command("Page.navigate",{url:origin+"/faculty/adjustments"});await text("Adjustment source unavailable");await text("SUBMITTED");
      await evaluate(`[...document.querySelectorAll('[aria-label="My request history"] button')][0].click();true`);await text("Request details");await text("UNAVAILABLE");await click("Withdraw request");await text("Request withdrawn.");await text("3. WITHDRAWN");
      await rm(config.faultFile);faultOwned=false;
    });
    await check("D11-L12","mobile view exposes preserved proposal/history after recovery",async()=>{
      await command("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:false});
      await open();await text("WITHDRAWN");await evaluate(`[...document.querySelectorAll('[aria-label="My request history"] button')][0].click();true`);await text("Request details");await text("CURRENT");await evaluate(`document.querySelector('[aria-label="Request details"]').scrollIntoView();true`);await screenshot("D11-L12-mobile-history");
      assert.equal(await evaluate(`fetch(${JSON.stringify(config.backend+"/api/schedules/me")},{credentials:'include'}).then(r=>r.json()).then(v=>JSON.stringify(v.assignments))`),beforeSchedule);
    });
    assert.deepEqual(errors,[]);
  }finally{
    if(faultOwned)await rm(config.faultFile);
    if(process.env.D11_SCREENSHOT_DIR){await mkdir(resolve(process.env.D11_SCREENSHOT_DIR),{recursive:true});await writeFile(join(resolve(process.env.D11_SCREENSHOT_DIR),"browser-results.json"),JSON.stringify(sanitizeTree({scope:"Actual Edge -> FastAPI HTTP -> owned SQLite; real faculty sessions/Origin/CSRF, fictional guarded schedules/term/catalog/GEC source. No GA execution, PostgreSQL or genuine institutional authority",browser:version?.product,node:process.version,scenarios,captures}),null,2),{flag:"wx"});}
    for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error("Live browser closing"));}socket?.close();
    if(browser&&browser.exitCode===null)spawnSync("taskkill",["/PID",String(browser.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await vite?.close();
    const target=resolve(profile),parent=resolve(tmpdir());assert.ok(target.startsWith(parent+sep)&&basename(target).startsWith("d11-live-browser-"));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200});
  }
});
