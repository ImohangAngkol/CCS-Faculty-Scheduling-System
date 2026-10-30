"""Read-only preservation/privacy checks; update only this audit's manifest."""
import ast
from collections import Counter
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
OWN={'backend/tests/audit/test_thesis_correctness.py','docs/thesis-functional-correctness-audit.md','docs/thesis-objective-traceability.md'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for k,v in value.items():yield str(k);yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==1691 and all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in baseline.items()),'PRESERVATION_MISMATCH_STOP_NO_REPAIR'
    assert sum(p.startswith('backend/data/') for p in baseline)==23
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True).strip()
    assert git('rev-parse','HEAD')=='1423812e13a5791a550c893ef6b17bfef4b4ebfb' and git('branch','--show-current')=='main'
    assert not git('diff','--cached','--name-only')
    tracked=set(git('diff','--name-only').splitlines());assert tracked=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    own=set(git('ls-files','--others','--exclude-standard').splitlines())-set(baseline)
    assert OWN<=own and all(p in OWN or p.startswith('docs/testing/thesis-functional-audit/') for p in own),'UNEXPECTED_PATH_STOP'
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import ENCODED,URI,PEM,SENSITIVE
    patterns=[ENCODED,URI,PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    latest={};attempts=[];artifacts=[]
    for relative in sorted(own-{'docs/testing/thesis-functional-audit/manifest.json'}):
        path=ROOT/relative;assert path.suffix in {'.py','.json','.md'}
        text=path.read_text(encoding='utf-8');assert all(line==line.rstrip() for line in text.splitlines()),relative
        values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            data=json.loads(text);values=list(strings(data))
            if path.name=='command.json':
                assert not any(SENSITIVE.search(line) for key in ('stdout','stderr') for line in data.get(key,'').splitlines()),'SENSITIVE_LOG_WITHHELD'
                latest[data['selection']]=(relative,data)
                attempts.append({'path':relative,'selection':data['selection'],'exit_code':data['exit_code'],
                    'summary':data['stdout'].splitlines()[-1] if data['selection']!='frontend' else 'Node summary preserved in command.json'})
        assert not any(pattern.search(value) for pattern in patterns for value in values),'SENSITIVE_VALUE_WITHHELD'
        artifacts.append({'path':relative,'sha256':sha(path),'bytes':path.stat().st_size})
    assert set(latest)=={'audit','engine','workflow','metrics','frontend'}
    tests={}
    for key,expected in [('audit',33),('engine',83),('workflow',48),('metrics',23)]:
        path,data=latest[key];assert data['exit_code']==0 and re.search(r'\b'+str(expected)+r' passed\b',data['stdout'])
        assert not re.search(r'\b[1-9]\d* (failed|errors?|skipped)\b',data['stdout'])
        tests[key]={'path':path,'passed':expected,'failed':0,'skipped':0,'scope':'Fictional/schema-only; audit includes explicit gap characterizations'}
    path,data=latest['frontend'];assert data['exit_code']==0 and re.search(r'\bpass 99\b',data['stdout']) and re.search(r'\bfail 0\b',data['stdout'])
    tests['frontend']={'path':path,'passed':99,'failed':0,'scope':'Node contracts, no browser or live HTTP'}
    failures=[a for a in attempts if a['exit_code']!=0]
    assert len(failures)==2 and all(a['selection']=='workflow' for a in failures)
    observed=ROOT/tests['audit']['path'];observed=observed.parent
    read=lambda name:json.loads((observed/(name+'.json')).read_text(encoding='utf-8'))
    assert read('fairness-counterexample')['workload_penalty_balanced']==500 and read('fairness-counterexample')['workload_penalty_concentrated']==475
    assert read('legacy-roster-coverage')['runtime_members_from_original_loop']==1
    assert read('availability-reset')['room_boolean_reopened'] and not read('availability-reset')['section_boolean_reopened']
    for field in ('admin','research','extension'):
        value=read('nonteaching-'+field);assert value['active_fixed_input'] and value['workload_penalty_with_release']==0 and value['workload_penalty_without_release']==500 and value['formal_adviser_alignment']=='UNVERIFIED'
    matrix=json.loads((BASE/'traceability.json').read_text(encoding='utf-8'))
    assert matrix['formal_alignment']=='UNVERIFIED' and len(matrix['rows'])==42 and len({r['id'] for r in matrix['rows']})==42
    for row in matrix['rows']:
        assert row['status'] in matrix['status_definitions']
        for source in row['source'].split('; '):
            if source.startswith(('backend/','frontend/','docs/')):assert (ROOT/source.split(':')[0]).is_file(),source
    previous=0
    for name in ('ga-performance-phase2','ga-performance-phase3','ga-memory-study','ga-retention-phase5','ga-reconstruction-phase6','dashboard-d15'):
        manifest=json.loads((ROOT/'docs/testing'/name/'manifest.json').read_text(encoding='utf-8'))
        for entry in manifest['artifacts']:
            assert sha(ROOT/entry['path'])==entry['sha256'],'HISTORICAL_ARTIFACT_MISMATCH'
            previous+=1
    subprocess.run(['git','diff','--check'],cwd=ROOT,env=env,check=True)
    subprocess.run(['git','diff','--cached','--check'],cwd=ROOT,env=env,check=True)
    assert all(sha(ROOT/p)==h for p,h in baseline.items()),'POST_GIT_PRESERVATION_MISMATCH'
    report={'milestone':'Thesis objectives and functional correctness audit','recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'source_HEAD':git('rev-parse','HEAD'),'python':sys.version,'platform':platform.platform(),
        'formal_thesis_alignment':'UNVERIFIED','adviser_approval_claimed':False,'working_requirements_source':'User current clarification and project documents, not approved manuscript',
        'planned_methodology':'DSRM','working_scope_discrepancy':'Admin/research/extension loads are active fixed inputs despite the user-stated exclusion; no policy change authorized or made',
        'preserved_preexisting_paths':1691,'protected_academic_files_preserved':23,'existing_files_modified_by_audit':0,
        'preexisting_tracked_modifications_unchanged':sorted(tracked),'Git_index_HEAD_preserved':True,'new_file_inventory':sorted(own|{'docs/testing/thesis-functional-audit/manifest.json'}),
        'new_file_type_counts':dict(Counter(Path(p).suffix for p in own|{'docs/testing/thesis-functional-audit/manifest.json'})),
        'artifacts':artifacts,'historical_artifact_entries_reverified':previous,'final_tests':tests,'backend_passed':187,'frontend_contracts_passed':99,
        'all_test_attempts':attempts,'historical_nonzero_attempts_preserved':failures,'traceability_status_counts':dict(Counter(r['status'] for r in matrix['rows'])),
        'gap_probes_are_not_requirement_acceptance':True,'privacy_findings':0,
        'privacy_scope':'No institutional row parsing. New records are fictional numeric/structural findings; complete/truncated receipt, key and credential patterns scanned. No private stdin/session copied.',
        'production_algorithm_settings_policy_changes':0,'PostgreSQL_operations':0,'dependencies_installed':0,'staged_files':0,'commits_pushes':0,
        'actual_browser_verification':'NOT_RUN','production_build_lint':'NOT_RUN_NO_FRONTEND_OR_PRODUCTION_EDIT','institutional_activation':'BLOCKED',
        'remaining_limitations':['Approved manuscript and policy thresholds unavailable','Roster AST probe is not a real roster import','No institutional quality/usability study','Fictional in-process FastAPI/SQLite and Node contracts, no fresh browser or PostgreSQL acceptance'],
        'hash_convention':'Raw bytes; manifest excludes itself; no prior artifacts rewritten'}
    encoded=(json.dumps(report,indent=2)+'\n').encode();assert not any(p.search(encoded.decode()) for p in patterns)
    (BASE/'manifest.json').write_bytes(encoded)
    print(json.dumps({'preserved_existing_paths':1691,'artifacts_hashed':len(artifacts),'new_files':len(report['new_file_inventory']),
        'backend_passed':187,'frontend_contracts_passed':99,'privacy_findings':0,'formal_alignment':'UNVERIFIED','historical_artifact_entries_verified':previous}))


if __name__=='__main__':main()
