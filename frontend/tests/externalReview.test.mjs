import {test} from "node:test";
import assert from "node:assert/strict";
import axios from "axios";
import {apiClient} from "../src/services/apiSession.ts";
import {reviewExternal,reviewProjectionSchema} from "../src/api/externalSchedules.ts";
import {filterReviewRows,emptyReviewFilters,reviewCalendarEvents,hasResourceOverlap} from "../src/components/schedule/externalReviewModel.ts";
import {makeSource,makeProjection,inputs} from "./externalReview.fixtures.mjs";

async function post(fn,action){const saved=apiClient.post;apiClient.post=fn;try{await action();}finally{apiClient.post=saved;}}
test("review sends only receipt and explicit mapping IDs through existing transport",async()=>{
  const source=makeSource(),mappings=[{source_row:2,sections:[{reference_index:0,target_id:"section-a"}]}],signal=new AbortController().signal;
  await post(async(url,body,options)=>{assert.ok(url.endsWith("/api/external-schedules/review"));assert.deepEqual(body,{review_token:source.review_token,mappings});assert.equal(options.signal,signal);return {data:makeProjection(source,mappings)};},
    async()=>assert.equal((await reviewExternal(source,mappings,signal)).source_sha256,source.source_sha256));
});
test("old previews without a receipt cannot be silently reconciled",async()=>{
  await post(()=>assert.fail("No request expected"),async()=>assert.rejects(reviewExternal({...makeSource(),review_token:null},[]),/Preview the source again/));
});
test("source hash, name, row numbers and original text cannot be substituted",async()=>{
  const source=makeSource();
  for(const change of [{source_sha256:"c".repeat(64)},{source_name:"other.csv"},{rows:makeProjection(source).rows.slice(1)},
    {rows:makeProjection(source).rows.map((row,i)=>i?row:{...row,source_row:99})},
    {rows:makeProjection(source).rows.map((row,i)=>i?row:{...row,original:{...row.original,notes:"changed"}})}]){
    await post(async()=>({data:{...makeProjection(source),...change}}),async()=>assert.rejects(reviewExternal(source,[]),/original preview provenance/));
  }
});
test("activated/persisted output and impossible resolved states fail the review boundary",()=>{
  for(const change of [{activated:true},{persisted:true},{preview_only:false}])assert.equal(reviewProjectionSchema.safeParse({...makeProjection(),...change}).success,false);
  const result=makeProjection();result.rows[0].room={...result.rows[0].room,id:null,state:"resolved"};
  assert.equal(reviewProjectionSchema.safeParse(result).success,false);
});
test("section filtering follows canonical mapping instead of imported labels",()=>{
  const projection=makeProjection(makeSource(),[{source_row:2,sections:[{reference_index:0,target_id:"section-b"}]}]);
  assert.deepEqual(filterReviewRows(projection.rows,{...emptyReviewFilters,section:"section-b"}).map(r=>r.source_row),[2,4]);
  assert.equal(projection.rows[0].original.sections[0],"Imported section");
});
test("supplier, subject and intake intent filters combine without changing source rows",()=>{
  const rows=makeProjection().rows;
  assert.deepEqual(filterReviewRows(rows,{...emptyReviewFilters,supplier:"Another Fictional College"}).map(r=>r.source_row),[4]);
  assert.deepEqual(filterReviewRows(rows,{...emptyReviewFilters,subject:"SYN-GEC202",intent:"draft"}).map(r=>r.source_row),[3]);
  assert.equal(filterReviewRows(rows,{...emptyReviewFilters,subject:"SYN-GEC202",intent:"tentative"}).length,0);
});
test("reference filters distinguish ambiguity, pending and missing optional resources",()=>{
  const rows=makeProjection().rows;
  assert.deepEqual(filterReviewRows(rows,{...emptyReviewFilters,references:"ambiguous"}).map(r=>r.source_row),[2]);
  assert.deepEqual(filterReviewRows(rows,{...emptyReviewFilters,references:"resolved"}).map(r=>r.source_row),[3,4]);
  assert.deepEqual(filterReviewRows(rows,{...emptyReviewFilters,references:"missing_optional"}).map(r=>r.source_row),[4,5]);
  assert.deepEqual(filterReviewRows(makeProjection(makeSource(),[],{unsupported:true}).rows,{...emptyReviewFilters,references:"unsupported"}).map(r=>r.source_row),[2,3]);
});
test("calendar preserves exact off-grid times and original row boundaries without academic dates",()=>{
  const source=makeSource([{...inputs[0],start:"09:10"},{...inputs[0],start:"10:00",end:"11:00"}]);
  const events=reviewCalendarEvents(makeProjection(source).rows);
  assert.equal(events.length,2);assert.equal(events[0].startTime,"09:10");
  assert.deepEqual(events[0].daysOfWeek,[1]);assert.notEqual(events[0].id,events[1].id);
  assert.equal("start" in events[0],false);assert.equal("date" in events[0],false);
});
test("invalid patterns stay available as details but are excluded from plotting",()=>{
  const rows=makeProjection().rows;
  assert.equal(rows[3].calendar_supported,false);assert.equal(reviewCalendarEvents(rows).length,3);
  assert.equal(rows[3].source_row,5);
});
test("overlap highlighting uses full-batch findings even after filtering",()=>{
  const row=filterReviewRows(makeProjection().rows,{...emptyReviewFilters,subject:"SYN-GEC101"})[0];
  assert.ok(hasResourceOverlap(row));assert.equal(reviewCalendarEvents([row])[0].borderColor,"#be123c");
});
test("authorization and stale-reference failures retain HTTP status instead of fabricating output",async()=>{
  for(const status of [401,403,409,422,503]){
    const error=new axios.AxiosError("synthetic",undefined,undefined,undefined,{status});
    await post(async()=>{throw error;},async()=>assert.rejects(reviewExternal(makeSource(),[]),value=>value===error));
  }
});
