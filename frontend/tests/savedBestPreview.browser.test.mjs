// Real React/Edge; fictional intercepted HTTP. No FastAPI, GA or database execution.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {record,review} from './adjustments.fixtures.mjs';
import {binding,proposal} from './mySchedule.fixtures.mjs';
const id='70000000-0000-4000-8000-000000000001',other='70000000-0000-4000-8000-000000000002';
const decision={id,status:'APPROVED_PENDING_APPLICATION',action:'APPROVE',actor_id:id,department_id:id,explanation:'Fictional independent approval',decided_at:'2026-10-24T16:00:00+08:00',request_version:2,schedule_revision:record.content.input.revision,constraint_digest:review.constraint_digest,validation:review.validation,provenance:{mandate_reference:'fictional-chair',policy_digest:'a'.repeat(64),scope_reference:'fictional',D11_history_head:'b'.repeat(64),constraint_heads:[],trust_status:'FRESH_D8_D9_D10',schedule_changed:false},payload_digest:'c'.repeat(64),schedule_changed:false};
const approved={...record,status:'APPROVED_PENDING_APPLICATION',version:2,approval:'APPROVED_PENDING_APPLICATION',base_status:'SUBMITTED',decision};
const applied={id:other,status:'APPLIED',applied_at:'2026-10-24T16:01:00+08:00',previous_version_id:id,new_version_id:other,previous_revision:record.content.input.revision,new_revision:'d'.repeat(64),sequence:2,constraint_digest:review.constraint_digest,payload_digest:'e'.repeat(64),schedule_changed:true};
const preview={request:approved,application:null,can_apply:true,status:'PENDING_APPLICATION',before:review.original,after:review.proposal,validation:{outcome:'VALID',findings:[],policy_reference:'fictional-full-policy',capacity_applicability:'required',capacity_reference:'fictional-capacity',fitness_recalculated:false},current:{id:null,sequence:1,revision:record.content.input.revision},command:{decision_id:id,decision_digest:decision.payload_digest,expected_revision:record.content.input.revision,expected_sequence:1,constraint_digest:review.constraint_digest}};
const published={...proposal,schema_version:2,source:{kind:'published_schedule',label:'Published schedule with authorized post-GA changes',version_id:other,sequence:2,revision:applied.new_revision,academic_year:'2026-2027',term:'Fictional first term',post_ga_changes:true,constraint_status:'NOT_RECHECKED_READ_ONLY'}};

const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(action,label){const end=Date.now()+15000;while(Date.now()<end){try{if(await action())return;}catch{}await pause(40);}throw new Error(label);}
test('U5PA independent application preview/history state', {timeout:120000},async t=>{
 let vite,browser,socket,seq=0,origin,mode={},releaseHistory=true,releasePreview=true;
 const pending=new Map(),handlers=new Map(),scenarios=[],errors=[],requests=[];
 const profile=await mkdtemp(join(tmpdir(),'u5pa-browser-'));
 const evidence=process.env.U5PA_EVIDENCE_DIR;
 const second=structuredClone(preview);second.request.id='70000000-0000-4000-8000-000000000003';second.request.history=second.request.history.map(e=>({...e,request_id:second.request.id}));
 const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout: '+method));},15000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.text);return r.result.value;};
 const text=s=>until(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(s)})`),'Missing text '+s);
 const click=async s=>{await until(()=>evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent===${JSON.stringify(s)}&&!b.disabled)`),'Enabled button '+s);return evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent===${JSON.stringify(s)}&&!b.disabled).click();true`);};
 const navigate=async()=>{const token=crypto.randomUUID();await command('Page.addScriptToEvaluateOnNewDocument',{source:'window.__u5paDocument='+JSON.stringify(token)});await command('Page.navigate',{url:origin+'/schedule-applications'});await until(()=>evaluate('window.__u5paDocument==='+JSON.stringify(token)),'Fresh document');await text('Approved requests');};
 const open=async which=>{const request=which===1?preview:second;await until(()=>evaluate(`[...document.querySelectorAll('main button')].some(b=>b.textContent.includes(${JSON.stringify(which===1?'FIC-ONE':'FIC-TWO')})&&!b.disabled)`),'Selectable application '+which);await evaluate(`[...document.querySelectorAll('main button')].find(b=>b.textContent.includes(${JSON.stringify(which===1?'FIC-ONE':'FIC-TWO')})).click();true`);await text(request.request.id);};
 const count=()=>requests.filter(r=>r.path.endsWith('/preview')).length;
 const check=async(name,action)=>{let failed;await t.test(name,async()=>{try{await action();scenarios.push({name,status:'PASS'});}catch(e){scenarios.push({name,status:'FAIL',message:e.message});failed=e;throw e;}});if(failed)throw failed;};
 const capture=async name=>{if(!evidence)return;await evaluate('document.fonts.ready');const r=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await writeFile(join(evidence,name+'.png'),Buffer.from(r.data,'base64'),{flag:'wx'});};
 try{
  vite=await createServer({envDir:false,server:{host:'localhost',port:0,strictPort:true},logLevel:'error'});await vite.listen();origin=`http://localhost:${vite.httpServer.address().port}`;
  browser=spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
  let port;await until(async()=>{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];return /^\d+$/.test(port);},'Edge startup');
  const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{socket.addEventListener('open',r);socket.addEventListener('error',j);});
  socket.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);if(p){clearTimeout(p.timer);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);}}else handlers.get(m.method)?.(m.params);});
  await command('Runtime.enable');await command('Page.enable');
  handlers.set('Runtime.exceptionThrown',()=>errors.push('Unexpected runtime exception'));
  handlers.set('Fetch.requestPaused',async({requestId,request})=>{
   const current={...mode},path=new URL(request.url).pathname;requests.push({path,method:request.method});let status=200,body;
   if(path==='/api/auth/me'){if(current.anonymous){status=401;body={detail:'Authentication required'};}else body={user:{id:'fictional-u5pa',username:'operator@example.invalid',role:'admin',is_active:true,faculty_id:null,faculty:null},csrf_token:'fictional-not-a-credential',expires_at:'2099-01-01T00:00:00Z'};}
   else if(path==='/api/schedule-applications/access'){status=current.unauthorized?403:200;body=current.unauthorized?{detail:'Fictional authority denied'}:{capability:'schedule_application',departments:[{id:current.two?other:id,label:current.two?'Fictional Two':'Fictional One'}]};}
   else if(path==='/api/schedule-applications'){const list=current.two?[second]:[preview,second];body={items:list.map((p,i)=>({id:p.request.id,department_id:p===preview?id:other,faculty_id:'b1000000-0000-4000-8000-000000000001',subject:p===preview?'FIC-ONE':'FIC-TWO',section:'FIC-A',status:'PENDING_APPLICATION',decision_id:id}))};}
   else if(path.endsWith('/versions')){if(current.holdHistory)await until(()=>releaseHistory,'Release old history');status=current.historyError?503:200;body=current.historyError?{detail:'Fictional history unavailable'}:{versions:[],current_version_id:null,source_revision:record.content.input.revision,read_only:true};}
   else if(path.endsWith('/preview')){if(current.holdPreview)await until(()=>releasePreview,'Release old preview');const selected=path.includes(second.request.id)?second:preview;status=current.previewError?403:200;body=current.previewError?{detail:'Fictional preview denied'}:current.invalid?{...selected,status:'APPLICATION_BLOCKED',can_apply:false,command:null,validation:{...selected.validation,outcome:'BLOCKED'}}:selected;}
   else{status=404;body={detail:'No fictional handler'};}
   try{await command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:origin},{name:'Access-Control-Allow-Credentials',value:'true'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});}catch(error){if(!/Invalid InterceptionId/i.test(error.message))errors.push('Unexpected fulfillment failure: '+error.message);} // Cancelled document interceptions are retained as test cancellation, not backend success.
  });
  await command('Fetch.enable',{patterns:[{urlPattern:`${process.env.VITE_API_URL??'http://localhost:8000'}/*`,requestStage:'Request'}]});
  await check('U5PA-B01 history failure preserves valid action',async()=>{mode={historyError:true};await navigate();await text('Published history unavailable');await open(1);await text('Apply adjustment');await capture('U5PA-B01-preview-with-history-error');});
  await check('U5PA-B02 history retry issues no preview request',async()=>{const before=count();mode={};await click('Retry loading');await text('Published version history');assert.equal(count(),before);await text(preview.request.id);});
  await check('U5PA-B03 switching schedules clears confirmation',async()=>{await click('Apply adjustment');await text('Commit this approved change');await open(2);assert.equal(await evaluate(`Boolean(document.querySelector('[role=alertdialog]'))`),false);assert.equal(await evaluate(`document.querySelector('[aria-label="Application review"]').textContent.includes(${JSON.stringify(preview.request.id)})`),false);});
  await check('U5PA-B04 invalid preview has no apply action',async()=>{mode={invalid:true};await open(1);await text('Application: APPLICATION_BLOCKED');assert.equal(await evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Apply adjustment')`),false);});
  await check('U5PA-B05 denied preview clears actions',async()=>{mode={previewError:true};await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('FIC-ONE')).click();true`);await text('Schedule application blocked');assert.equal(await evaluate(`Boolean(document.querySelector('[aria-label="Application review"]'))`),false);});
  await check('U5PA-B06 changed authorized scope cannot retain old preview/history',async()=>{mode={};await click('Refresh applications');await open(1);mode={holdHistory:true};releaseHistory=false;await click('Refresh published history');await text('Loading published history');mode={two:true};await click('Refresh applications');await text('FIC-TWO');releaseHistory=true;await open(2);await pause(100);assert.equal(await evaluate(`document.querySelector('[aria-label="Application review"]').textContent.includes(${JSON.stringify(preview.request.id)})`),false);});
  await check('U5PA-B07 old preview completion after unmount cannot replace new selection',async()=>{mode={holdPreview:true};releasePreview=false;await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('FIC-TWO')).click();true`);await pause(100);mode={};await navigate();await open(1);releasePreview=true;await pause(150);await text(preview.request.id);assert.equal(await evaluate(`document.querySelector('[aria-label="Application review"]').textContent.includes(${JSON.stringify(second.request.id)})`),false);});
  await check('U5PA-B08 refreshed page requires a fresh selection',async()=>{await navigate();assert.equal(await evaluate(`Boolean(document.querySelector('[aria-label="Application review"]'))`),false);await open(1);await capture('U5PA-B08-fresh-preview');});
  await check('U5PA-B09 absent application authority has no controls',async()=>{mode={unauthorized:true};await command('Page.navigate',{url:origin+'/schedule-applications'});await text('Schedule application blocked');assert.equal(await evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Apply adjustment')`),false);});
  await check('U5PA-B10 anonymous user returns to sign-in',async()=>{mode={anonymous:true};await command('Page.navigate',{url:origin+'/schedule-applications'});await until(()=>evaluate(`Boolean(document.querySelector('input[type=password]'))`),'Sign-in form');assert.equal(await evaluate(`Boolean(document.querySelector('[aria-label="Application review"]'))`),false);});
  assert.deepEqual(errors,[]);
 }finally{
  releaseHistory=true;releasePreview=true;
  if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({scope:'Actual Edge/React with fictional intercepted HTTP only; no FastAPI, PostgreSQL, institutional authority or GA execution',scenarios,requests,runtime_errors:errors},null,2),{flag:'wx'});
  for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Owned test cleanup'));}pending.clear();socket?.close();browser?.kill();await vite?.close();
 }
});
