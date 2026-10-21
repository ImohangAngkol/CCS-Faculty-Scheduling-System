import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import axios from 'axios';
import {apiClient} from '../src/services/apiSession.ts';
import {prepareExternalHandoff,handoffIdentity,handoffSchema} from '../src/api/externalSchedules.ts';
import {makeSource,inputs} from './externalReview.fixtures.mjs';
import {makeHandoff} from './externalHandoff.fixtures.mjs';
async function post(fn,action){const saved=apiClient.post;apiClient.post=fn;try{await action();}finally{apiClient.post=saved;}}

test('handoff preparation always sends the current receipt and maps, never a filtered projection',async()=>{
  const source=makeSource(),mappings=[{source_row:2,room_id:'room-b'}],signal=new AbortController().signal;let calls=0;
  await post(async(url,body,options)=>{calls++;assert.ok(url.endsWith('/handoff'));assert.deepEqual(body,{review_token:source.review_token,mappings});assert.equal(options.signal,signal);return {data:await makeHandoff(source,mappings)};},
    async()=>{await prepareExternalHandoff(source,mappings,signal);await prepareExternalHandoff(source,mappings,signal);assert.equal(calls,2);});
});
test('old previews without receipts cannot prepare output',async()=>{
  await post(()=>assert.fail('No request expected'),async()=>assert.rejects(prepareExternalHandoff({...makeSource(),review_token:null},[]),/Preview the source again/));
});
test('tampered, truncated, duplicate and swapped original rows fail provenance even with a recomputed fingerprint',async()=>{
  const source=makeSource();
  for(const change of [d=>d.review.source_sha256='c'.repeat(64),d=>d.review.rows.pop(),d=>d.review.rows[0].source_row=99,d=>d.review.rows[0].original.notes='substituted',d=>d.review.rows[0]=d.review.rows[1]]){
    const value=await makeHandoff(source);change(value);value.preview_id=await handoffIdentity(value.review);
    await post(async()=>({data:value}),async()=>assert.rejects(prepareExternalHandoff(source,[]),/provenance/));
  }
});
test('fingerprint binds resource IDs and discrepancies, not only original file hash',async()=>{
  for(const change of [d=>d.review.rows[0].discrepancies=[],d=>d.review.rows[1].room.id='another-id',d=>d.preview_id='d5-'+'f'.repeat(64)]){
    const value=await makeHandoff();change(value);
    await post(async()=>({data:value}),async()=>assert.rejects(prepareExternalHandoff(makeSource(),[]),/identity/));
  }
});
test('approval, activation, missing warning label and malformed timestamps fail the DTO',async()=>{
  const value=await makeHandoff();
  for(const extra of [{approved:true},{activated:true},{persisted:true},{label:'Approved schedule'},{revalidated_at:'unknown'},{preview_id:'session-token'}])assert.equal(handoffSchema.safeParse({...value,...extra}).success,false);
});
test('invalid and unresolved rows remain present in the complete handoff',async()=>{
  await post(async()=>({data:await makeHandoff()}),async()=>{
    const value=await prepareExternalHandoff(makeSource(),[]);assert.equal(value.review.rows.length,4);
    assert.equal(value.review.rows[3].status,'invalid');assert.equal(value.review.rows[0].instructor.state,'ambiguous');
    assert.ok(value.review.rows.some(r=>r.discrepancies.some(d=>d.code==='ROOM_OVERLAP')));
  });
});
test('ASCII JSON fingerprint matches server canonical ordering and Unicode surrogate escapes',async()=>{
  const value={z:'Fictional caf\u00e9 \ud83e\uddea\n<script>',a:[{b:1,a:false}]};
  const canonical='{"a":[{"a":false,"b":1}],"z":"Fictional caf\\u00e9 \\ud83e\\uddea\\n<script>"}';
  assert.equal(await handoffIdentity(value),'d5-'+createHash('sha256').update(canonical).digest('hex'));
  const source=makeSource([{...inputs[0],notes:value.z}]);assert.ok((await makeHandoff(source)).preview_id.startsWith('d5-'));
});
test('stale, unauthorized, invalid and unavailable responses preserve HTTP failure instead of output',async()=>{
  for(const status of [401,403,409,413,422,503]){
    const error=new axios.AxiosError('synthetic',undefined,undefined,undefined,{status});
    await post(async()=>{throw error;},async()=>assert.rejects(prepareExternalHandoff(makeSource(),[]),value=>value===error));
  }
});
