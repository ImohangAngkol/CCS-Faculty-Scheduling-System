import {test} from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {apiClient} from "../src/services/apiSession.ts";
import {applicationPreview} from "../src/api/scheduleApplications.ts";

test("preview cancellation reaches HTTP and rejection is preserved",async()=>{
 const old=apiClient.get,signal=new AbortController().signal;
 try{const error=new Error("Fictional cancelled preview");apiClient.get=async(url,options)=>{assert.equal(url,"/api/schedule-applications/fictional-id/preview");assert.equal(options.signal,signal);throw error;};await assert.rejects(applicationPreview("fictional-id",signal),e=>e===error);}finally{apiClient.get=old;}
});
test("history component owns cancellation, errors and retry independently",async()=>{
 const source=await readFile(new URL("../src/pages/admin/ScheduleApplications.tsx",import.meta.url),"utf8");
 const history=source.slice(source.indexOf("function PublishedHistory("));
 assert.match(history,/publishedVersions\(undefined,c.signal\)/);
 assert.doesNotMatch(history,/setDetail|applicationPreview|applyAdjustment/);
 assert.match(history,/return\(\)=>c.abort\(\)/);
 assert.match(history,/Published history unavailable/);
 assert.match(history,/Refresh published history/);
});
test("context invalidation and preview completion use an epoch and cancellation guard",async()=>{
 const source=await readFile(new URL("../src/pages/admin/ScheduleApplications.tsx",import.meta.url),"utf8");
 assert.match(source,/previewRequest.current\?\.abort\(\)/);
 assert.match(source,/token===epoch.current.value/);
 assert.match(source,/setDetail\(undefined\)/);
 assert.match(source,/key=\{user.id\}/);
 assert.match(source,/!detail\?\.can_apply\|\|!detail.command\|\|!confirm/);
});
