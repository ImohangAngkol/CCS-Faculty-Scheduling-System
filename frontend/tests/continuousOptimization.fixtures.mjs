export const readinessFixture=()=>({schema_version:1,contract:'ga-continuous-foundation-v1',availability:'BLOCKED',executable:false,supported_datasets:[],
  input_consumption:'NOT_ESTABLISHED',receipt_capability:'UNVERIFIED_ONLY',institutional_authorization:'NOT_ESTABLISHED',fixed_generations:'EXISTING_PATH_UNCHANGED',
  requirements:['IMMUTABLE_CONSUMPTION_REQUIRED','SCOPED_AUTHORITY_REQUIRED','VERSIONED_WORKER_REQUIRED','RESOURCE_ENFORCEMENT_REQUIRED','RUN_LOCAL_PERSISTENCE_REQUIRED'].map(code=>({code,message:'Fictional readiness example: '+code})),
  lifecycle:{states:['IDLE','STARTING','RUNNING','PAUSING','PAUSED','RESUMING','STOPPING','STOPPED','COMPLETED','FAILED','INTERRUPTED'],implementation:'CONTRACT_ONLY_NO_CONTINUOUS_WORKER',commands:'UNAVAILABLE'},
  safeguards:{enforcement:'NOT_IMPLEMENTED',required:['FICTIONAL_REQUIRED_RESOURCE_BUDGET']},existing_fixed_controls:'Existing fixed controls are separate.',best_so_far:'No continuous chromosome exists.'});
