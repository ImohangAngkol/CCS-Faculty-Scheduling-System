// Real DOM and FullCalendar interaction checks, using a local headless browser.
// API fixtures isolate writes; backend contract tests separately check real persistence.
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join, resolve, sep } from "node:path";
import { faculty as fixtureFaculty, subjects as fixtureSubjects, preference } from "./preferenceFixtures.mjs";

// Use the requested CCC121 example without changing shared model fixtures or real metadata.
const faculty = fixtureFaculty.map(row => ({ ...row, eligible_subject_codes: row.eligible_subject_codes.map(code => code === "CCC100" ? "CCC121" : code) }));
const subjects = fixtureSubjects.map(subject => subject.subject_code === "CCC100" ? { ...subject, course_id: "course-CCC121", subject_code: "CCC121", subject_title: "Data Structures and Algorithms" } : subject);

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
        field: (name) => [...document.querySelectorAll('input,select')].find(el => el.getAttribute('aria-label') === name) ?? [...document.querySelectorAll('label')].find(el => [...el.childNodes].filter(node => node.nodeType === 3).map(node => node.textContent).join('').trim() === name)?.querySelector('input,select'),
        set: (el, value) => { if (!el) throw Error('Field missing'); Object.getOwnPropertyDescriptor(el.tagName === 'SELECT' ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value').set.call(el, value); el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', {bubbles:true})); },
        status: () => document.querySelector('.preference-save-bar [role=status]').textContent
      }; true`);
    }
    const click = name => evaluate(`ui.button(${JSON.stringify(name)}).click(); true`);
    const set = (name, value) => evaluate(`ui.set(ui.field(${JSON.stringify(name)}), ${JSON.stringify(value)}); true`);
    const status = value => eventually(() => evaluate(`ui.status() === ${JSON.stringify(value)}`), `Expected save state ${value}`);
    const navigate = async path => { await client.send("Page.navigate", { url: `http://localhost:5187${path}` }); await ready(); };
    const sourceSelector = (code, type, meetingDay = "") => `.preference-component-drag[data-subject-code="${code}"][data-component-type="${type}"][data-meeting-day="${meetingDay}"]`;
    async function dragToSlot(selector, targetDate, targetTime, slotFraction = 0.1) {
      let box = await evaluate(`var element=document.querySelector(${JSON.stringify(selector)});
        if(element.classList.contains('preference-component-drag')) document.getElementById('preference-section-2').scrollIntoView({block:'start'});
        else element.scrollIntoView({block:'center'});
        var rect=element.getBoundingClientRect(); var slot=document.querySelector('.fc-timegrid-slots [data-time="${targetTime}:00"]').getBoundingClientRect(); var col=document.querySelector('.fc-timegrid-col[data-date="${targetDate}"]').getBoundingClientRect();
        ({x:rect.x+rect.width/2,y:rect.y+20,targetX:col.x+col.width/2,targetY:slot.top+slot.height*${slotFraction}})`);
      assert.ok(box.y >= 0 && box.y < 840, `Real pointer drag must begin at a visible source: ${JSON.stringify(box)}`);
      await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y });
      await client.send("Input.dispatchMouseEvent", { type: "mousePressed", x: box.x, y: box.y, button: "left", buttons: 1, clickCount: 1 });
      if (box.targetY > 760 || box.targetY < 100) {
        await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x+10, y: box.y+10, buttons: 1 });
        const edgeY = box.targetY > 760 ? 895 : 5;
        await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.targetX, y: edgeY, buttons: 1 });
        await eventually(() => evaluate(`var rect=document.querySelector('.fc-timegrid-slots [data-time="${targetTime}:00"]').getBoundingClientRect(); rect.top>=100 && rect.bottom<=740`), "Page auto-scrolling did not reveal the drop row");
        const targetY = await evaluate(`var rect=document.querySelector('.fc-timegrid-slots [data-time="${targetTime}:00"]').getBoundingClientRect(); rect.top+rect.height*${slotFraction}`);
        await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.targetX, y: targetY, buttons: 1 });
        box = { x: box.targetX, y: targetY, targetX: box.targetX, targetY };
      }
      for (let step = 1; step <= 10; step++) {
        await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x + (box.targetX - box.x) * step / 10, y: box.y + (box.targetY - box.y) * step / 10, buttons: 1 });
        await pause(40);
      }
      await client.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.targetX, y: box.targetY, button: "left", clickCount: 1 });
      await pause(100);
    }
    const dragSource = (code, type, date, time, meetingDay = "", fraction = 0.1) => dragToSlot(sourceSelector(code, type, meetingDay), date, time, fraction);
    async function assertEventRows(count, type = "Lecture") {
      const size = await evaluate(`({event:[...document.querySelectorAll('.fc-event:not(.fc-event-mirror)')].find(el=>el.textContent.includes(${JSON.stringify(type)})).getBoundingClientRect().height,row:document.querySelector('.fc-timegrid-slot').getBoundingClientRect().height})`);
      assert.ok(Math.abs(size.event - size.row * count) <= 3, `Event must span ${count} half-hour rows: ${JSON.stringify(size)}`);
    }
    async function captureSchedule(filename) {
      // A tall viewport captures the entire section without the sticky save bar covering rows.
      await client.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 2200, deviceScaleFactor: 1, mobile: false });
      const wasOpen = await evaluate(`document.querySelector('.preference-meeting-controls').open`);
      await evaluate(`document.querySelector('.preference-meeting-controls').open=false; document.getElementById('preference-section-2').closest('section').scrollIntoView({block:'start'}); new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))`);
      const clip = await evaluate(`var rect=document.getElementById('preference-section-2').closest('section').getBoundingClientRect(); ({x:rect.x+window.scrollX,y:rect.y+window.scrollY,width:rect.width,height:rect.height,scale:1})`);
      assert.ok(clip.height > 1000, "Visual capture must include the entire timetable");
      await mkdir(new URL("../.cache", import.meta.url), { recursive: true });
      const shot = await client.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip });
      await writeFile(new URL(`../.cache/${filename}`, import.meta.url), Buffer.from(shot.data, "base64"));
      await evaluate(`document.querySelector('.preference-meeting-controls').open=${wasOpen}; true`);
      await client.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false });
    }
    await navigate("/admin/preferences");

    await t.test("private selector, eligibility, categories, search, ineligible disabled", async () => {
      assert.deepEqual(await evaluate(`[...ui.field('Select faculty').options].map(el => el.textContent)`), ["Faculty 0", "Faculty 1"]);
      assert.equal(await evaluate(`document.body.textContent.includes('Palad') || document.body.textContent.includes('stable-faculty')`), false);
      assert.equal(await evaluate(`document.querySelectorAll('.preference-subject-browser li').length`), 3);
      await click("ITD"); assert.equal(await evaluate(`document.querySelectorAll('.preference-subject-browser li').length`), 1);
      await click("ALL"); await set("Find a subject", "Data Structures"); assert.equal(await evaluate(`document.querySelectorAll('.preference-subject-browser li').length`), 1);
      await set("Find a subject", "");
      await evaluate(`[...document.querySelectorAll('label')].find(el=>el.textContent.includes('Show all offered subjects')).querySelector('input').click(); true`);
      await eventually(() => evaluate(`!!ui.button('Add ITE184 to preferred subjects')`), "All courses did not load");
      assert.equal(await evaluate(`ui.button('Add ITE184 to preferred subjects').disabled`), true);
    });
    await t.test("dedicated compact tray contains only ranked subjects and their real components", async () => {
      assert.equal(await evaluate(`document.getElementById('draggable-subject-preferences-title').textContent`), "Draggable Subject Preferences");
      assert.equal(await evaluate(`document.querySelectorAll('.preference-component-tray .preference-component-card').length`), 0);
      assert.equal(await evaluate(`document.querySelector('.preference-component-tray').nextElementSibling.classList.contains('preference-weekly-schedule')`), true);
      assert.equal(await evaluate(`document.querySelector('.preference-tray-empty').textContent`), "Select a preferred subject above to schedule its components.");
      assert.ok(await evaluate(`document.querySelector('.preference-component-tray').getBoundingClientRect().height<80`));
      assert.equal(await evaluate(`document.getElementById('preferred-weekly-schedule-title').textContent`), "Preferred Weekly Schedule");
      assert.equal(await evaluate(`!!document.querySelector('[aria-label="Calendar view"]')`), false);
      await click("Add CCC121 to preferred subjects");
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('.preference-component-tray .preference-component-card')].map(el => [el.dataset.subjectCode,el.dataset.componentType])`), [["CCC121", "Lecture"], ["CCC121", "Laboratory"]]);
      assert.equal(await evaluate(`[...document.querySelectorAll('.preference-component-tray .preference-component-drag')].every(el=>el.dataset.componentDrag==='true' && getComputedStyle(el).cursor==='grab' && el.textContent.includes('Drag to preferred time'))`), true);
      assert.equal(await evaluate(`document.querySelector('.preference-component-drag').textContent.includes('Data Structures and Algorithms') && document.querySelector('.preference-component-drag').textContent.includes('LECTURE')`), true);
      assert.equal(await evaluate(`document.querySelector('.preference-component-card').getBoundingClientRect().width<=210`), true);
      assert.equal(await evaluate(`ui.button('Add CCC121 Lecture preference').textContent.trim()`), "Add");
      await click("Add ITD105 to preferred subjects"); await click("Add ITN102 to preferred subjects");
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('.preference-component-tray .preference-component-card')].map(el=>[el.dataset.subjectCode,el.dataset.componentType])`), [["CCC121", "Lecture"], ["CCC121", "Laboratory"], ["ITD105", "Lecture"], ["ITN102", "Laboratory"]]);
      assert.equal(await evaluate(`!!ui.button('+ Add General Preferred Period').closest('.preference-component-tray')`), false);
    });
    await t.test("full weekly timetable grows naturally; later times use page scrolling", async () => {
      assert.ok(await evaluate(`document.querySelector('.preference-calendar').getBoundingClientRect().height>800`));
      assert.equal(await evaluate(`[...document.querySelectorAll('.preference-calendar .fc-scroller')].every(el=>el.scrollHeight<=el.clientHeight+1)`), true);
      const before = await evaluate(`document.getElementById('preference-section-2').scrollIntoView({block:'start'}); window.scrollY`);
      const after = await evaluate(`document.querySelector('.preference-timetable-end').scrollIntoView({block:'center'}); window.scrollY`);
      assert.ok(after > before + 400, "The page must scroll through the full timetable");
      assert.equal(await evaluate(`document.querySelector('.preference-timetable-end').textContent`), "10:00 PM");
      assert.equal(await evaluate(`[...document.querySelectorAll('.preference-calendar .fc-scroller')].every(el=>el.scrollTop===0)`), true);
    });
    await t.test("one ranked list and synchronized dropdown and drag order", async () => {
      await status("Unsaved changes");
      await evaluate(`ui.set(document.getElementById('rank-ITN102'),'1'); true`);
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('[id^=rank-]')].map(el=>el.id)`), ["rank-ITN102", "rank-CCC121", "rank-ITD105"]);
      await evaluate(`var data = new DataTransfer(); data.setData('text/plain','ITD105'); document.getElementById('rank-ITN102').closest('li').dispatchEvent(new DragEvent('drop',{bubbles:true,dataTransfer:data})); true`);
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('[id^=rank-]')].map(el=>[el.id,el.value])`), [["rank-ITD105", "1"], ["rank-ITN102", "2"], ["rank-CCC121", "3"]]);
      assert.equal(await evaluate(`!!ui.button('Add ITD105 Laboratory preference') || !!ui.button('Add ITN102 Lecture preference')`), false);
      assert.equal(await evaluate(`ui.button('Add CCC121 Laboratory preference').parentElement.textContent.includes('3 hours')`), true);
    });
    await t.test("all half-hour rows are labeled and lower-half drops snap to 30 minutes", async () => {
      const labels = await evaluate(`[...document.querySelectorAll('.fc-timegrid-slot-label-cushion')].map(el=>el.textContent)`);
      assert.equal(labels.length, 29);
      assert.deepEqual(labels.slice(0,3), ["07:30–08:00", "08:00–08:30", "08:30–09:00"]); assert.equal(labels.at(-1), "21:30–22:00");
      assert.deepEqual(await evaluate(`[...document.querySelectorAll('.fc-col-header-cell-cushion')].map(el=>el.textContent)`), ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]);
      assert.equal(await evaluate(`getComputedStyle(document.querySelector('.fc-col-header')).backgroundColor`), "rgb(17, 94, 89)");
      assert.equal(await evaluate(`document.querySelector('.fc-timegrid-slot').getBoundingClientRect().height`), 38);
      assert.equal(await evaluate(`document.querySelectorAll('.fc-timegrid-col[data-date]').length`), 6);
      await dragSource("CCC121", "Lecture", "2026-09-28", "10:30", "", 0.7);
      await eventually(() => evaluate(`!!document.querySelector('details') && document.querySelector('details').textContent.includes('Monday · 10:30–12:30')`), "Lower-half drop created a quarter-hour instead of a half-hour start");
      await click("Remove CCC121 Lecture preference");
    });
    await t.test("reference acceptance: centered class blocks, exact drops, movement, no bottom resizing and removal", async () => {
      await dragSource("CCC121", "Lecture", "2026-09-29", "10:30");
      await eventually(() => evaluate(`document.querySelector('details')?.textContent.includes('Tuesday · 10:30–12:30')`), "Reference lecture did not land at Tuesday 10:30");
      await assertEventRows(4);
      assert.deepEqual(await evaluate(`[...document.querySelector('.preference-block-lecture .preference-block-content').children].map(el=>el.textContent)`), ["CCC121", "Data Structures and Algorithms", "Lecture", "10:30 AM – 12:30 PM"]);
      assert.equal(await evaluate(`getComputedStyle(document.querySelector('.preference-block-content')).textAlign`), "center");
      await dragSource("CCC121", "Laboratory", "2026-10-01", "13:30");
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Thursday · 13:30–16:30')`), "Reference lab did not land at Thursday 13:30");
      await assertEventRows(6, "Laboratory");
      assert.deepEqual(await evaluate(`[...document.querySelector('.preference-block-laboratory .preference-block-content').children].map(el=>el.textContent)`), ["CCC121", "Data Structures and Algorithms", "Laboratory", "1:30 PM – 4:30 PM"]);
      await captureSchedule("preferences-reference-timetable.png");
      await dragToSlot('.preference-block-lecture:not(.fc-event-mirror)', "2026-10-02", "08:00", 0.7);
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Friday · 08:00–10:00')`), "Reference lecture did not move to Friday 08:00–10:00");
      await assertEventRows(4);
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event-resizer').length`), 0);
      for (const [type, rows] of [["Lecture",4],["Laboratory",6]]) {
        const box = await evaluate(`var event=document.querySelector('.preference-block-${type.toLowerCase()}:not(.fc-event-mirror)'); event.scrollIntoView({block:'center'}); var rect=event.getBoundingClientRect(); ({x:rect.x+rect.width/2,y:rect.bottom-3})`);
        await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", ...box });
        await client.send("Input.dispatchMouseEvent", { type: "mousePressed", ...box, button: "left", buttons: 1, clickCount: 1 });
        await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: box.x, y: box.y+38, buttons: 1 });
        await pause(100);
        await client.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: box.x, y: box.y+38, button: "left", clickCount: 1 });
        await pause(100);
        await assertEventRows(rows, type);
      }
      await evaluate(`document.querySelector('details').open=true; true`);
      await click("Remove CCC121 Laboratory preference");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Laboratory"))}).dataset.componentDrag`), "true");
      await click("Remove CCC121 Lecture preference");
    });
    await t.test("general period uses a separate neutral block and spans one half-hour row", async () => {
      await click("+ Add General Preferred Period"); await set("Start time", "18:00"); await set("End time", "18:30"); await click("Add preference");
      assert.equal(await evaluate(`document.querySelector('.preference-block-general').getBoundingClientRect().height >= 35 && document.querySelector('.preference-block-general').getBoundingClientRect().height <= 38`), true);
      assert.deepEqual(await evaluate(`[...document.querySelector('.preference-block-general .preference-block-content').children].map(el=>el.textContent)`), ["General preferred period", "6:00 PM – 6:30 PM"]);
      assert.equal(await evaluate(`getComputedStyle(document.querySelector('.preference-block-general')).backgroundColor`), "rgb(241, 245, 249)");
      await click("Remove general period");
    });
    await t.test("a held card drag reaches an evening row by scrolling the page", async () => {
      const source = await evaluate(`document.getElementById('preference-section-2').scrollIntoView({block:'start'}); var rect=document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Lecture"))}).getBoundingClientRect(); ({x:rect.x+rect.width/2,y:rect.y+20})`);
      const before = await evaluate(`window.scrollY`);
      await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", ...source });
      await client.send("Input.dispatchMouseEvent", { type: "mousePressed", ...source, button: "left", buttons: 1, clickCount: 1 });
      await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: source.x + 10, y: source.y + 10, buttons: 1 });
      const targetX = await evaluate(`var col=document.querySelector('.fc-timegrid-col[data-date="2026-09-29"]').getBoundingClientRect(); col.x+col.width/2`);
      await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: targetX, y: 450, buttons: 1 });
      const deltaY = await evaluate(`document.querySelector('.fc-timegrid-slots [data-time="19:30:00"]').getBoundingClientRect().top-450`);
      await client.send("Input.dispatchMouseEvent", { type: "mouseWheel", x: targetX, y: 450, deltaX: 0, deltaY, buttons: 1 });
      await eventually(() => evaluate(`window.scrollY>${before}+300`), "Dragging must allow the page to scroll to evening times");
      const targetY = await evaluate(`var rect=document.querySelector('.fc-timegrid-slots [data-time="19:30:00"]').getBoundingClientRect(); rect.top+rect.height/2`);
      await client.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: targetX, y: targetY, buttons: 1 });
      await pause(100);
      await client.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: targetX, y: targetY, button: "left", clickCount: 1 });
      await eventually(() => evaluate(`document.querySelector('details')?.textContent.includes('Tuesday · 19:30–21:30')`), "Evening drop must use its exact time and locked duration");
      await assertEventRows(4);
      assert.equal(await evaluate(`[...document.querySelectorAll('.preference-calendar .fc-scroller')].every(el=>el.scrollTop===0)`), true);
      await click("Remove CCC121 Lecture preference");
    });
    await t.test("dragging a lecture source uses the dropped start and backend two-hour duration", async () => {
      await dragSource("CCC121", "Lecture", "2026-09-29", "10:30");
      await eventually(() => evaluate(`!!document.querySelector('details') && document.querySelector('details').textContent.includes('Tuesday · 10:30–12:30')`), "Lecture drop did not use its exact start and duration");
      await assertEventRows(4);
      assert.equal(await evaluate(`document.querySelector('.preference-meeting-controls').open`), false);
      await evaluate(`document.querySelector('details').open=true; true`);
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Lecture"))}).dataset.componentDrag`), "false");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Lecture"))}).textContent.includes('✓ Placed')`), true);
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Lecture"))}).getBoundingClientRect().height>0`), true);
    });
    await t.test("completed sources reject duplicate drags; existing lecture moves without resizing", async () => {
      await dragSource("CCC121", "Lecture", "2026-09-29", "10:30");
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event').length`), 1);
      assert.equal(await evaluate(`document.querySelector('.preference-component-card[data-subject-code="CCC121"][data-component-type="Lecture"] button').disabled`), true);
      await dragToSlot('.fc-event:not(.fc-event-mirror)', "2026-10-01", "13:30", 0.4);
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Thursday · 13:30–15:30')`), "Dragging lecture changed its two-hour duration");
      await assertEventRows(4);
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event-resizer').length`), 0);
      await click("Move CCC121 Lecture on Thursday"); assert.equal(await evaluate(`!!ui.field('End time')`), false);
      await set("Start time", "13:00"); await click("Move preference");
      assert.equal(await evaluate(`document.querySelector('details').textContent.includes('Thursday · 13:00–15:00')`), true);
    });
    await t.test("removing a placement re-enables its source and a fresh drop works", async () => {
      await click("Remove CCC121 Lecture preference");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Lecture"))}).dataset.componentDrag`), "true");
      assert.equal(await evaluate(`ui.button('Add CCC121 Lecture preference').disabled`), false);
      await dragSource("CCC121", "Lecture", "2026-09-28", "10:30");
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Monday · 10:30–12:30')`), "Re-enabled source failed to place");
    });
    await t.test("dragging lab creates one continuous 180-minute block, locked during moves", async () => {
      await dragSource("CCC121", "Laboratory", "2026-09-29", "13:30");
      await eventually(() => evaluate(`document.querySelector('details').textContent.includes('Tuesday · 13:30–16:30')`), "Laboratory drop did not use 180 minutes");
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event-resizer').length`), 0);
      assert.equal(await evaluate(`document.querySelector('.fc-event').textContent.includes('CCC121')`), true);
      await assertEventRows(6, "Laboratory");
      await captureSchedule("preferences-weekly-timetable.png");
      await evaluate(`document.querySelector('details').open=true; true`);
      await click("Move CCC121 Laboratory on Tuesday");
      assert.equal(await evaluate(`!!ui.field('End time')`), false);
      await set("Day", "W"); await set("Start time", "14:00"); await click("Move preference");
      assert.equal(await evaluate(`document.querySelector('details').textContent.includes('Wednesday · 14:00–17:00')`), true);
      await assertEventRows(6, "Laboratory");
      await click("Remove CCC121 Lecture preference");
    });
    await t.test("explicit multi-pattern choice and complete independently movable meetings", async () => {
      assert.equal(await evaluate(`document.querySelectorAll('.preference-component-drag[data-subject-code="ITD105"][data-component-drag="true"]').length`), 0);
      await click("Add ITD105 Lecture preference");
      assert.equal(await evaluate(`ui.field('Meeting pattern').value`), "");
      await set("Meeting pattern", "1"); await set("Meeting days", "0"); await set("Start time", "08:00"); await click("Add preference");
      await click("Move ITD105 Lecture on Monday"); await set("Start time", "09:00"); await click("Move preference");
      assert.equal(await evaluate(`!!ui.button('+ Add General Preferred Period').closest('[data-component-drag]')`), false);
      await captureSchedule("preferences-drag-cards.png");
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
      // Completed sources cannot initiate drag auto-scrolling; use a visible target cell.
      await dragSource("ITD105", "Lecture", "2026-10-01", "08:00", "TH");
      assert.equal(await evaluate(`document.querySelectorAll('.fc-event').length`), 3);
      await click("Move ITD105 Lecture on Monday"); await set("Start time", "09:00"); await click("Move preference");
    });
    await t.test("actual calendar pointer dragging preserves the three-hour laboratory", async () => {
      const box = await evaluate(`var event = [...document.querySelectorAll('.fc-event')].find(el=>el.textContent.includes('CCC121')); event.scrollIntoView({block:'center'}); var rect=event.getBoundingClientRect(); var target=document.querySelector('.fc-timegrid-col[data-date="2026-10-01"]').getBoundingClientRect(); ({x:rect.x+rect.width/2,y:rect.y+12,targetX:target.x+target.width/2})`);
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
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Laboratory"))}).dataset.componentDrag`), "false");
      assert.equal(await evaluate(`document.querySelector(${JSON.stringify(sourceSelector("CCC121", "Laboratory"))}).textContent.includes('✓ Placed')`), true);
      assert.equal(await evaluate(`ui.field('Meeting pattern for ITD105 Lecture').value`), "1");
    });
    await t.test("discard restores baseline and each faculty loads its own eligibility", async () => {
      await click("Remove CCC121 from preferred subjects"); await status("Unsaved changes"); await click("Discard"); await status("No changes");
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
