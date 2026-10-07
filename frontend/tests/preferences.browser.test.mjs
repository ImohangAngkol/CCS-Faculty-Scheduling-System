// Real DOM and FullCalendar interaction checks, using a local headless browser.
// API fixtures isolate writes; backend contract tests separately check real persistence.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join, resolve, sep } from "node:path";
import { faculty, subjects, preference } from "./preferenceFixtures.mjs";

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
    send: (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); }),
  };
}

test("Faculty Preferences browser interactions", { timeout: 120000 }, async t => {
  const profile = await mkdtemp(join(tmpdir(), "faculty-preference-browser-"));
  const frontend = new URL("../", import.meta.url);
  const vite = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "--host", "localhost", "--port", "5187", "--strictPort"], { cwd: frontend, windowsHide: true, stdio: "pipe" });
  let serverOutput = ""; vite.stdout.on("data", data => { serverOutput += data; }); vite.stderr.on("data", data => { serverOutput += data; });
  const executable = process.env.PREFERENCE_TEST_BROWSER ?? (process.platform === "win32" ? "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" : "chromium");
  const edge = spawn(executable, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=9226", `--user-data-dir=${profile}`, "about:blank"], { windowsHide: true, stdio: "ignore" });
  let launchError = null; edge.on("error", error => { launchError = error; });
  let socket;
  try {
    await eventually(async () => (await fetch("http://localhost:5187")).ok, `Vite did not start: ${serverOutput}`);
    const targets = await eventually(async () => { if (launchError) throw launchError; return await (await fetch("http://127.0.0.1:9226/json/list")).json(); }, "Headless browser did not start. Set PREFERENCE_TEST_BROWSER to an installed Chromium browser.");
    socket = new WebSocket(targets.find(target => target.type === "page").webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    const client = cdp(socket);
    const errors = [];
    client.on("Runtime.exceptionThrown", event => errors.push(event.exceptionDetails.text));
    const saved = new Map(faculty.map(row => [row.faculty_code, { faculty_code: row.faculty_code, ...structuredClone(preference) }]));
    let failSave = false, lastWrite = null;
    client.on("Fetch.requestPaused", async ({ requestId, request }) => {
      try {
        const url = new URL(request.url); let status = 200, data = {};
        if (request.method === "OPTIONS") data = {};
        else if (url.pathname === "/api/faculty/") data = { data: [...faculty, { faculty_id: "outside-pool", faculty_code: 99, display_code: "Atty. Eddie Bouy Palad", instructor_type: "preassigned_external" }] };
        else if (url.pathname.endsWith("/eligible-subjects")) {
          const row = faculty.find(item => url.pathname.includes(item.faculty_id) || url.pathname.includes(`/${item.faculty_code}/`));
          const all = subjects.map(subject => ({ ...subject, eligibility: { explicitly_eligible: row.eligible_subject_codes.includes(subject.subject_code) }, offerings: [{ can_be_assigned: row.eligible_subject_codes.includes(subject.subject_code), is_preassigned: false }] }));
          data = { faculty: row, eligible_only: url.searchParams.get("eligible_only") !== "false", data: url.searchParams.get("eligible_only") === "false" ? all : all.filter(item => item.eligibility.explicitly_eligible) };
        } else if (url.pathname.startsWith("/preferences/")) {
          const code = Number(url.pathname.split("/").at(-1));
          if (request.method === "PUT") {
            lastWrite = JSON.parse(request.postData); await pause(120);
            if (failSave) { status = 500; data = { detail: "Test save failed" }; }
            else { saved.set(code, { faculty_code: code, ...lastWrite }); data = saved.get(code); }
          } else data = saved.get(code);
        }
        await client.send("Fetch.fulfillRequest", { requestId, responseCode: status, responseHeaders: [{ name: "Content-Type", value: "application/json" }, { name: "Access-Control-Allow-Origin", value: "http://localhost:5187" }, { name: "Access-Control-Allow-Headers", value: "content-type" }, { name: "Access-Control-Allow-Methods", value: "GET, PUT, OPTIONS" }], body: Buffer.from(JSON.stringify(data)).toString("base64") });
      } catch (error) { errors.push(String(error)); await client.send("Fetch.failRequest", { requestId, errorReason: "Failed" }); }
    });
    await client.send("Runtime.enable"); await client.send("Page.enable");
    await client.send("Fetch.enable", { patterns: [{ urlPattern: "http://127.0.0.1:8000/*", requestStage: "Request" }] });
    await client.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    const evaluate = async expression => {
      const result = await client.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
      return result.result.value;
    };
    async function ready() {
      await eventually(() => evaluate(`!!document.querySelector('.preference-save-bar')`), "Preference editor did not load");
      await evaluate(`window.ui = {
        button: (name) => [...document.querySelectorAll('button')].find(el => el.getAttribute('aria-label') === name || el.textContent.trim() === name),
        field: (name) => [...document.querySelectorAll('label')].find(el => [...el.childNodes].filter(node => node.nodeType === 3).map(node => node.textContent).join('').trim() === name)?.querySelector('input,select'),
        set: (el, value) => { if (!el) throw Error('Field missing'); Object.getOwnPropertyDescriptor(el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value').set.call(el, value); el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', {bubbles:true})); },
        status: () => document.querySelector('.preference-save-bar [role=status]').textContent
      }; true`);
    }
    const click = name => evaluate(`ui.button(${JSON.stringify(name)}).click(); true`);
    const set = (name, value) => evaluate(`ui.set(ui.field(${JSON.stringify(name)}), ${JSON.stringify(value)}); true`);
    const status = value => eventually(() => evaluate(`ui.status() === ${JSON.stringify(value)}`), `Expected save state ${value}`);
    const navigate = async path => { await client.send("Page.navigate", { url: `http://localhost:5187${path}` }); await ready(); };
    const sourceSelector = (code, type, meetingDay = "") => `.preference-component-drag[data-subject-code="${code}"][data-component-type="${type}"][data-meeting-day="${meetingDay}"]`;
    async function pointerDrag(box) {
      await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y });
      await client.send("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", buttons: 1, clickCount: 1 });
      for (let step = 1; step <= 10; step++) {
        await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x + (box.targetX - box.x) * step / 10, y: box.y + (box.targetY - box.y) * step / 10, buttons: 1 });
        await pause(40);
      }
      await client.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.targetX, y: box.targetY, button: "left", clickCount: 1 });
      await pause(100);
    }
    async function dragSource(code, type, targetDate, targetTime, meetingDay = "") {
      const selector = sourceSelector(code, type, meetingDay);
      const box = await evaluate(`document.getElementById('preference-section-2').scrollIntoView({block:'start'});
        var row = document.querySelector('.fc-timegrid-slots [data-time="${targetTime}:00"]');
        var scroller = row.closest('.fc-scroller'); scroller.scrollTop += row.getBoundingClientRect().top - scroller.getBoundingClientRect().top - 60;
        window.scrollBy(0, Math.max(0, row.getBoundingClientRect().top + 3 - (window.innerHeight - 110)));
        var source = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();
        var target = document.querySelector('.fc-timegrid-col[data-date="${targetDate}"]').getBoundingClientRect(); var slot = row.getBoundingClientRect();
        ({x:source.x+source.width/2,y:source.y+20,targetX:target.x+target.width/2,targetY:slot.top+3})`);
      assert.ok(box.y >= 0 && box.targetY < 840, `Source and target must be visible for a real pointer drag: ${JSON.stringify(box)}`);
      await pointerDrag(box);
    }
    await navigate("/admin/preferences");

    await t.test("private selector, eligibility, categories, search, ineligible disabled", async () => {
      assert.deepEqual(await evaluate(`[...ui.field('Select faculty').options].map(el => el.textContent)`), ["Faculty 0", "Faculty 1"]);
      assert.equal(await evaluate(`document.body.textContent.includes('Palad') || document.body.textContent.includes('stable-faculty')`), false);
      assert.equal(await evaluate(`document.querySelectorAll('.preference-subject-browser li').length`), 3);
      await click("ITD"); assert.equal(await evaluate(`document.querySelectorAll('.preference-subject-browser li').length`), 1);
      await click("ALL"); await set("Find a subject", "Foundations"); assert.equal(await evaluate(`document.querySelectorAll('.preference-subject-browser li').length`), 1);
      await set("Find a subject", "");
      await evaluate(`[...document.querySelectorAll('label')].find(el=>el.textContent.includes('Show all offered subjects')).querySelector('input').click(); true`);
      await eventually(() => evaluate(`!!ui.button('Add ITE184 to preferred subjects')`), "All courses did not load");
      assert.equal(await evaluate(`ui.button('Add ITE184 to preferred subjects').disabled`), true);
    });
    await t.test("one ranked list and synchronized dropdown and drag order", async () => {
      await click("Add CCC100 to preferred subjects"); await click("Add ITD105 to preferred subjects"); await click("Add ITN102 to preferred subjects");
      await status("Unsaved changes");
      await evaluate(`ui.set(document.getElementById('rank-ITN102'),'1'); true`);
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('[id^=rank-]')].map(el=>el.id)`), ["rank-ITN102", "rank-CCC100", "rank-ITD105"]);
      await evaluate(`var data = new DataTransfer(); data.setData('text/plain','ITD105'); document.getElementById('rank-ITN102').closest('li').dispatchEvent(new DragEvent('drop',{bubbles:true,dataTransfer:data})); true`);
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('[id^=rank-]')].map(el=>[el.id,el.value])`), [["rank-ITD105", "1"], ["rank-ITN102", "2"], ["rank-CCC100", "3"]]);
      assert.equal(await evaluate(`!!ui.button('Add ITD105 Laboratory preference') || !!ui.button('Add ITN102 Lecture preference')`), false);
      assert.equal(await evaluate(`ui.button('Add CCC100 Laboratory preference').parentElement.textContent.includes('3 hours')`), true);
    });
    await t.test("dragging a lecture source uses the dropped start and backend two-hour duration", async () => {
      await dragSource("CCC100", "Lecture", "2026-09-28", "10:30");
      await eventually(() => evaluate(`!!document.querySelector('details') && document.querySelector('details').textContent.includes('Monday · 10:30–12:30')`), "Lecture drop did not use its exact start and duration");
      await evaluate(`document.querySelector('details').open=true; true`);
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC100", "Lecture"))}).dataset.componentDrag`), "false");
    });
    await t.test("completed sources reject duplicate drags; existing lecture moves without resizing", async () => {
      await dragSource("CCC100", "Lecture", "2026-09-29", "10:30");
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event').length`), 1);
      assert.equal(await evaluate(`document.querySelector('.preference-component-card[data-subject-code="CCC100"][data-component-type="Lecture"] button').disabled`), true);
      const box = await evaluate(`var event=document.querySelector('.fc-event'); event.scrollIntoView({block:'center'}); var rect=event.getBoundingClientRect(); var col=document.querySelector('.fc-timegrid-col[data-date="2026-09-30"]').getBoundingClientRect(); ({x:rect.x+rect.width/2,y:rect.y+12,targetX:col.x+col.width/2,targetY:rect.y+12})`);
      await pointerDrag(box);
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Wednesday · 10:30–12:30')`), "Dragging lecture changed its two-hour duration");
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event-resizer').length`), 0);
      await click("Move CCC100 Lecture on Wednesday"); assert.equal(await evaluate(`!!ui.field('End time')`), false);
      await set("Start time", "13:00"); await click("Move preference");
      assert.equal(await evaluate(`document.querySelector('details').textContent.includes('Wednesday · 13:00–15:00')`), true);
    });
    await t.test("removing a placement re-enables its source and a fresh drop works", async () => {
      await click("Remove CCC100 Lecture preference");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC100", "Lecture"))}).dataset.componentDrag`), "true");
      assert.equal(await evaluate(`ui.button('Add CCC100 Lecture preference').disabled`), false);
      await dragSource("CCC100", "Lecture", "2026-09-28", "10:30");
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Monday · 10:30–12:30')`), "Re-enabled source failed to place");
      await click("Remove CCC100 Lecture preference");
    });
    await t.test("dragging lab creates one continuous 180-minute block, locked during moves", async () => {
      await dragSource("CCC100", "Laboratory", "2026-09-29", "13:00");
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Tuesday · 13:00–16:00')`), "Laboratory drop did not use 180 minutes");
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event-resizer').length`), 0);
      assert.equal(await evaluate(`document.querySelector('.fc-event').textContent.includes('CCC100')`), true);
      await evaluate(`document.querySelector('details').open=true; true`);
      await click("Move CCC100 Laboratory on Tuesday");
      assert.equal(await evaluate(`!!ui.field('End time')`), false);
      await set("Day", "W"); await set("Start time", "14:00"); await click("Move preference");
      assert.equal(await evaluate(`document.querySelector('details').textContent.includes('Wednesday · 14:00–17:00')`), true);
    });
    await t.test("explicit multi-pattern choice and complete independently movable meetings", async () => {
      assert.equal(await evaluate(`document.querySelectorAll('.preference-component-drag[data-subject-code="ITD105"][data-component-drag="true"]').length`), 0);
      await click("Add ITD105 Lecture preference");
      assert.equal(await evaluate(`ui.field('Meeting pattern').value`), "");
      await set("Meeting pattern", "1"); await set("Meeting days", "0"); await set("Start time", "08:00"); await click("Add preference");
      await click("Move ITD105 Lecture on Monday"); await set("Start time", "09:00"); await click("Move preference");
      assert.equal(await evaluate(`!!ui.button('Add general preferred period').closest('[data-component-drag]')`), false);
      await evaluate(`document.getElementById('preference-section-2').scrollIntoView({block:'start'}); true`);
      await mkdir(new URL("../.cache", import.meta.url), { recursive: true });
      const shot = await client.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      await writeFile(new URL("../.cache/preferences-drag-cards.png", import.meta.url), Buffer.from(shot.data, "base64"));
      assert.equal(await evaluate(`document.querySelector('details').textContent.includes('Monday · 09:00–10:30') && document.querySelector('details').textContent.includes('Thursday · 08:00–09:30')`), true);
    });
    await t.test("selected multi-meeting source cards place one complete fixed-duration pair", async () => {
      await click("Remove ITD105 Lecture preference");
      await set("Meeting pattern for ITD105 Lecture", "0");
      assert.equal(await evaluate(`document.querySelector('.preference-component-drag[data-subject-code="ITD105"]').dataset.duration`), "180");
      await set("Meeting pattern for ITD105 Lecture", "1");
      assert.equal(await evaluate(`document.querySelectorAll('.preference-component-drag[data-subject-code="ITD105"][data-component-drag="true"]').length`), 0);
      await set("Meeting days for ITD105 Lecture", "0");
      assert.equal(await evaluate(`document.querySelectorAll('.preference-component-drag[data-subject-code="ITD105"][data-component-drag="true"]').length`), 2);
      await dragSource("ITD105", "Lecture", "2026-09-28", "08:00", "M");
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Monday · 08:00–09:30') && document.querySelector('details').textContent.includes('Thursday · 08:00–09:30')`), "Dragging paired card did not create both fixed meetings");
      assert.equal(await evaluate(`document.querySelectorAll('.preference-component-drag[data-subject-code="ITD105"][data-component-drag="true"]').length`), 0);
      await dragSource("ITD105", "Lecture", "2026-10-01", "10:30", "TH");
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event').length`), 3);
      await click("Move ITD105 Lecture on Monday"); await set("Start time", "09:00"); await click("Move preference");
    });
    await t.test("actual calendar pointer dragging preserves the three-hour laboratory", async () => {
      const box = await evaluate(`var event = [...document.querySelectorAll('.fc-event')].find(el=>el.textContent.includes('CCC100')); event.scrollIntoView({block:'center'}); var rect=event.getBoundingClientRect(); var target=document.querySelector('.fc-timegrid-col[data-date="2026-10-01"]').getBoundingClientRect(); ({x:rect.x+rect.width/2,y:rect.y+12,targetX:target.x+target.width/2})`);
      await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y });
      await client.send("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", buttons: 1, clickCount: 1 });
      for (let step = 1; step <= 6; step++) { await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x + (box.targetX - box.x) * step / 6, y: box.y, buttons: 1 }); await pause(40); }
      await client.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.targetX, y: box.y, button: "left", clickCount: 1 });
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Thursday · 14:00–17:00')`), "Dragged laboratory did not preserve duration");
    });
    await t.test("importance visibility, internal labels and legacy zero", async () => {
      assert.equal(await evaluate(`!!ui.field('Schedule style importance')`), false);
      await evaluate(`[...document.querySelectorAll('input[name=schedule-style]')].find(el=>el.value==='Scattered').click(); true`);
      assert.equal(await evaluate(`ui.field('Schedule style importance').selectedOptions[0].textContent`), "No weight / informational only");
      await evaluate(`[...document.querySelectorAll('input[name=lecture-lab]')].find(el=>el.value==='Different Day').click(); true`);
      assert.equal(await evaluate(`ui.field('Lecture and laboratory preference importance').value`), "0");
    });
    await t.test("faculty switching confirms dirty state and cancel preserves draft", async () => {
      let prompt = null;
      client.on("Page.javascriptDialogOpening", event => { prompt = event.message; void client.send("Page.handleJavaScriptDialog", { accept: false }); });
      await set("Select faculty", "stable-faculty-1");
      await eventually(() => prompt, "No unsaved change prompt");
      assert.match(prompt, /Discard unsaved/);
      assert.equal(await evaluate(`ui.field('Select faculty').value`), "stable-faculty-0");
    });
    await t.test("failure retains draft, retry saves and reload persists payload", async () => {
      failSave = true; await click("Save Preferences"); await status("Saving…");
      assert.equal(await evaluate(`ui.field('Select faculty').disabled`), true);
      await status("Save failed"); assert.equal(await evaluate(`document.querySelectorAll('[id^=rank-]').length`), 3);
      failSave = false; await click("Save Preferences"); await status("Saved");
      assert.equal(lastWrite.faculty_priority, 3); assert.equal(lastWrite.gap_preference, "Scattered"); assert.equal(lastWrite.gap_importance, 0);
      assert.equal(lastWrite.preferred_schedule_blocks.filter(b=>b.component==='Lecture').length, 2);
      assert.equal(lastWrite.preferred_schedule_blocks.find(b=>b.component==='Laboratory').end_time, "17:00");
      await navigate("/admin/preferences"); await status("No changes"); assert.equal(await evaluate(`document.querySelectorAll('[id^=rank-]').length`), 3);
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC100", "Laboratory"))}).dataset.componentDrag`), "false");
      assert.equal(await evaluate(`ui.field('Meeting pattern for ITD105 Lecture').value`), "1");
    });
    await t.test("discard restores baseline and each faculty loads its own eligibility", async () => {
      await click("Remove CCC100 from preferred subjects"); await status("Unsaved changes"); await click("Discard"); await status("No changes");
      await set("Select faculty", "stable-faculty-1"); await eventually(() => evaluate(`document.querySelectorAll('.preference-subject-browser li').length===1`), "Faculty-specific eligibility did not change");
      assert.equal(await evaluate(`document.querySelector('.preference-subject-browser').textContent.includes('ITD105')`), true);
    });
    await t.test("smaller laptop has a readable form and visible sticky save bar", async () => {
      await client.send("Emulation.setDeviceMetricsOverride", { width: 1024, height: 768, deviceScaleFactor: 1, mobile: false });
      assert.equal(await evaluate(`document.querySelector('.preference-section').getBoundingClientRect().width > 650`), true);
      assert.equal(await evaluate(`getComputedStyle(document.querySelector('.preference-save-bar')).position`), "sticky");
      await mkdir(new URL("../.cache", import.meta.url), { recursive: true });
      const shot = await client.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      await writeFile(new URL("../.cache/preferences-laptop.png", import.meta.url), Buffer.from(shot.data, "base64"));
    });
    await t.test("faculty self-service hides priority; small viewport has no horizontal overflow", async () => {
      await navigate("/faculty/preferences"); assert.equal(await evaluate(`!!ui.field('Faculty priority') || !!ui.field('Select faculty')`), false);
      await client.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
      await pause(100);
      assert.equal(await evaluate(`document.documentElement.scrollWidth <= window.innerWidth`), true);
      assert.equal(await evaluate(`document.querySelector('.preference-section').getBoundingClientRect().width >= 350`), true);
      await mkdir(new URL("../.cache", import.meta.url), { recursive: true });
      const shot = await client.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      await writeFile(new URL("../.cache/preferences-mobile.png", import.meta.url), Buffer.from(shot.data, "base64"));
    });
    assert.deepEqual(errors, [], "Browser console/runtime errors");
  } finally {
    socket?.close(); edge.kill(); vite.kill();
    await Promise.race([pause(3000), Promise.all([new Promise(resolve => edge.exitCode !== null || edge.signalCode !== null ? resolve() : edge.once("exit", resolve)), new Promise(resolve => vite.exitCode !== null || vite.signalCode !== null ? resolve() : vite.once("exit", resolve))])]);
    // Only the verified, unique temporary browser profile is removed.
    assert.ok(resolve(profile).startsWith(resolve(tmpdir()) + sep) && basename(profile).startsWith("faculty-preference-browser-"), "Unexpected browser cleanup target");
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
  }
});
