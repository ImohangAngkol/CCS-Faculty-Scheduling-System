// U2: actual Edge + React DOM, CDP-intercepted fictional preferences; memory-only saves.
// No FastAPI, GA execution, PostgreSQL, real credentials or institutional authority.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, sep} from 'node:path';

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(action, label, timeout = 15000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {try {const result = await action(); if (result) return result;} catch {} await pause(50);}
  throw new Error(label);
}
import {faculty as fixtureFaculty, subjects, preference} from './preferenceFixtures.mjs';
const faculty={...fixtureFaculty[0],faculty_id:'fictional-it-1',faculty_code:1,display_code:'Faculty 1',name:'Fictional IT Lecturer'};

test('U2 navigation and preference controls with fictional intercepted responses', {timeout:180000}, async t => {
  const profile = await mkdtemp(join(tmpdir(),'dashboard-u2-'));
  let vite, browser, socket, sequence=0, mode={}, browserVersion;
  let persisted={faculty_code:1,...structuredClone(preference)};
  const writes=[];
  const pending=new Map(), handlers=new Map(), scenarios=[], captures=[], requests=[], errors=[];
  const evidence=process.env.U2_EVIDENCE_DIR;
  function command(method,params={}) {
    return new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);reject(new Error(`CDP timeout: ${method}`));},method==='Page.captureScreenshot'?30000:10000);
      pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});socket.send(JSON.stringify({id,method,params}));});
  }
  async function evaluate(expression) {
    const response=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    if(response.exceptionDetails)throw new Error(response.exceptionDetails.text);
    return response.result.value;
  }
  async function capture(name) {
    if(!evidence)return;
    await command('Page.bringToFront');
    if(name.includes('subjects'))await evaluate(`document.getElementById('preference-section-1').scrollIntoView({block:'start'})`);
    if(name.includes('segments'))await evaluate(`document.getElementById('preference-section-3').scrollIntoView({block:'center'})`);
    await evaluate('document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))');
    const image=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(join(evidence,name+'.png'),Buffer.from(image.data,'base64'),{flag:'wx'});
    captures.push({file:name+'.png',observed_at:new Date().toISOString(),viewport:await evaluate(`({width:innerWidth,height:innerHeight})`),scope:'Fictional API responses intercepted in Edge. Actual React DOM; no live FastAPI acceptance.'});
  }
  async function check(name, action){
    let failure;
    await t.test(name,async()=>{try {await action();scenarios.push({name,status:'PASS'});} catch(error){failure=error;scenarios.push({name,status:'FAIL',message:error.message});throw error;}});
    if(failure)throw new Error(`Browser scenario stopped: ${name}`);
  }
  try {
    vite=await createServer({server:{host:'localhost',port:0,strictPort:true},logLevel:'error'});await vite.listen();
    const origin=`http://localhost:${vite.httpServer.address().port}`;
    browser=spawn(process.env.PREFERENCE_TEST_BROWSER??'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
    const port=await eventually(async()=>(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0],'Edge startup');
    const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    socket=new WebSocket(targets.find(target=>target.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve);socket.addEventListener('error',reject);});
    socket.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.id){const entry=pending.get(message.id);pending.delete(message.id);if(message.error)entry?.reject(new Error(message.error.message));else entry?.resolve(message.result);}else handlers.get(message.method)?.(message.params);});
    browserVersion=await command('Browser.getVersion');
    await command('Runtime.enable');await command('Page.enable');
    handlers.set('Runtime.exceptionThrown',()=>errors.push('Unexpected browser runtime exception'));
    handlers.set('Fetch.requestPaused',async({requestId,request})=>{
      const url=new URL(request.url),path=url.pathname;requests.push({path,method:request.method});
      let status=200,body={};
      if(request.method==='OPTIONS')body={};
      else if(path==='/api/auth/me')body={user:{id:'fictional-user',username:'lecturer@fictional.invalid',role:mode.role??'admin',is_active:true,faculty_id:faculty.faculty_id,faculty},csrf_token:'fictional-test-only',expires_at:'2099-01-01T00:00:00Z'};
      else if(path==='/api/ga/status')body={control_version:'3c.1',pause_resume_version:'3d.1',process_instance_id:'fictional-process',active_run:null,paused_runs:[]};
      else if(path==='/api/ga/latest'){status=404;body={detail:'No fictional result'};}
      else if(path==='/api/faculty/'||path==='/api/faculty')body={data:[faculty]};
      else if(path.endsWith('/eligible-subjects')){
        const expanded=url.searchParams.get('eligible_only')==='false';
        body={faculty,eligible_only:!expanded,data:expanded?subjects:subjects.filter(subject=>subject.eligibility.explicitly_eligible)};
      }else if(path==='/preferences/1'){
        if(request.method==='PUT'){const data=JSON.parse(request.postData);writes.push(structuredClone(data));persisted={faculty_code:1,...data};}
        body=persisted;
      }else{status=404;body={detail:'No fictional handler'};}
      await command('Fetch.fulfillRequest',{requestId,responseCode:status,responseHeaders:[
        {name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:origin},
        {name:'Access-Control-Allow-Credentials',value:'true'},{name:'Access-Control-Allow-Headers',value:'content-type,x-csrf-token'},
        {name:'Access-Control-Allow-Methods',value:'GET,PUT,OPTIONS'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});
    });
    await command('Fetch.enable',{patterns:[{urlPattern:`${process.env.VITE_API_URL ?? 'http://localhost:8000'}/*`,requestStage:'Request'}]});
    const resize=async(width,height)=>command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
    await resize(1280,960);
    async function go(path,settings={}){mode=settings;await command('Page.navigate',{url:origin+path});}
    const text=label=>eventually(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(label)})`),`Missing text: ${label}`);
    const click=label=>evaluate(`[...document.querySelectorAll('button')].find(button=>button.getAttribute('aria-label')===${JSON.stringify(label)}||button.textContent.trim()===${JSON.stringify(label)}).click()`);
    async function key(key,code,keyCode){await command('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:keyCode});await command('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:keyCode});}
    async function set(selector,value){await evaluate(`var el=document.querySelector(${JSON.stringify(selector)});Object.getOwnPropertyDescriptor(el.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype,'value').set.call(el,${JSON.stringify(value)});el.dispatchEvent(new Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}))`);}
    const ready=()=>eventually(()=>evaluate(`!!document.querySelector('.preference-save-bar')`),'Preference editor ready');
    const state=value=>eventually(()=>evaluate(`document.querySelector('.preference-save-bar [role=status]').textContent===${JSON.stringify(value)}`),`Save state: ${value}`);
    const styleValue=()=>evaluate(`document.querySelector('input[name="schedule-style"]:checked').value`);
    const labValue=()=>evaluate(`document.querySelector('input[name="lecture-lab"]:checked').value`);
    await check('U2-B01 desktop sidebar stays visible while content uses one document scrollbar',async()=>{
      await go('/admin/preferences');await ready();
      const bounds=await evaluate(`var aside=document.querySelector('aside').getBoundingClientRect(), main=document.querySelector('main').getBoundingClientRect(), header=document.querySelector('.dashboard-content > header').getBoundingClientRect();({asideTop:aside.top,asideRight:aside.right,mainLeft:main.left,headerLeft:header.left,width:aside.width,scrollable:document.documentElement.scrollHeight>innerHeight})`);
      assert.equal(bounds.asideTop,0);assert.equal(bounds.width,256);assert.ok(bounds.mainLeft>=bounds.asideRight&&bounds.headerLeft>=bounds.asideRight&&bounds.scrollable,JSON.stringify(bounds));
      await evaluate(`window.scrollTo(0,2000)`);
      const scrolling=await evaluate(`({contentScroll:window.scrollY,sidebarTop:document.querySelector('aside').getBoundingClientRect().top,documentHeight:document.documentElement.scrollHeight,viewportHeight:innerHeight,mainOverflow:getComputedStyle(document.querySelector('main')).overflowY})`);
      assert.ok(scrolling.contentScroll>500&&Math.abs(scrolling.sidebarTop)<1&&scrolling.documentHeight>scrolling.viewportHeight&&scrolling.mainOverflow==='visible',JSON.stringify(scrolling));
    });
    await check('U2-B02 short desktop navigation scrolls independently and preserves footer branding',async()=>{
      await resize(1280,500);
      const pageScroll=await evaluate(`window.scrollY`);
      await evaluate(`document.querySelector('aside').scrollTop=document.querySelector('aside').scrollHeight`);
      assert.ok(await evaluate(`var aside=document.querySelector('aside'), footer=document.querySelector('.dashboard-sidebar-footer').getBoundingClientRect();aside.scrollTop>0 && footer.bottom<=innerHeight+1 && footer.top>=0`));
      assert.equal(await evaluate(`window.scrollY`),pageScroll);
      await capture('U2-B02-short-sidebar');
      await resize(1280,960);await evaluate(`document.querySelector('aside').scrollTop=0;window.scrollTo(0,0)`);
    });
    await check('U2-B03 navigation preserves active route and visible keyboard focus',async()=>{
      await key('Tab','Tab',9);
      await evaluate(`document.querySelector('nav[aria-label="Admin navigation"] a[aria-current="page"]').focus()`);
      assert.ok(await evaluate(`var el=document.activeElement;el.classList.contains('dashboard-navigation-active') && getComputedStyle(el).outlineStyle!=='none'`));
    });
    await check('U2-B04 mobile disclosure opens by keyboard, closes with Escape, and closes on navigation',async()=>{
      await resize(390,844);
      assert.ok(await evaluate(`var toggle=document.querySelector('.dashboard-navigation-toggle'),nav=document.querySelector('.dashboard-navigation');toggle.getAttribute('aria-expanded')==='false' && nav.getClientRects().length===0`));
      await evaluate(`document.querySelector('.dashboard-navigation-toggle').focus()`);await key(' ','Space',32);
      assert.ok(await evaluate(`document.querySelector('.dashboard-navigation-toggle').getAttribute('aria-expanded')==='true' && document.querySelector('.dashboard-navigation').getClientRects().length>0`));
      await evaluate(`document.querySelector('.dashboard-navigation a').focus()`);await key('Escape','Escape',27);
      assert.ok(await evaluate(`document.activeElement===document.querySelector('.dashboard-navigation-toggle') && document.activeElement.getAttribute('aria-expanded')==='false'`));
      await key(' ','Space',32);await evaluate(`document.querySelector('.dashboard-navigation a[href="/admin/preferences"]').click()`);
      assert.equal(await evaluate(`document.querySelector('.dashboard-navigation-toggle').getAttribute('aria-expanded')`),'false');
      assert.ok(await evaluate(`document.documentElement.scrollWidth<=innerWidth && Math.abs(document.querySelector('aside').getBoundingClientRect().top)<1`));
    });
    await check('U2-B05 faculty uses the same independent layout and saved preference controls',async()=>{
      await resize(1280,960);await go('/faculty/preferences',{role:'faculty'});await ready();await state('No changes');
      assert.ok(await evaluate(`document.querySelector('aside').textContent.includes('Faculty Portal') && document.querySelector('nav[aria-label="Faculty navigation"] a[aria-current="page"]').textContent==='My Preferences'`));
      await capture('U2-B05-subjects');
    });
    await check('U2-B06 subject switch uses Space and updates only the draft without autosaving',async()=>{
      await evaluate(`document.querySelector('input[role="switch"][aria-label="Consider my subject preferences"]').focus()`);
      await key(' ','Space',32);await state('Unsaved changes');
      assert.equal(await evaluate(`document.querySelector('input[aria-label="Consider my subject preferences"]').checked`),false);assert.equal(writes.length,0);
      assert.ok(await evaluate(`getComputedStyle(document.querySelector('.preference-switch-track')).outlineStyle!=='none'`));
      await click('Discard');await state('No changes');
    });
    await check('U2-B07 expanded browsing exposes ineligible subjects without granting Add access',async()=>{
      await evaluate(`document.querySelector('input[aria-label="Show all offered subjects (eligibility still applies)"]').click()`);await text('Not eligible for this faculty member');
      assert.ok(await evaluate(`document.querySelector('button[aria-label="Add ITE184 to preferred subjects"]').disabled`));
      assert.ok(await evaluate(`[...document.querySelectorAll('.preference-eligibility')].every(el=>el.tagName==='SPAN'&&!el.hasAttribute('role'))`));
      await state('No changes');assert.equal(writes.length,0);
    });
    await check('U2-B08 categories stay single-choice and code/title search still filters',async()=>{
      await evaluate(`document.querySelector('.preference-category[aria-pressed="true"]').focus()`);
      await click('ITD');assert.equal(await evaluate(`document.querySelectorAll('.preference-category[aria-pressed="true"]').length`),1);
      await set('input[type="search"]','Data');
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('.preference-subject-browser > li strong')].map(el=>el.textContent)`),['ITD105']);
      await set('input[type="search"]','');await click('ALL');await state('No changes');
    });
    await check('U2-B09 Add/rank stay functional and ineligible clicks cannot enter the ranked list',async()=>{
      await click('Add CCC100 to preferred subjects');await click('Add ITD105 to preferred subjects');
      await evaluate(`document.querySelector('button[aria-label="Add ITE184 to preferred subjects"]').click()`);
      await set('#rank-ITD105','1');
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('[id^="rank-"]')].map(el=>el.id)`),['rank-ITD105','rank-CCC100']);
      await state('Unsaved changes');assert.equal(writes.length,0);
    });
    await check('U2-B10 schedule style retains exclusive native arrow-key behavior and enum values',async()=>{
      await evaluate(`document.getElementById('preference-section-3').scrollIntoView({block:'center'});document.querySelector('input[name="schedule-style"]:checked').focus()`);
      await key('ArrowRight','ArrowRight',39);assert.equal(await styleValue(),'Compact');
      await key('ArrowRight','ArrowRight',39);assert.equal(await styleValue(),'Scattered');
      assert.equal(await evaluate(`document.querySelectorAll('input[name="schedule-style"]:checked').length`),1);
      await eventually(()=>evaluate(`var label=document.querySelector('input[name="schedule-style"]:checked').nextElementSibling;getComputedStyle(label).backgroundColor==='rgb(17, 94, 89)' && getComputedStyle(label).outlineStyle!=='none'`),'Selected segment paint and keyboard focus');
      await key('ArrowRight','ArrowRight',39);assert.equal(await styleValue(),'No Preference');
    });
    await check('U2-B11 lecture/lab remains single-choice with original Different Day value',async()=>{
      await evaluate(`document.querySelector('input[name="lecture-lab"]:checked').focus()`);
      await key('ArrowRight','ArrowRight',39);assert.equal(await labValue(),'Same Day');
      await key('ArrowRight','ArrowRight',39);assert.equal(await labValue(),'Different Day');
      assert.equal(await evaluate(`document.querySelectorAll('input[name="lecture-lab"]:checked').length`),1);assert.equal(writes.length,0);
    });
    await check('U2-B12 Discard restores all saved selections and ranked subjects',async()=>{
      await click('Discard');await state('No changes');assert.equal(await styleValue(),'No Preference');assert.equal(await labValue(),'No Preference');
      assert.equal(await evaluate(`document.querySelectorAll('[id^="rank-"]').length`),0);
      assert.equal(await evaluate(`document.querySelector('input[aria-label="Consider my subject preferences"]').checked`),true);
    });
    await check('U2-B13 explicit Save sends original enums/flags and preserves unrelated fields',async()=>{
      await evaluate(`document.querySelector('input[name="schedule-style"][value="Compact"]').click();document.querySelector('input[name="lecture-lab"][value="Same Day"]').click();document.querySelector('input[aria-label="Consider my subject preferences"]').click()`);
      await state('Unsaved changes');assert.equal(writes.length,0);
      await click('Save Preferences');await state('Saved');assert.equal(writes.length,1);
      assert.equal(writes[0].gap_preference,'Compact');assert.equal(writes[0].use_gap_preference,true);
      assert.equal(writes[0].lecture_lab_preference,'Same Day');assert.equal(writes[0].use_lecture_lab_preference,true);
      assert.equal(writes[0].use_subject_preference,false);assert.equal(writes[0].subject_importance,preference.subject_importance);
      assert.deepEqual(writes[0].preferred_schedule_blocks,preference.preferred_schedule_blocks);
      await capture('U2-B13-segments');
    });
    await check('U2-B14 actual reload restores mock-saved controls and no automatic save occurs',async()=>{
      await command('Page.reload');await ready();await state('No changes');assert.equal(await styleValue(),'Compact');assert.equal(await labValue(),'Same Day');
      assert.equal(await evaluate(`document.querySelector('input[aria-label="Consider my subject preferences"]').checked`),false);assert.equal(writes.length,1);
    });
    await check('U2-B15 narrow preference controls wrap without page overflow and mobile navigation works',async()=>{
      await resize(390,844);await evaluate(`document.getElementById('preference-section-3').scrollIntoView({block:'center'})`);
      assert.ok(await evaluate(`[...document.querySelectorAll('.preference-segment-label')].every(el=>{var r=el.getBoundingClientRect();return r.width>0&&r.left>=0&&r.right<=innerWidth}) && document.documentElement.scrollWidth<=innerWidth`));
      await capture('U2-B15-mobile-segments');await click('Open navigation');
      assert.equal(await evaluate(`document.querySelector('.dashboard-navigation-toggle').getAttribute('aria-expanded')`),'true');await click('Close navigation');
    });
    await check('U2-B16 reduced-motion disables control transitions and the skip link focuses the page',async()=>{
      await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
      assert.ok(await evaluate(`getComputedStyle(document.querySelector('.preference-switch-thumb')).transitionDuration==='0s' && getComputedStyle(document.querySelector('.preference-segment-label')).transitionDuration==='0s'`));
      await evaluate(`document.querySelector('.dashboard-skip-link').focus()`);await key('Enter','Enter',13);
      assert.equal(await evaluate(`document.activeElement.id`),'dashboard-main');
    });
    await check('U2-B17 accessibility tree exposes native switch/radio state and hides collapsed navigation',async()=>{
      const tree=await command('Accessibility.getFullAXTree');
      const nodes=tree.nodes.filter(node=>!node.ignored);
      const subject=nodes.find(node=>node.role?.value==='switch'&&node.name?.value==='Consider my subject preferences');
      assert.ok(subject);assert.equal(subject.properties.find(property=>property.name==='checked').value.value,'false');
      const radios=nodes.filter(node=>node.role?.value==='radio');assert.equal(radios.length,6);
      assert.equal(radios.filter(node=>node.properties.find(property=>property.name==='checked')?.value.value==='true').length,2);
      assert.ok(nodes.some(node=>node.role?.value==='group'&&node.name?.value==='Schedule style'));
      assert.ok(nodes.some(node=>node.role?.value==='group'&&node.name?.value==='Lecture and laboratory days'));
      assert.equal(nodes.some(node=>node.role?.value==='link'&&node.name?.value==='My Preferences'),false);
    });
    assert.deepEqual(errors,[]);assert.ok(requests.every(row=>['GET','PUT','OPTIONS'].includes(row.method)));
    assert.ok(requests.filter(row=>row.method==='PUT').every(row=>row.path==='/preferences/1'));
  } finally {
    if(evidence)await writeFile(join(evidence,'browser-results.json'),JSON.stringify({browser:browserVersion?.product,node:process.version,scope:'Actual headless Edge/React. CDP-intercepted fictional preferences, memory-only mocked save/reload; no FastAPI, GA or database operations.',scenarios,captures,requests,fictional_put_count:writes.length,runtime_errors:errors},null,2)+'\n',{flag:'wx'});
    socket?.close();for(const item of pending.values())item.reject(new Error('Browser closed'));
    if(browser&&browser.exitCode===null){browser.kill();await Promise.race([pause(3000),new Promise(resolve=>browser.once('exit',resolve))]);}
    await vite?.close();const target=resolve(profile);assert.ok(target.startsWith(resolve(tmpdir())+sep)&&target.split(sep).at(-1).startsWith('dashboard-u2-'));await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
