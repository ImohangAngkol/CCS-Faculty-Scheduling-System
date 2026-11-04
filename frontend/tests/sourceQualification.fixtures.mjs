export const qualificationFixture=()=>({
  contract:'ga-source-qualification-inspection-v1',qualification:'BLOCKED',eligible_for_current:false,
  institutional_approval:'NOT_ESTABLISHED',source_metadata:null,input_fingerprint:'c'.repeat(64),
  file_set_stable_during_inspection:true,cached_tables:[{source:'offerings_source',status:'MATCH',row_count:2}],
  reasons:['INSTITUTIONAL_SOURCE_NOT_CONFIGURED','RUN_CONSUMPTION_BINDING_UNAVAILABLE','FULL_TRANSFORMED_MODEL_MAPPING_UNVERIFIED'],
  scope:'Fictional intercepted diagnostic only. No institutional approval or GA execution.'
});
