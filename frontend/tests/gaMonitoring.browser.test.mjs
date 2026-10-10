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

test("Live GA dashboard updates before final result and distinguishes disconnect", { timeout: 90000 }, async t => {
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
      window.mockStateError = false;
      window.mockLegacyBackend = false;
      window.fetch = async (input, options) => {
        const url = String(input);
        const processId = sessionStorage.getItem('mockProcessId') ?? 'browser-process';
        if (url.endsWith('/api/ga/status')) return Response.json(window.mockLegacyBackend ? {status:'ready'} : {control_version:'3c.1',process_instance_id:processId,active_run:JSON.parse(sessionStorage.getItem('mockActiveRun') ?? 'null')});
        if (url.includes('/api/ga/runs/') && !url.endsWith('/stop') && !url.endsWith('/result')) {
          if (window.mockStateError) throw new Error('Status connection lost');
          const snapshot = JSON.parse(sessionStorage.getItem('mockActiveRun') ?? sessionStorage.getItem('mockTerminalRun') ?? 'null');
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
        if (url.includes('/api/ga/latest')) { const latest = sessionStorage.getItem('mockLatestGA'); return latest ? Response.json({status:'success',data:JSON.parse(latest)}) : new Response('',{status:404}); }
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
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Stop requested') && window.mockStopRequests.length===1`), "Stop request was not sent");
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
      await client.send("Page.reload");
      await eventually(() => evaluate(`document.querySelector('[data-testid="ga-run-id"]')?.textContent==='browser-run' && !![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Stop Generation' && !button.disabled)`), "Active worker not recovered");
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
    assert.deepEqual(errors, []);
  } finally {
    socket?.close(); edge.kill(); vite.kill();
    await Promise.race([pause(3000), Promise.all([new Promise(resolve => edge.exitCode !== null || edge.signalCode !== null ? resolve() : edge.once('exit',resolve)), new Promise(resolve => vite.exitCode !== null || vite.signalCode !== null ? resolve() : vite.once('exit',resolve))])]);
    const target = resolve(profile);
    assert.ok(target.startsWith(resolve(tmpdir()) + sep) && basename(target).startsWith('ga-monitoring-browser-'));
    await rm(target, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
});
