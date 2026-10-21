import {test} from "node:test";
import assert from "node:assert/strict";
import axios from "axios";
import {apiClient} from "../src/services/apiSession.ts";
import {emptyExternalRow,getExternalMetadata,previewManual,previewFile,previewSchema} from "../src/api/externalSchedules.ts";
import {row,metadata,preview,issue} from "./externalSchedules.fixtures.mjs";

async function mock(method,fn,action) {const saved=apiClient[method];apiClient[method]=fn;try {await action();} finally {apiClient[method]=saved;}}
test("metadata uses the administrator reference endpoint and records the unknown term boundary",async()=>{
  const signal=new AbortController().signal;
  await mock("get",async(url,options)=>{assert.ok(url.endsWith("/api/external-schedules/metadata"));assert.equal(options.signal,signal);return {data:metadata};},
    async()=>assert.deepEqual(await getExternalMetadata(signal),metadata));
});
test("manual preview sends the complete draft without faculty selectors or confirmation flags",async()=>{
  const signal=new AbortController().signal;
  await mock("post",async(url,body,options)=>{assert.ok(url.endsWith("/preview"));assert.deepEqual(body,{rows:[row]});assert.equal(options.signal,signal);return {data:preview()};},
    async()=>assert.equal((await previewManual([row],signal)).persisted,false));
});
test("file preview sends raw bytes through shared cookie/CSRF transport without multipart spooling",async()=>{
  const file=new File(["fictional input"],"fictional.csv");const signal=new AbortController().signal;
  await mock("post",async(url,body,options)=>{assert.ok(url.endsWith("/preview-file"));assert.equal(body,file);assert.deepEqual(options.params,{filename:file.name});assert.equal(options.signal,signal);assert.equal(options.headers["Content-Type"],"application/octet-stream");return {data:preview([row],"csv")};},
    async()=>assert.equal((await previewFile(file,signal)).source_kind,"csv"));
});
test("oversized and unsupported selected files are rejected before an HTTP upload",async()=>{
  await mock("post",()=>assert.fail("Unexpected upload"),async()=>{
    await assert.rejects(previewFile(new File(["x"],"unsafe.xls")),/CSV or XLSX/);
    await assert.rejects(previewFile(new File([new Uint8Array(1048577)],"large.xlsx")),/1 MiB/);
  });
});
test("an activated, persisted or malformed response is never accepted as a preview",()=>{
  for(const changed of [{activated:true},{persisted:true},{preview_only:false},{source_sha256:"invalid"},{rows:[{...preview().rows[0],status:"confirmed"}]}])
    assert.equal(previewSchema.safeParse({...preview(),...changed}).success,false);
});
test("structured discrepancies and source rows are retained instead of fabricated success",()=>{
  const result=previewSchema.parse(preview([row],"xlsx",[issue("SECTION_OVERLAP","error","sections",[3])]));
  assert.equal(result.rows[0].source_row,2);assert.equal(result.rows[0].status,"invalid");
  assert.deepEqual(result.rows[0].discrepancies[0].related_rows,[3]);
});
test("empty manual defaults contain no invented academic records or approval state",()=>{
  const empty=emptyExternalRow();assert.equal(empty.status,"draft");assert.deepEqual(empty.sections,[]);assert.equal(empty.academic_term,"");
});
test("unauthorized, denied, unsafe-file and unavailable errors propagate for honest UI handling",async()=>{
  for (const status of [401,403,413,422,503]) {
    const error=new axios.AxiosError("synthetic",undefined,undefined,undefined,{status});
    await mock("post",async()=>{throw error;},async()=>assert.rejects(previewManual([row]),v=>v===error));
  }
});
