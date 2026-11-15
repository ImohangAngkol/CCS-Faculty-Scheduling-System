import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateView, changeFor} from '../src/prototypeWorkload/model.mjs';

const view = () => ({contract:'prototype-explicit-minimum-v1', prototype_only:true, production_admission:'BLOCKED',
  optimizer_executed:false, active_restore:false, continuous_optimization:'DISABLED', institutional_saved_best_promotion:false,
  seven_day:'NO_GO', policy:{revision:0,digest:'a'.repeat(64)}, bundle_fingerprint:'b'.repeat(64),
  input_capture_verification:'UNVERIFIED',optimizer_consumption:'NOT_ESTABLISHED',
  scope:{academic_year:'FICTIONAL-YEAR',term:'FICTIONAL-TERM',catalog_revision:'FICTIONAL-CATALOG-1'},
  can_configure:true, preflight:'NOT_PROVEN_INFEASIBLE', faculty:[1,2].map(faculty_code=>({faculty_code,
    soft_target_teaching_units:24, maximum_teaching_units:40, eligible_units:12, minimum_teaching_units:null}))});

test('blank minimum remains unspecified for other faculty',()=>{
  assert.deepEqual(changeFor(view(),new Map([[1,''],[2,'24']])),{expected_revision:0,minimums:[{faculty_code:2,minimum_teaching_units:24}]});
});
test('zero is an explicit minimum',()=>assert.equal(changeFor(view(),new Map([[2,'0']])).minimums[0].minimum_teaching_units,0));
for(const text of ['-1','24.5','NaN','41','true','1e2'])test('invalid minimum rejected '+text,()=>assert.throws(()=>changeFor(view(),new Map([[2,text]]))));
test('read permission does not grant configuration',()=>assert.throws(()=>changeFor({...view(),can_configure:false},new Map([[2,'24']]))));
test('production/optimizer claims rejected',()=>{
  assert.throws(()=>validateView({...view(),production_admission:'CURRENT'}));
  assert.throws(()=>validateView({...view(),optimizer_executed:true}));
});
test('duplicate or invalid faculty metadata rejected',()=>{
  const x=view();x.faculty[1].faculty_code=1;assert.throws(()=>validateView(x));
});
test('infeasibility is explicit and sufficient units are not called feasible',()=>{
  assert.equal(validateView({...view(),preflight:'MINIMUM_WORKLOAD_INFEASIBLE'}).preflight,'MINIMUM_WORKLOAD_INFEASIBLE');
  assert.throws(()=>validateView({...view(),preflight:'FEASIBLE'}));
});
test('safe DOM, stale response guard, no unsupported execution controls',async()=>{
  const code=await readFile(new URL('../src/prototypeWorkload/console.mjs',import.meta.url),'utf8');
  const html=await readFile(new URL('../src/prototypeWorkload/index.html',import.meta.url),'utf8');
  assert.ok(!code.includes('innerHTML')&&!code.includes('localStorage'));
  assert.ok(code.includes('if (key !== epoch) return')&&code.includes('Save outcome may be uncertain'));
  assert.ok(code.includes('method: \'PUT\'')&&code.includes('/api/prototype/workload'));
  assert.ok(!/<button[^>]*>[^<]*(Start|Pause|Resume|Restore|Promote)/.test(html));
});
