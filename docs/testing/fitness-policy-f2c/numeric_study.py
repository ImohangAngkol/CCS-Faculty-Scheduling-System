"""Fictional scalar arithmetic study, not GA execution or scoring activation."""
from decimal import Decimal,localcontext
from fractions import Fraction
import json
import math
from pathlib import Path
import platform
import random
import statistics
import sys
import time

from contract_model import workload_exact

LCM=math.lcm(*range(1,25))


def fixed(actual,targets):
    # Same bounded integer domain as oracle; call sites prevalidate for timings.
    return sum((a-t)**2*(LCM//t) for a,t in zip(actual,targets) if t)


def binary(actual,targets):return math.fsum((a-t)**2/t for a,t in zip(actual,targets) if t)


def decimal28(actual,targets):
    with localcontext() as c:
        c.prec=28
        return sum((Decimal((a-t)**2)/Decimal(t) for a,t in zip(actual,targets) if t),Decimal(0))


def measure(function,actual,targets,repeat=7,iterations=1000):
    for _ in range(100):function(actual,targets)
    values=[]
    for _ in range(repeat):
        start=time.perf_counter_ns()
        for _ in range(iterations):function(actual,targets)
        values.append((time.perf_counter_ns()-start)/iterations)
    return dict(unit='ns_per_call',repeat=repeat,iterations=iterations,warmup_calls=100,values=values,
        median=statistics.median(values),sample_stdev=statistics.stdev(values),min=min(values),max=max(values))


def main():
    rng=random.Random(4827);rows=[];pairs=0;disagreements=0;max_error=Fraction()
    for n in (2,12,24):
        targets=[rng.randrange(1,25) for _ in range(n)]
        actual=[rng.randrange(0,41) for _ in range(n)]
        exact=workload_exact(actual,targets)
        assert Fraction(fixed(actual,targets),LCM)==exact
        rows.append(dict(fictional_cohort_size=n,actual=actual,targets=targets,exact=str(exact),
            timings={name:measure(fn,actual,targets) for name,fn in (
                ('Fraction_oracle_with_domain_checks',workload_exact),('integer_numerator_prevalidated',fixed),
                ('binary64_fsum_prevalidated',binary),('decimal28_local_context_prevalidated',decimal28))}))
        for _ in range(1000):
            a=[rng.randrange(0,41) for _ in range(n)];b=[rng.randrange(0,41) for _ in range(n)]
            x,y=workload_exact(a,targets),workload_exact(b,targets)
            fx,fy=binary(a,targets),binary(b,targets)
            max_error=max(max_error,abs(Fraction(fx)-x),abs(Fraction(fy)-y))
            assert Fraction(fixed(a,targets),LCM)==x and Fraction(fixed(b,targets),LCM)==y
            pairs+=1;disagreements+=((x>y)-(x<y)!=(fx>fy)-(fx<fy))
    # Input bounds alone do not bound a future weighted aggregate total.
    fbase=Fraction(2**53);first=fbase+Fraction(1,3);second=fbase+Fraction(2,3)
    with localcontext() as c:
        c.prec=28;dbase=Decimal(10)**30
        dx,dy=dbase+Decimal(1)/3,dbase+Decimal(2)/3
    assert first<second and float(first)==float(second) and dx==dy
    output=dict(scope='F2C fictional arithmetic only; not a GA speedup, policy calibration or activation',python=sys.version,
        platform=platform.platform(),seed=4827,lcm_1_to_24=LCM,measurements=rows,random_pairs=pairs,
        sampled_order_disagreements=disagreements,maximum_sampled_float_absolute_error=str(max_error),
        exact_integer_fast_path_all_samples_agree=True,
        adversarial=dict(binary64_distinct_exact_totals_collapse_to_tie=True,decimal28_distinct_exact_totals_collapse_to_tie=True,
            qualification='These aggregate totals exceed ordinary fixture workload totals; no production misranking is claimed.'),
        limitations=['Prevalidated kernels exclude input checks; Fraction oracle includes them.',
            'No total-fitness calibration, memory, GA runtime or native measurements.',
            'Canonical JSON/digest/large-integer limits must be tested separately.',
            'Finite decimal precision and binary64 are not a universally exact comparison contract.'])
    path=Path(sys.argv[1]);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(output,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=path.name,random_pairs=pairs,sampled_order_disagreements=disagreements,
        maximum_sampled_float_absolute_error=str(max_error),lcm=LCM)))


if __name__=='__main__':main()
