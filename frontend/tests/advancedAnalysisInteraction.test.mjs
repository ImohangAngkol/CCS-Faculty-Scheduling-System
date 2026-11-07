import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {barAppearance,chartNumber} from '../src/services/analysisChartPresentation.ts';

for(const n of [null,NaN,Infinity])test(`unavailable chart value ${n} is never a zero`,()=>{
  assert.equal(chartNumber(n),null);assert.equal(barAppearance(n,'satisfaction','#0f766e').status,'Unavailable');
});
for(const n of [0,39,39.99])test(`low satisfaction ${n} is descriptive and highlighted`,()=>{
  assert.equal(barAppearance(n,'satisfaction','#0f766e').fill,'#9a3412');
  assert.match(barAppearance(n,'satisfaction','#0f766e').status,/descriptive/);
});
for(const n of [40,70,100])test(`satisfaction ${n} preserves its normal series color`,()=>assert.equal(barAppearance(n,'satisfaction','#0f766e').fill,'#0f766e'));
test('preparations highlight only above an explicit captured reference',()=>{
  assert.equal(barAppearance(3,'preparations','#0f766e',2).fill,'#9a3412');
  for(const ref of [null,NaN,Infinity])assert.equal(barAppearance(3,'preparations','#0f766e',ref).fill,'#0f766e');
  assert.equal(barAppearance(2,'preparations','#0f766e',2).fill,'#0f766e');
});
test('diverging deviations have distinct above below and zero presentations',()=>{
  assert.equal(barAppearance(-.5,'deviation','base').fill,'#0369a1');
  assert.equal(barAppearance(.5,'deviation','base').fill,'#9a3412');
  assert.equal(barAppearance(0,'deviation','base').fill,'#475569');
});
test('numeric display accepts exact zero without string coercion',()=>{
  assert.equal(chartNumber(0),0);assert.equal(chartNumber('0'),null);assert.equal(chartNumber(1.5),1.5);
});
test('all faculty charts connect selection without changing progress or scoring',async()=>{
  const s=await readFile(new URL('../src/components/ga/AdvancedAnalysis.tsx',import.meta.url),'utf8');
  assert.equal((s.match(/\{\.\.\.facultyChart\}/g)||[]).length,5); // Three dimension charts plus four individual charts.
  for(const feature of ['entry.payload?.faculty','role={interactive?"button"','event.key==="Enter"','<LabelList','<ReferenceDot','Weekly contact-hour totals','recordedBest','Best-so-far chromosome indicator'])assert.ok(s.includes(feature),feature);
  assert.doesNotMatch(s,/setInterval|dangerouslySetInnerHTML|method:.*POST/);
});
