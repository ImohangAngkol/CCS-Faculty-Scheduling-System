// Inserted only into the owned D16 harness; not application functionality.
await check('U5O-A02','survey all page routes and sanitized HTTP metadata without submitting forms',async()=>{
  const rows=[],network=[],methods=new Map();
  const listener=event=>{
    const message=JSON.parse(event.data),p=message.params;
    if(message.method==='Network.requestWillBeSent'){
      const url=new URL(p.request.url);
      if(url.origin===config.backend)methods.set(p.requestId,p.request.method);
    }
    if(message.method==='Network.responseReceived'&&methods.has(p.requestId)&&network.length<2000){
      network.push({method:methods.get(p.requestId),path:new URL(p.response.url).pathname,status:p.response.status});
      methods.delete(p.requestId);
    }
  };
  await command('Network.enable');socket.addEventListener('message',listener);
  async function visit(path,role){
    const begin=network.length;
    await command('Page.navigate',{url:origin+path});
    await eventually(()=>evaluate('Boolean(document.querySelector("h1,main form,form"))'),'Route did not render a heading/form: '+path);
    await pause(200);
    const dom=await evaluate(`({path:location.pathname,heading:document.querySelector('h1')?.textContent?.trim()??null,
      controls:[...document.querySelectorAll('button,input,select,textarea,form,a,table,[role=dialog],[role=alertdialog],.recharts-wrapper')].map(e=>({
        tag:e.tagName.toLowerCase(),role:e.getAttribute('role'),type:e.getAttribute('type'),disabled:Boolean(e.disabled),
        label:(e.getAttribute('aria-label')??e.getAttribute('title')??(['BUTTON','A'].includes(e.tagName)?e.textContent:e.getAttribute('name'))??'').trim().replace(/\\s+/g,' ').slice(0,140),
        visible:e.getClientRects().length>0&&!e.hidden})),alerts:document.querySelectorAll('[role=alert]').length})`);
    rows.push({requested_path:path,fixture_role:role,...dom,http_responses:network.slice(begin),
      verification:'ACTUAL_EDGE_FASTAPI_SQLITE_RENDER_AND_READS_ONLY; NO_CONTROL_ACTION_OR_PERSISTENCE_PROOF'});
  }
  try{
    await click('Sign out');await loginAdmin();
    for(const path of ['/admin','/admin/faculty','/admin/subjects','/admin/preferences','/admin/rooms','/admin/generate','/admin/chromosomes','/admin/schedules','/admin/analysis','/admin/history','/admin/accounts','/admin/external-schedules'])await visit(path,'fictional administrator');
    await visit('/chair/requests','fictional independently appointed Chair');
    await click('Sign out');await loginPublisher();await visit('/schedule-applications','fictional independently authorized scheduler');
    await click('Sign out');await loginFaculty(0);
    for(const path of ['/faculty','/faculty/preferences','/faculty/schedule','/faculty/profile','/faculty/adjustments'])await visit(path,'fictional faculty');
    await click('Sign out');await visit('/login','anonymous');
    assert.equal(rows.length,20);assert.equal(new Set(rows.map(r=>r.requested_path)).size,20);
    assert.ok(process.env.D16_SCREENSHOT_DIR);
    await writeFile(join(resolve(process.env.D16_SCREENSHOT_DIR),'route-survey.json'),JSON.stringify(sanitizeTree({
      scope:'Actual working-tree frontend in owned snapshot, real loopback FastAPI/SQLite and explicit fictional providers. Values, headers, cookies, bodies and URL queries deliberately omitted. Background reads can appear; per-control causality is not inferred.',rows}),null,2),{flag:'wx'});
    await loginFaculty(2);
  }finally{socket.removeEventListener('message',listener);await command('Network.disable');}
});
