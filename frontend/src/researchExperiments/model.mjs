export const schema='fictional-research-experiment-v1';
export function validateView(d,run){
 if(d?.schema!==schema||d.run_id!==run||d.production_admission!=='BLOCKED'||d.continuous_ui!=='DISABLED'||d.active_restore!==false||d.institutional_saved_best_promotion!==false||d.seven_day!=='NO_GO'||typeof d.exportable!=='boolean')throw new Error('Experiment contract rejected');
 if(d.exportable&&(d.verification!=='VERIFIED_RECORDED_FICTIONAL_RESULT'||d.record?.run_id!==run||d.record.experiment_id!==d.experiment_id||!/^[a-f0-9]{64}$/.test(d.record_sha256)))throw new Error('Unverified experiment export rejected');
 if(!d.exportable&&(d.record!==null||d.record_sha256!==null))throw new Error('Unverified metrics rejected');
 return d;
}
export function selection(d){
 if(d?.schema!==schema||d.production_admission!=='BLOCKED'||d.contexts?.length!==1||!/^[a-f0-9]{64}$/.test(d.contexts[0]?.selection_key)||!d.contexts[0].context?.dataset?.startsWith('FICTIONAL-'))throw new Error('Server context rejected');
 return d.contexts[0];
}
