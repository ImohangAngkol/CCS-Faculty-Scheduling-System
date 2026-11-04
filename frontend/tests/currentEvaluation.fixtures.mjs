// Fictional technical identity only; no institutional policy/approval or real resources.
export function evaluationFixture(mode = 'current') {
  const run = {run_id:'00000000-0000-4000-8000-000000000601',state:'COMPLETED',classification:'CURRENT_COMPATIBLE',reason:'SAME_RELEASE_POLICY_AND_INPUTS',generation:2,configuration_fingerprint:'d'.repeat(64),fitness:12.3456789,chromosome_id:'e'.repeat(64)};
  const data = {schema_version:1,contract:'ga-result-compatibility-v1',current_identity:{engine_family:'V1',engine_version:'ga-continuation-v1',engine_fingerprint:'a'.repeat(64),fitness_policy:'preference-policy-2',preference_scoring_version:2,scorer_sha256:'b'.repeat(64),constraint_policy:'v1-source-bound-publication-gate',input_fingerprint:'c'.repeat(64),result_schema_version:1,academic_context:{kind:'verified-recorded-context',academic_year:'FICTIONAL-YEAR',term:'FICTIONAL-TERM'}},coverage_complete:true,current_runs:1,best:run,runs:[run],issues:[],saved_chromosome:{classification:'UNKNOWN_COMPATIBILITY',baseline_eligible:false,reason:'SAVED_BEST_HAS_NO_CAPTURED_PRODUCER_IDENTITY'},comparison_basis:'Same V1 engine, scoring policy and full input fingerprint; verified recorded academic context and configuration fingerprint only.',institutional_authorization:'NOT_ESTABLISHED'};
  if (mode === 'empty') {data.current_runs=0;data.best=null;data.runs=[];}
  if (mode === 'legacy' || mode === 'unknown') {data.current_runs=0;data.best=null;data.runs=[{...run,classification:mode==='legacy'?'LEGACY_INCOMPATIBLE':'UNKNOWN_COMPATIBILITY',reason:mode==='legacy'?'FITNESS_POLICY_CHANGED':'FITNESS_POLICY_NOT_CAPTURED',fitness:null,chromosome_id:null}];}
  if (mode === 'incomplete') {data.coverage_complete=false;data.current_runs=null;data.best=null;data.issues=['ARCHIVED_RECORD_UNREADABLE'];}
  if (mode === 'zero') data.best.fitness=0;
  return data;
}
