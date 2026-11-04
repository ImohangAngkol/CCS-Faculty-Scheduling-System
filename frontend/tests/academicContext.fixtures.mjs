import {evaluationFixture} from './currentEvaluation.fixtures.mjs';
// Fictional server responses, never an institutional context provider.
export function academicFixture(mode='current') {
  const data=evaluationFixture(['empty','legacy','unknown','incomplete','zero'].includes(mode)?mode:'current');
  data.schema_version=2;data.contract='ga-result-compatibility-v2';
  const context={kind:'verified-recorded-context',version:1,academic_year:'FICTIONAL-YEAR',term:'FICTIONAL-TERM',
    academic_year_id:'00000000-0000-4000-8000-000000000701',term_id:'00000000-0000-4000-8000-000000000702',scope_id:'00000000-0000-4000-8000-000000000703',
    department:'Fictional Department',dataset_id:'fictional-dataset',dataset_revision:'fictional-revision.1',input_fingerprint:'c'.repeat(64),context_sha256:'9'.repeat(64)};
  data.current_identity.academic_context=context;data.current_identity.context_verification='VERIFIED';
  data.comparison_basis='Same engine, scoring policy, inputs, verified academic context and exact run-start configuration only.';
  for(const run of data.runs){
    if(run.classification==='CURRENT_COMPATIBLE'){
      run.classification='CURRENT';run.academic_context={...context};
      run.provenance={contract:'ga-run-start-provenance-v1',run_start_sha256:'8'.repeat(64),context_sha256:context.context_sha256,started_at:'2026-11-04T00:00:00+08:00'};
    }
  }
  if(mode==='legacy')data.runs[0].reason='ACADEMIC_CONTEXT_CHANGED';
  if(mode==='unknown')data.runs[0].reason='RUN_START_PROVENANCE_NOT_CAPTURED';
  if(mode==='unavailable'){
    data.current_runs=0;data.best=null;
    data.current_identity.context_verification='UNAVAILABLE';data.current_identity.academic_context={kind:'legacy-input-file-set',academic_year:null,term:null};
    data.runs=[{...data.runs[0],classification:'UNKNOWN_COMPATIBILITY',reason:'ACADEMIC_CONTEXT_UNAVAILABLE',fitness:null,chromosome_id:null}];
  }
  return data;
}
