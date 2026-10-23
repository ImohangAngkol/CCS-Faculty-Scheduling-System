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

test("D10 actual HTTP/Edge V2 with fictional institutional providers",{timeout:150000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),"d10-live-browser-"));let browser,vite,socket,origin,sequence=0,version,runId;
  const pending=new Map(),errors=[],scenarios=[],captures=[];
  const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error("Browser command timeout: "+method));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const value=await command("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});if(value.exceptionDetails)throw new Error(value.exceptionDetails.text);return value.result.value;};
  const text=value=>eventually(()=>evaluate(`document.querySelector('main')?.textContent.includes(${JSON.stringify(value)})`),"Missing live UI text: "+value);
  const click=value=>evaluate(`[...document.querySelectorAll('button')].find(e=>e.textContent===${JSON.stringify(value)}).click();true`);
  const input=(selector,value)=>evaluate(`{const e=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event('input',{bubbles:true}));}true`);
  const check=(id,title,action)=>t.test(id+" "+title,async()=>{const started_at=now();try{await action();scenarios.push({id,title,started_at,finished_at:now(),result:"PASS"});}catch(error){scenarios.push({id,title,started_at,finished_at:now(),result:"FAIL",error:error.message});throw error;}});
  const screenshot=async name=>{
    if(!process.env.D10_SCREENSHOT_DIR)return;
    const destination=resolve(process.env.D10_SCREENSHOT_DIR),allowed=resolve(root,"../docs/screenshots/dashboard-d10"),child=relative(allowed,destination);
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
    await check("D10-L01","real unauthenticated request is rejected",async()=>{
      await command("Page.navigate",{url:origin+"/login"});await eventually(()=>evaluate("Boolean(document.querySelector('input[type=password]'))"),"Login form missing");
      assert.equal(await evaluate(`fetch(${JSON.stringify(config.backend+"/api/ga/v2/status")},{credentials:'include'}).then(r=>r.status)`),401);
    });
    await check("D10-L02","real administrator login and current D9 review",async()=>{
      await input('input[autocomplete=username]',"admin@example.invalid");await input('input[type=password]',config.password);await evaluate("document.querySelector('form').requestSubmit();true");await eventually(()=>evaluate("location.pathname==='/admin'"),"Administrator login failed");
      await command("Page.navigate",{url:origin+"/admin/generate"});await text("Confirmed GEC constraints");await input('[aria-label="V2 academic year"]',"2026-2027");await input('[aria-label="V2 term"]',"Fictional first term");await click("Check confirmed constraints");await text("1 fixed weekly commitments");
    });
    await check("D10-L03","real original operators produce a constrained proposal",async()=>{
      await input('[aria-label="V2 population"]',"2");await input('[aria-label="V2 generations"]',"1");await click("Start constrained V2");await text("V2: COMPLETED");runId=await evaluate("new URLSearchParams(location.search).get('v2run')");assert.match(runId,/^[a-f0-9-]{36}$/);
    });
    await check("D10-L04","real timetable has current source provenance",async()=>{
      await command("Page.navigate",{url:origin+"/admin/schedules?v2run="+runId});await text("V2 constrained schedule");await text("SYN101");await text("canonical_manual_content");await text("not Chair-approved or official");await screenshot("D10-L04-real-api-proposal");
    });
    await check("D10-L05","real original fitness and admission history are rendered",async()=>{
      await command("Page.navigate",{url:origin+"/admin/analysis?v2run="+runId});await text("Original fitness evaluation");await text("construction:ACCEPTED");await text("Generation 1");await screenshot("D10-L05-real-api-analysis");
    });
    await check("D10-L06","real faculty session cannot retrieve the administrator V2 run",async()=>{
      await click("Sign out");await eventually(()=>evaluate("location.pathname==='/login'"),"Sign-out did not finish");await input('input[autocomplete=username]',"faculty0@example.invalid");await input('input[type=password]',config.password);await evaluate("document.querySelector('form').requestSubmit();true");await eventually(()=>evaluate("location.pathname==='/faculty'"),"Faculty login failed");
      assert.equal(await evaluate(`fetch(${JSON.stringify(config.backend+"/api/ga/v2/runs/")+"+"+JSON.stringify(runId)},{credentials:'include'}).then(r=>r.status)`),403);
    });
    assert.deepEqual(errors,[]);
  }finally{
    if(process.env.D10_SCREENSHOT_DIR){await mkdir(resolve(process.env.D10_SCREENSHOT_DIR),{recursive:true});await writeFile(join(resolve(process.env.D10_SCREENSHOT_DIR),"browser-results.json"),JSON.stringify(sanitizeTree({scope:"Actual Edge -> FastAPI HTTP -> owned SQLite, real passwords/sessions/Origin/CSRF and original GA functions; entirely fictional resources and institutional providers, no PostgreSQL or genuine institutional authority",browser:version?.product,node:process.version,scenarios,captures}),null,2),{flag:"wx"});}
    for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error("Live browser closing"));}socket?.close();
    if(browser&&browser.exitCode===null)spawnSync("taskkill",["/PID",String(browser.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await vite?.close();
    const target=resolve(profile),parent=resolve(tmpdir());assert.ok(target.startsWith(parent+sep)&&basename(target).startsWith("d10-live-browser-"));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200});
  }
});
