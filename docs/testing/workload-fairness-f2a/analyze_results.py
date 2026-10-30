"""Summarize existing fictional evidence; never rerun GA or source data."""
from datetime import datetime,timedelta,timezone
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent


def score(value):return Fraction(value['exact']) if isinstance(value,dict) else Fraction(value)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    commands=[]
    for path in sorted(BASE.glob('*-backend/command.json')):
        record=json.loads(path.read_text())
        if record['exit_code']==0:commands.append(path)
    source=commands[-1].parent;results=[];hashes=[]
    for path in sorted(source.glob('scenario-*.json')):
        data=json.loads(path.read_text());hashes.append(dict(path=path.relative_to(BASE).as_posix(),sha256=sha(path)))
        counts={}
        for name in data['winners']:
            counter=dict(agree=0,opposite=0,original_tie_only=0,candidate_tie_only=0,both_tie=0)
            for a,b in itertools.combinations(data['rows'],2):
                diff=score(a['scores']['original_workload'])-score(b['scores']['original_workload'])
                other=score(a['scores'][name])-score(b['scores'][name])
                if diff==0 and other==0:key='both_tie'
                elif diff==0:key='original_tie_only'
                elif other==0:key='candidate_tie_only'
                elif diff*other>0:key='agree'
                else:key='opposite'
                counter[key]+=1
            counts[name]=counter
        sensitivity={}
        for strength in (0,1,5,25):
            scores=[score(r['scores']['target_relative'])+strength*r['metrics']['positive_target_eligible_zero_count'] for r in data['rows']]
            sensitivity[str(strength)]=[r['actual'] for r,s in zip(data['rows'],scores) if s==min(scores)]
        results.append(dict(scenario=data['scenario'],targets=data['targets'],offered_units=data['offered_teaching_units'],
            hard_valid_assignments_checked=data['explicitly_eligible_assignments_checked'],unique_vectors=data['unique_workload_vectors'],
            winners=data['winners'],pairwise_ranking_vs_original=counts,zero_penalty_sensitivity=sensitivity,
            zero_penalty_scope='Unapproved coefficient in raw target_relative units; only positive-target members with explicit eligible offerings counted. This is not proof of feasible assignment opportunity.'))
    assert len(results)==9
    directory=BASE/(datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S%f+0800')+'-analysis');directory.mkdir(exist_ok=False)
    record=dict(source_command=commands[-1].relative_to(BASE).as_posix(),source_artifact_hashes=hashes,scenarios=results,
        total_hard_valid_fixed_geometry_assignments=sum(r['hard_valid_assignments_checked'] for r in results),
        total_unique_workload_vectors=sum(r['unique_vectors'] for r in results),
        policy='User-reported target-relative fairness and Option B; exact function/weights/zero-target convention not independently approved',
        interpretation='Pairwise agreement is descriptive, not accuracy against a trusted fairness oracle. Enumeration does not cover alternate meeting geometries.',
        recommendation='target_relative is suitable for conditional F2 consideration, not production integration approval',
        production_integration=False)
    with (directory/'analysis.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(path=directory.relative_to(BASE).as_posix(),hard_valid_assignments=record['total_hard_valid_fixed_geometry_assignments'],
        unique_workload_vectors=record['total_unique_workload_vectors'],scenarios=len(results))))


if __name__=='__main__':main()
