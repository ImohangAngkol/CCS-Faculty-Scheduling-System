import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {apiClient} from '../src/services/apiSession.ts';
import {validateDetail,researchDetail,researchEvents,researchRuns} from '../src/api/researchObservations.ts';
import {run,other,hash,safety,detail} from './researchObservations.fixtures.mjs';
test('exact zero and bounded typed provenance survive validation',()=>assert.equal(validateDetail(detail,run).overview.best_so_far_fitness,0));
for(const mode of ['run','point-run','point-order','point-increase','availability','extra','operational','infinite'])test('reject inconsistent observation '+mode,()=>{
 const d=structuredClone(detail);
 if(mode==='run')d.overview.run_id=other;
 if(mode==='point-run')d.fitness.points[0].run_id=other;
 if(mode==='point-order')d.fitness.points[1].generation=0;
 if(mode==='point-increase')d.fitness.points[1].best_ever_fitness=1;
 if(mode==='availability')d.fitness.availability='UNAVAILABLE_NOT_RECORDED';
 if(mode==='extra')d.secret='forbidden';
 if(mode==='operational')d.operational_controls=true;
 if(mode==='infinite')d.overview.best_so_far_fitness=Infinity;
 assert.throws(()=>validateDetail(d,run));
});
test('missing metrics remain explicit rather than becoming zero',()=>{const d=structuredClone(detail);d.overview.best_so_far_fitness=null;d.fitness={availability:'UNAVAILABLE_NOT_RECORDED',points:[]};assert.equal(validateDetail(d,run).overview.best_so_far_fitness,null);});
test('GET wrappers forward cancellation and bounded timeout',async()=>{const old=apiClient.get,signal=new AbortController().signal;try{apiClient.get=async(url,options)=>{assert.equal(options.signal,signal);assert.equal(options.timeout,8000);return {data:detail};};assert.equal((await researchDetail(run,signal)).overview.run_id,run);}finally{apiClient.get=old;}});
test('telemetry cross-context/run and cursor reuse are rejected',async()=>{const old=apiClient.get;try{apiClient.get=async()=>({data:{...safety,run_id:run,context_id:hash,items:[{run_id:other,sequence:1,observed_at:1}],total:1,next_after:null}});await assert.rejects(researchEvents(run,0,hash));}finally{apiClient.get=old;}});
for(const mode of ['duplicate','offset','total','cursor'])test('reject inconsistent run page '+mode,async()=>{
 const old=apiClient.get;try{const page={...safety,items:[detail.overview],total:1,offset:0,next_offset:null};
 if(mode==='duplicate'){page.items.push(detail.overview);page.total=2;}
 if(mode==='offset')page.offset=1;
 if(mode==='total')page.total=0;
 if(mode==='cursor')page.next_offset=1;
 apiClient.get=async()=>({data:page});await assert.rejects(researchRuns());
 }finally{apiClient.get=old;}
});
test('missing fictional context is rejected',()=>{const d=structuredClone(detail);delete d.provenance.context.term;assert.throws(()=>validateDetail(d,run));});
test('console lifecycle is bounded cancellable keyed and read-only',async()=>{
 const s=await readFile(new URL('../src/pages/ResearchConsole.tsx',import.meta.url),'utf8');
 assert.match(s,/polls\+\+<6/);assert.match(s,/10000/);assert.match(s,/clearTimeout\(timer\)/);assert.match(s,/abort\.abort\(\)/);assert.match(s,/key=\{user.id\}/);assert.match(s,/key=\{`\$\{selected\}:\$\{key\}`\}/);assert.match(s,/if\(abort.signal.aborted\)return/);assert.doesNotMatch(s,/dangerouslySetInnerHTML|\.post\(|\.put\(|\.delete\(/);
});
test('router provides authenticated console and dashboard link',async()=>{const r=await readFile(new URL('../src/routes/AppRoutes.tsx',import.meta.url),'utf8');const l=await readFile(new URL('../src/layouts/AdminLayout.tsx',import.meta.url),'utf8');assert.match(r,/path="\/research\/runs"/);assert.match(l,/Research observations/);});
