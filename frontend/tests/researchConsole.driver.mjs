// Owned CDP/Vite helper. No external installation or institutional service.
import {createServer} from 'vite';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
export const pause=ms=>new Promise(r=>setTimeout(r,ms));
export async function until(action,label){const end=Date.now()+20000;while(Date.now()<end){try{if(await action())return;}catch{}await pause(40);}throw new Error(label);}
export async function driver(evidence,port=0){
 const profile=await mkdtemp(join(tmpdir(),'u5pc-edge-'));let browser,socket,vite,seq=0;
 const pending=new Map(),handlers=new Map(),errors=[],requests=[];
 const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error('Browser evaluation failed');return r.result.value;};
 async function close(){for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Owned cleanup'));}pending.clear();socket?.close();browser?.kill();await vite?.close();}
 try{
  vite=await createServer({envDir:false,server:{host:'localhost',port,strictPort:true},logLevel:'error'});await vite.listen();const origin=`http://localhost:${vite.httpServer.address().port}`;
  browser=spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
  let devPort;await until(async()=>{devPort=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];return /^\d+$/.test(devPort);},'Edge startup');
  const tabs=await(await fetch(`http://127.0.0.1:${devPort}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.addEventListener('open',r);socket.addEventListener('error',j);});
  socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){clearTimeout(p.timer);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);}}else handlers.get(m.method)?.(m.params);});
  await command('Runtime.enable');await command('Page.enable');await command('Network.enable');await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  handlers.set('Runtime.exceptionThrown',()=>errors.push('Unexpected runtime exception'));
  handlers.set('Network.requestWillBeSent',({request})=>{const p=new URL(request.url);if(p.pathname.startsWith('/api/research/'))requests.push({path:p.pathname,method:request.method});});
  const text=s=>until(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(s)})`),'Missing text '+s);
  const click=async s=>{await until(()=>evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent===${JSON.stringify(s)}&&!b.disabled)`),'Enabled button '+s);return evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent===${JSON.stringify(s)}&&!b.disabled).click();true`);};
  const select=async run=>{await until(()=>evaluate(`[...document.querySelectorAll('main button')].some(b=>b.textContent.includes(${JSON.stringify(run)}))`),'Run in list');await evaluate(`[...document.querySelectorAll('main button')].find(b=>b.textContent.includes(${JSON.stringify(run)})).click();true`);};
  const navigate=async(path='/research/runs')=>{const mark=crypto.randomUUID();await command('Page.addScriptToEvaluateOnNewDocument',{source:'window.__u5pc='+JSON.stringify(mark)});await command('Page.navigate',{url:origin+path});await until(()=>evaluate('window.__u5pc==='+JSON.stringify(mark)),'Fresh document');};
  const capture=async name=>{if(!evidence)return;await evaluate('document.fonts.ready');const layout=await command('Page.getLayoutMetrics');const size=layout.cssContentSize;const r=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1440,height:Math.min(6000,Math.ceil(size.height)),scale:1}});await writeFile(join(evidence,name+'.png'),Buffer.from(r.data,'base64'),{flag:'wx'});};
  return {origin,command,evaluate,text,click,select,navigate,capture,handlers,requests,errors,close};
 }catch(e){await close();throw e;}
}
