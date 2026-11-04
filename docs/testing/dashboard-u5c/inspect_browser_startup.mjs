// Dedicated temporary Chromium profile only. No app/API/credentials; no target URLs archived.
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {join,resolve,sep} from 'node:path';
import {tmpdir} from 'node:os';
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const profile=await mkdtemp(join(tmpdir(),'u5c-startup-probe-'));
const isolated=process.argv.includes('--disable-extensions');
const args=['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'];
if(isolated)args.unshift('--disable-extensions');
const executable=process.argv.includes('--chrome')?'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe':'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const browser=spawn(executable,args,{windowsHide:true,stdio:'ignore'});
let socket;
const observations=[];
try {
  let port;
  for(let i=0;i<150;i++){try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{}await pause(100);}
  const targets=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(targets.find(target=>target.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve);socket.addEventListener('error',reject);});
  let sequence=0;const pending=new Map();
  socket.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.id){const callback=pending.get(message.id);pending.delete(message.id);callback?.(message);}});
  async function command(method,params={}){
    const id=++sequence,start=performance.now();let timer;
    const result=await Promise.race([new Promise(resolve=>{pending.set(id,resolve);socket.send(JSON.stringify({id,method,params}));}),new Promise(resolve=>{timer=setTimeout(()=>resolve({timeout:true}),5000);})]);
    clearTimeout(timer);pending.delete(id);
    observations.push({method,elapsed_ms:Math.round(performance.now()-start),timed_out:result.timeout??false,error:result.error?.message??null});
    return result;
  }
  const version=await command('Browser.getVersion');
  await command('Page.enable');await command('Runtime.evaluate',{expression:'1+1',returnByValue:true});await command('Runtime.enable');
  console.log(JSON.stringify({scope:'Owned blank-page renderer probe only; no application or API loaded.',extensions_disabled:isolated,
    browser:version.result?.product,extension_targets:targets.filter(target=>target.type==='background_page').length,observations}));
  await command('Browser.close');
}finally{
  socket?.close();if(browser.exitCode===null)browser.kill();await pause(1500);
  const target=resolve(profile);if(!target.startsWith(resolve(tmpdir())+sep)||!target.split(sep).at(-1).startsWith('u5c-startup-probe-'))throw Error('Owned temporary profile check failed');
  await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
}
