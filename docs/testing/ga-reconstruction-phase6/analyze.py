"""Summarize matching experiments without pooling profiler/allocation timings."""
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import statistics as stats

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent


def distribution(values):
    values=list(values)
    return {'n':len(values),'samples':values,'mean':stats.mean(values),'median':stats.median(values),
            'sample_standard_deviation':stats.stdev(values) if len(values)>1 else None,'min':min(values),'max':max(values)}


def latest(part,count):
    directories=sorted(p for p in BASE.iterdir() if p.is_dir() and p.name.endswith('-'+part))
    path=directories[-1];summary=json.loads((path/'summary.json').read_text())
    assert len(summary['results'])==count and all(r['status']=='SUCCESS' for r in summary['results'])
    records=[json.loads(p.read_text()) for p in sorted(path.glob('[0-9][0-9][0-9]-*.json'))]
    assert len(records)==count and all(r['result']['status']=='SUCCESS' for r in records)
    return path,records


def main():
    inputs={};data={}
    for part,count in [('reference',9),('profile',9),('timing',54),('memory',27)]:
        path,records=latest(part,count);data[part]=records
        for p in sorted(path.glob('*.json')):inputs[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    grouped={}
    for part,records in data.items():
        for r in records:
            key=(r['config']['scenario'],r['config']['seed'],json.dumps(r['result']['parameters'],sort_keys=True))
            projection=r['result']['correctness']
            if key in grouped:assert grouped[key]==projection,'Full differential evidence mismatch'
            else:grouped[key]=projection
    result={'recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'input_sha256':inputs,
            'scope':'Engine intervals only. Timing excludes warm-up, preprocessing, post-verification, profiling and tracing. No persistence. Memory/profile runs never pooled with wall timing.',
            'correctness':{'all_matching_full_state_projections_equal':True,'all_final_populations_original_admitted':True,
                           'warmup_and_trial_fingerprints_equal':True,'reference_original_Phase2_parameters_passes':9},'scenarios':{}}
    for scenario in ('small','medium','large'):
        variants={}
        for variant in ('baseline','parse_cache','calendar_cache'):
            times=[r for r in data['timing'] if r['config']['scenario']==scenario and r['config']['variant']==variant]
            mem=[r['result'] for r in data['memory'] if r['config']['scenario']==scenario and r['config']['variant']==variant]
            profile=next(r['result'] for r in data['profile'] if r['config']['scenario']==scenario and r['config']['variant']==variant)
            metrics={}
            for name,extract in {
                'traced_engine_peak_MiB':lambda r:r['measurement']['engine_allocation_point']['traced_peak_bytes_NOT_RSS']/1048576,
                'traced_engine_live_MiB':lambda r:r['measurement']['engine_allocation_point']['traced_current_bytes']/1048576,
                'tracer_metadata_MiB':lambda r:r['measurement']['engine_allocation_point']['tracer_metadata_bytes']/1048576,
                'sampled_engine_working_set_peak_MiB':lambda r:r['measurement']['process_sampling']['sampled_interval_peak_working_set_bytes']/1048576,
                'engine_end_private_commit_MiB':lambda r:r['measurement']['process_after']['private_commit_bytes_NOT_RSS']/1048576,
                'worker_lifetime_working_set_peak_MiB_includes_warmup_and_copy_probe':lambda r:r['post_release']['process']['process_lifetime_peak_working_set_bytes']/1048576,
                'engine_working_set_delta_MiB':lambda r:(r['measurement']['process_after']['working_set_bytes']-r['measurement']['process_before']['working_set_bytes'])/1048576,
                'engine_private_commit_delta_MiB':lambda r:(r['measurement']['process_after']['private_commit_bytes_NOT_RSS']-r['measurement']['process_before']['private_commit_bytes_NOT_RSS'])/1048576,
                'post_release_traced_KiB':lambda r:r['post_release']['traced_current_bytes']/1024,
                'original_deepcopy_incremental_peak_MiB':lambda r:r['transient_copy_control']['incremental_peak_bytes']/1048576,
                'original_deepcopy_incremental_live_MiB':lambda r:r['transient_copy_control']['incremental_live_bytes']/1048576,
                'traced_engine_seconds_NOT_wall_baseline':lambda r:r['measurement']['engine_seconds'],
            }.items():metrics[name]=distribution(extract(r) for r in mem)
            key=lambda r:(r['config']['seed'],r['config']['repetition'])
            base={key(r):r['result']['measurement']['engine_seconds'] for r in data['timing'] if r['config']['scenario']==scenario and r['config']['variant']=='baseline'}
            own={key(r):r['result']['measurement']['engine_seconds'] for r in times}
            variants[variant]={'timing_seconds':distribution(own.values()),
                'excluded_warmup_seconds':distribution(r['result']['warmup_excluded']['engine_seconds'] for r in times),
                'paired_speedup_baseline_over_variant':distribution(base[k]/own[k] for k in sorted(base)),
                'paired_seconds_saved':distribution(base[k]-own[k] for k in sorted(base)),
                'untraced_process_memory':{
                    'sampled_engine_working_set_peak_MiB':distribution(r['result']['measurement']['process_sampling']['sampled_interval_peak_working_set_bytes']/1048576 for r in times),
                    'engine_end_private_commit_MiB':distribution(r['result']['measurement']['process_after']['private_commit_bytes_NOT_RSS']/1048576 for r in times),
                    'working_set_delta_MiB':distribution((r['result']['measurement']['process_after']['working_set_bytes']-r['result']['measurement']['process_before']['working_set_bytes'])/1048576 for r in times),
                    'private_commit_delta_MiB':distribution((r['result']['measurement']['process_after']['private_commit_bytes_NOT_RSS']-r['result']['measurement']['process_before']['private_commit_bytes_NOT_RSS'])/1048576 for r in times)},
                'memory':metrics,'profile_engine_seconds':profile['measurement']['engine_seconds'],
                'profile_selected_functions':[r for r in profile['measurement']['profile'] if r['function'] in {
                    'admit','validate_publication','payload_to_chromosome','_validate_baseline_components','time_to_minutes',
                    'deepcopy','_deepcopy_dict','_deepcopy_list','_reconstruct','faculty_preference_fitness',
                    '_build_effective_preferences','_legacy_preferences_to_map','_normalize_dashboard_preference','calendar_allowed','parse'}],
                'cache_diagnostics_profile_only':profile['cache_diagnostics_profile_only'],
                'experimental_provenance':profile['provenance']}
        result['scenarios'][scenario]=variants
    result['failures_and_invalid_evidence']=[{'path':p.relative_to(ROOT).as_posix(),'record':json.loads(p.read_text())}
        for p in BASE.glob('*-baseline-profile/validity.json')]
    directory=sorted(p for p in BASE.iterdir() if p.is_dir() and p.name.endswith('-operations'))[-1]
    summary=json.loads((directory/'summary.json').read_text());assert len(summary['results'])==9 and all(r['status']=='SUCCESS' for r in summary['results'])
    operations={};unobserved={}
    for path in sorted(directory.glob('*.json')):
        inputs[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        if path.name=='summary.json':continue
        row=json.loads(path.read_text())['result'];assert row['status']=='SUCCESS'
        unobserved[row['scenario']+'/'+row['variant']]={
            'timing_seconds':distribution(control['engine_seconds'] for control in row['unobserved_engine_controls']),
            'excluded_warmup_seconds':row['excluded_engine_warmup_seconds'],
            'scope':'Three identical-seed warmed repetitions in one fresh variant/scale process; no sampling thread, tracer or profiler. Separate from independent-process, varied-seed timing matrix.'}
        operations[row['scenario']+'/'+row['variant']]={name:{
            metric:distribution(control[metric] for control in controls)
            for metric in ('uninstrumented_seconds','traced_seconds_NOT_wall_baseline','traced_peak_bytes_NOT_RSS',
                           'traced_current_return_held_bytes','post_release_GC_traced_bytes')}
            for name,controls in row['operations'].items()}
        comparison_key=(row['scenario'],row['seed'],json.dumps(row['parameters'],sort_keys=True))
        assert grouped[comparison_key]==row['correctness']
    result['separate_operation_controls']=operations
    result['unobserved_engine_controls']=unobserved
    result['operation_scope']='Three repeated calls per operation from one matching prepared best per variant/scale; not three independent seeds. Traced peaks and uninstrumented call durations are separate invocations.'
    directory=BASE/(datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S%f+0800')+'-analysis');directory.mkdir(exist_ok=False)
    (directory/'analysis.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    for scenario,variants in result['scenarios'].items():
        print(scenario,json.dumps({v:{'time':r['timing_seconds'],'paired_speedup':r['paired_speedup_baseline_over_variant'],
            'traced_peak_MiB':r['memory']['traced_engine_peak_MiB']['median'],
            'WS_peak_MiB':r['memory']['sampled_engine_working_set_peak_MiB']['median'],
            'private_MiB':r['memory']['engine_end_private_commit_MiB']['median']} for v,r in variants.items()}))
    print(directory.relative_to(ROOT).as_posix())


if __name__=='__main__':main()
