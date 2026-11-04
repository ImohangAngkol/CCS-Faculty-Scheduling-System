import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {facultyCoverage} from '../src/services/facultyCoverage.ts';
import {workloadPresentation} from '../src/services/workloadPresentation.ts';
import {isVerifiedCurrent,penaltyLabel} from '../src/services/resultPresentation.ts';
const load=(faculty,actual,target,status)=>({faculty,teaching_units:actual,required_teaching_load:target,workload_status:status});
test('roster zero-assignment faculty remain visible in numeric order including Faculty 0',()=>{
  const result=facultyCoverage([10,2,1,0].map(faculty_code=>({faculty_code})),[{faculty:'1'}]);
  assert.deepEqual(result.map(row=>row.key),['0','1','2','10']);assert.equal(result[2].assignments,0);assert.equal(result[2].label,'Faculty 2');
});
test('captured analysis adds an unassigned member missing from metadata or assignments',()=>{
  const result=facultyCoverage([], [{faculty:'1'}],[{Faculty_Code:2,Teaching_Load:0}]);
  assert.deepEqual(result.map(row=>[row.key,row.assignments]),[['1',1],['2',0]]);assert.deepEqual(result[1].sources,['recorded analysis']);
});
test('faculty normalization merges sources without creating assignments or altering rows',()=>{
  const metadata=Object.freeze([Object.freeze({faculty_code:1})]),schedule=Object.freeze([Object.freeze({faculty:'1.0'}),Object.freeze({faculty:'Faculty 1'})]);
  const before=JSON.stringify([metadata,schedule]);const result=facultyCoverage(metadata,schedule,[{Faculty_Code:'1'}]);
  assert.equal(result.length,1);assert.equal(result[0].assignments,2);assert.equal(JSON.stringify([metadata,schedule]),before);
});
test('external metadata is not treated as an unassigned optimization faculty roster entry',()=>{
  assert.deepEqual(facultyCoverage([{faculty_code:'external:fictional',instructor_type:'preassigned_external'}],[]),[]);
  const actual=facultyCoverage([], [{faculty:'external:fictional',faculty_name:'Fictional visiting instructor'}]);assert.equal(actual[0].external,true);assert.equal(actual[0].assignments,1);
});
test('empty and malformed cohort observations do not create anonymous faculty',()=>{
  assert.deepEqual(facultyCoverage([],[],[]),[]);
  assert.deepEqual(facultyCoverage([{faculty_code:undefined},{faculty_code:''},{faculty_code:NaN}],[]),[]);
});
test('zero actual teaching is a real observation, distinct from missing actual or target',()=>{
  const view=workloadPresentation([load('Faculty 2',0,24,'underload'),load('Faculty 3',null,24,'unavailable'),load('Faculty 4',12,null,'unavailable')]);
  assert.equal(view.rows[0].actual,0);assert.equal(view.rows[0].actualWidth,0);assert.equal(view.rows[0].status,'Underload');
  assert.equal(view.rows[1].actual,null);assert.equal(view.rows[2].target,null);
});
test('chart maximum includes actual overload without truncating it at the target or 40',()=>{
  const view=workloadPresentation([load('Faculty 1',45,24,'overload')]);
  assert.equal(view.maximum,45);assert.equal(view.rows[0].actualWidth,100);assert.equal(view.rows[0].actual,45);assert.equal(view.rows[0].status,'Overload');
});
test('zero targets avoid division by zero and preserve positive actual observations',()=>{
  const view=workloadPresentation([load('Faculty 1',0,0,'on_target'),load('Faculty 2',4,0,'overload')]);
  assert.equal(view.rows[0].status,'Balanced (at target)');assert.equal(view.rows[1].status,'Overload');
  assert.ok(view.rows.every(row=>Number.isFinite(row.actualWidth)&&Number.isFinite(row.targetWidth)));
});
test('invalid numeric observations are unavailable rather than coerced to zero',()=>{
  for(const value of [NaN,Infinity,-1,'0',undefined])assert.equal(workloadPresentation([load('Faculty 1',value,24) ]).rows[0].actual,null);
});
test('decimal teaching units and targets remain exact inputs and naturally sorted without mutation',()=>{
  const rows=Object.freeze([Object.freeze(load('Faculty 10',31.25,18.5,'overload')),Object.freeze(load('Faculty 2',18.5,18.5,'on_target'))]);
  const before=JSON.stringify(rows),view=workloadPresentation(rows);
  assert.deepEqual(view.rows.map(row=>row.observation.faculty),['Faculty 2','Faculty 10']);assert.equal(view.rows[1].actual,31.25);assert.equal(JSON.stringify(rows),before);
});
test('inconsistent recorded status is flagged instead of silently accepted',()=>assert.equal(workloadPresentation([load('Faculty 1',30,24,'on_target')]).rows[0].inconsistent,true));
test('empty workload view has no invented faculty or measured values',()=>assert.deepEqual(workloadPresentation([]),{maximum:1,rows:[]}));
test('unknown saved compatibility cannot become current from a date, title, reset or penalty zero',()=>{
  assert.equal(isVerifiedCurrent({fitness:0,created_at:'2099-01-01',evaluation:'current'}),false);assert.equal(penaltyLabel(null),'—');assert.equal(penaltyLabel(0),'0');
});
test('current saved view is the default; archived card requires an explicit archive selection',async()=>{
  const source=await readFile(new URL('../src/pages/admin/ChromosomeViewer.tsx',import.meta.url),'utf8');
  assert.ok(source.includes('{!archive && <CurrentEvaluation mode="best"'));
  const current=await readFile(new URL('../src/components/ga/CurrentEvaluation.tsx',import.meta.url),'utf8');
  for(const text of ['params.get("view") === "archive"','{archive && <section','Current Runs:','Current Best Fitness:','Saved Chromosome:','Start Fresh Evaluation (not available)','No reset has occurred'])assert.ok((source+current).includes(text));
  assert.match(current,/type="button" disabled[^>]*>Start Fresh Evaluation/);assert.doesNotMatch(source,/fitness.*\?\? 0/);
});
test('schedule empty/result/coverage errors are honest and chart retains keyboard/exact-value access',async()=>{
  const source=await readFile(new URL('../src/pages/admin/ScheduleView.tsx',import.meta.url),'utf8');
  for(const text of ['if (!gaData)','recorded faculty analysis','Retry roster','No assigned subjects','faculty_analysis?.faculty'])assert.ok(source.includes(text));
  const chart=await readFile(new URL('../src/components/ga/WorkloadChart.tsx',import.meta.url),'utf8');
  for(const text of ['tabIndex={0}','aria-label={label}','title={label}','String(value)','No workload observations match this view.'])assert.ok(chart.includes(text));
});
