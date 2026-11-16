"""Offline content consistency only, never authority or exact replay proof."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
from datetime import datetime

SCHEMA='fictional-research-experiment-v1'
FIELDS=['schema','experiment_id','run_id','record_sha256','export_generated_at','series','generation','best_so_far_fitness','classification','dataset','academic_year','term','department_id','context_fingerprint','input_bundle_fingerprint','engine_fingerprint','optimizer_version','fitness_version','configuration_fingerprint','fitness_direction','termination_state','termination_reason','satisfaction_availability','hard_conflict_count_availability']
METRICS=['actual_generation_count','initial_fitness','final_best_fitness','fitness_improvement','percentage_improvement','elapsed_admission_to_terminal','soft_penalty_breakdown','preference_satisfaction','hard_conflict_counts']


def load(path,limit):
    p=Path(path);assert p.stat().st_size<=limit,'EXPORT_SIZE_REJECTED';return p.read_bytes()


def verify(json_path,csv_path=None,text_path=None):
    d=json.loads(load(json_path,256*1024));r=d['record']
    assert d['schema']==r['schema']==SCHEMA and d['verification']=='VERIFIED_RECORDED_FICTIONAL_RESULT'
    assert d['production_admission']=='BLOCKED' and d['active_restore'] is False and d['institutional_saved_best_promotion'] is False
    assert hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==d['record_sha256'],'JSON_CONTENT_HASH_REJECTED'
    if csv_path:
        reader=csv.DictReader(io.StringIO(load(csv_path,128*1024).decode('utf-8')));assert reader.fieldnames==FIELDS
        rows=list(reader);assert len(rows)<=256
        expected=[(s,str(p['generation']),str(p[k])) for s,points,k in [('checkpoint',r['checkpoint_observations'],'best_so_far_fitness'),('generation',r['original_generation_history'],'best_ever_fitness')] for p in points]
        assert [(x['series'],x['generation'],x['best_so_far_fitness']) for x in rows]==expected,'CSV_OBSERVATION_REJECTED'
        stamps=set()
        for row in rows:
            assert row['schema']==SCHEMA and row['run_id']==r['run_id'] and row['experiment_id']==r['experiment_id'] and row['record_sha256']==d['record_sha256'] and row['classification']=='OBSERVED'
            assert datetime.fromisoformat(row['export_generated_at']).tzinfo is not None;stamps.add(row['export_generated_at'])
            ctx=r['fictional_context'];prov=r['provenance']
            expected=[ctx['dataset'],ctx['academic_year'],ctx['term'],ctx['department_id'],ctx['context_fingerprint'],prov['input_bundle_fingerprint'],prov['engine_fingerprint'],prov['optimizer_version'],prov['fitness_version'],prov['configuration_fingerprint'],'MINIMIZE',r['termination']['state'],r['termination']['reason'] or '','UNAVAILABLE_NOT_RECORDED','UNAVAILABLE_NOT_RECORDED']
            assert [row[k] for k in FIELDS[9:]]==expected,'CSV_PROVENANCE_REJECTED'
        assert len(stamps)==1
    if text_path:
        lines=load(text_path,128*1024).decode('utf-8').splitlines()
        assert len(lines)==12+len(METRICS)+3 and lines[0]=='FICTIONAL RESEARCH EVIDENCE — NOT INSTITUTIONAL APPROVAL'
        assert lines[1:5]==[f'Schema: {SCHEMA}',f'Experiment: {r["experiment_id"]}',f'Run: {r["run_id"]}',f'Record SHA-256: {d["record_sha256"]}']
        assert lines[5].startswith('Export generated at: ') and datetime.fromisoformat(lines[5].split(': ',1)[1]).tzinfo is not None
        assert lines[6:10]==[f'Context: {r["fictional_context"]["dataset"]} / {r["fictional_context"]["term"]}',f'Engine: {r["provenance"]["optimizer_version"]}',f'Input bundle: {r["provenance"]["input_bundle_fingerprint"]}','Fitness direction: MINIMIZE']
        assert lines[10]=='Fictional context: '+json.dumps(r['fictional_context'],sort_keys=True) and lines[11]=='Provenance: '+json.dumps(r['provenance'],sort_keys=True)
        for line,key in zip(lines[12:12+len(METRICS)],METRICS,strict=True):assert line==key+': '+json.dumps(r[key],sort_keys=True),'TEXT_METRIC_REJECTED'
        assert lines[-3]=='Termination: '+json.dumps(r['termination'],sort_keys=True)
        assert lines[-2]=='RNG: private initial state omitted; exact replay from export NOT established.' and lines[-1]==r['evidence_notice']
    return dict(status='CONTENT_CONSISTENCY_VERIFIED',record_sha256=d['record_sha256'],institutional_authority='NOT_ESTABLISHED',exact_replay='NOT_ESTABLISHED')


if __name__=='__main__':
    if not 1<=len(sys.argv[1:])<=3:raise SystemExit('Usage: verify_export.py JSON [CSV [TXT]]')
    try:print(json.dumps(verify(*sys.argv[1:])))
    except (AssertionError,ValueError,KeyError,TypeError,OSError):raise SystemExit('EXPORT_CONTENT_REJECTED; no private contents printed') from None
