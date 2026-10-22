// Synthetic HTTP policy output only. READY simulates an injected trusted test verifier.
import {emptyCompletion,READINESS_LABEL} from '../src/api/externalReadiness.ts';
import {handoffIdentity} from '../src/api/externalSchedules.ts';
import {makeProjection} from './externalReview.fixtures.mjs';
export function completeMetadata(source) {
 const value=emptyCompletion(source);Object.assign(value,{supplier:'Fictional College',source_reference:'Fictional memo',source_revision:'Example 1',evidence_reference:'Fictional evidence',academic_year:'2026-2027',term:'Fictional first term',effective_start:'2026-08-03',effective_end:'2026-12-18',timezone:'Asia/Manila',recurrence:'weekly',exceptions:'none_reported'});
 value.rows.forEach(r=>Object.assign(r,{title:'Fictional completed title',component:'external_meeting',shared:'single_section',room_applicability:'not_applicable',instructor_applicability:'not_applicable',evidence_reference:'Fictional row evidence'}));return value;
}
export async function makeAssessment(source,mappings,metadata,mode={}) {
 const effective_review=structuredClone(makeProjection(source,mappings));effective_review.legacy=source.legacy??null;
 effective_review.rows.forEach(row=>{const completion=metadata.rows.find(r=>r.source_row===row.source_row);if(completion?.title)row.original.title=completion.title;if(completion?.proposed_meeting)Object.assign(row.original,completion.proposed_meeting);delete row.original.reason;delete row.original.evidence_reference;row.calendar_supported=!!row.original.start&&row.original.start!=='invalid';});
 const findings=mode.ready?[]:[{code:mode.missing?'MISSING_TERM':'AUTHORITATIVE_VERIFICATION_REQUIRED',severity:'blocker',field:mode.missing?'term':'verification',source_row:null,related_rows:[],explanation:'Fictional blocker: complete metadata is not trusted institutional verification.',action:'Obtain authorized source evidence and policy; assess again.'}];
 const value={policy_version:'d7.1',label:READINESS_LABEL,status:mode.ready?'READY':'BLOCKED',approved:false,activated:false,persisted:false,metadata_origin:'administrator_provided',verification_status:mode.ready?'verified_for_readiness':'unavailable',verification_reference:mode.ready?'Fictional trusted evidence':null,authority_policy_version:mode.ready?'fictional-policy.1':null,metadata:structuredClone(metadata),source_fingerprint:'a'.repeat(64),input_fingerprint:'c'.repeat(64),reference_digest:effective_review.reference_digest,blocker_count:findings.length,warning_count:0,findings,effective_review,original_row_count:source.rows.length};
 return {...value,assessment_fingerprint:(await handoffIdentity(value)).replace(/^d5-/,'d7-'),assessed_at:'2026-10-22T12:00:00Z',expires_at:'2099-01-01T00:00:00Z',assessment_receipt:'public-d7-synthetic-receipt'};
}
