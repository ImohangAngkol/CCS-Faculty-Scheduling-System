import {test} from 'node:test';import assert from 'node:assert/strict';
import {makeSource} from './externalReview.fixtures.mjs';
import {completeMetadata} from './externalReadiness.fixtures.mjs';
import {makeAssessment} from './externalEvidence.fixtures.mjs';
import {verifyAssessment} from '../src/api/externalReadiness.ts';
import {evidenceTrustSchema,verifyEvidenceCoverage,EVIDENCE_LABEL} from '../src/api/externalEvidence.ts';

for(const outcome of ['PROVIDER_UNAVAILABLE','UNVERIFIED','INVALID','EXPIRED','REVOKED','STALE','UNSUPPORTED'])test('explicit '+outcome+' evidence stays blocked',async()=>{
 const source=makeSource(),meta=completeMetadata(source);const value=await verifyAssessment(await makeAssessment(source,[],meta,{trustOutcome:outcome}),source,meta);
 assert.equal(value.status,'BLOCKED');assert.equal(value.evidence_trust.outcome,outcome);assert.equal(value.evidence_trust.institutionally_confirmed,false);
});
test('fictional VERIFIED provider is distinct from institutional confirmation',async()=>{
 const source=makeSource(),meta=completeMetadata(source);const value=await verifyAssessment(await makeAssessment(source,[],meta,{ready:true}),source,meta);
 assert.equal(value.evidence_trust.label,EVIDENCE_LABEL);assert.equal(value.status,'READY');assert.equal(value.approved,false);
});
test('missing row coverage and forged provider fields are rejected',async()=>{
 const source=makeSource(),meta=completeMetadata(source),value=(await makeAssessment(source,[],meta,{ready:true})).evidence_trust;
 for(const change of [v=>v.rows.pop(),v=>v.rows[0].source_row=999,v=>v.revocation_status='unknown',v=>v.verified_issuer=null,v=>v.valid_until='2020-01-01T00:00:00Z',v=>v.source_match=false]){
  const copy=structuredClone(value);change(copy);assert.throws(()=>verifyEvidenceCoverage(copy,source.rows.map(r=>r.source_row)));
 }
 assert.equal(evidenceTrustSchema.safeParse({...value,raw_provider_response:'not-allowed'}).success,false);
});
test('tampered evidence cannot pass the complete assessment content fingerprint',async()=>{
 const source=makeSource(),meta=completeMetadata(source),value=await makeAssessment(source,[],meta,{ready:true});value.evidence_trust.verified_issuer='forged-issuer';
 await assert.rejects(verifyAssessment(value,source,meta));
});

test('browser evidence sanitizer removes truncated and nested secrets before writes',async()=>{
 const {sanitizeText,sanitizeTree}=await import('./evidencePrivacy.mjs');
 const token='eyJmaWN0aW9uYWwiOiJub3QtcmVhbC1zZWNyZXQifQ...tail.'+'f'.repeat(64);
 for(const text of ["E {'review_token': '"+token+"'}",'fragment '+token,'Authorization: Bearer fictional-private']){const clean=sanitizeText(text);assert.ok(!clean.includes(token));assert.ok(!clean.includes('fictional-private'));}
 assert.equal(sanitizeTree({password:'fictional-private'}).password,'[REDACTED_SESSION_RECEIPT]');
});
