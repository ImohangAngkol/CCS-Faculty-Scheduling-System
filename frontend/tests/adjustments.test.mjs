import {test} from "node:test";
import assert from "node:assert/strict";
import {apiClient} from "../src/services/apiSession.ts";
import {getAdjustmentAssignments,listAdjustments,getAdjustment,previewAdjustment,createAdjustment,transitionAdjustment} from "../src/api/adjustments.ts";
import {bundle,input,review,record} from "./adjustments.fixtures.mjs";

async function intercept(method,response,action,verify=()=>{}) {const previous=apiClient[method];try{apiClient[method]=async(...args)=>{verify(...args);return {data:response};};return await action();}finally{apiClient[method]=previous;}}
test("own assignments use only server identity and support cancellation",async()=>{
 const signal=new AbortController().signal;
 assert.deepEqual(await intercept("get",bundle,()=>getAdjustmentAssignments(signal),(url,options)=>{assert.equal(url,"/api/adjustment-requests/assignments");assert.equal(options.signal,signal);assert.equal(options.params,undefined);}),bundle);
});
test("requests paginate without faculty selectors",async()=>{
 const page={items:[record],next_cursor:record.id};
 assert.deepEqual(await intercept("get",page,()=>listAdjustments(undefined,record.id),(_u,o)=>assert.deepEqual(o.params,{before:record.id})),page);
});
test("preview preserves exact schedule scope, resource IDs and text",async()=>{
 const body={...input,justification:"<script>fictional text</script>"};
 assert.deepEqual(await intercept("post",review,()=>previewAdjustment(body),(u,b)=>{assert.equal(u,"/api/adjustment-requests/preview");assert.deepEqual(b,body);}),review);
});
test("draft creation retains supplied idempotency key without authority claims",async()=>{
 await intercept("post",record,()=>createAdjustment(input,record.id),(_u,b)=>{assert.deepEqual(b,{...input,operation_id:record.id});assert.equal(b.faculty_id,undefined);assert.equal(b.approved,undefined);});
});
test("submit and withdrawal use optimistic version and explicit operation IDs",async()=>{
 for(const action of ["submit","withdraw"])await intercept("post",record,()=>transitionAdjustment(record,action,record.id),(u,b)=>{assert.equal(u,`/api/adjustment-requests/${record.id}/${action}`);assert.deepEqual(b,{operation_id:record.id,expected_version:1});});
});
test("details preserve original revision, validation and immutable history",async()=>{
 assert.deepEqual(await intercept("get",record,()=>getAdjustment(record.id)),record);
});
for(const [label,change] of [["approval status",{status:"APPROVED"}],["schedule change",{schedule_changed:true}],["approval flag",{approval:"APPROVED"}],["unknown authority",{authorized:true}],["history rewrite",{history:[{...record.history[0],action:"APPLIED"}]}]])test("contract rejects "+label,async()=>{
 await assert.rejects(intercept("get",{...record,...change},()=>getAdjustment(record.id)));
});
test("stale references and unresolved conflicts stay explicit in detail",async()=>{
 const changed={...record,freshness:{state:"STALE",code:"GEC_CONSTRAINT_SET_CHANGED",validation:null},content:{...record.content,review:{...review,validation:{...review.validation,conflict_free:false,outcome:"REQUIRES_REVIEW",findings:[{code:"ROOM_CONFLICT",message:"Review required."}]}}}};
 assert.deepEqual(await intercept("get",changed,()=>getAdjustment(record.id)),changed);
});
test("unauthorized and unavailable responses propagate instead of success fallback",async()=>{
 const before=apiClient.get;try{for(const status of [401,403,409,503]){apiClient.get=async()=>{throw Object.assign(new Error("unavailable"),{status});};await assert.rejects(getAdjustmentAssignments(),e=>e.status===status);}}finally{apiClient.get=before;}
});
