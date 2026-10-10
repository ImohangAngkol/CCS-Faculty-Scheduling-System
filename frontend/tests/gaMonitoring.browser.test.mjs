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
      window.fetch = async (input, options) => {
        const url = String(input);
        if (url.includes('/api/ga/stream')) return new Response(new ReadableStream({ start(controller) { window.mockGAController = controller; } }), { headers: { 'Content-Type': 'text/event-stream' } });
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
      const payload = { schema_version: 1, run_id: "browser-run", sequence: ++sequence, type, timestamp: "2026-10-10T03:00:00Z", data };
      await evaluate(`window.mockGAController.enqueue(new TextEncoder().encode(${JSON.stringify('data: '+JSON.stringify(payload)+'\r\n\r\n')})); true`);
    }
    await client.send("Page.navigate", { url: "http://localhost:5188/admin/generate" });
    await eventually(() => evaluate(`!![...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule')`), "Generate button missing");
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
    await t.test("disconnect is explicitly unknown execution, never stopped", async () => {
      await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.trim()==='Generate Schedule').click(); true`);
      await eventually(() => evaluate("!!window.mockGAController"), "Second stream missing");
      sequence = 0;
      await send("run_started", { status: "RUNNING" });
      await send("initial_population_ready", metrics(0));
      await evaluate("window.mockGAController.close(); true");
      await eventually(() => evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Monitoring disconnected')`), "Disconnect status missing");
      assert.ok(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('server may still be running')`));
      assert.equal(await evaluate(`document.querySelector('[data-testid="live-ga-monitor"]').textContent.includes('Stopped')`), false);
      await client.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
      await eventually(() => evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile overflow");
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
