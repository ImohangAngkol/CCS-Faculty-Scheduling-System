import {test} from 'node:test';
import assert from 'node:assert/strict';
import {apiClient} from '../src/services/apiSession.ts';
import {getChairAccess,getChairQueue,getChairReview,decideChair,chairError} from '../src/api/chairReviews.ts';
import {getAdjustment} from '../src/api/adjustments.ts';
import {record,review} from './adjustments.fixtures.mjs';

const id='70000000-0000-4000-8000-000000000001';
const decision={id,status:'APPROVED_PENDING_APPLICATION',action:'APPROVE',actor_id:id,department_id:id,explanation:'Fictional explanation <script>unsafe()</script>',decided_at:'2026-10-24T10:00:00+08:00',request_version:2,schedule_revision:record.content.input.revision,constraint_digest:review.constraint_digest,validation:review.validation,provenance:{mandate_reference:'fictional',policy_digest:'a'.repeat(64),scope_reference:'fictional',D11_history_head:'b'.repeat(64),constraint_heads:[],trust_status:'FRESH_D8_D9_D10',schedule_changed:false},payload_digest:'c'.repeat(64),schedule_changed:false};
const detail={request:{...record,status:'SUBMITTED',version:2},faculty_id:id,department_id:id,current_review:review,approval_block:null,can_approve:true,can_reject:true,decision_history:[],schedule_changed:false};
async function intercept(method,data,action,check=()=>{}){const old=apiClient[method];try{apiClient[method]=async(...args)=>{check(...args);return {data};};return await action();}finally{apiClient[method]=old;}}
test('Chair access comes from a verified server capability, not account role',async()=>{
 const value={capability:'department_chair',departments:[{id,label:'Fictional department'}]};assert.deepEqual(await intercept('get',value,()=>getChairAccess(),u=>assert.equal(u,'/api/chair-reviews/access')),value);
});
test('queue filter restricts scope without sending authority claims',async()=>{
 await intercept('get',{items:[]},()=>getChairQueue(id,false),(u,o)=>{assert.equal(u,'/api/chair-reviews');assert.deepEqual(o.params,{department_id:id,include_decided:false});});
});
test('review retains original content, current findings and immutable history',async()=>{assert.deepEqual(await intercept('get',detail,()=>getChairReview(record.id)),detail);});
test('approve and reject bind exact version/revisions and use explicit idempotency',async()=>{
 for(const action of ['approve','reject'])await intercept('post',decision,()=>decideChair(detail,action,decision.explanation,id),(u,b)=>{assert.equal(u,`/api/chair-reviews/${record.id}/${action}`);assert.deepEqual(b,{operation_id:id,expected_version:2,explanation:decision.explanation,content_digest:record.content_digest,schedule_revision:record.content.input.revision,constraint_digest:review.constraint_digest});assert.equal(b.department_id,undefined);assert.equal(b.approved,undefined);});
});
test('faculty sees decision status with original D11 history preserved',async()=>{
 const decided={...record,version:2,status:decision.status,approval:decision.status,base_status:'SUBMITTED',decision};assert.deepEqual(await intercept('get',decided,()=>getAdjustment(record.id)),decided);
});
for(const [name,value] of [['unverified role',{capability:'admin',departments:[]}],['invented grant',{capability:'department_chair',departments:[{id:'name-derived',label:'Guess'}]}]])test('access rejects '+name,async()=>{await assert.rejects(intercept('get',value,()=>getChairAccess()));});
for(const [name,value] of [['applied status',{status:'APPLIED_TO_SCHEDULE'}],['schedule write',{schedule_changed:true}],['contradictory action',{action:'REJECT'}],['unverified provenance',{provenance:{...decision.provenance,trust_status:'UNVERIFIED'}}]])test('decision rejects '+name,async()=>{await assert.rejects(intercept('post',{...decision,...value},()=>decideChair(detail,'approve','explanation',id)));});
test('a fabricated decided faculty row without an audit decision fails closed',async()=>{await assert.rejects(intercept('get',{...record,status:'REJECTED',approval:'REJECTED'},()=>getAdjustment(record.id)));});
test('stale validation and conflict findings remain visible, never a success fallback',async()=>{const v={...detail,can_approve:false,approval_block:{code:'STALE_SCHEDULE_REFERENCE',message:'Reload required.'},current_review:{...review,validation:{...review.validation,conflict_free:false,outcome:'REQUIRES_REVIEW',findings:[{code:'CONFIRMED_GEC_CONFLICT',message:'Conflict'}]}}};assert.deepEqual(await intercept('get',v,()=>getChairReview(record.id)),v);});
test('authority and storage failures propagate',async()=>{const old=apiClient.get;try{for(const status of [401,403,409,503]){apiClient.get=async()=>{throw Object.assign(new Error('unavailable'),{status});};await assert.rejects(getChairAccess(),e=>e.status===status);}}finally{apiClient.get=old;}});

test('Chair errors preserve sanitized authority code without mislabeling the account role',()=>{assert.match(chairError({isAxiosError:true,response:{status:403,data:{detail:{code:'CHAIR_AUTHORITY_REQUIRED',message:'A verified mandate is required.'}}}},'Unavailable'),/CHAIR_AUTHORITY_REQUIRED/);assert.equal(chairError(new Error('private internal message'),'Unavailable'),'Unavailable');});
