import {test} from "node:test";
import assert from "node:assert/strict";
import {getFitnessReport, compareFitness, validateFitnessReport, loadedEvaluationReport, downloadLoadedEvaluation, metric, statusLabel} from "../src/services/fitnessReporting.ts";
const id = "00000000-0000-4000-8000-000000000001";
const keys=["subject_preference","time_preference","day_preference","schedule_style","lecture_lab_preference","number_of_preparations","teaching_load_balance","daily_teaching_load"];
const report = () => ({schema_version:1, source:{run_id:id,generation:1,candidate:"best_ever"},overall_penalty:100,
  breakdown_available:true,recorded_component_sum:100,components:keys.map(key=>({key,label:key,penalty:key==="teaching_load_balance"?100:0})),faculty:[]});
test("report provenance, finite observations and component reconciliation are verified",()=>{
  assert.equal(validateFitnessReport(report(),id,1,"best_ever").overall_penalty,100);
  for (const change of [{source:{run_id:"wrong"}}, {overall_penalty:NaN}, {components:[{penalty:99}]}, {components:[{penalty:null}]}]) assert.throws(()=>validateFitnessReport({...report(),...change},id,1,"best_ever"));
  const missing = {...report(),breakdown_available:false,components:keys.map(key=>({key,penalty:null}))};
  assert.equal(validateFitnessReport(missing).components[0].penalty,null);
});
test("missing values remain distinct from real zero and disabled preferences",()=>{
  assert.equal(metric(null),"Not captured"); assert.equal(metric(0),"0"); assert.equal(metric(100,"%"),"100%");
  assert.equal(statusLabel("disabled"),"Disabled"); assert.equal(statusLabel("partially_satisfied"),"Partially satisfied");
});
test("historical and latest reports issue only bounded GET requests",async()=>{
  const before=globalThis.fetch, requests=[];
  globalThis.fetch=async(url,options)=>{requests.push({url,options});return Response.json(report());};
  try {
    await getFitnessReport(id,1,"best_ever"); await getFitnessReport();
    assert.ok(requests.every(request=>!request.options.method && request.options.signal));
    assert.match(requests[0].url,/generations\/1\/fitness-analysis\?candidate=best_ever/);
    assert.match(requests[1].url,/fitness-analysis\/latest$/);
    await assert.rejects(getFitnessReport("../private",1),/Invalid historical run/);
    await assert.rejects(getFitnessReport(id,-1),/recorded generation/);
  } finally {globalThis.fetch=before;}
});
test("comparison source is verified and missing contributions stay null",async()=>{
  const before=globalThis.fetch;
  const comparison={schema_version:1,source:{run_id:id,left:0,right:1,candidate:"generation_best"},overall_reduction:10,component_changes:[{reduction:null}],faculty_changes:[]};
  globalThis.fetch=async()=>Response.json(comparison);
  try {
    assert.equal((await compareFitness(id,0,1,"generation_best")).component_changes[0].reduction,null);
    await assert.rejects(compareFitness(id,1,0,"generation_best"),/Comparison source/);
  } finally {globalThis.fetch=before;}
});
test("corrupt analysis and unavailable backend are actionable errors",async()=>{
  const before=globalThis.fetch;
  try {
    globalThis.fetch=async()=>Response.json({detail:{code:"GA_REPORT_INVALID",message:"Stored components do not reconcile."}},{status:422});
    await assert.rejects(getFitnessReport(),/Fitness analysis.*GA_REPORT_INVALID/);
    globalThis.fetch=async()=>{throw new TypeError("offline");};
    await assert.rejects(getFitnessReport(),/Backend unavailable/);
  } finally {globalThis.fetch=before;}
});
test("loaded candidate retains its existing evaluation without current targets or extra API calls",()=>{
  const data={best_fitness:100,fitness_breakdown:Object.fromEntries(keys.map(key=>[key,key==='teaching_load_balance'?100:0])),schedule:[],
    faculty_analysis:{faculty:[{Faculty_Code:7.0,Teaching_Load:12,Preparations:2,Total_Penalty:100,Load_Balance_Penalty:100,Subject_Satisfaction:50,Subject_Importance:4}],daily_load:[]}};
  const view=loadedEvaluationReport(data);
  assert.equal(view.source.kind,'loaded-chromosome-evaluation'); assert.equal(view.source.generation,null);
  assert.equal(view.faculty[0].faculty,'Faculty 7'); assert.equal(view.faculty[0].required_teaching_load,null);
  assert.equal(view.faculty[0].preferences[0].satisfaction_percent,50); assert.equal(view.faculty[0].workload_penalty,100);
});
test("loaded report CSV protects spreadsheet cells and identifies unavailable generation",async()=>{
  const beforeDocument=globalThis.document, beforeURL=URL.createObjectURL, blobs=[];
  globalThis.document={createElement:()=>({click(){}})}; URL.createObjectURL=blob=>{blobs.push(blob);return 'blob:fitness-test';};
  const data={best_fitness:100,fitness_breakdown:Object.fromEntries(keys.map(key=>[key,key==='teaching_load_balance'?100:0])),schedule:[],faculty_analysis:{faculty:[]}};
  try {
    const view=loadedEvaluationReport(data); view.components[0].definition='=HYPERLINK("unsafe")';
    await downloadLoadedEvaluation(view,'fitness','csv');
    const csv=await blobs[0].text(); assert.ok(csv.includes("'=HYPERLINK")); assert.ok(csv.includes('loaded-chromosome-evaluation'));
    assert.ok(csv.includes('"generation"')); assert.ok(csv.includes(',"",'));
  } finally {globalThis.document=beforeDocument;URL.createObjectURL=beforeURL;}
});
