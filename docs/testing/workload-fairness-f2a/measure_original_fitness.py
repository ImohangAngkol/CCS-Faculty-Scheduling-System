"""Separate original eight-component scorer timing on one fictional control.

Not comparable to full-engine latency or a measured integrated replacement.
"""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent


def main():
    sys.path.insert(0,str(ROOT/'backend'))
    from benchmarks.retention_runtime import runtime,data_guard
    from benchmarks import scaled_python as bench
    runtime()
    from fictional_schedules import SCENARIOS,templates,snapshot,arrange
    engine,fitness,inputs,Setting,*_=runtime()
    before=random.getstate();start=datetime.now(timezone(timedelta(hours=8)))
    try:
        values=templates(SCENARIOS[0]);pinned=snapshot(values);reduced=engine.reduced_templates(pinned,values)
        candidate=arrange(reduced,(0,1));engine.admit(candidate,pinned,reduced)
        with bench.synthetic_scoring(values,[],Setting().to_dict()),data_guard(),bench.no_io():
            token=inputs.set(engine.freeze(values))
            try:
                tick=time.perf_counter_ns();total,components=fitness.faculty_preference_fitness(candidate,return_breakdown=True)
                cold=(time.perf_counter_ns()-tick)/1000
                assert total==components['teaching_load_balance']==500
                for _ in range(100):fitness.faculty_preference_fitness(candidate,return_breakdown=True)
                samples=[]
                for _ in range(7):
                    tick=time.perf_counter_ns()
                    for _ in range(100):fitness.faculty_preference_fitness(candidate,return_breakdown=True)
                    samples.append((time.perf_counter_ns()-tick)/1000/100)
            finally:inputs.reset(token)
    finally:random.setstate(before)
    folder=BASE/(start.strftime('%Y%m%dT%H%M%S%f+0800')+'-original-timing');folder.mkdir(exist_ok=False)
    record=dict(started_at=start.isoformat(),finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),python=sys.version,platform=platform.platform(),
        original_function='genetic_algorithm.operators.FitnessFunction.faculty_preference_fitness',return_breakdown=True,
        faculty=2,offerings=2,teaching_units=[2,2],targets=[24,24],original_total=total,components=components,
        cold_us=cold,warmup_calls=100,repetitions=7,calls_per_repetition=100,us_per_call=samples,
        median_us=statistics.median(samples),sample_stdev_us=statistics.stdev(samples),mean_us=statistics.mean(samples),min_us=min(samples),max_us=max(samples),
        global_rng_restored=True,scope='Original full eight-component scorer with already frozen fictional inputs. Preparation, construction, admission, freezing and evidence writes excluded; no candidate scorer integrated and no engine speedup measured.',
        command=[sys.executable,'-B',str(Path(__file__).resolve())])
    with (folder/'original-fitness-timing.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=folder.relative_to(BASE).as_posix(),median_us=record['median_us'],sample_stdev_us=record['sample_stdev_us'],original_score=total)))


if __name__=='__main__':main()
