import {test} from "node:test";
import assert from "node:assert/strict";
import axios from "axios";
import {apiClient} from "../src/services/apiSession.ts";
import {constraintsSchema,resultSchema,runSchema,statusSchema,currentConstraints,startConstrained,constrainedRun,controlConstrained,constrainedError} from "../src/api/constrainedGA.ts";
import {scope,result,job,status,runId} from "./constrainedGA.fixtures.mjs";

test("explicit version and production block cannot be reinterpreted as legacy or active authority",()=>{
  assert.equal(statusSchema.parse(status).production_status,"BLOCKED");
  for(const changed of [{...status,production_status:"ACTIVE"},{...status,constrained_mode:"LEGACY_V1"}])assert.equal(statusSchema.safeParse(changed).success,false);
});
test("complete constraints require revision and source provenance",()=>{
  assert.equal(constraintsSchema.parse(scope).revisions[0].source_hash_kind,"canonical_manual_content");
  for(const changed of [{...scope,revisions:[]},{...scope,constraint_digest:"unknown"},{...scope,activated:true}])assert.equal(constraintsSchema.safeParse(changed).success,false);
});
test("result contract rejects approval claims and unknown engine versions",()=>{
  assert.equal(resultSchema.parse(result).source,"GA-generated proposal");
  for(const changed of [{...result,approved:true},{...result,engine_version:"ga-continuation-v1"},{...result,source:"official"}])assert.equal(resultSchema.safeParse(changed).success,false);
});
test("malformed result fields and numeric diagnostics are rejected",()=>{
  for(const changed of [{...result,schedule:[{...result.schedule[0],start:null}]},{...result,best_fitness:Infinity},{...result,diagnostics:{rejected:-1}}])assert.equal(resultSchema.safeParse(changed).success,false);
});
test("job states distinguish no committed population and a durable completed result",()=>{
  assert.equal(runSchema.parse({...job,status:"INITIALIZING",execution_active:true,generation:null,result:undefined}).generation,null);
  assert.equal(runSchema.parse(job).result.schedule.length,1);
});
test("term review uses exact supplied labels and cancellation",async()=>{
  const before=apiClient.get,signal=new AbortController().signal;
  try{apiClient.get=async(url,options)=>{assert.ok(url.endsWith("/api/ga/v2/constraints"));assert.deepEqual(options.params,{academic_year:scope.academic_year,term:scope.term});assert.equal(options.signal,signal);return {data:scope};};assert.deepEqual(await currentConstraints(scope.academic_year,scope.term,signal),scope);}finally{apiClient.get=before;}
});
test("start sends reviewed digest and explicit seed, no resource selection or authority flags",async()=>{
  const before=apiClient.post;
  try{apiClient.post=async(url,body)=>{assert.ok(url.endsWith("/api/ga/v2/runs"));assert.deepEqual(Object.keys(body).sort(),["academic_year","term","constraint_digest","seed","parameters"].sort());assert.equal(body.constraint_digest,scope.constraint_digest);assert.equal(body.seed,"saved");assert.deepEqual(body.parameters,{population_size:2,generations:1});return {data:job};};await startConstrained(scope,"saved",{population_size:2,generations:1});}finally{apiClient.post=before;}
});
test("only canonical run IDs address V2 results",async()=>{
  const before=apiClient.get;let calls=0;
  try{apiClient.get=async url=>{calls++;assert.ok(url.endsWith(runId));return {data:job};};await constrainedRun(runId);await assert.rejects(constrainedRun("../legacy"));assert.equal(calls,1);}finally{apiClient.get=before;}
});
test("versioned control does not touch V1 execution endpoints",async()=>{
  const before=apiClient.post;
  try{apiClient.post=async(url,body)=>{assert.ok(url.includes("/api/ga/v2/runs/"));assert.deepEqual(body,{action:"resume"});return {data:job};};await controlConstrained(runId,"resume");}finally{apiClient.post=before;}
});
test("authorization, stale constraints and provider failures remain visible",()=>{
  for(const [status,message] of [[401,"Sign in"],[403,"administrator"],[503,"unavailable"]]){
    const e=new axios.AxiosError("failed");e.response={status,data:{}};assert.ok(constrainedError(e).includes(message));
  }
  const e=new axios.AxiosError("failed");e.response={status:409,data:{detail:{code:"CONSTRAINT_SET_CHANGED",message:"Review the current set again."}}};assert.match(constrainedError(e),/CONSTRAINT_SET_CHANGED/);
});
test("imported text remains data in validated DTOs",()=>{
  const text='<img src=x onerror="window.__executed=true">';
  assert.equal(resultSchema.parse({...result,schedule:[{...result.schedule[0],title:text}]}).schedule[0].title,text);
});
