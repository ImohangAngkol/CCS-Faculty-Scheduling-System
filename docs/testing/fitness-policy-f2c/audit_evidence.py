"""F2C hash/privacy/preservation audit; no data parsing or DB imports.

Initial invocation creates a manifest exclusively. --verify is read-only and
rejects additional unarchived paths; reruns never silently refresh a manifest.
"""
import ast
from collections import Counter
from datetime import datetime,timedelta,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
REPORTS={'docs/fitness-policy-f2c-contract.md','docs/fitness-policy-f2c-call-paths.md'}
HEAD='1423812e13a5791a550c893ef6b17bfef4b4ebfb'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,child in value.items():yield str(key);yield from strings(child)
    elif isinstance(value,list):
        for child in value:yield from strings(child)


def audit():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text(encoding='utf-8'))
    assert len(baseline)==1870 and sum(p.startswith('backend/data/') for p in baseline)==23
    def preserved():
        bad=[p for p,h in baseline.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
        assert not bad,'PRESERVATION_MISMATCH_STOP_NO_REPAIR: '+','.join(bad)
    preserved()
    env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=env,text=True).strip()
    assert git('branch','--show-current')=='main' and git('rev-parse','HEAD')==HEAD
    assert not git('diff','--cached','--name-only')
    assert set(git('diff','--name-only').splitlines())=={'backend/data/faculty_preferences.json','backend/data/ga_settings.json'}
    own=set(git('ls-files','--others','--exclude-standard').splitlines())-set(baseline)
    assert REPORTS<=own and all(p in REPORTS or p.startswith('docs/testing/fitness-policy-f2c/') for p in own),'UNEXPECTED_PATH_STOP'
    spec=importlib.util.spec_from_file_location('f2c_sanitizer',ROOT/'backend/services/evidence_sanitization.py')
    privacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(privacy)
    patterns=[privacy.ENCODED,privacy.URI,privacy.PEM,re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),
        re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')]
    manifest=BASE/'manifest.json';relative_manifest=manifest.relative_to(ROOT).as_posix()
    artifacts=[];commands=[];outcomes={};numeric=None;index=None;engine=None
    for relative in sorted(own-{relative_manifest}):
        path=ROOT/relative;assert path.suffix in {'.json','.md','.py'}
        text=path.read_text(encoding='utf-8');assert all(line==line.rstrip() for line in text.splitlines()),'WHITESPACE_STOP: '+relative
        values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            data=json.loads(text);values=list(strings(data))
            if path.name=='command.json':
                assert not any(privacy.SENSITIVE.search(line) for field in ('stdout','stderr') for line in data.get(field,'').splitlines()),'SENSITIVE_LOG_STOP'
                commands.append(dict(path=relative,selection=data['selection'],exit_code=data['exit_code'],timed_out=data['timed_out']))
            elif path.name=='outcomes.json':outcomes[relative]=(data['selection'],data['counts'],data['collected'],data['exit_code'])
            elif path.name=='numeric.json':numeric=data
            elif path.name=='call-paths.json':index=data
            elif path.name=='engine-identity.json':engine=data
        assert not any(pattern.search(value) for pattern in patterns for value in values),'PRIVACY_FINDING_WITHHELD_STOP'
        artifacts.append(dict(path=relative,sha256=sha(path),bytes=path.stat().st_size))
    assert len(commands)==5 and all(row['exit_code']==0 and not row['timed_out'] for row in commands)
    assert sorted(v[1]['passed'] for v in outcomes.values())==[30,73,80]
    assert all(v[1]['failed']==v[1]['errors']==v[1]['skipped']==0 and v[2]==v[1]['passed'] and v[3]==0 for v in outcomes.values())
    assert numeric and numeric['random_pairs']==3000 and numeric['sampled_order_disagreements']==0
    assert numeric['lcm_1_to_24']==5354228880 and numeric['exact_integer_fast_path_all_samples_agree']
    assert index and len(index['files'])==31 and sum(len(row['calls']) for row in index['files'])==154
    for entry in index['files']:assert sha(ROOT/entry['path'])==entry['sha256'],'INDEX_SOURCE_CHANGED'
    historical=0
    for name in ('ga-performance-phase2','ga-performance-phase3','ga-memory-study','ga-retention-phase5','ga-reconstruction-phase6',
        'dashboard-d15','thesis-functional-audit','faculty-policy-qualification','faculty-cohort-f1','faculty-cohort-f1-5',
        'workload-fairness-f2a','workload-fairness-f2b'):
        previous=json.loads((ROOT/'docs/testing'/name/'manifest.json').read_text(encoding='utf-8'))
        for entry in previous['artifacts']:
            assert sha(ROOT/entry['path'])==entry['sha256'],'HISTORICAL_ARTIFACT_MISMATCH_STOP'
            historical+=1
    prior=json.loads((ROOT/'docs/testing/workload-fairness-f2b/manifest.json').read_text(encoding='utf-8'))
    record=next(x for x in prior['artifacts'] if x['path'].endswith('135345404946+0800-backend/shared_scorer_boundary.json'))
    default=json.loads((ROOT/record['path']).read_text(encoding='utf-8'))
    assert engine['v1']==default['current_engine_fingerprint'] and engine['v2']==default['current_V2_fingerprint']
    for report in REPORTS:
        for link in re.findall(r'\]\(([^)]+)\)',(ROOT/report).read_text(encoding='utf-8')):
            if not link.startswith(('http:','https:','#')):
                destination=((ROOT/report).parent/link.split('#')[0]).resolve()
                assert destination==manifest or destination.is_file(),'BROKEN_LINK_STOP: '+link
    for args in [('diff','--check'),('diff','--cached','--check')]:
        reply=subprocess.run(['git',*args],cwd=ROOT,env=env,capture_output=True,text=True)
        assert reply.returncode==0,'GIT_WHITESPACE_STOP_OUTPUT_WITHHELD'
    preserved()
    inventory=sorted(own|{relative_manifest})
    record=dict(milestone='F2C versioned fitness policy contract',source_HEAD=HEAD,branch='main',
        recorded_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),python=sys.version,platform=platform.platform(),
        status='CONTRACT_INVESTIGATION_COMPLETE_NO_PRODUCTION_INTEGRATION',
        recommendation='CONTRACT_REVIEW_GO_PRODUCTION_INTEGRATION_NO_GO_PENDING_RELEASE_AND_POLICY_GATES',
        new_file_inventory=inventory,new_file_type_counts=dict(Counter(Path(p).suffix for p in inventory)),artifacts=artifacts,
        commands=commands,pytest_outcomes={p:dict(selection=v[0],counts=v[1],collected=v[2],exit_code=v[3]) for p,v in sorted(outcomes.items())},
        final_tests=dict(contract=80,unchanged_D10_V2=30,total=110,failed=0,skipped=0,
            earlier_contract_selection=73,earlier_selection_not_added=True),
        warning='One PytestAssertRewriteWarning: anyio already imported during existing schema-only bootstrap.',
        intermediate_audit=dict(failed_attempts=1,cause='New audit used wrong F2B field name; corrected new tooling only.',
            preserved_record='docs/testing/fitness-policy-f2c/audit-initial-error.json',protected_hash_mismatch=False),
        arithmetic_study=dict(random_pairs=3000,sampled_order_disagreements=0,exact_integer_fast_path_agrees=True,
            not_GA_or_production_performance=True),
        current_engine_fingerprints=engine,
        preservation=dict(baseline_files=len(baseline),all_match=True,academic_files=23,protected_preferences_and_settings_unchanged=True,
            git_index_unchanged=True,GA_operators_scoring_RNG_migrations_checkpoints_schedules_prior_evidence_unchanged=True,
            previous_artifact_entries_verified=historical),
        privacy=dict(status='PASS',complete_and_partial_encoded_fragments_checked=True,credential_URI_and_key_and_header_patterns_checked=True,
            log_sensitive_assignment_patterns_checked=True,fictional_numeric_and_authority_fixtures_only=True,
            academic_data_text_not_parsed_or_exported=True),
        whitespace=dict(new_text_files_checked=True,git_diff_check=True,cached_diff_check=True),
        activity=dict(application_files_modified=0,PostgreSQL_operations=0,experimental_production_scoring=False,
            checkpoint_rewrites=False,dependency_installations=0,staging=False,commits=False,push=False),
        limitations=['Contract models are not production dispatch/authority/codec integration.',
            'V1 mirror tests and other prior milestones reviewed as historical evidence, not fresh F2C runs.',
            'Institutional workload-exception authority absent; authorized-zero numeric policy/weight/overload composition unsettled.',
            'No new-mode GA/checkpoint/API/browser or PostgreSQL acceptance performed.',
            'Manifest excludes itself; hashes establish bytes, not institutional authorization.'])
    if '--verify' in sys.argv:
        saved=json.loads(manifest.read_text(encoding='utf-8'))
        assert saved['new_file_inventory']==inventory and saved['artifacts']==artifacts,'ARCHIVE_INTEGRITY_MISMATCH_STOP'
        assert saved['final_tests']==record['final_tests'] and saved['preservation']==record['preservation'],'AUDIT_RESULT_MISMATCH_STOP'
        print(json.dumps(dict(status='VERIFIED',new_files=len(inventory),artifact_hashes=len(artifacts),tests=110,baseline=len(baseline),historical_entries=historical)))
    else:
        with manifest.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
        print(json.dumps(dict(status='MANIFEST_CREATED',new_files=len(inventory),artifact_hashes=len(artifacts),tests=110,baseline=len(baseline),historical_entries=historical)))


if __name__=='__main__':audit()
