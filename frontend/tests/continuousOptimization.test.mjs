import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateReadiness,CONTINUOUS_STATES} from '../src/services/continuousOptimization.ts';
import {readinessFixture} from './continuousOptimization.fixtures.mjs';

test('foundation cannot supply an executable dataset or verified receipt',()=>{
  const r=validateReadiness(readinessFixture());assert.equal(r.executable,false);assert.deepEqual(r.supported_datasets,[]);assert.equal(r.receipt_capability,'UNVERIFIED_ONLY');assert.equal(CONTINUOUS_STATES.length,11);
});
for(const field of ['executable','availability','supported_datasets','input_consumption','receipt_capability','institutional_authorization','lifecycle','safeguards','requirements'])test(`forged ${field} cannot activate controls`,()=>{
  const v=readinessFixture();const values={executable:true,availability:'READY',supported_datasets:['fictional'],input_consumption:'VERIFIED',receipt_capability:'VERIFIED',institutional_authorization:'APPROVED',lifecycle:{states:[],commands:'AVAILABLE'},safeguards:{enforcement:'ENFORCED',required:[]},requirements:[]};v[field]=values[field];assert.throws(()=>validateReadiness(v));
});
test('duplicated or unknown requirements fail closed',()=>{
  for(const code of ['UNKNOWN','IMMUTABLE_CONSUMPTION_REQUIRED']){const v=readinessFixture();v.requirements[1].code=code;assert.throws(()=>validateReadiness(v));}
});
test('noninstalled commands and malformed state vocabulary fail closed',()=>{
  const v=readinessFixture();v.lifecycle.states.reverse();assert.throws(()=>validateReadiness(v));
});
test('selector is a local read-only view with explicit unavailability and no polling',async()=>{
  const s=await readFile(new URL('../src/components/ga/OptimizationMode.tsx',import.meta.url),'utf8');
  assert.match(s,/Start Optimization — unavailable/);assert.match(s,/disabled aria-describedby/);assert.match(s,/AbortController/);
  assert.doesNotMatch(s,/setInterval|setTimeout|dangerouslySetInnerHTML|method:.*POST/);
});
test('continuous selection is guarded before upload or fixed engine invocation',async()=>{
  const s=await readFile(new URL('../src/pages/admin/GenerateSchedule.tsx',import.meta.url),'utf8');
  const start=s.slice(s.indexOf('async function handleGenerate()'),s.indexOf('  return (',s.indexOf('async function handleGenerate()')));
  assert.ok(start.indexOf('optimizationMode!=="fixed"')<start.indexOf('uploadBaselineChromosome('));
  assert.ok(start.indexOf('optimizationMode!=="fixed"')<start.indexOf('await runGA('));
  assert.match(s,/fieldset hidden=\{optimizationMode!=="fixed"\} disabled=\{optimizationMode!=="fixed"\}/);
  assert.match(s,/window.confirm\("Stop this fixed-generation run/);
});
