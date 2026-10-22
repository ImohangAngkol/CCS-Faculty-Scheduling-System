// Fictional HTTP provider simulation ONLY; never institutional authority evidence.
import {makeAssessment as priorAssessment} from './externalReadiness.fixtures.mjs';
import {EVIDENCE_LABEL} from '../src/api/externalEvidence.ts';
import {handoffIdentity} from '../src/api/externalSchedules.ts';
export async function makeAssessment(source,mappings,metadata,mode={}) {
 const result=await priorAssessment(source,mappings,metadata,mode);
 const outcome=mode.trustOutcome??(mode.ready?'VERIFIED':'PROVIDER_UNAVAILABLE'),verified=outcome==='VERIFIED';
 const evidence_trust={version:'d8.1',label:EVIDENCE_LABEL,outcome,evidence_id:verified?'fictional-evidence':null,evidence_revision:verified?'fictional-evidence.1':null,verified_issuer:verified?'fictional-issuer':null,issuing_organization:verified?'fictional-college':null,evidence_type:verified?'provider_attestation':null,verification_method:verified?'trusted_provider':null,policy_revision:verified?'fictional-policy.1':null,policy_digest:verified?'d'.repeat(64):null,policy_provenance:verified?'fictional-authorization':null,authority_organizations:verified?['fictional-college']:[],authority_terms:verified?['Fictional first term']:[],authority_subjects:verified?['SYN-GEC101']:[],source_match:verified,term_match:verified,coverage_mode:verified?'authorized_revision':null,verified_at:verified?'2026-10-23T01:00:00Z':null,valid_until:verified?'2099-01-01T00:00:00Z':null,revocation_status:verified?'good':outcome==='REVOKED'?'revoked':'unknown',rows:source.rows.map(r=>({source_row:r.source_row,outcome:verified?'VERIFIED':'UNVERIFIED'})),findings:verified?[]:[{code:mode.code??outcome,explanation:'Fictional provider finding: evidence does not establish current scoped authority.',action:'Obtain scoped current evidence through an authorized provider.',source_row:null}],institutionally_confirmed:false,activated:false};
 result.evidence_trust=evidence_trust;
 const {assessment_fingerprint,assessed_at,expires_at,assessment_receipt,...content}=result;
 return {...result,assessment_fingerprint:(await handoffIdentity(content)).replace(/^d5-/,'d7-')};
}
