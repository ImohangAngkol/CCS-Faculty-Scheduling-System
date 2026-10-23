// Actual React/Edge rendering with fictional HTTP replies. No FastAPI/GA authority.
import {test} from "node:test";
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {createServer as viteServer} from "vite";
import {spawn,spawnSync} from "node:child_process";
import {mkdtemp,readFile,writeFile,mkdir,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,resolve,relative,isAbsolute,basename,sep} from "node:path";
import {fileURLToPath} from "node:url";
import {account} from "./dashboardD1.fixtures.mjs";
import {job,result,scope,status,runId} from "./constrainedGA.fixtures.mjs";
import {sanitizeTree} from "./evidencePrivacy.mjs";

const root=fileURLToPath(new URL("../",import.meta.url));
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const now=()=>new Date(Date.now()+8*3600000).toISOString().replace("Z","+08:00");
async function eventually(action,message){const end=Date.now()+15000;while(Date.now()<end){try{if(await action())return;}catch{}await pause(50);}throw new Error(message);}

test("D10 versioned constrained UI with synthetic HTTP",{timeout:150000},async t=>{
  const profile=await mkdtemp(join(tmpdir(),"dashboard-d10-browser-"));
  let browser,vite,socket,origin,sequence=0,mode={},hold;
  const pending=new Map(),errors=[],scenarios=[],captures=[],requests=[];
  const transport={commands:[],replies:0,events:[],closed:null};
  const api=createServer(async(request,response)=>{
    response.setHeader("Access-Control-Allow-Origin",origin??"http://localhost");response.setHeader("Access-Control-Allow-Credentials","true");
    response.setHeader("Access-Control-Allow-Headers","Content-Type,X-CSRF-Token");response.setHeader("Access-Control-Allow-Methods","GET,POST,OPTIONS");
    response.setHeader("Content-Type","application/json");response.setHeader("Cache-Control","no-store");
    const reply=(code,body)=>{response.writeHead(code);response.end(JSON.stringify(body));};
    if(request.method==="OPTIONS")return reply(200,{});
    const path=new URL(request.url,"http://localhost").pathname;requests.push({method:request.method,path});
    if(path==="/api/auth/me")return mode.anonymous?reply(401,{detail:"Sign in required"}):reply(200,{user:mode.faculty?account:{...account,role:"admin",faculty_id:null,faculty:null},csrf_token:"public-d10-fictional-fixture",expires_at:"2099-01-01T00:00:00Z"});
    if(path==="/api/ga/status")return reply(200,{control_version:"3c.1",process_instance_id:"fictional-d10",active_run:null,paused_runs:[]});
    if(path==="/api/ga/latest")return reply(404,{detail:"No legacy synthetic result"});
    if(path==="/api/ga/v2/status")return reply(200,status);
    if(path==="/api/ga/v2/constraints")return mode.blocked?reply(503,{detail:{code:"INSTITUTIONAL_AUTHORITY_UNAVAILABLE",message:"No genuine provider configured."}}):reply(200,scope);
    if(path===`/api/ga/v2/runs/${runId}`){
      if(hold)await hold;
      if(mode.stale)return reply(409,{detail:{code:"CONSTRAINT_SET_CHANGED",message:"Fictional head changed; restart from a fresh set."}});
      if(mode.unavailable)return reply(503,{detail:{code:"EVIDENCE_NOT_CURRENT",message:"Fictional authority unavailable."}});
      const value=structuredClone(job);
      if(mode.active){value.status="RUNNING";value.execution_active=true;delete value.result;}
      if(mode.paused){value.status="PAUSED";value.execution_active=false;value.result.status="PAUSED";}
      if(mode.malicious)value.result.commitments[0].subject='<img src=x onerror="window.__executed=true">';
      if(mode.tampered)value.result.approved=true;
      return reply(200,value);
    }
    if(request.method==="POST"&&path.startsWith("/api/ga/v2/")){
      assert.equal(request.headers["x-csrf-token"],"public-d10-fictional-fixture");
      const chunks=[];for await(const chunk of request)chunks.push(chunk);const body=JSON.parse(Buffer.concat(chunks).toString());
      if(path==="/api/ga/v2/runs"){
        assert.equal(body.constraint_digest,scope.constraint_digest);assert.equal(body.term,scope.term);assert.equal(body.authorized,undefined);
        mode.active=true;return reply(202,{...job,status:"RUNNING",execution_active:true,result:undefined});
      }
      if(path.endsWith("/control")){
        mode.paused=body.action==="pause";mode.active=body.action==="resume";
        return reply(200,{...job,status:mode.paused?"PAUSED":mode.active?"RUNNING":"STOPPED",execution_active:mode.active,result:undefined});
      }
    }
    return reply(404,{detail:"Not a D10 synthetic endpoint"});
  });
  const command=(method,params={})=>new Promise((resolve,reject)=>{transport.commands.push(method);const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error("Browser command timeout: "+method));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
  const evaluate=async expression=>{const value=await command("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});if(value.exceptionDetails)throw new Error(value.exceptionDetails.text);return value.result.value;};
  const text=value=>eventually(()=>evaluate(`document.querySelector('main')?.textContent.includes(${JSON.stringify(value)})`),"Missing page text: "+value);
  const click=value=>evaluate(`[...document.querySelectorAll('main button')].find(e=>e.textContent===${JSON.stringify(value)}).click();true`);
  const go=async(settings={},path="/admin/generate")=>{mode=settings;await command("Page.navigate",{url:origin+path});};
  const check=(id,title,action)=>t.test(id+" "+title,async()=>{const started_at=now();try{await action();scenarios.push({id,title,started_at,finished_at:now(),result:"PASS"});}catch(error){scenarios.push({id,title,started_at,finished_at:now(),result:"FAIL",error:error.message});throw error;}});
  const screenshot=async name=>{
    if(!process.env.D10_SCREENSHOT_DIR)return;
    const destination=resolve(process.env.D10_SCREENSHOT_DIR),allowed=resolve(root,"../docs/screenshots/dashboard-d10"),child=relative(allowed,destination);
    assert.ok(child&&!child.startsWith("..")&&!isAbsolute(child));await mkdir(destination,{recursive:true});
    await command("Page.bringToFront");await evaluate("document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))");
    const {data}=await command("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});await writeFile(join(destination,name+".png"),Buffer.from(data,"base64"),{flag:"wx"});
    captures.push({name:name+".png",captured_at:now(),url:await evaluate("location.origin+location.pathname"),query_omitted:true,viewport:await evaluate("({width:innerWidth,height:innerHeight})")});
  };
  let version;
  try{
    await new Promise(resolve=>api.listen(0,"127.0.0.1",resolve));
    vite=await viteServer({root,envDir:false,configFile:join(root,"vite.config.ts"),server:{host:"localhost",port:0,strictPort:true},logLevel:"error",define:{"import.meta.env.VITE_API_URL":JSON.stringify(`http://127.0.0.1:${api.address().port}`)}});await vite.listen();origin=vite.resolvedUrls.local[0].replace(/\/$/,"");
    browser=spawn("C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--remote-debugging-port=0",`--user-data-dir=${profile}`,"about:blank"],{windowsHide:true,stdio:"ignore"});
    let launchError;browser.on("error",error=>launchError=error);let port;
    await eventually(async()=>{if(launchError)throw launchError;port=(await readFile(join(profile,"DevToolsActivePort"),"utf8")).split("\n")[0];return /^\d+$/.test(port);},"Owned Edge did not start");
    const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(targets.find(t=>t.type==="page").webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true});});
    socket.addEventListener("close",event=>{transport.closed=event.code;});
    socket.addEventListener("message",event=>{const value=JSON.parse(event.data),entry=pending.get(value.id);if(entry){transport.replies++;pending.delete(value.id);clearTimeout(entry.timer);value.error?entry.reject(new Error(value.error.message)):entry.resolve(value.result);}else if(value.method&&transport.events.length<10)transport.events.push(value.method);if(value.method==="Runtime.exceptionThrown")errors.push(value.params.exceptionDetails.text);});
    await command("Runtime.enable");await command("Page.enable");version=await command("Browser.getVersion");await command("Emulation.setDeviceMetricsOverride",{width:1366,height:1000,deviceScaleFactor:1,mobile:false});
    await check("D10-B01","production block and explicit term fields",async()=>{await go({blocked:true});await text("Production institutional authority remains BLOCKED");assert.equal(await evaluate(`document.querySelector('[aria-label="V2 academic year"]').value`),"");assert.equal(await evaluate(`[...document.querySelectorAll('button')].some(e=>e.textContent==='Start constrained V2')`),false);await screenshot("D10-B01-production-blocked");});
    await check("D10-B02","review current set and start explicit V2",async()=>{await go();await text("Confirmed GEC constraints");await evaluate(`for(const [label,value] of [['V2 academic year','2026-2027'],['V2 term','Fictional first term']]){const e=document.querySelector('[aria-label="'+label+'"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,value);e.dispatchEvent(new Event('input',{bubbles:true}));}true`);await click("Check confirmed constraints");await text("1 fixed weekly commitments");await click("Start constrained V2");await text("Pause V2");});
    await check("D10-B03","pause and resume controls stay versioned",async()=>{await click("Pause V2");await text("Resume V2");await click("Resume V2");await text("Pause V2");assert.ok(requests.filter(r=>r.method==="POST").every(r=>r.path.startsWith("/api/ga/v2/")));});
    await check("D10-B04","timetable and source-row provenance",async()=>{await go({},`/admin/schedules?v2run=${runId}`);await text("V2 constrained schedule");await text("SYN101");await text("canonical_manual_content");await text("Fictional GEC");await text("not Chair-approved or official");await screenshot("D10-B04-validated-proposal");});
    await check("D10-B05","fitness and rejected candidates are visible",async()=>{await go({},`/admin/analysis?v2run=${runId}`);await text("Original fitness evaluation: 12");await text("crossover:EXTERNAL_FACULTY_CONFLICT");await text("Generation 2");await screenshot("D10-B05-fitness-provenance");});
    await check("D10-B06","stale head hides rows and retry recovers",async()=>{await go({stale:true},`/admin/schedules?v2run=${runId}`);await text("CONSTRAINT_SET_CHANGED");assert.equal(await evaluate(`document.querySelector('main').textContent.includes('SYN101')`),false);mode.stale=false;await click("Retry V2 result");await text("SYN101");});
    await check("D10-B07","authority unavailable hides prior result",async()=>{await go({unavailable:true},`/admin/schedules?v2run=${runId}`);await text("EVIDENCE_NOT_CURRENT");assert.equal(await evaluate(`document.querySelector('main').textContent.includes('SYN101')`),false);});
    await check("D10-B08","tampered approval reply is rejected",async()=>{await go({tampered:true},`/admin/schedules?v2run=${runId}`);await text("incomplete or incompatible");assert.equal(await evaluate(`document.querySelector('main').textContent.includes('SYN101')`),false);});
    await check("D10-B09","imported HTML remains escaped text",async()=>{await go({malicious:true},`/admin/schedules?v2run=${runId}`);await text("<img src=x");assert.equal(await evaluate("Boolean(window.__executed)"),false);assert.equal(await evaluate("document.querySelectorAll('main img,main script').length"),0);});
    await check("D10-B10","faculty and anonymous routes cannot fetch V2 data",async()=>{const before=requests.filter(r=>r.path.startsWith("/api/ga/v2/")).length;await go({faculty:true},`/admin/schedules?v2run=${runId}`);await eventually(()=>evaluate("document.body.textContent.includes('Access unavailable')"),"Role denial missing");await go({anonymous:true},`/admin/schedules?v2run=${runId}`);await eventually(()=>evaluate("location.pathname==='/login'"),"Anonymous redirect missing");assert.equal(requests.filter(r=>r.path.startsWith("/api/ga/v2/")).length,before);});
    await check("D10-B11","loading waits for a validated result",async()=>{let release;hold=new Promise(resolve=>release=resolve);await go({},`/admin/schedules?v2run=${runId}`);await text("Loading validated V2 result");hold=null;release();await text("SYN101");});
    await check("D10-B12","mobile remains contained",async()=>{await command("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:false});await go({},`/admin/analysis?v2run=${runId}`);await text("Original fitness evaluation");assert.ok(await evaluate("document.documentElement.scrollWidth<=innerWidth"));await evaluate("document.querySelector('main').scrollIntoView();true");await screenshot("D10-B12-mobile-analysis");});
    assert.deepEqual(errors,[]);
  }finally{
    if(process.env.D10_SCREENSHOT_DIR){await mkdir(resolve(process.env.D10_SCREENSHOT_DIR),{recursive:true});await writeFile(join(resolve(process.env.D10_SCREENSHOT_DIR),"browser-results.json"),JSON.stringify(sanitizeTree({scope:"Actual Edge/React with synthetic HTTP only; no live FastAPI authorization, real GA execution or genuine institutional authority",browser:version?.product,node:process.version,transport,scenarios,captures}),null,2),{flag:"wx"});}
    for(const entry of pending.values()){clearTimeout(entry.timer);entry.reject(new Error("Browser test closing"));}socket?.close();
    if(browser){if(browser.exitCode===null)spawnSync("taskkill",["/PID",String(browser.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});await pause(200);}await vite?.close();api.closeAllConnections();await new Promise(resolve=>api.close(resolve));
    const target=resolve(profile),parent=resolve(tmpdir());assert.ok(target.startsWith(parent+sep)&&basename(target).startsWith("dashboard-d10-browser-"));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:200});
  }
});
