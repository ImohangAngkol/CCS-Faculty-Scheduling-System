"""Pure scoring microbenchmarks; no GA, tracemalloc, cProfile or persistence."""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time

from fairness_models import FUNCTIONS

BASE=Path(__file__).resolve().parent


def main():
    start=datetime.now(timezone(timedelta(hours=8)));directory=BASE/(start.strftime('%Y%m%dT%H%M%S%f+0800')+'-timing');directory.mkdir(exist_ok=False)
    before=random.getstate();results=[];order_rng=random.Random(620026)
    for size in (2,12,24):
        targets=[(24,12,6,0)[i%4] for i in range(size)]
        actual=[t//2+(i%3)*2 for i,t in enumerate(targets)]
        samples={k:[] for k in FUNCTIONS};cold={}
        for name,fn in FUNCTIONS.items():
            tick=time.perf_counter_ns();fn(actual,targets);cold[name]=(time.perf_counter_ns()-tick)/1000
            for _ in range(100):fn(actual,targets)
        for _ in range(7):
            names=list(FUNCTIONS);order_rng.shuffle(names)
            for name in names:
                fn=FUNCTIONS[name];tick=time.perf_counter_ns()
                for _ in range(1000):fn(actual,targets)
                samples[name].append((time.perf_counter_ns()-tick)/1000/1000)
        for name,values in samples.items():
            results.append(dict(function=name,faculty_count=size,actual=actual,targets=targets,cold_us=cold[name],
                repetitions=7,calls_per_repetition=1000,warmup_calls=100,us_per_call=values,mean_us=statistics.mean(values),
                median_us=statistics.median(values),sample_stdev_us=statistics.stdev(values),min_us=min(values),max_us=max(values)))
    assert random.getstate()==before
    record=dict(started_at=start.isoformat(),finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),python=sys.version,platform=platform.platform(),
        results=results,global_rng_unchanged=True,scope='Microbenchmark of new pure arithmetic functions INCLUDING argument checks and Fraction construction. Baseline is workload reference arithmetic, not the full original fitness function. Not a GA speedup or exclusive removable-time measurement.',
        profiler_or_allocation_tracing=False,candidate_numeric_type='Exact Fraction; original reference uses original float/ceil arithmetic',
        command=[sys.executable,'-B',str(Path(__file__).resolve())])
    with (directory/'timing.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=directory.relative_to(BASE).as_posix(),measurements=len(results),global_rng_unchanged=True)))


if __name__=='__main__':main()
