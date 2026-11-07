import assert from 'node:assert/strict';
export async function runContinuousScenarios({check,go,text,click,capture,command,evaluate,eventually,resize,requests,mode:currentMode,runId,confirmations}){
  const choose=async mode=>{await eventually(()=>evaluate(`!!document.querySelector('input[name="optimizationMode"][value="${mode}"]')`),'Mounted mode selector');return evaluate(`document.querySelector('input[name="optimizationMode"][value="${mode}"]').click()`);};
  const monitor=()=>evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent`);
  const enabled=label=>eventually(()=>evaluate(`[...document.querySelectorAll('button')].some(b=>b.textContent.trim()===${JSON.stringify(label)}&&!b.disabled)`),`Enabled ${label}`);
  await check('U5F-B01 Fixed mode remains default without requesting continuous readiness',async()=>{
    await go({idle:true});await text('Optimization Mode');await enabled('Generate Schedule');
    assert.ok(await evaluate(`document.querySelector('input[name="optimizationMode"][value="fixed"]').checked`));assert.equal(requests.filter(r=>r.path.startsWith('/api/ga/continuous')).length,0);await capture('U5F-B01-default');
  });
  await check('U5F-B02 Continuous is visibly blocked and never starts an execution',async()=>{
    await choose('continuous');await text('Execution blockers');await text('UNVERIFIED_ONLY');assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Start Optimization')).disabled`));assert.equal(requests.filter(r=>r.method==='POST').length,0);await capture('U5F-B02-blocked');
  });
  await check('U5F-B03 Hidden fixed settings cannot submit in continuous view',async()=>{
    assert.ok(await evaluate(`document.querySelector('fieldset.min-w-0').hidden&&document.querySelector('fieldset.min-w-0').disabled`));await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Generate Schedule').click()`);assert.equal(requests.filter(r=>r.method==='POST').length,0);
  });
  await check('U5F-B04 Forged executable metadata is rejected',async()=>{
    await go({idle:true,forgedReadiness:true});await choose('continuous');await text('Continuous readiness could not be validated');assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Start Optimization')).disabled`));
  });
  await check('U5F-B05 Readiness error retries without GA execution',async()=>{
    await go({idle:true,readinessError:true});await choose('continuous');await text('Continuous readiness unavailable (503)');currentMode().readinessError=false;await click('Retry continuous readiness');await text('Execution blockers');
  });
  await check('U5F-B06 Loading has no invented continuous state',async()=>{
    await go({idle:true,readinessHold:true});await choose('continuous');await text('Checking continuous-mode prerequisites');await text('No continuous worker');currentMode().readinessHold=false;await text('Execution blockers');
  });
  await check('U5F-B07 Lifecycle vocabulary and budgets are explicitly not active',async()=>{
    await evaluate(`[...document.querySelectorAll('summary')].find(e=>e.textContent.includes('Lifecycle and required safeguards')).click()`);await text('This list is not a run history');await text('No limits are represented as enforced');await capture('U5F-B07-contract');
  });
  await check('U5F-B08 Switching mode preserves fixed parameter values',async()=>{
    await choose('fixed');await evaluate(`(()=>{const n=document.querySelector('fieldset.min-w-0 input[type="number"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(n,'12');n.dispatchEvent(new Event('input',{bubbles:true}));})()`);await choose('continuous');await text('12');await choose('fixed');assert.equal(await evaluate(`document.querySelector('fieldset.min-w-0 input[type="number"]').value`),'12');
  });
  await check('U5F-B09 Refresh resets only mode selection and never auto-starts',async()=>{
    await choose('continuous');const n=requests.filter(r=>r.method==='POST').length;await go({idle:true});await enabled('Generate Schedule');assert.ok(await evaluate(`document.querySelector('input[name="optimizationMode"][value="fixed"]').checked`));assert.equal(requests.filter(r=>r.method==='POST').length,n);
  });
  await check('U5F-B10 Existing fixed pause waits for its backend acknowledgement',async()=>{
    await go({holdPause:true});await enabled('Pause Generation');await choose('continuous');await text('Execution blockers');const n=requests.filter(r=>r.method==='POST'&&r.path.endsWith('/pause')).length;
    await click('Pause Generation');await eventually(()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/pause')).length===n+1,'Pause sent');assert.equal((await monitor()).includes('Paused'),false);await click('Pause Generation');assert.equal(requests.filter(r=>r.method==='POST'&&r.path.endsWith('/pause')).length,n+1);
    currentMode().holdPause=false;await eventually(async()=>/Pause requested/i.test(await monitor()),'Pause acknowledged');currentMode().state='PAUSED';await enabled('Resume Generation');await capture('U5F-B10-fixed-paused');
  });
  await check('U5F-B11 Existing fixed resume retains its run identity',async()=>{
    await click('Resume Generation');await eventually(async()=>/Resuming|Restoring/.test(await monitor()),'Resume acknowledged');assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`),runId);currentMode().state='RUNNING';currentMode().generation=3;await enabled('Pause Generation');
  });
  await check('U5F-B12 Stop cancellation then confirmation preserves backend truth',async()=>{
    currentMode().cancelConfirm=true;const n=requests.filter(r=>r.method==='POST'&&r.path.endsWith('/stop')).length;await click('Stop Generation');assert.equal(requests.filter(r=>r.method==='POST'&&r.path.endsWith('/stop')).length,n);
    currentMode().cancelConfirm=false;await click('Stop Generation');await eventually(()=>requests.filter(r=>r.method==='POST'&&r.path.endsWith('/stop')).length===n+1,'Confirmed stop sent');await eventually(async()=>/Stop requested/i.test(await monitor()),'Stop acknowledged');currentMode().state='STOPPED';await text('Stopped after generation');assert.equal(confirmations(),2);await capture('U5F-B12-fixed-stopped');
  });
  await check('U5F-B13 Invalid checkpoint cannot enable existing resume',async()=>{
    await go({state:'PAUSED',invalidCheckpoint:true});await text('Fictional checkpoint mismatch');assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Resume Generation').disabled`));
  });
  await check('U5F-B14 Interrupted execution does not become completed',async()=>{
    await go({state:'INTERRUPTED'});await eventually(async()=>/interrupted|unknown/i.test(await monitor()),'Interrupted status');assert.equal(await evaluate(`[...document.querySelectorAll('button')].some(b=>['Pause Generation','Resume Generation','Stop Generation'].includes(b.textContent.trim())&&!b.disabled)`),false);
  });
  await check('U5F-B15 Faculty and anonymous users cannot view privileged controls',async()=>{
    await go({role:'faculty'});await text('Access unavailable');assert.equal(await evaluate(`!!document.querySelector('[aria-label="Optimization mode"]')`),false);await go({anonymous:true});await eventually(()=>evaluate(`location.pathname==='/login'`),'Login redirect');
  });
  await check('U5F-B16 Mobile blocked mode has no document overflow',async()=>{
    await resize(390,844);await go({idle:true});await text('Optimization Mode');await choose('continuous');await text('Execution blockers');assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth'));await capture('U5F-B16-mobile');
  });
  assert.ok(requests.filter(r=>r.path.startsWith('/api/ga/continuous')).every(r=>r.method==='GET'));
}
