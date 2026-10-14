// Genuine FastAPI sessions and atomic temporary preferences; invoked by pytest.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve, basename, sep} from 'node:path';
const backend=process.env.AUTH_TEST_URL, password=process.env.AUTH_TEST_PASSWORD;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function eventually(check,message,timeout=15000){const end=Date.now()+timeout;while(Date.now()<end){try{if(await check())return;}catch{}await sleep(60);}throw Error(message);}

test('Phase 4A real browser authentication and authorization', {skip:!backend,timeout:120000}, async t=>{
  assert.match(backend,/^http:\/\/localhost:\d+$/);
  const profile=await mkdtemp(join(tmpdir(),'phase4a-auth-browser-'));
  const vite=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','localhost','--port','5189','--strictPort'],{cwd:new URL('../',import.meta.url),env:{...process.env,VITE_API_URL:backend},windowsHide:true,stdio:'pipe'});
  const edge=spawn(process.env.PREFERENCE_TEST_BROWSER??'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=9230',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'pipe'});
  let socket,startupError,sequence=0;const pending=new Map();
  for(const child of [vite,edge]){child.on('error',error=>startupError=error);child.stdout?.resume();child.stderr?.resume();}
  try{
    await eventually(async()=>{if(startupError)throw startupError;return(await fetch('http://localhost:5189')).ok;},'Vite did not start');
    let targets;await eventually(async()=>{targets=await(await fetch('http://127.0.0.1:9230/json/list')).json();return targets.length;},'Browser did not start');
    socket=new WebSocket(targets.find(row=>row.type==='page').webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
    socket.addEventListener('message',event=>{const data=JSON.parse(event.data),entry=pending.get(data.id);if(entry){pending.delete(data.id);clearTimeout(entry.timer);data.error?entry.reject(Error(data.error.message)):entry.resolve(data.result);}});
    const command=(method,params={})=>new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(Error('Browser command timeout: '+method));},10000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
    const evaluate=async expression=>{const result=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description??result.exceptionDetails.text);return result.result.value;};
    await command('Runtime.enable');await command('Page.enable');
    const goto=path=>command('Page.navigate',{url:'http://localhost:5189'+path});
    const waitText=text=>eventually(()=>evaluate(`document.body.textContent.includes(${JSON.stringify(text)})`),'Missing browser text: '+text);
    const button=label=>`[...document.querySelectorAll('button')].find(el=>el.textContent.trim()===${JSON.stringify(label)})`;
    const click=label=>evaluate(`${button(label)}.click();true`);
    const login=async username=>{
      await waitText('Sign in with your administrator');
      await evaluate(`var fields=document.querySelectorAll('form input');var setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(fields[0],${JSON.stringify(username)});fields[0].dispatchEvent(new Event('input',{bubbles:true}));setter.call(fields[1],${JSON.stringify(password)});fields[1].dispatchEvent(new Event('input',{bubbles:true}));true`);
      await click('Sign in');
    };
    await t.test('anonymous route redirects and empty login is disabled',async()=>{await goto('/admin/generate');await waitText('Sign in with your administrator');assert.equal(await evaluate('location.pathname'),'/login');assert.equal(await evaluate(`${button('Sign in')}.disabled`),true);});
    await t.test('invalid login is explained and password is cleared',async()=>{
      await evaluate(`var fields=document.querySelectorAll('form input');var setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(fields[0],'admin@test.invalid');fields[0].dispatchEvent(new Event('input',{bubbles:true}));setter.call(fields[1],'incorrect-test-password');fields[1].dispatchEvent(new Event('input',{bubbles:true}));true`);
      await click('Sign in');await waitText('Invalid credentials or account unavailable.');assert.equal(await evaluate(`document.querySelector('input[type=password]').value`),'');
    });
    await t.test('administrator login and account navigation',async()=>{await login('admin@test.invalid');await waitText('Admin Dashboard');assert.ok(await evaluate(`!!document.querySelector('a[href="/admin/accounts"]')`));});
    await t.test('administrator creates a faculty account through the binding form',async()=>{
      await goto('/admin/accounts');await waitText('Account Administration');
      await eventually(()=>evaluate(`document.querySelectorAll('form select')[2]?.options.length===12`),'Imported faculty bindings did not load');
      await evaluate(`var fields=document.querySelectorAll('form input');var setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(fields[0],'created-ui@test.invalid');fields[0].dispatchEvent(new Event('input',{bubbles:true}));setter.call(fields[1],${JSON.stringify(password)});fields[1].dispatchEvent(new Event('input',{bubbles:true}));var binding=document.querySelectorAll('form select')[2];Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(binding,[...binding.options].find(row=>row.textContent.startsWith('Faculty 2 ·')).value);binding.dispatchEvent(new Event('change',{bubbles:true}));true`);
      await click('Save account');await waitText('Account saved.');assert.equal(await evaluate(`document.querySelector('input[type=password]').value`),'');
      await goto('/admin');await waitText('Admin Dashboard');
    });
    await t.test('HttpOnly session survives refresh without localStorage auth',async()=>{await command('Page.reload');await waitText('Admin Dashboard');assert.equal(await evaluate(`document.cookie.includes('ccs_session')`),false);assert.equal(await evaluate(`Object.keys(localStorage).some(key=>/token|password|auth/i.test(key))`),false);});
    await t.test('administrator GA monitoring and history remain accessible',async()=>{await goto('/admin/generate');await waitText('Generate Schedule');await goto('/admin/history');await waitText('Generation History');assert.equal(await evaluate(`location.pathname`),'/admin/history');});
    await t.test('logout invalidates session and protected reload returns login',async()=>{await click('Sign out');await waitText('Sign in with your administrator');await goto('/admin/preferences');await waitText('Sign in with your administrator');});
    await t.test('faculty login resolves own binding and hides admin navigation',async()=>{await login('faculty@test.invalid');await waitText('Faculty Dashboard');assert.equal(await evaluate(`!!document.querySelector('a[href="/admin/accounts"]')`),false);await goto('/faculty/preferences');await eventually(()=>evaluate(`!!document.querySelector('.preference-save-bar')`),'Own preferences did not load');assert.equal(await evaluate(`document.body.textContent.includes('Faculty priority')`),false);});
    await t.test('own preference save and browser reload persist',async()=>{await evaluate(`[...document.querySelectorAll('label')].find(el=>el.textContent.includes('Consider my subject preferences')).querySelector('input').click();true`);await click('Save Preferences');await waitText('Saved');await command('Page.reload');await eventually(()=>evaluate(`!!document.querySelector('.preference-save-bar')`),'Saved preferences did not reload');assert.equal(await evaluate(`[...document.querySelectorAll('label')].find(el=>el.textContent.includes('Consider my subject preferences')).querySelector('input').checked`),false);});
    await t.test('faculty cannot change identity through URL or payload',async()=>{const status=await evaluate(`(async()=>{const session=await(await fetch(${JSON.stringify(backend+'/api/auth/me')},{credentials:'include'})).json();return(await fetch(${JSON.stringify(backend+'/preferences/1')},{method:'PUT',credentials:'include',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},body:JSON.stringify({use_subject_preference:false})})).status})()`);assert.equal(status,403);await goto('/admin/preferences');await waitText('Access unavailable');assert.equal(await evaluate(`!!document.querySelector('.preference-editor')`),false);});
    await t.test('revoked session returns login and displays session error',async()=>{
      const origin='http://localhost:5189';
      const reply=await fetch(backend+'/api/auth/login',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({username:'admin@test.invalid',password})});assert.equal(reply.status,200);
      const session=await reply.json(),cookie=reply.headers.get('set-cookie').split(';')[0];
      const headers={Origin:origin,Cookie:cookie,'X-CSRF-Token':session.csrf_token,'Content-Type':'application/json'};
      const users=await(await fetch(backend+'/api/auth/users',{headers})).json(),faculty=users.find(user=>user.username==='faculty@test.invalid');
      assert.equal((await fetch(backend+'/api/auth/users/'+faculty.id,{method:'PATCH',headers,body:JSON.stringify({is_active:false})})).status,200);
      await evaluate(`(async()=>{const transport=await import('/src/services/apiSession.ts');await transport.apiFetch(${JSON.stringify(backend+'/preferences/0')});return true})()`);
      await waitText('Sign in with your administrator');await waitText('Your session expired or was revoked.');
      assert.equal(await evaluate(`location.pathname`),'/login');
    });
    await t.test('anonymous direct API write remains rejected',async()=>{assert.equal((await fetch(backend+'/preferences/0',{method:'PUT',headers:{Origin:'http://localhost:5189','Content-Type':'application/json'},body:'{}'})).status,401);});
  }finally{
    socket?.close();for(const entry of pending.values())clearTimeout(entry.timer);edge.kill();vite.kill();
    await Promise.race([sleep(3000),Promise.all([edge,vite].map(child=>new Promise(resolve=>child.exitCode!==null||child.signalCode!==null?resolve():child.once('exit',resolve))))]);
    assert.ok(resolve(profile).startsWith(resolve(tmpdir())+sep)&&basename(profile).startsWith('phase4a-auth-browser-'));await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});
  }
});
