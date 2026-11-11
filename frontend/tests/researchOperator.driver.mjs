// Standalone FastAPI page: original CDP operations, no unused Vite server.
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
export async function until(action,label){const end=Date.now()+20000;while(Date.now()<end){try{if(await action())return;}catch{/* Retain the original bounded polling contract. */}await pause(40);}throw new Error(label);}
export async function driver(evidence){
 const profile=await mkdtemp(join(tmpdir(),'u5pe-operator-edge-'));let browser,socket,seq=0,exited=false,closing;
 const pending=new Map(),handlers=new Map(),errors=[],requests=[];
 function rejectPending(){for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Owned browser closed'));}pending.clear();}
 const command=(method,params={})=>new Promise((resolve,reject)=>{if(socket?.readyState!==WebSocket.OPEN){reject(new Error('Owned CDP unavailable'));return;}const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error('Browser evaluation failed');return r.result.value;};
 const waitExit=ms=>new Promise(resolve=>{if(!browser||exited){resolve(true);return;}const done=()=>{clearTimeout(timer);resolve(true);};const timer=setTimeout(()=>{browser.off('exit',done);resolve(exited);},ms);browser.once('exit',done);});
 function close(){
  if(closing)return closing;
  closing=(async()=>{
   if(socket?.readyState===WebSocket.OPEN){try{await command('Browser.close');}catch{/* Browser may close the transport before acknowledging shutdown. */}}
   rejectPending();socket?.close();
   if(!await waitExit(5000)){browser.kill();if(!await waitExit(5000))throw new Error('OWNED_BROWSER_EXIT_UNVERIFIED');}
   return {root_process_exit_verified:!browser||exited,unused_Vite_started:false,scope:'Owned uniquely profiled Edge root only; no unrelated process termination or claim about host-wide resources.'};
  })();return closing;
 }
 try{
  browser=spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
  browser.once('exit',()=>{exited=true;});browser.once('error',()=>{exited=true;});
  let devPort;await until(async()=>{devPort=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];return /^\d+$/.test(devPort);},'Edge startup');
  const tabs=await(await fetch(`http://127.0.0.1:${devPort}/json/list`,{signal:AbortSignal.timeout(20000)})).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
  socket.addEventListener('close',rejectPending);
  socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){clearTimeout(p.timer);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);}}else handlers.get(m.method)?.(m.params);});
  await command('Runtime.enable');await command('Page.enable');await command('Network.enable');await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  handlers.set('Runtime.exceptionThrown',()=>errors.push('Unexpected runtime exception'));
  handlers.set('Network.requestWillBeSent',({request})=>{const p=new URL(request.url);if(p.pathname.startsWith('/api/research/'))requests.push({path:p.pathname,method:request.method});});
  const text=s=>until(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(s)})`),'Missing text '+s);
  const click=async s=>{await until(()=>evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent===${JSON.stringify(s)}&&!b.disabled)`),'Enabled button '+s);return evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent===${JSON.stringify(s)}&&!b.disabled).click();true`);};
  const capture=async name=>{await evaluate('document.fonts.ready');const layout=await command('Page.getLayoutMetrics');const r=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1440,height:Math.min(6000,Math.ceil(layout.cssContentSize.height)),scale:1}});await writeFile(join(evidence,name+'.png'),Buffer.from(r.data,'base64'),{flag:'wx'});};
  return {command,evaluate,text,click,capture,handlers,requests,errors,close};
 }catch(error){await close();throw error;}
}
