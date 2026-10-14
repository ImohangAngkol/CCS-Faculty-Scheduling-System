import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, resolve, join, sep } from "node:path";
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function eventually(check, message, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) { try { const value = await check(); if (value) return value; } catch { /* startup or pending render */ } await pause(30); }
  throw new Error(message);
}
function cdp(socket) {
  let sequence = 0;
  const pending = new Map(), listeners = new Map();
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const entry = pending.get(message.id); pending.delete(message.id);
      if (message.error) entry?.reject(new Error(message.error.message)); else entry?.resolve(message.result);
    } else listeners.get(message.method)?.(message.params);
  });
  return {
    on: (name, handler) => listeners.set(name, handler),
    send: (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; const timer = setTimeout(() => {pending.delete(id); reject(new Error(`Browser command timed out: ${method}`));}, 10000); pending.set(id, { resolve: value => {clearTimeout(timer); resolve(value);}, reject: error => {clearTimeout(timer); reject(error);} }); socket.send(JSON.stringify({ id, method, params })); }),
  };
}


const metrics = generation => ({ status: "RUNNING", generation, generation_limit: 2,
  population_requested: 10, population_actual: 8, generation_best_fitness: 100 - generation,
  best_ever_fitness: 100 - generation, average_fitness: 150 - generation, worst_fitness: 200,
  best_ever_improvement: generation ? 1 : 0, generations_without_improvement: 0,
  elapsed_ms: generation * 1000, generation_elapsed_ms: 1000,
  accepted_new_chromosomes_total: 8 + generation * 3, baseline_chromosomes: 0,
  fitness_evaluations_total: null, input_fingerprint: "inputs", configuration_fingerprint: "config",
  metrics_comparable: true, validation_status: "passed" });
const result = { best_fitness: 98, fitness_breakdown: {}, generations_completed: 2,
  population_size: 10, history: [{ generation: 0, best_fitness: 100 }, { generation: 1, generation_best_fitness: 99, best_ever_fitness: 99 }], schedule: [] };

test("Live GA dashboard updates before final result and distinguishes disconnect", { timeout: 180000 }, async t => {
  const profile = await mkdtemp(join(tmpdir(), "ga-monitoring-browser-"));
  const vite = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "--host", "localhost", "--port", "5188", "--strictPort"], { cwd: new URL("../", import.meta.url), windowsHide: true, stdio: "pipe" });
  let output = ""; vite.stdout.on("data", data => output += data); vite.stderr.on("data", data => output += data);
  const executable = process.env.PREFERENCE_TEST_BROWSER ?? (process.platform === "win32" ? "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" : "chromium");
  const edge = spawn(executable, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=9227", `--user-data-dir=${profile}`, "about:blank"], { windowsHide: true, stdio: ["ignore", "ignore", "pipe"] });
  let browserOutput = ""; edge.stderr?.on("data", data => browserOutput += data);
  let launchError; edge.on("error", error => launchError = error);
  let socket;
  try {
    await eventually(async () => (await fetch("http://localhost:5188", {signal:AbortSignal.timeout(2000)})).ok, `Vite startup: ${output}`);
    const targets = await eventually(async () => { if (launchError) throw launchError; return (await fetch("http://127.0.0.1:9227/json/list", {signal:AbortSignal.timeout(2000)})).json(); }, `Headless browser startup failed: ${launchError ?? browserOutput}`);
    socket = new WebSocket(targets.find(target => target.type === "page").webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    const client = cdp(socket), errors = [];
    client.on("Runtime.exceptionThrown", event => { const message = event.exceptionDetails.exception?.description ?? event.exceptionDetails.text; errors.push(message); console.log("Browser error:",message); });
    await client.send("Runtime.enable"); await client.send("Page.enable");
    await client.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    await client.send("Page.addScriptToEvaluateOnNewDocument", { source: `
      const originalFetch = window.fetch.bind(window);
      window.mockGAController = null;
      window.mockStopRequests = [];
      window.mockStopResolve = null;
      window.mockPauseResolve = null;
      window.mockControlRequests = [];
      window.mockCheckpointRequests = [];
      window.mockLogRequests = [];
      window.mockHistoryRequests = [];
      const originalTimeout = window.setTimeout.bind(window);
      window.setTimeout = (callback, delay, ...args) => originalTimeout(callback, (delay===120000 && sessionStorage.getItem('mockFastTimeout')==='true') || (delay===10000 && sessionStorage.getItem('mockFastLogTimeout')==='true') ? 50 : delay, ...args);
      window.mockStateError = false;
      window.mockLegacyBackend = false;
      window.fetch = async (input, options) => {
        const url = String(input);
        if (url.includes('/api/ga/runs') && sessionStorage.getItem('mockHistory')) {
          const archive = JSON.parse(sessionStorage.getItem('mockHistory'));
          const parsed = new URL(url), route = parsed.pathname;
          if (route === '/api/ga/runs' || route.startsWith('/api/ga/runs/' + archive.run.run_id + '/')) {
            window.mockHistoryRequests.push({url,method:options?.method??'GET'});
            if (sessionStorage.getItem('mockHistoryFailure') === 'true') return Response.json({detail:{message:'History checksum failed.'}},{status:422});
            if (route.endsWith('/generations/0/analysis') && sessionStorage.getItem('mockAnalysisFailure') === 'true') return Response.json({detail:{code:'GA_HISTORY_INVALID',message:'History could not be read or validated.'}},{status:422});
            if (route.endsWith('/export')) return new Response(route.includes('history/export')?'generation,best_ever_fitness\\n0,100\\n1,100\\n':JSON.stringify({schedule:archive.schedule}),{headers:{'content-disposition':'attachment; filename="run-'+archive.run.run_id+'-history.json"'}});
            if (route === '/api/ga/runs') return Response.json({schema_version:1,items:[archive.run],total:1,offset:0,limit:20,errors:[]});
            if (route.endsWith('/generations')) return Response.json({schema_version:1,run:archive.run,items:archive.items,total:2,offset:0,limit:50});
            if (route.endsWith('/compare')) return Response.json(archive.comparison);
            const generation = Number(route.split('/').at(-2));
            const bestEver = parsed.searchParams.get('candidate') === 'best_ever';
            if (route.endsWith('/schedule')) return Response.json({schema_version:1,run_id:archive.run.run_id,generation,chromosome_id:bestEver?'best-ever':'generation-best',schedule:archive.schedule,current_inputs_match:true,validation:{status:'passed'}});
            if (route.endsWith('/analysis')) return Response.json({schema_version:1,run_id:archive.run.run_id,generation,chromosome_id:bestEver?'best-ever':'generation-best',timestamp:archive.run.created_at,fitness:bestEver?100:110,fitness_breakdown:null,breakdown_unavailable_reason:'No additional fitness evaluation was performed.',preference_unavailable_reason:'Per-faculty preferences were not captured.',workload:[{faculty:'Faculty 7',required_teaching_load:19,teaching_units:15,difference:-4,fulfillment_percent:15/19*100,preparations:1,assigned_subjects:['ITD104']}],validation:{status:'passed'}});
          }
        }
        const processId = sessionStorage.getItem('mockProcessId') ?? 'browser-process';
        if (url.includes('/api/ga/runs/') && url.includes('/logs?')) {
          window.mockLogRequests.push(url);
          if (sessionStorage.getItem('mockLogUnsupported')==='true') return Response.json({detail:'Not Found'},{status:404});
          if (sessionStorage.getItem('mockLogError')==='true') throw new Error('Console backend unavailable');
          if (sessionStorage.getItem('mockLogPending')==='true') return new Promise(()=>{});
          const runId = new URL(url).pathname.split('/').at(-2);
          const snapshots = [JSON.parse(sessionStorage.getItem('mockActiveRun') ?? 'null'),JSON.parse(sessionStorage.getItem('mockTerminalRun') ?? 'null'),...JSON.parse(sessionStorage.getItem('mockPausedRuns') ?? '[]')];
          const snapshot = snapshots.find(run=>run && run.run_id===runId);
          const all = JSON.parse(sessionStorage.getItem('mockLogEntries') ?? '[]');
          const latest = all.at(-1)?.sequence ?? 0;
          const requested = Number(new URL(url).searchParams.get('after_sequence'));
          const reset = requested > latest;
          const cursor = reset ? 0 : requested;
          const entries = all.filter(entry=>entry.sequence>cursor).slice(0,4);
          const next = entries.at(-1)?.sequence ?? cursor;
          return Response.json({run_id:runId,process_instance_id:processId,log_epoch:sessionStorage.getItem('mockLogEpoch')??'initial-epoch',
            state:snapshot?.state??'RUNNING',execution_active:snapshot?.execution_active??true,entries,
            latest_sequence:latest,next_sequence:next,has_more:next<latest,cursor_reset:reset,
            earlier_logs_truncated:sessionStorage.getItem('mockLogTruncated')==='true' || reset});
        }
        if (url.endsWith('/api/ga/status')) {
          if (sessionStorage.getItem('mockDiscoveryPending')==='true') return new Promise(()=>{});
          if (sessionStorage.getItem('mockDiscoveryError')==='true') throw new Error('Backend unavailable');
          return Response.json(window.mockLegacyBackend ? {status:'ready'} : {control_version:'3c.1',pause_resume_version:'3d.1',process_instance_id:processId,active_run:JSON.parse(sessionStorage.getItem('mockActiveRun') ?? 'null'),paused_runs:JSON.parse(sessionStorage.getItem('mockPausedRuns') ?? '[]')});
        }
        if (url.endsWith('/checkpoint-status')) {
          window.mockCheckpointRequests.push(url);
          if (sessionStorage.getItem('mockCheckpointPending')==='true') return new Promise(resolve => { window.mockCheckpointResolve=resolve; });
          if (sessionStorage.getItem('mockCheckpointError')==='true') throw new Error('Checkpoint service unavailable');
          return Response.json({run_id:url.split('/').at(-2),process_instance_id:processId,state:'PAUSED',resumable:sessionStorage.getItem('mockCheckpointInvalid')!=='true',error:sessionStorage.getItem('mockCheckpointInvalid')==='true'?'Checkpoint inputs changed':undefined});
        }
        if (url.endsWith('/pause') || url.endsWith('/resume')) {
          window.mockControlRequests.push({url,process:options?.headers?.['X-GA-Process-ID']});
          if (url.endsWith('/pause')) return new Promise(resolve => {window.mockPauseResolve=resolve;});
          if (sessionStorage.getItem('mockResumeConflict')==='true') return Response.json({detail:{code:'GA_RESUME_CONFLICT',message:'This run is already stopping; resume was not admitted.'}},{status:409});
          if (sessionStorage.getItem('mockCheckpointInvalid')==='true') return Response.json({detail:{code:'GA_CHECKPOINT_INPUT_CHANGED',message:'Checkpoint inputs changed; no worker was started.'}},{status:409});
          const snapshot=JSON.parse(sessionStorage.getItem('mockTerminalRun'));
          const resuming={...snapshot,state:'RESUMING',execution_active:true,accepting_pause:false,accepting_resume:false};
          sessionStorage.setItem('mockActiveRun',JSON.stringify(resuming)); sessionStorage.setItem('mockPausedRuns','[]');
          return Response.json({...resuming,accepted:true});
        }
        if (url.includes('/api/ga/runs/') && !url.endsWith('/stop') && !url.endsWith('/result')) {
          if (window.mockStateError) throw new Error('Status connection lost');
          const snapshots = [JSON.parse(sessionStorage.getItem('mockActiveRun') ?? 'null'),JSON.parse(sessionStorage.getItem('mockTerminalRun') ?? 'null'),...JSON.parse(sessionStorage.getItem('mockPausedRuns') ?? '[]')];
          const snapshot = snapshots.find(run=>run && url.endsWith('/'+run.run_id));
          if (options?.headers?.['X-GA-Process-ID'] !== processId) return Response.json({detail:{code:'GA_PROCESS_CHANGED',message:'Backend process changed; no cancellation occurred.'}},{status:409});
          return snapshot && url.endsWith('/'+snapshot.run_id) ? Response.json(snapshot) : Response.json({detail:{code:'GA_UNKNOWN_RUN',message:'Run is unknown in this server process; no cancellation occurred.'}},{status:404});
        }
        if (url.includes('/api/ga/runs/') && url.endsWith('/result')) return Response.json({status:'success',data:JSON.parse(sessionStorage.getItem('mockStoppedResult'))});
        if (url.includes('/api/ga/runs/') && url.endsWith('/stop')) {
          window.mockStopRequests.push(url);
          return new Promise(resolve => { window.mockStopResolve = resolve; });
        }
        if (url.includes('/api/ga/stream')) {
          sessionStorage.setItem('mockStreamCount',String(Number(sessionStorage.getItem('mockStreamCount') ?? '0')+1));
          return new Response(new ReadableStream({ start(controller) { window.mockGAController = controller; } }), { headers: { 'Content-Type': 'text/event-stream' } });
        }
        if (url.includes('/api/ga/latest')) {
          if (sessionStorage.getItem('mockLatestPending')==='true') return new Promise((resolve,reject) => { options?.signal?.addEventListener('abort',()=>reject(options.signal.reason),{once:true}); });
          const latest = sessionStorage.getItem('mockLatestGA'); return latest ? Response.json({status:'success',data:JSON.parse(latest)}) : new Response('',{status:404}); }
        if (url.includes('/api/chromosomes/best')) return Response.json({ status:'success', data:{exists:false,fitness:null,created_at:null} });
        return originalFetch(input, options);
      };
    ` });
    async function evaluate(expression) {
      const response = await client.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description ?? response.exceptionDetails.text);
      return response.result.value;
    }
    let sequence = 0;
    async function send(type, data) {
      if (type === "run_created" || type === "run_started") data = { ...data, process_instance_id: "browser-process" };
      const payload = { schema_version: 1, run_id: "browser-run", sequence: ++sequence, type, timestamp: "2026-10-10T03:00:00Z", data };
      await evaluate(`window.mockGAController.enqueue(new TextEncoder().encode(${JSON.stringify('data: '+JSON.stringify(payload)+'\r\n\r\n')})); true`);
    }
    await client.send("Page.navigate", { url: "http://localhost:5188/admin/generate" });
    await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Generate button missing");
    await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
    await eventually(() => evaluate("!!window.mockGAController"), "Stream not opened");
    await t.test("initial population and completed generations update metrics and graph live", async () => {
      await send("run_created", { status: "CREATED" }); await send("run_started", { status: "RUNNING" });
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Preparing initial schedules')`), "Initialization status missing");
      await send("initial_population_ready", metrics(0));
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent==='0 / 2'`), "Generation zero missing");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-population"]').textContent`), "8 / 10");
      await send("generation_completed", metrics(1));
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points==='2'`), "Graph did not update live");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-accepted"]').textContent`), "11");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-best-ever"]').textContent`), "99");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-average"]').textContent`), "149");
      assert.equal(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Completed')`), false);
      await evaluate(`sessionStorage.setItem('mockLogEntries',JSON.stringify([{sequence:1,message:'INITIAL MUTATION OUTPUT',timestamp:'2026-10-11T03:00:00Z',line_truncated:false}])); true`);
      await send("log",{message:"INITIAL MUTATION OUTPUT",log_sequence:1,log_epoch:"initial-epoch"});
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.includes('INITIAL MUTATION OUTPUT')`), "Initial run diagnostics did not arrive");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.split('INITIAL MUTATION OUTPUT').length-1`),1);
      await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').scrollIntoView({block:'start'}); true`);
      const clip = await evaluate(`var box=document.querySelector('[data-testid="live-ga-monitor"]').getBoundingClientRect(); ({x:box.x+window.scrollX,y:box.y+window.scrollY,width:box.width,height:box.height,scale:1})`);
      const shot = await client.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip });
      await mkdir(new URL("../.cache", import.meta.url), { recursive: true });
      await writeFile(new URL("../.cache/ga-monitoring-desktop.png", import.meta.url), Buffer.from(shot.data, "base64"));
    });
    await t.test("final result completes and existing latest-result restoration works", async () => {
      await send("result", result); await send("done", { status: "COMPLETED" });
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Completed')`), "Terminal status missing");
      await evaluate(`sessionStorage.setItem('mockLatestGA',${JSON.stringify(JSON.stringify(result))}); true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`window.mockGAController===null && document.body.textContent.includes('Generations Completed')`), "Final result was not restored");
    });
    await t.test("stop button requests by run ID, keeps progress, and preserves a stopped schedule", async () => {
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate("!!window.mockGAController"), "Stop scenario stream missing");
      sequence = 0;
      await send("run_created", { status: "CREATED" });
      await send("run_started", { status: "INITIALIZING" });
      await send("initial_population_ready", metrics(0));
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation' && !button.disabled)`), "Stop button not enabled");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation').click(); true`);
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Waiting for acknowledgement') && window.mockStopRequests.length===1`), "Stop request was not sent");
      assert.ok(await evaluate(`window.mockStopRequests[0].endsWith('/api/ga/runs/browser-run/stop')`));
      assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation').disabled`));
      await send("run_state_changed", { status: "STOP_REQUESTED" });
      await send("generation_completed", metrics(1));
      await send("run_state_changed", { status: "STOPPING" });
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Stopping')`), "Stopping state missing");
      // A delayed HTTP acknowledgement must not regress the newer SSE state.
      await evaluate(`window.mockStopResolve(Response.json({run_id:'browser-run',state:'STOP_REQUESTED',accepted:true})); true`);
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Stopping')`), "HTTP acknowledgement regressed the stopping state");
      assert.equal(await evaluate("window.mockStopRequests.length"), 1);
      await send("run_state_changed", { status: "STOPPED", elapsed_ms: 4000 });
      await send("result", { ...result, best_fitness: 99, status: "STOPPED", run_id: "browser-run", generations_completed: 1, elapsed_ms: 4000 });
      await send("done", { status: "STOPPED", has_result: true });
      await eventually(() => evaluate(`document.body.textContent.includes('Stopped — preserved schedule')`), "Stopped schedule not available");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "1 / 2");
      assert.ok(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('optimization did not complete')`));
    });
    await t.test("stop before initialization leaves the previous completed result intact", async () => {
      // Restore the completed fixture first; stopping must not replace that result.
      await client.send("Page.reload");
      await eventually(() => evaluate(`document.body.textContent.includes('Generations Completed')`), "Previous completed result missing");
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Run discovery has not enabled start");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate("!!window.mockGAController"), "Early stop stream missing");
      sequence = 0;
      await send("run_started", { status: "INITIALIZING" });
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation' && !button.disabled)`), "Early stop button missing");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation').click(); true`);
      await eventually(() => evaluate("!!window.mockStopResolve"), "Early stop not sent");
      await evaluate(`window.mockStopResolve(Response.json({run_id:'browser-run',state:'STOP_REQUESTED',accepted:true})); true`);
      await send("run_state_changed", { status: "STOPPING" });
      await send("run_state_changed", { status: "STOPPED", elapsed_ms: 1000 });
      await send("done", { status: "STOPPED", has_result: false });
      await eventually(() => evaluate(`document.body.textContent.includes('No schedule was produced') && document.body.textContent.includes('Previous completed schedule')`), "No-result stop did not preserve completed result");
    });
    await t.test("disconnect after a stop request is unknown execution, never stopped", async () => {
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Previous stop has not settled");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate("!!window.mockGAController"), "Second stream missing");
      sequence = 0;
      await send("run_started", { status: "RUNNING" });
      await send("initial_population_ready", metrics(0));
      await send("run_state_changed", { status: "STOP_REQUESTED" });
      await evaluate("window.mockStateError=true; true");
      await evaluate("window.mockGAController.close(); true");
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Monitoring disconnected')`), "Disconnect status missing");
      assert.ok(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('server may still be running')`));
      assert.equal(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Stopped')`), false);
      await client.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
      await eventually(() => evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile overflow");
    });
    await client.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    await t.test("route-level Not Found explains the failure without claiming cancellation", async () => {
      await client.send("Page.reload");
      await eventually(() => evaluate(`window.mockGAController===null && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Reload discovery did not finish");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate("!!window.mockGAController"), "404 scenario stream missing");
      sequence = 0;
      await send("run_started", { status: "INITIALIZING" });
      await send("generation_completed", metrics(1));
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent==='browser-run'`), "Registered ID missing");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation').click(); true`);
      await eventually(() => evaluate("!!window.mockStopResolve"), "404 stop not sent");
      await evaluate(`window.mockStopResolve(Response.json({detail:'Not Found'},{status:404})); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('Restart the correct backend')`), "Missing route error was not actionable");
      assert.ok(await evaluate(`document.body.textContent.includes('No stop was acknowledged')`));
      assert.equal(await evaluate(`document.body.textContent.includes('Stopped — preserved schedule')`), false);
      await send("result", result); await send("done", { status: "COMPLETED" });
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Completed')`), "Failed stop stopped monitoring");
    });
    await t.test("legacy backend preflight rejects control incompatibility before starting a worker", async () => {
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Completed run did not release the start button");
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`window.mockLegacyBackend=true; [...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('does not advertise Phase 3C.1 control support')`), "Legacy backend was accepted");
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), before);
      await evaluate("window.mockLegacyBackend=false; true");
    });
    await t.test("refresh discovers the same worker and stops it through bounded polling without another start", async () => {
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`window.mockGAController=null; [...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate(`!!window.mockGAController && sessionStorage.getItem('mockStreamCount')!==${JSON.stringify(before)}`), "Refresh scenario stream missing");
      sequence = 0;
      await send("run_created", { status: "CREATED" });
      await send("generation_completed", metrics(1));
      const snapshot = { run_id: "browser-run", process_instance_id: "browser-process", state: "RUNNING",
        execution_active: true, accepting_stop: true, configuration: { population_size: 10, generations: 2, fresh_chromosomes: 2 },
        latest_progress: metrics(1), latest_completed_generation: 1, elapsed_ms: 1000, terminal_error: null, result_reference: null };
      await evaluate(`sessionStorage.setItem('mockActiveRun',${JSON.stringify(JSON.stringify(snapshot))}); true`);
      const started = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate("window.oldDocument=true; true");
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.querySelector('[data-testid="ga-run-id"]')?.textContent==='browser-run' && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation' && !button.disabled)`), "Active worker not recovered");
      assert.equal(await evaluate("window.mockGAController"), null);
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), started);
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "1 / 2");
      assert.ok(await evaluate(`document.body.textContent.includes('Earlier events may be missing')`));
      assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generating Schedule...').disabled`));
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation').click(); true`);
      await eventually(() => evaluate("!!window.mockStopResolve"), "Recovered stop not sent");
      await evaluate(`sessionStorage.setItem('mockActiveRun',${JSON.stringify(JSON.stringify({ ...snapshot, state: "STOP_REQUESTED", accepting_stop: false }))}); window.mockStopResolve(Response.json({run_id:'browser-run',state:'STOP_REQUESTED',accepted:true})); true`);
      assert.ok(await evaluate(`window.mockStopRequests[0].endsWith('/api/ga/runs/browser-run/stop')`));
      const preserved = { ...result, run_id: "browser-run", status: "STOPPED", generations_completed: 1, best_fitness: 99 };
      const terminal = { ...snapshot, state: "STOPPED", execution_active: false, accepting_stop: false, result_reference: "stopped_runs/browser-run.json" };
      await evaluate(`sessionStorage.setItem('mockStoppedResult',${JSON.stringify(JSON.stringify(preserved))}); sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(terminal))}); sessionStorage.removeItem('mockActiveRun'); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('Stopped — preserved schedule') && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Polling did not deliver stopped result");
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), started);
    });
    await t.test("a result identity failure preserves the authoritative terminal state", async () => {
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`var snapshot=JSON.parse(sessionStorage.getItem('mockTerminalRun')); snapshot.state='COMPLETED'; snapshot.result_reference='latest_ga_result.json'; sessionStorage.setItem('mockTerminalRun',JSON.stringify(snapshot)); sessionStorage.setItem('ga.active-run.v1',JSON.stringify({run_id:'browser-run',process_instance_id:'browser-process'})); sessionStorage.setItem('mockStoppedResult',JSON.stringify({run_id:'another-run',status:'COMPLETED'})); true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`document.body.textContent.includes('preserved result could not be loaded')`), "Result identity failure was hidden");
      assert.ok(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Completed')`));
      assert.equal(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Monitoring disconnected')`), false);
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), before);
    });
    await t.test("a replaced backend reports interrupted ownership without restoring a population", async () => {
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`sessionStorage.setItem('ga.active-run.v1',JSON.stringify({run_id:'old-run',process_instance_id:'browser-process'})); sessionStorage.setItem('mockProcessId','new-process'); sessionStorage.removeItem('mockTerminalRun'); sessionStorage.removeItem('mockActiveRun'); true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`document.body.textContent.includes('Previous run interrupted or unknown')`), "Process loss was not disclosed");
      assert.ok(await evaluate(`document.body.textContent.includes('population was not restored')`));
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`), "old-run");
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), before);
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation')`), false);
    });
    await t.test("pause waits for durable acknowledgement and preserves the graph without publishing a schedule", async () => {
      await evaluate("window.pauseScenarioOldDocument=true; sessionStorage.removeItem('ga.active-run.v1'); sessionStorage.setItem('mockProcessId','browser-process'); sessionStorage.removeItem('mockTerminalRun'); true");
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.pauseScenarioOldDocument && window.mockGAController===null && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Pause scenario discovery did not finish");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate("!!window.mockGAController"), "Pause scenario stream missing");
      sequence = 0;
      await send("run_started",{status:"INITIALIZING",accepting_pause:true,accepting_stop:true});
      await send("initial_population_ready",metrics(0)); await send("generation_completed",metrics(1));
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Pause Generation' && !button.disabled)`), "Pause button missing");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Pause Generation').click(); true`);
      await eventually(() => evaluate("!!window.mockPauseResolve"), "Pause was not requested");
      assert.ok(await evaluate(`document.body.textContent.includes('Sending pause request')`));
      assert.equal(await evaluate(`document.body.textContent.includes('Pause requested — waiting for a safe generation boundary.')`), false);
      assert.ok(await evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation' && !button.disabled)`));
      await evaluate(`window.mockPauseResolve(Response.json({run_id:'browser-run',process_instance_id:'browser-process',state:'PAUSE_REQUESTED',accepted:true})); true`);
      await send("run_state_changed",{status:"PAUSING",accepting_pause:false,accepting_stop:true});
      assert.equal(await evaluate(`document.body.textContent.includes('Paused: checkpoint saved.')`), false);
      const snapshot={run_id:"browser-run",process_instance_id:"browser-process",state:"PAUSED",execution_active:false,
        accepting_stop:true,accepting_pause:false,accepting_resume:true,configuration:{population_size:10,generations:2,fresh_chromosomes:2},
        latest_progress:metrics(1),progress_history:[metrics(0),metrics(1)],latest_completed_generation:1,elapsed_ms:1000,
        terminal_error:null,result_reference:null,checkpoint:"checkpoint-1.json.gz",checkpoint_status:{resumable:true}};
      await evaluate(`sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(snapshot))}); sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([snapshot]))}); sessionStorage.removeItem('mockActiveRun'); true`);
      await send("run_state_changed",{status:"PAUSED",accepting_resume:false,accepting_pause:false,checkpoint:snapshot.checkpoint});
      await send("done",{status:"PAUSED",has_result:false});
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Durable pause did not enable resume after worker exit");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`),"2");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`),"1 / 2");
      assert.equal(await evaluate(`document.body.textContent.includes('Stopped — preserved schedule')`),false);
    });
    await t.test("acknowledged pause survives refresh even when saved-result loading never responds", async () => {
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate("sessionStorage.setItem('mockLatestPending','true'); window.oldDocument=true; true");
      await client.send("Page.reload");
      await eventually(() => evaluate("!window.oldDocument"), "Refresh did not remount");
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Paused refresh stalled behind saved-result loading");
      for (const [id, value] of Object.entries({'ga-run-id':'browser-run','ga-generation':'1 / 2','ga-population':'8 / 10','ga-best-ever':'99','ga-generation-best':'99','ga-average':'149','ga-accepted':'11','ga-elapsed':'0m 1s'})) {
        assert.equal(await evaluate(`document.querySelector('[data-testid="${id}"]').textContent`), value);
      }
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`), "2");
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), before);
      await evaluate("sessionStorage.removeItem('mockLatestPending'); true");
    });
    await t.test("refresh during pending pause and slow checkpoint verification hydrates before enabling resume", async () => {
      await evaluate(`var paused=JSON.parse(sessionStorage.getItem('mockTerminalRun')); var pending={...paused,state:'PAUSE_REQUESTED',execution_active:true,accepting_resume:false}; sessionStorage.setItem('mockActiveRun',JSON.stringify(pending)); sessionStorage.setItem('mockPausedRuns','[]'); window.oldDocument=true; true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('Pause requested')`), "Pending pause was not recovered");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "1 / 2");
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), false);
      await evaluate(`sessionStorage.setItem('mockCheckpointPending','true'); var paused=JSON.parse(sessionStorage.getItem('mockTerminalRun')); sessionStorage.setItem('mockPausedRuns',JSON.stringify([paused])); sessionStorage.removeItem('mockActiveRun'); true`);
      await eventually(() => evaluate(`!!window.mockCheckpointResolve && document.body.textContent.includes('Checking compatibility')`), "Checkpoint verification was not separated from hydration");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`), "2");
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), false);
      await evaluate(`sessionStorage.removeItem('mockCheckpointPending'); window.mockCheckpointResolve(Response.json({run_id:'browser-run',process_instance_id:'browser-process',state:'PAUSED',resumable:true})); true`);
      await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Verified checkpoint did not enable resume");
    });
    await t.test("same-run resume survives refresh during RESUMING and continues its history", async () => {
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation').click(); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('Restoring saved population')`), "Resume did not begin");
      await evaluate("window.oldDocument=true; true");
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('Restoring saved population')`), "RESUMING refresh failed");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "1 / 2");
      assert.equal(await evaluate("window.mockControlRequests.length"), 0);
      await evaluate(`var running=JSON.parse(sessionStorage.getItem('mockActiveRun')); running.state='RUNNING'; running.latest_progress=${JSON.stringify(metrics(2))}; running.progress_history.push(running.latest_progress); sessionStorage.setItem('mockActiveRun',JSON.stringify(running)); true`);
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent==='2 / 2'`), "Resumed generation was not monitored");
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), before);
      await evaluate(`var paused=JSON.parse(sessionStorage.getItem('mockTerminalRun')); sessionStorage.removeItem('mockActiveRun'); sessionStorage.setItem('mockPausedRuns',JSON.stringify([paused])); window.oldDocument=true; true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Next paused recovery failed");
    });
    await t.test("restart discovers the same paused identity and resume preserves history without another stream", async () => {
      const before=await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`var saved=JSON.parse(sessionStorage.getItem('mockTerminalRun')); saved.process_instance_id='restarted-process'; sessionStorage.setItem('mockProcessId','restarted-process'); sessionStorage.setItem('mockTerminalRun',JSON.stringify(saved)); sessionStorage.setItem('mockPausedRuns',JSON.stringify([saved])); window.oldDocument=true; true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('Durable paused checkpoint recovered') && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Restart did not recover checkpoint");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`),"browser-run");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`),"2");
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Resume Generation').click(); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('Restoring saved population and random state.')`), "Resuming state missing");
      assert.equal(await evaluate("window.mockControlRequests[0].process"),"restarted-process");
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"),before);
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`),"1 / 2");
      await evaluate(`var saved=JSON.parse(sessionStorage.getItem('mockActiveRun')); saved.state='RUNNING'; saved.accepting_pause=true; saved.latest_progress=${JSON.stringify(metrics(2))}; saved.progress_history.push(saved.latest_progress); sessionStorage.setItem('mockActiveRun',JSON.stringify(saved)); true`);
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent==='2 / 2'`), "Resumed progress missing");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`),"3");
      await evaluate(`var saved=JSON.parse(sessionStorage.getItem('mockActiveRun')); saved.state='COMPLETED'; saved.execution_active=false; saved.result_reference='latest_ga_result.json'; sessionStorage.setItem('mockTerminalRun',JSON.stringify(saved)); sessionStorage.removeItem('mockActiveRun'); sessionStorage.setItem('mockStoppedResult',${JSON.stringify(JSON.stringify({...result,run_id:"browser-run",status:"COMPLETED"}))}); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('Generation Complete') && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule' && !button.disabled)`), "Resumed run did not complete");
    });
    await t.test("incompatible resume is rejected without starting a new population", async () => {
      await evaluate(`var saved=JSON.parse(sessionStorage.getItem('mockTerminalRun')); saved.state='PAUSED'; saved.result_reference=null; saved.accepting_resume=true; saved.latest_progress=${JSON.stringify(metrics(1))}; saved.progress_history=[${JSON.stringify(metrics(0))},${JSON.stringify(metrics(1))}]; saved.checkpoint_status={resumable:true}; sessionStorage.setItem('mockTerminalRun',JSON.stringify(saved)); sessionStorage.setItem('mockPausedRuns',JSON.stringify([saved])); sessionStorage.setItem('ga.active-run.v1',JSON.stringify({run_id:saved.run_id,process_instance_id:saved.process_instance_id})); true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`window.mockControlRequests.length===0 && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Invalid-resume scenario missing");
      const before=await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`sessionStorage.setItem('mockCheckpointInvalid','true'); [...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Resume Generation').click(); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('Checkpoint inputs changed; no worker was started.')`), "Incompatible checkpoint error missing");
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"),before);
      assert.ok(await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Resume Generation').disabled`));
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`),"1 / 2");
    });
    await t.test("checkpoint failures preserve paused history and disable resume", async () => {
      await evaluate("sessionStorage.removeItem('mockCheckpointInvalid'); sessionStorage.setItem('mockCheckpointError','true'); window.oldDocument=true; true");
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('Checkpoint service unavailable')`), "Checkpoint error was not surfaced");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "1 / 2");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`), "2");
      assert.ok(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && button.disabled)`));
      assert.equal(await evaluate(`document.body.textContent.includes('Checking the backend for an active run')`), false);
      await evaluate("sessionStorage.removeItem('mockCheckpointError'); true");
    });
    await t.test("incomplete paused metrics produce an explicit error instead of fabricated values", async () => {
      const saved=await evaluate("sessionStorage.getItem('mockPausedRuns')");
      await evaluate(`var paused=JSON.parse(sessionStorage.getItem('mockPausedRuns')); delete paused[0].latest_progress.average_fitness; sessionStorage.setItem('mockPausedRuns',JSON.stringify(paused)); window.oldDocument=true; true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('incomplete metrics')`), "Missing metrics were silently accepted");
      assert.equal(await evaluate(`document.body.textContent.includes('Checking the backend for an active run')`), false);
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), false);
      assert.equal(await evaluate("window.mockControlRequests.length"), 0);
      await evaluate(`sessionStorage.setItem('mockPausedRuns',${JSON.stringify(saved)}); true`);
    });
    await t.test("unavailable and nonresponding discovery settle into actionable errors", async () => {
      for (const [key, message] of [['mockDiscoveryError','Backend unavailable'],['mockDiscoveryPending','Recovery request timed out']]) {
        await evaluate(`sessionStorage.setItem('${key}','true'); window.oldDocument=true; true`);
        await client.send("Page.reload");
        await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('${message}')`), "Discovery did not settle into an error", 16000);
        assert.equal(await evaluate(`document.body.textContent.includes('Checking the backend for an active run')`), false);
        assert.equal(await evaluate("window.mockControlRequests.length"), 0);
        await evaluate(`sessionStorage.removeItem('${key}'); true`);
      }
    });
    await t.test("stop during paused verification never fabricates a server stop state", async () => {
      await evaluate(`sessionStorage.setItem('mockCheckpointPending','true'); window.oldDocument=true; true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && !!window.mockCheckpointResolve && document.body.textContent.includes('Checking compatibility')`), "Paused verification did not start");
      try {
        await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Stop Generation').click(); true`);
        await eventually(() => evaluate("!!window.mockStopResolve"), "Stop HTTP request missing");
        assert.equal(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Stop requested')`), false, "Unacknowledged HTTP request must not become backend STOP_REQUESTED");
        assert.ok(await evaluate(`document.body.textContent.includes('Paused: checkpoint saved.')`));
        assert.equal(await evaluate(`document.body.textContent.includes('Checking compatibility')`), false);
        assert.ok(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && button.disabled)`));
      } finally {
        await evaluate(`sessionStorage.removeItem('mockCheckpointPending'); window.mockCheckpointResolve(Response.json({run_id:'browser-run',process_instance_id:sessionStorage.getItem('mockProcessId'),state:'PAUSED',resumable:true})); window.mockStopResolve(Response.json({detail:{code:'GA_CHECKPOINT_INPUT_CHANGED',message:'Stop checkpoint validation rejected changed inputs; no stop was acknowledged.'}},{status:409})); true`);
      }
      await eventually(() => evaluate(`document.body.textContent.includes('Stop checkpoint validation rejected changed inputs') && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Rejected stop did not reverify the authoritative paused run");
      assert.equal(await evaluate(`document.body.textContent.includes('Stop requested')`), false);
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "1 / 2");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`), "2");
    });
    await t.test("checkpoint verification cannot keep resume enabled when the same run is stopping", async () => {
      const paused = await evaluate("JSON.parse(sessionStorage.getItem('mockTerminalRun'))");
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      for (const state of ['STOP_REQUESTED', 'STOPPING']) {
        await evaluate(`sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(paused))}); sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([paused]))}); sessionStorage.setItem('ga.active-run.v1',JSON.stringify({run_id:'browser-run',process_instance_id:sessionStorage.getItem('mockProcessId')})); sessionStorage.setItem('mockCheckpointPending','true'); window.oldDocument=true; true`);
        await client.send("Page.reload");
        await eventually(() => evaluate(`!window.oldDocument && !!window.mockCheckpointResolve`), "Verification did not start");
        await evaluate(`var stopping={...JSON.parse(sessionStorage.getItem('mockTerminalRun')),state:'${state}',execution_active:true,accepting_stop:false,accepting_resume:false}; sessionStorage.setItem('mockActiveRun',JSON.stringify(stopping)); sessionStorage.setItem('mockPausedRuns','[]'); sessionStorage.removeItem('mockCheckpointPending'); window.mockCheckpointResolve(Response.json({run_id:'browser-run',process_instance_id:sessionStorage.getItem('mockProcessId'),state:'${state}',resumable:false})); true`);
        await eventually(() => evaluate(`document.body.textContent.includes('${state==='STOPPING'?'Stopping':'Stop requested'}') && !document.body.textContent.includes('Checking compatibility')`), "Server stop state was not reconciled");
        assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation')`), false);
        await evaluate("window.oldDocument=true; true");
        await client.send("Page.reload");
        try {
          await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('${state==='STOPPING'?'Stopping':'Stop requested'}')`), "Stopping refresh failed");
        } catch (reason) {
          console.log('Stopping refresh diagnostics:', await evaluate(`({monitor:document.querySelector('[data-testid="live-ga-monitor"]')?.textContent,active:sessionStorage.getItem('mockActiveRun'),reference:sessionStorage.getItem('ga.active-run.v1'),paused:sessionStorage.getItem('mockPausedRuns'),errors:[...document.querySelectorAll('[role="alert"]')].map(el=>el.textContent)})`));
          throw reason;
        }
        assert.equal(await evaluate("window.mockCheckpointRequests.length"), 0);
        assert.equal(await evaluate("window.mockControlRequests.length + window.mockStopRequests.length"), 0);
        assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "1 / 2");
        await evaluate("sessionStorage.removeItem('mockActiveRun'); true");
      }
      const stopped = {...paused,state:'STOPPED',execution_active:false,accepting_stop:false,accepting_resume:false,process_instance_id:'terminal-restarted-process'};
      const other = {...paused,run_id:'another-paused-run',process_instance_id:stopped.process_instance_id};
      await evaluate(`sessionStorage.setItem('mockProcessId','terminal-restarted-process'); sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(stopped))}); sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([other]))}); window.oldDocument=true; true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('Stopped after generation 1')`), "Terminal run was incorrectly replaced by another paused run");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`), "browser-run");
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation')`), false);
      assert.equal(await evaluate("window.mockCheckpointRequests.length"), 0);
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), before);
      await evaluate(`sessionStorage.setItem('mockProcessId',${JSON.stringify(paused.process_instance_id)}); sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(paused))}); sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([paused]))}); sessionStorage.setItem('ga.active-run.v1',JSON.stringify({run_id:'browser-run',process_instance_id:sessionStorage.getItem('mockProcessId')})); true`);
    });
    await t.test("checkpoint verification timeout reports a specific error and preserves paused metrics", async () => {
      await evaluate("sessionStorage.setItem('mockCheckpointPending','true'); sessionStorage.setItem('mockFastTimeout','true'); window.oldDocument=true; true");
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && document.body.textContent.includes('Recovery request timed out')`), "Checkpoint timeout did not settle");
      assert.equal(await evaluate(`document.body.textContent.includes('Checking compatibility')`), false);
      assert.ok(await evaluate(`document.body.textContent.includes('Paused: checkpoint saved.')`));
      assert.ok(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && button.disabled)`));
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`), "2");
      await evaluate("sessionStorage.removeItem('mockCheckpointPending'); sessionStorage.removeItem('mockFastTimeout'); true");
    });
    await t.test("selecting another paused run rehydrates only that run and revalidates its checkpoint", async () => {
      const paused = await evaluate("JSON.parse(sessionStorage.getItem('mockTerminalRun'))");
      const other = {...paused,run_id:'another-paused-run',latest_completed_generation:2,latest_progress:metrics(2),progress_history:[metrics(0),metrics(1),metrics(2)],elapsed_ms:2000};
      await evaluate(`sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([paused,other]))}); window.oldDocument=true; true`);
      await client.send("Page.reload");
      await eventually(() => evaluate(`!window.oldDocument && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), "First paused candidate was not verified");
      await evaluate(`var select=document.querySelector('select[aria-label="Saved paused run"]'); select.value='another-paused-run'; select.dispatchEvent(new Event('change',{bubbles:true})); true`);
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent==='another-paused-run' && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`), "Selected paused run did not hydrate and verify");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`), "2 / 2");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-best-ever"]').textContent`), "98");
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`), "3");
      assert.ok(await evaluate(`window.mockCheckpointRequests.at(-1).endsWith('/another-paused-run/checkpoint-status')`));
      assert.equal(await evaluate("window.mockControlRequests.length + window.mockStopRequests.length"), 0);
    });
    await t.test("resume rejection reconciles a concurrent server stop instead of inventing PAUSED", async () => {
      const paused = await evaluate("JSON.parse(sessionStorage.getItem('mockPausedRuns')).find(run=>run.run_id==='another-paused-run')");
      const stopping = {...paused,state:'STOPPING',execution_active:true,accepting_stop:false,accepting_resume:false};
      const before = await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`sessionStorage.setItem('mockResumeConflict','true'); sessionStorage.setItem('mockActiveRun',${JSON.stringify(JSON.stringify(stopping))}); sessionStorage.setItem('mockPausedRuns','[]'); [...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation').click(); true`);
      await eventually(() => evaluate(`document.body.textContent.includes('Stopping') && document.body.textContent.includes('resume was not admitted')`), "Failed resume invented a paused lifecycle");
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation')`), false);
      assert.equal(await evaluate(`document.body.textContent.includes('Checking compatibility')`), false);
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`), "another-paused-run");
      assert.equal(await evaluate("window.mockControlRequests.length"), 1);
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"), before);
    });
    const logEntry=(sequence,message)=>({sequence,message,timestamp:'2026-10-11T03:00:00Z',line_truncated:false});
    let logPaused;
    await t.test("paused refresh recovers ordered console output, then resume delivers live logs before metrics advance", async()=>{
      const template=await evaluate("JSON.parse(sessionStorage.getItem('mockTerminalRun'))");
      logPaused={...template,run_id:'console-run',state:'PAUSED',execution_active:false,latest_completed_generation:1,
        latest_progress:metrics(1),progress_history:[metrics(0),metrics(1)],accepting_stop:true,accepting_resume:false};
      const initial=[logEntry(1,'initial console output'),logEntry(2,'GENETIC ALGORITHM PAUSED')];
      await evaluate(`sessionStorage.removeItem('mockResumeConflict'); sessionStorage.removeItem('mockActiveRun'); sessionStorage.removeItem('mockLogTruncated'); sessionStorage.setItem('mockLogEpoch','console-epoch'); sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(logPaused))}); sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([logPaused]))}); sessionStorage.setItem('ga.active-run.v1',${JSON.stringify(JSON.stringify({run_id:logPaused.run_id,process_instance_id:logPaused.process_instance_id}))}); sessionStorage.setItem('mockLogEntries',${JSON.stringify(JSON.stringify(initial))}); window.oldDocument=true; true`);
      await client.send('Page.reload');
      await eventually(()=>evaluate(`!window.oldDocument && document.querySelector('[data-testid="ga-console-output"]')?.textContent.includes('GENETIC ALGORITHM PAUSED') && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`),'Paused console did not recover');
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent`),'PAUSED');
      assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
      const before=await evaluate("sessionStorage.getItem('mockStreamCount')");
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation').click(); true`);
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent==='RESUMING'`),'Console did not show authoritative RESUMING');
      const resumed=[...initial,logEntry(3,'GENETIC ALGORITHM RESUMING'),logEntry(4,'live mutation attempt'),logEntry(5,'live mutation attempt')];
      await evaluate(`var resumed=JSON.parse(sessionStorage.getItem('mockActiveRun')); resumed.state='RUNNING'; sessionStorage.setItem('mockActiveRun',JSON.stringify(resumed)); sessionStorage.setItem('mockLogEntries',${JSON.stringify(JSON.stringify(resumed))}); true`);
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.split('live mutation attempt').length-1===2 && document.querySelector('[data-testid="ga-console-status"]').textContent==='RUNNING'`),'Resumed diagnostics did not continue');
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-generation"]').textContent`),'1 / 2');
      assert.ok(await evaluate(`window.mockLogRequests.some(url=>url.endsWith('after_sequence=2'))`));
      await pause(1200);
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.split('GENETIC ALGORITHM RESUMING').length-1`),1);
      assert.equal(await evaluate("sessionStorage.getItem('mockStreamCount')"),before);
      assert.equal(await evaluate('window.mockControlRequests.length'),1);
    });
    await t.test("refresh during RUNNING replays available logs without posting another worker",async()=>{
      await evaluate('window.oldDocument=true; true'); await client.send('Page.reload');
      await eventually(()=>evaluate(`!window.oldDocument && document.querySelector('[data-testid="ga-console-output"]')?.textContent.split('live mutation attempt').length-1===2`),'Running refresh lost console');
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.split('live mutation attempt').length-1`),2);
      assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
    });
    await t.test("changed log epochs replay from zero and disclose truncated history",async()=>{
      const retained=[logEntry(100,'first retained line'),logEntry(101,'last retained line')];
      await evaluate(`sessionStorage.setItem('mockLogEpoch','evicted-epoch'); sessionStorage.setItem('mockLogTruncated','true'); sessionStorage.setItem('mockLogEntries',${JSON.stringify(JSON.stringify(retained))}); true`);
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.includes('first retained line') && document.querySelector('[data-testid="ga-console-notice"]').textContent.includes('truncated')`),'Buffer eviction skipped earliest retained logs');
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.includes('GENETIC ALGORITHM PAUSED')`),false);
    });
    await t.test("restart retains checkpoint identity and resumed workers reconnect after earlier logs are lost",async()=>{
      const restarted={...logPaused,process_instance_id:'console-restarted-process'};
      await evaluate(`sessionStorage.removeItem('mockActiveRun'); sessionStorage.setItem('mockProcessId','console-restarted-process'); sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(restarted))}); sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([restarted]))}); sessionStorage.setItem('mockLogEpoch','restart-epoch'); sessionStorage.setItem('mockLogEntries','[]'); window.oldDocument=true; true`);
      await client.send('Page.reload');
      await eventually(()=>evaluate(`!window.oldDocument && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled) && document.querySelector('[data-testid="ga-console-notice"]').textContent.includes('truncated')`),'Restart did not recover paused checkpoint/log notice');
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`),'console-run');
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`),'2');
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation').click(); true`);
      const restartedLogs=[logEntry(1,'GENETIC ALGORITHM RESUMING'),logEntry(2,'restarted mutation output')];
      await evaluate(`var run=JSON.parse(sessionStorage.getItem('mockActiveRun')); run.state='RUNNING'; sessionStorage.setItem('mockActiveRun',JSON.stringify(run)); sessionStorage.setItem('mockLogEntries',${JSON.stringify(JSON.stringify(restartedLogs))}); true`);
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]').textContent.includes('restarted mutation output')`),'Restarted resume did not deliver logs');
      assert.equal(await evaluate('window.mockControlRequests.length'),1);
      assert.equal(await evaluate(`window.mockControlRequests[0].process`),'console-restarted-process');
    });
    await t.test("terminal state drains final logs and stops requesting console pages",async()=>{
      const terminal={...logPaused,process_instance_id:'console-restarted-process',state:'STOPPED',execution_active:false,accepting_stop:false,accepting_resume:false};
      await evaluate(`sessionStorage.removeItem('mockActiveRun'); sessionStorage.setItem('mockPausedRuns','[]'); sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(terminal))}); var lines=JSON.parse(sessionStorage.getItem('mockLogEntries')); lines.push(${JSON.stringify(logEntry(3,'GENETIC ALGORITHM STOPPED'))}); sessionStorage.setItem('mockLogEntries',JSON.stringify(lines)); true`);
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent==='STOPPED' && document.querySelector('[data-testid="ga-console-output"]').textContent.includes('GENETIC ALGORITHM STOPPED')`),'Final console logs were not drained');
      await pause(300); const count=await evaluate('window.mockLogRequests.length'); await pause(1500);
      assert.equal(await evaluate('window.mockLogRequests.length'),count);
    });
    await t.test("console recovery failures and timeouts show errors without hiding a verified checkpoint",async()=>{
      const paused={...logPaused,process_instance_id:'console-restarted-process'};
      await evaluate(`sessionStorage.setItem('mockTerminalRun',${JSON.stringify(JSON.stringify(paused))}); sessionStorage.setItem('mockPausedRuns',${JSON.stringify(JSON.stringify([paused]))}); sessionStorage.setItem('ga.active-run.v1',${JSON.stringify(JSON.stringify({run_id:paused.run_id,process_instance_id:paused.process_instance_id}))}); true`);
      for(const [key,message] of [['mockLogError','Console backend unavailable'],['mockLogPending','Recovery request timed out']]) {
        await evaluate(`sessionStorage.setItem('${key}','true'); sessionStorage.setItem('mockFastLogTimeout','true'); window.oldDocument=true; true`);
        await client.send('Page.reload');
        await eventually(()=>evaluate(`!window.oldDocument && document.querySelector('[data-testid="ga-console-notice"]')?.textContent.includes('${message}') && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`),'Console failure did not settle separately from checkpoint verification');
        assert.equal(await evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent`),'PAUSED');
        assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
        await evaluate(`sessionStorage.removeItem('${key}'); sessionStorage.removeItem('mockFastLogTimeout'); true`);
      }
    });
    await t.test("idle paused log monitoring detects another tab's resume without posting a control",async()=>{
      await evaluate('window.oldDocument=true; true'); await client.send('Page.reload');
      await eventually(()=>evaluate(`!window.oldDocument && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Resume Generation' && !button.disabled)`),'Paused observer did not settle');
      const active={...logPaused,process_instance_id:'console-restarted-process',state:'RUNNING',execution_active:true,accepting_resume:false};
      await evaluate(`sessionStorage.setItem('mockActiveRun',${JSON.stringify(JSON.stringify(active))}); sessionStorage.setItem('mockPausedRuns','[]'); var entries=JSON.parse(sessionStorage.getItem('mockLogEntries')); entries.push(${JSON.stringify(logEntry(4,'other tab resumed output'))}); sessionStorage.setItem('mockLogEntries',JSON.stringify(entries)); true`);
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent==='RUNNING' && document.querySelector('[data-testid="ga-console-output"]').textContent.includes('other tab resumed output')`),'Paused observer did not detect external resume');
      assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`),'console-run');
    });
    await t.test("working log retrieval retries disconnected metric monitoring without starting a worker",async()=>{
      await evaluate('window.mockStateError=true; true');
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent==='DISCONNECTED'`),'Metric failure did not report disconnect');
      await evaluate('window.mockStateError=false; true');
      try {
        await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-status"]').textContent==='RUNNING'`),'Available run logs did not trigger authoritative status recovery');
      } catch(reason) {
        console.log('Disconnected recovery diagnostics:',await evaluate(`({monitor:document.querySelector('[data-testid="live-ga-monitor"]').textContent,console:document.querySelector('[data-testid="ga-console-notice"]').textContent,active:sessionStorage.getItem('mockActiveRun'),lastLogs:window.mockLogRequests.slice(-3)})`));
        throw reason;
      }
      assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-run-id"]').textContent`),'console-run');
    });
    await t.test("legacy SSE console lines survive discovery when a server lacks cursor logs",async()=>{
      await evaluate(`sessionStorage.removeItem('ga.active-run.v1'); sessionStorage.removeItem('mockActiveRun'); sessionStorage.removeItem('mockTerminalRun'); sessionStorage.setItem('mockPausedRuns','[]'); sessionStorage.setItem('mockProcessId','browser-process'); sessionStorage.setItem('mockLogUnsupported','true'); window.oldDocument=true; true`);
      await client.send('Page.reload');
      await eventually(()=>evaluate(`!window.oldDocument && !![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Generate Schedule' && !button.disabled)`),'Legacy test discovery failed');
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(()=>evaluate('!!window.mockGAController'),'Legacy stream missing');
      sequence=0; await send('run_started',{status:'RUNNING'}); await send('log',{message:'legacy live diagnostic'});
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-output"]')?.textContent.includes('legacy live diagnostic') && document.querySelector('[data-testid="ga-console-notice"]')?.textContent.includes('endpoint is missing')`),'Legacy console output was discarded');
      await send('result',result); await send('done',{status:'COMPLETED'});
      await eventually(()=>evaluate(`document.querySelector('[data-testid="ga-console-status"]')?.textContent==='COMPLETED'`),'Legacy stream did not finish');
    });
    const archiveId='00000000-0000-4000-8000-000000000001';
    const archiveMetrics=metrics(1);
    archiveMetrics.best_ever_fitness=100; archiveMetrics.generation_best_fitness=110;
    const archive={run:{run_id:archiveId,state:'PAUSED',created_at:'2026-10-11T03:00:00Z',ended_at:null,generations_recorded:2,latest:{generation:1,metrics:archiveMetrics},errors:[],skipped_generations:[],history_error:null,bytes_written:5000},
      items:[0,1].map(generation=>({generation,timestamp:'2026-10-11T03:00:00Z',metrics:{...archiveMetrics,generation},snapshot_bytes:2500})),
      schedule:[{subject:'ITD104',title:'Database Systems',section:'4A',type:'Laboratory',faculty:'7',room:'DATABASE LAB',day:'Tuesday',start:'13:00',end:'16:00'},
        {subject:'ITE184',title:'Social Legal and Professional Issues',section:'4A',type:'Lecture',faculty:'external:eddie-bouy-palad',faculty_name:'Atty. Eddie Bouy Palad',room:'ICT 3A',day:'Wednesday',start:'12:00',end:'13:30'}],
      comparison:{schema_version:1,run_id:archiveId,left:0,right:1,candidate:'generation_best',identical_chromosomes:true,improvement:{generation_best_fitness:-10,best_ever_fitness:0,average_fitness:10},left_metrics:metrics(0),right_metrics:archiveMetrics,changes:[],left_workload:[],right_workload:[],preference_unavailable_reason:'No historical preference analysis.'}};
    await t.test('generation history inspection stays read-only, separates best ever and reuses the calendar',async()=>{
      await evaluate(`sessionStorage.setItem('mockHistory',${JSON.stringify(JSON.stringify(archive))}); true`);
      await client.send('Page.navigate',{url:'http://localhost:5188/admin/history?run='+archiveId});
      await eventually(()=>evaluate(`!!document.querySelector('[data-testid="generation-history"]') && document.body.textContent.includes('2 generations recorded')`),'History page did not load');
      assert.equal(await evaluate(`document.querySelector('[data-testid="ga-convergence"]').dataset.points`),'2');
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.getAttribute('aria-label')==='Inspect generation 1').click(); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Overall penalty: 110') && document.body.textContent.includes('Faculty 7') && document.body.textContent.includes('13:00–16:00')`),'Historical candidate did not render');
      assert.equal(await evaluate(`document.body.textContent.includes('external:eddie-bouy-palad')`),false);
      assert.equal(await evaluate(`document.body.textContent.includes('Atty. Eddie Bouy Palad')`),true);
      await evaluate(`var select=document.querySelector('select[aria-label="Candidate kind"]'); select.value='best_ever'; select.dispatchEvent(new Event('change',{bubbles:true})); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Overall penalty: 100')`),'Best-ever candidate selection invented a score');
      assert.ok(await evaluate(`window.mockHistoryRequests.every(request=>request.method==='GET')`));
      assert.equal(await evaluate(`!![...document.querySelectorAll('button')].find(button=>['Resume Generation','Stop Generation','Generate Schedule'].includes(button.textContent.trim()))`),false);
    });
    await t.test('comparison shows identical schedules while separating average from best-ever improvement',async()=>{
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Compare generations').click(); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Identical schedule candidates') && document.body.textContent.includes('10 higher (worse)') && document.body.textContent.includes('10 lower (improved)') && document.body.textContent.includes('Unchanged')`),'Comparison sign or identity was wrong');
    });
    await t.test('comparison distinguishes an unavailable contribution from an actual zero penalty',async()=>{
      await evaluate(`var archive=JSON.parse(sessionStorage.getItem('mockHistory')); archive.comparison.left_fitness_breakdown={subject_preference:0}; archive.comparison.right_fitness_breakdown={subject_preference:5,time_preference:0}; sessionStorage.setItem('mockHistory',JSON.stringify(archive)); [...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Compare generations').click(); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Available penalty contributions') && document.body.textContent.includes('Not captured') && document.body.textContent.includes('5 higher (worse)')`),'Unavailable comparison contribution was presented as zero');
      assert.ok(await evaluate(`window.mockHistoryRequests.every(request=>request.method==='GET')`));
    });
    await t.test('a transient analysis failure clears after successful inspection of the same generation',async()=>{
      await evaluate(`sessionStorage.setItem('mockAnalysisFailure','true'); [...document.querySelectorAll('button')].find(button=>button.getAttribute('aria-label')==='Inspect generation 0').click(); true`);
      await eventually(()=>evaluate(`document.querySelector('[role="alert"]')?.textContent.includes('Fitness analysis:') && document.querySelector('[role="alert"]')?.textContent.includes('GA_HISTORY_INVALID')`),'Analysis failure did not identify the failed operation');
      await evaluate(`sessionStorage.removeItem('mockAnalysisFailure'); [...document.querySelectorAll('button')].find(button=>button.getAttribute('aria-label')==='Inspect generation 1').click(); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Generation 1 · Schedule candidate') && !document.querySelector('[role="alert"]')`),'Another valid generation did not load');
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.getAttribute('aria-label')==='Inspect generation 0').click(); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Generation 0 · Schedule candidate') && !document.querySelector('[role="alert"]')`),'Recovered generation retained a stale validation error');
      assert.ok(await evaluate(`window.mockHistoryRequests.every(request=>request.method==='GET')`));
    });
    await t.test('validated export errors are visible and refresh restores the same historical run',async()=>{
      await evaluate(`sessionStorage.setItem('mockHistoryFailure','true'); [...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Download candidate JSON').click(); true`);
      await eventually(()=>evaluate(`document.querySelector('[role="alert"]')?.textContent.includes('History checksum failed.')`),'Invalid export error was hidden');
      await evaluate(`sessionStorage.removeItem('mockHistoryFailure'); window.oldDocument=true; true`);
      await client.send('Page.reload');
      await eventually(()=>evaluate(`!window.oldDocument && document.body.textContent.includes('2 generations recorded') && document.querySelector('select[aria-label="Historical run"]').value==='${archiveId}'`),'Historical run refresh lost identity');
      assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
      assert.ok(await evaluate(`window.mockHistoryRequests.every(request=>request.method==='GET')`));
    });
    await t.test('missing or corrupt history settles into an actionable error',async()=>{
      await evaluate(`sessionStorage.setItem('mockHistoryFailure','true'); [...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Refresh history').click(); true`);
      await eventually(()=>evaluate(`document.querySelector('[role="alert"]')?.textContent.includes('History checksum failed.')`),'History recovery did not settle into error');
      assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
    });
    await t.test('an invalid history URL identity displays an error without crashing or starting a run',async()=>{
      await evaluate(`sessionStorage.removeItem('mockHistoryFailure'); true`);
      await client.send('Page.navigate',{url:'http://localhost:5188/admin/history?run=invalid-run'});
      await eventually(()=>evaluate(`document.querySelector('[data-testid="generation-history"]') && document.querySelector('[role="alert"]')?.textContent.includes('Invalid historical run identity')`),'Invalid history identity crashed instead of reporting an error');
      assert.equal(await evaluate('window.mockControlRequests.length + window.mockStopRequests.length'),0);
    });
    const componentKeys=['subject_preference','time_preference','day_preference','schedule_style','lecture_lab_preference','number_of_preparations','teaching_load_balance','daily_teaching_load'];
    const fitnessFixture={schema_version:1,source:{kind:'historical',run_id:archiveId,generation:1,candidate:'generation_best',timestamp:'2026-10-11T03:00:00Z',chromosome_id:'candidate'},overall_penalty:110,breakdown_available:true,recorded_component_sum:110,
      components:componentKeys.map(key=>({key,label:key==='teaching_load_balance'?'Teaching workload':key.replaceAll('_',' '),definition:'Recorded scorer definition',penalty:key==='teaching_load_balance'?75:key==='subject_preference'?35:0})),
      faculty:[{faculty:'Faculty 1',teaching_units:15,required_teaching_load:19,difference:-4,fulfillment_percent:15/19*100,admin_load:3,research_load:1,extension_load:1,workload_status:'underload',heavy_overload:false,workload_penalty:75,underload_steps:3,preparations:2,total_penalty:110,priority_multiplier:2,penalties:{teaching_load_balance:75,subject_preference:35},unavailable_reason:null,
        preferences:[{key:'subject_preference',status:'partially_satisfied',satisfaction_percent:50,importance:4,affects_fitness:true,penalty:35,matched:1,total:2,explanation:'Descriptive match; recorded penalty is separate.'},{key:'schedule_style',status:'disabled',satisfaction_percent:null,importance:0,affects_fitness:false,penalty:0,matched:0,total:0,explanation:'Schedule style disabled.'}]}],
      external_instructors:[{name:'Atty. Eddie Bouy Palad',subject:'ITE184',section:'4A',scoring:'Excluded from normal workload/preference scoring'}],
      definitions:{overall:'Overall penalty is the sum of eight recorded components; lower is better.',target:'24 minus administrative, research and extension releases.',actual:'Course units, not repeated meeting hours.',difference:'Actual minus target.',fulfillment:'100 times actual divided by target.',priority:'Importance and faculty priority affect recorded penalties.',indicators:'Descriptive indicators do not add to fitness.'},fitness_configuration:null,limitations:['Missing values are not invented.']};
    await client.send('Page.addScriptToEvaluateOnNewDocument',{source:`
      window.fitnessRequests=[]; const previousFitnessFetch=window.fetch.bind(window);
      window.fetch=async(input,options)=>{
        const url=String(input); if(!url.includes('fitness-analysis')&&!url.includes('fitness-comparison')) return previousFitnessFetch(input,options);
        window.fitnessRequests.push({url,method:options?.method??'GET'});
        if(sessionStorage.getItem('fitnessFailure')) return Response.json({detail:{code:'GA_REPORT_INVALID',message:'Stored components do not reconcile.'}},{status:422});
        const report=${JSON.stringify(fitnessFixture)}; const parsed=new URL(url);
        const tokens=parsed.pathname.split('/'); const position=tokens.indexOf('generations');
        const generation=position>=0?tokens[position+1]:undefined; report.source.generation=generation?Number(generation):1;
        report.source.candidate=parsed.searchParams.get('candidate')??'best_ever';
        if(report.source.candidate==='best_ever'){report.overall_penalty=100;report.recorded_component_sum=100;report.components.find(row=>row.key==='subject_preference').penalty=25;report.faculty[0].total_penalty=100;report.faculty[0].penalties.subject_preference=25;report.faculty[0].preferences[0].penalty=25;}
        if(url.includes('fitness-comparison')) return Response.json({schema_version:1,source:{run_id:report.source.run_id,left:0,right:1,candidate:report.source.candidate},overall_reduction:10,component_changes:report.components.map(row=>({key:row.key,label:row.label,before:null,after:row.penalty,reduction:null})),faculty_changes:[{faculty:'Faculty 1',before:{...report.faculty[0],teaching_units:12,fulfillment_percent:12/19*100},after:report.faculty[0]}],assignment_changes:[],explanation:'Missing observations cannot explain the numerical reduction.'});
        if(generation==='0'){report.breakdown_available=false;report.recorded_component_sum=null;report.components.forEach(row=>row.penalty=null);report.faculty.forEach(row=>{row.preferences=null;row.penalties={};row.workload_penalty=null;row.unavailable_reason='Original preference context was not captured.';});}
        if(url.includes('/export')) return new Response(parsed.searchParams.get('format')==='csv'?'run_id,generation,definition\\n'+report.source.run_id+',1,Recorded calculation definitions':JSON.stringify(report),{headers:{'content-type':parsed.searchParams.get('format')==='csv'?'text/csv':'application/json','content-disposition':'attachment; filename="fitness-report.'+parsed.searchParams.get('format')+'"'}});
        return Response.json(report);
      };
    `});
    await client.send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:join(profile,'downloads')});
    await t.test('latest saved fitness analysis retains its recorded convergence chart',async()=>{
      await client.send('Page.navigate',{url:'http://localhost:5188/admin/analysis?run='});
      await eventually(()=>evaluate(`document.body.textContent.includes('Recorded component sum: 100 = overall penalty 100') && !!document.querySelector('[data-testid="ga-convergence"]')`),'Latest saved analysis lost its convergence chart');
      assert.equal(await evaluate(`document.querySelector('select[aria-label="Analysis source"]').value`),'');
    });
    await t.test('fitness analysis shows original workload, decomposition and preference explanations',async()=>{
      await client.send('Page.navigate',{url:`http://localhost:5188/admin/analysis?run=${archiveId}&generation=1`});
      await eventually(()=>evaluate(`document.body.textContent.includes('Recorded component sum: 110 = overall penalty 110')`),'Fitness explanation did not load');
      assert.ok(await evaluate(`document.body.textContent.includes('Partially satisfied') && document.body.textContent.includes('Disabled') && document.body.textContent.includes('79%')===false`));
      assert.ok(await evaluate(`document.body.textContent.includes('78.95%') && document.body.textContent.includes('Atty. Eddie Bouy Palad') && !document.body.textContent.includes('external:eddie')`));
      assert.equal(await evaluate(`document.querySelector('select[aria-label="Analysis source"]').value`),archiveId);
      const shot=await client.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      await writeFile(new URL('../.cache/fitness-analysis-desktop.png',import.meta.url),Buffer.from(shot.data,'base64'));
    });
    await t.test('fitness filters and missing historical components remain explicit',async()=>{
      await evaluate(`var filter=document.querySelector('select[aria-label="Workload filter"]'); filter.value='on_target'; filter.dispatchEvent(new Event('change',{bubbles:true})); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('No faculty match these filters.')`),'Workload filter did not apply');
      await evaluate(`var filter=document.querySelector('select[aria-label="Workload filter"]'); filter.value='all'; filter.dispatchEvent(new Event('change',{bubbles:true})); var generation=document.querySelector('select[aria-label="Analysis generation"]'); generation.value='0'; generation.dispatchEvent(new Event('change',{bubbles:true})); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('This generation recorded a total only.') && document.body.textContent.includes('Original preference context was not captured.')`),'Missing history was displayed as a score');
      assert.equal(await evaluate(`document.body.textContent.includes('Recorded component sum:')`),false);
    });
    await t.test('fitness comparison and all four report downloads are read only',async()=>{
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Compare fitness outcomes').click(); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Not captured at both generations') && document.body.textContent.includes('10 lower (improved)')`),'Comparison invented component changes');
      for(const label of ['Export analysis CSV','Export analysis JSON','Export workload CSV','Export workload JSON']){
        await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)}).click(); true`);
        await eventually(()=>evaluate(`![...document.querySelectorAll('button')].find(button=>button.textContent.trim()===${JSON.stringify(label)}).disabled`),'Export never settled');
      }
      assert.equal(await evaluate(`window.fitnessRequests.filter(request=>request.url.includes('/export')).length`),4);
      assert.ok(await evaluate(`window.fitnessRequests.every(request=>request.method==='GET')`));
    });
    await t.test('fitness errors settle and refresh preserves source and generation',async()=>{
      await evaluate(`sessionStorage.setItem('fitnessFailure','true'); [...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='Refresh analysis').click(); true`);
      await eventually(()=>evaluate(`document.querySelector('[role="alert"]')?.textContent.includes('GA_REPORT_INVALID')`),'Invalid report error was hidden');
      await evaluate(`sessionStorage.removeItem('fitnessFailure'); true`); await client.send('Page.reload');
      await eventually(()=>evaluate(`document.body.textContent.includes('This generation recorded a total only.') && document.querySelector('select[aria-label="Analysis generation"]').value==='0'`),'Fitness refresh lost its source');
      assert.ok(await evaluate(`window.fitnessRequests.every(request=>request.method==='GET')`));
    });
    await client.send('Page.addScriptToEvaluateOnNewDocument',{source:`
      const loadedNative=window.fetch.bind(window); window.loadedAnalysisRequests=0;
      window.fetch=async(input,options)=>{
        const url=String(input);
        if(url.endsWith('/api/chromosomes/best/analyze')){window.loadedAnalysisRequests++;return Response.json({status:'success',data:{best_fitness:110,fitness_breakdown:${JSON.stringify(Object.fromEntries(fitnessFixture.components.map(row=>[row.key,row.penalty])))},result_source:'loaded_chromosome',optimization_performed:false,loaded_chromosome_source:'saved',schedule:${JSON.stringify(archive.schedule)},history:[],generations_completed:0,population_size:0,faculty_analysis:{faculty:[{Faculty_Code:7,Teaching_Load:15,Preparations:2,Total_Penalty:110,Subject_Penalty:35,Load_Balance_Penalty:75,Subject_Satisfaction:50,Subject_Importance:4}],daily_load:[],summary:{total_fitness:110}}}});}
        if(url.endsWith('/api/chromosomes/best'))return Response.json({status:'success',data:{exists:true,fitness:110,created_at:'2026-10-11T03:00:00Z'}});
        return loadedNative(input,options);
      };
    `});
    await t.test('loaded candidate analysis retains original evaluation without extra scoring requests',async()=>{
      await client.send('Page.navigate',{url:'http://localhost:5188/admin/chromosomes'});
      await eventually(()=>evaluate(`!![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='View Results Only'&&!button.disabled)`),'Existing saved-candidate viewing button missing');
      await evaluate(`[...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='View Results Only').click(); true`);
      await eventually(()=>evaluate(`window.location.pathname==='/admin/schedules'`),'Existing load workflow did not complete');
      await evaluate(`document.querySelector('a[href="/admin/analysis"]').click(); true`);
      await eventually(()=>evaluate(`document.body.textContent.includes('Loaded candidate - original evaluation; no optimization ran') && document.querySelector('select[aria-label="Analysis source"]').value==='loaded'`),'Loaded evaluation was replaced by a saved run');
      assert.equal(await evaluate('window.loadedAnalysisRequests'),1);
      assert.equal(await evaluate('window.fitnessRequests.length'),0);
      assert.ok(await evaluate(`document.body.textContent.includes('Partially satisfied') && document.body.textContent.includes('Teaching targets, release details')`));
    });
    await client.send('Page.addScriptToEvaluateOnNewDocument', {source: `
      const auditFetch = window.fetch.bind(window);
      window.fetch = (input, options) => String(input).endsWith('/api/faculty/')
        ? Promise.resolve(Response.json({data: [{faculty_code:7,display_code:'Faculty 7'},{faculty_code:8,display_code:'Faculty 8'}]})) : auditFetch(input, options);
    `});
    const auditSchedule = [
      {subject:'CCC121',title:'Data Structures',type:'Lecture',day:'M',start:'09:00',end:'11:00',section:'3A',faculty:'7.0',room:'ICT 3A'},
      {subject:'ITE184',title:'Social Legal and Professional Issues in Computing',type:'Lecture',day:'W',start:'12:00',end:'13:30',section:'4A',faculty:'external:eddie-bouy-palad',faculty_name:'Atty. Eddie Bouy Palad',assignment_type:'preassigned_external',room:'ICT 3A'},
    ];
    await evaluate(`sessionStorage.setItem('mockLatestGA', ${JSON.stringify(JSON.stringify({...result,schedule:auditSchedule}))}); sessionStorage.removeItem('mockActiveRun'); sessionStorage.removeItem('mockTerminalRun'); sessionStorage.setItem('mockPausedRuns','[]'); true`);
    await t.test('audit faculty selector hides internal external IDs and normalizes numeric faculty codes', async () => {
      await client.send('Page.navigate', {url:'http://localhost:5188/admin/faculty'});
      await eventually(() => evaluate(`document.querySelector('main select')?.options.length===2`), 'Faculty schedule did not load');
      const labels = await evaluate(`[...document.querySelector('main select').options].map(option=>option.textContent)`);
      assert.ok(labels.includes('Faculty 7'));
      assert.ok(labels.some(label=>label.includes('Atty. Eddie Bouy Palad') && label.includes('Preassigned Instructor')));
      assert.ok(labels.every(label=>!label.includes('external:')));
    });
    await t.test('audit room calendar uses readable preassigned instructor names', async () => {
      await client.send('Page.navigate', {url:'http://localhost:5188/admin/rooms'});
      await eventually(() => evaluate(`document.querySelector('main')?.textContent.includes('ITE184')`), 'Room schedule did not load');
      const text = await evaluate(`document.querySelector('main').textContent`);
      assert.ok(text.includes('Atty. Eddie Bouy Palad') && text.includes('Faculty 7'));
      assert.ok(!text.includes('external:eddie-bouy-palad'));
    });
    await t.test('audit schedule table and filters hide internal instructor IDs', async () => {
      await client.send('Page.navigate', {url:'http://localhost:5188/admin/schedules'});
      await eventually(() => evaluate(`document.querySelector('main tbody')?.textContent.includes('ITE184')`), 'Schedule table did not load');
      const text = await evaluate(`document.querySelector('main').textContent`);
      assert.ok(text.includes('Atty. Eddie Bouy Palad') && text.includes('Faculty 7'));
      assert.ok(!text.includes('external:eddie-bouy-palad'));
    });
    await t.test('audit metadata faculty filter matches schedule IDs and includes external instructors', async () => {
      await evaluate(`var selector=document.querySelector('main select'); var option=[...selector.options].find(option=>option.textContent.trim()==='Faculty 7'); selector.value=option.value; selector.dispatchEvent(new Event('change',{bubbles:true})); true`);
      await eventually(() => evaluate(`document.querySelector('main tbody')?.textContent.includes('CCC121') && !document.querySelector('main tbody')?.textContent.includes('ITE184')`), 'Faculty metadata label did not match schedule identity');
      await evaluate(`var selector=document.querySelector('main select'); var option=[...selector.options].find(option=>option.textContent.includes('Atty. Eddie Bouy Palad')); if(!option) throw new Error('External instructor missing from schedule filter'); selector.value=option.value; selector.dispatchEvent(new Event('change',{bubbles:true})); true`);
      await eventually(() => evaluate(`document.querySelector('main tbody')?.textContent.includes('ITE184') && !document.querySelector('main tbody')?.textContent.includes('CCC121')`), 'External filter did not match its assignment');
    });
    await t.test('audit subject management and faculty portal routes are still placeholders', async () => {
      for (const path of ['/admin/subjects','/faculty/schedule','/faculty/profile']) {
        await client.send('Page.navigate', {url:'http://localhost:5188'+path});
        await eventually(() => evaluate(`document.querySelector('main')?.textContent.includes('This page will be built next.')`), `${path} placeholder not reproduced`);
      }
      await client.send('Page.navigate', {url:'http://localhost:5188/faculty'});
      await eventually(() => evaluate(`document.querySelector('main')?.textContent.trim()==='Faculty Dashboard'`), 'Faculty dashboard placeholder not reproduced');
    });
    assert.deepEqual(errors, []);
  } finally {
    socket?.close(); edge.kill(); vite.kill();
    await Promise.race([pause(3000), Promise.all([new Promise(resolve => edge.exitCode !== null || edge.signalCode !== null ? resolve() : edge.once('exit',resolve)), new Promise(resolve => vite.exitCode !== null || vite.signalCode !== null ? resolve() : vite.once('exit',resolve))])]);
    const target = resolve(profile);
    assert.ok(target.startsWith(resolve(tmpdir()) + sep) && basename(target).startsWith('ga-monitoring-browser-'));
    await rm(target, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
});
