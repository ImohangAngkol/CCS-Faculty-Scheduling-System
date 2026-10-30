"""Reproducible numeric analysis of completed Phase 5 records; no GA execution."""
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'docs/testing/ga-retention-phase5'


def summary(values):
    return dict(n=len(values),mean=statistics.mean(values),median=statistics.median(values),
                min=min(values),max=max(values),sample_sd=statistics.stdev(values) if len(values)>1 else None)


def main():
    jobs={};failed=[]
    for path in sorted(BASE.glob('*/*.json')):
        data=json.loads(path.read_text())
        if 'events' not in data or 'config' not in data:continue
        if data['status']=='SUCCESS':jobs[data['config']['name']]=(path,data)
        else:failed.append({'path':path.relative_to(ROOT).as_posix(),'status':data['status']})
    assert len(jobs)==19,'Complete reference, retention and ownership runs first'
    def runs(name):return [e['record'] for e in jobs[name][1]['events'] if e['event']=='run' and e['record']['label']=='measured']
    endpoints={}
    for name in jobs:
        records=runs(name);a=records[0]['after_release_gc'];b=records[-1]['after_release_gc']
        endpoints[name]={'runs':len(records),'seeds':[r['seed'] for r in records],
            'working_set_start_bytes':a['process']['working_set_bytes'],'working_set_end_bytes':b['process']['working_set_bytes'],
            'working_set_delta_bytes':b['process']['working_set_bytes']-a['process']['working_set_bytes'],
            'private_commit_delta_bytes':b['process']['private_commit_bytes_NOT_RSS']-a['process']['private_commit_bytes_NOT_RSS'],
            'traced_start_bytes':a.get('traced_current_bytes'),'traced_end_bytes':b.get('traced_current_bytes'),
            'post_release_models_constant':all(r['after_release_gc']['model_counts']==a['model_counts'] for r in records),
            'sampled_models_and_leases_released':all(r['released_roots']['sampled_model_count_alive']==r['released_roots']['reporting_leases_alive']==0 for r in records)}
    overhead={}
    for scenario in ('small','medium'):
        ram=[r['engine_seconds_with_instrumentation'] for cohort in ('A','B') for r in runs('ram-'+scenario+'-'+cohort) if r['seed']==714]
        light=[r['engine_seconds_with_instrumentation'] for r in runs('light-'+scenario) if r['seed']==714]
        traced=[r['engine_seconds_with_instrumentation'] for r in runs('trace-'+scenario) if r['seed']==714]
        overhead[scenario]={'seed':714,'counter_runs':summary(ram),'light_callback':summary(light),'traced_runs':summary(traced),
                            'counter_over_light_ratio':statistics.mean(ram)/statistics.mean(light),
                            'trace_over_counter_ratio':statistics.mean(traced)/statistics.mean(ram),
                            'scope':'Descriptive matched-seed ratios across sequential fresh cohorts; not randomized causal timing estimates'}
    ownership={}
    for scenario in ('small','medium'):
        prior=runs('ownership-'+scenario+'-retain_last');prototype=runs('ownership-'+scenario+'-final_only')
        pairs=[]
        for a,b in zip(prior,prototype):
            assert a['seed']==b['seed']
            assert (a['best_assignment_sha256'],a['history'],a['final_rng_sha256'])==(b['best_assignment_sha256'],b['history'],b['final_rng_sha256'])
            old=a['before_gc']['traced_peak_bytes_NOT_RSS'];new=b['before_gc']['traced_peak_bytes_NOT_RSS']
            pairs.append({'seed':a['seed'],'retain_last_peak_bytes':old,'final_only_peak_bytes':new,
                          'peak_delta_bytes_prototype_minus_prior':new-old,'assignment_history_rng_parity':True})
        release={}
        for policy in ('retain_last','final_only'):
            end=jobs['ownership-'+scenario+'-'+policy][1]['events'][-1]
            drop=end['report_buffer_release']
            release[policy]={'worker_records_dropped':drop['released_worker_run_records'],
                            'traced_before_drop_bytes':end['end']['traced_current_bytes'],
                            'traced_after_drop_bytes':drop['after_drop_gc']['traced_current_bytes'],
                            'traced_delta_bytes_after_minus_before':drop['after_drop_gc']['traced_current_bytes']-end['end']['traced_current_bytes']}
        ownership[scenario]={'pairs':pairs,'report_buffer_release':release,
                            'scope':'Isolated reporting ownership, no engine copy/scoring changes; execution+validation+probe peaks, two seeds only'}
    inputs=[]
    for path,_ in jobs.values():inputs.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    result={'scope':'Phase 5 descriptive analysis; no leak inference or production speedup/savings claim implied',
            'endpoints':endpoints,'instrumentation_overhead':overhead,'ownership_prototype':ownership,
            'historical_failures':failed,'inputs':inputs}
    directory=BASE/(datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S%f+0800')+'-analysis');directory.mkdir(exist_ok=False)
    (directory/'analysis.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(directory.relative_to(ROOT).as_posix())


if __name__=='__main__':main()
