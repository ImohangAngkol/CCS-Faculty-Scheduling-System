"""Read-only fictional experiment evidence over unchanged B/H/K/L/E records."""
from dataclasses import asdict,fields
from datetime import datetime,timezone
import csv
import hashlib
import io
import json
import math
import re
import time
from uuid import UUID,uuid5
from genetic_algorithm.models.ga_setting import GASetting
from services.ga_research_operator import Operator,read_guard
from services.ga_run_authority import RunError,canonical,digest,uuid
from services.ga_observation_freshness import evaluate

VERSION='fictional-research-experiment-v1'
NAMESPACE=UUID('8948db6f-51b1-45f2-9b59-120f1160a013')
CAPS={'json':256*1024,'csv':128*1024,'txt':128*1024}
BREAKDOWN={'subject_preference','time_preference','day_preference','schedule_style','lecture_lab_preference','number_of_preparations','teaching_load_balance','daily_teaching_load'}
SAFETY=dict(production_admission='BLOCKED',institutional_saved_best_promotion=False,continuous_ui='DISABLED',active_restore=False,seven_day='NO_GO')


def number(v):
    try:return type(v) in (int,float) and math.isfinite(v)
    except OverflowError:return False
def observed(v,source):return dict(value=v,classification='OBSERVED',source=source)
def unavailable(reason):return dict(value=None,classification='UNAVAILABLE',reason=reason)


def improvement(initial,final):
    if not number(initial) or not number(final):return unavailable('COMPARABLE_VALUES_NOT_RECORDED'),unavailable('COMPARABLE_VALUES_NOT_RECORDED')
    delta=initial-final
    if not number(delta):return unavailable('NUMERIC_RANGE'),unavailable('NUMERIC_RANGE')
    absolute=dict(value=delta,classification='DERIVED',formula='initial - final best; same bound run/context only')
    if initial<=0:return absolute,unavailable('ZERO_BASELINE' if initial==0 else 'NEGATIVE_BASELINE')
    percent=delta/initial*100
    return absolute,dict(value=percent,classification='DERIVED',formula='100 * (initial - final best) / initial') if number(percent) else unavailable('NUMERIC_RANGE')


def safe_settings(settings):
    allowed={f.name for f in fields(GASetting)}
    if type(settings) is not dict or not set(settings)<=allowed or any(type(v) not in (int,float) or not number(v) for v in settings.values()):raise RunError('EXPERIMENT_SETTINGS_UNSUPPORTED')
    # Exact original default/coercion implementation; no settings are changed.
    return dict(recorded=settings,effective=GASetting.from_dict(settings).to_dict(),effective_classification='DERIVED_BY_ORIGINAL_GA_SETTING_CONSTRUCTOR')


class Experiments:
    def __init__(self,operator,*,clock=time.time):
        if type(operator) is not Operator:raise RunError('EXPERIMENT_OPERATOR_REQUIRED')
        self.operator=operator;self.clock=clock

    def context(self,p):
        c=self.operator.capabilities(p)
        return dict(schema=VERSION,**SAFETY,contexts=[dict(selection_key=digest(c['context']),context=c['context'],limits=c['limits'])],
            notice='One server-bound fictional context. Selection acknowledges it; clients cannot change authority or scheduling inputs.')

    def view(self,p,run):
        uuid(run);o=self.operator;b=o.bridge;b.actor(p)
        with o._locked(),read_guard(b,p):
            runtime=o.runtime(p,run)
            with o.full_observer.snapshot(p) as db:
                o._guard(db);row=b.worker.store.row(db,b.actor(p),run)
                if (row['department'],row['catalog'])!=(b.permit.department,b.permit.catalog):raise RunError('EXPERIMENT_SCOPE_REJECTED',403)
                ctx,events=b.ledger.check(db,run)
                if len(events)>256:raise RunError('EXPERIMENT_HISTORY_LIMIT',413)
                if (ctx.get('run_id')!=run or ctx.get('permit_fingerprint')!=digest(asdict(b.permit))
                        or ctx['context']['bundle_fingerprint']!=row['bundle_hash'] or ctx['configuration_fingerprint']!=row['config_hash']):raise RunError('EXPERIMENT_BINDING_REJECTED')
                identity=str(uuid5(NAMESPACE,VERSION+':'+b.worker.storage.store_id+':'+run))
                generation=row['generation']
                if type(generation) is not int or not -1<=generation<=20:raise RunError('EXPERIMENT_GENERATION_INVALID')
                latest=db.execute('SELECT id,state,reason,at,tip FROM worker_events WHERE run=? ORDER BY id DESC LIMIT 1',(run,)).fetchone()
                fresh=evaluate(now=self.clock(),times=[e.get('observed_at') for e in events],state=runtime['recorded_state'],terminal_confirmed=runtime['terminal_cleanup_recorded'],terminal_at=latest['at'] if latest else None)
                value=dict(schema=VERSION,**SAFETY,experiment_id=identity,run_id=run,runtime=runtime,freshness=fresh,
                    generation=observed(generation,'ORIGINAL_COMMITTED_CHECKPOINT_METADATA_NOT_RESULT_VALIDATION') if generation>=0 else unavailable('NO_COMMITTED_CHECKPOINT'),
                    exportable=False,verification='RECORDED_METADATA_ONLY',record=None,record_sha256=None)
                thread=b.worker.threads.get(run)
                final_signed=latest is not None and any(e.get('worker_event_id')==latest['id'] and e.get('worker_state')==latest['state'] and e.get('checkpoint')==latest['tip'] for e in events)
                if not runtime['terminal_cleanup_recorded'] or thread is not None and thread.is_alive() or not final_signed:
                    value['export_reason']='TERMINAL_CLEANUP_AND_FINAL_SIGNED_OBSERVATION_REQUIRED';return value
                overview,ctx,events,result=o.full_observer._read(db,p,run)
                if overview['freshness']['state']!='TERMINAL' or result is None:raise RunError('EXPERIMENT_VERIFIED_CONSUMPTION_REQUIRED')
                history=o.full_observer._history(run,result)['points']
                if len(history)>256:raise RunError('EXPERIMENT_HISTORY_LIMIT',413)
                points=[];last=-1;best=math.inf
                for cp in db.execute('SELECT sequence,raw FROM worker_checkpoints WHERE run=? ORDER BY sequence',(run,)):
                    doc=json.loads(cp['raw']);proof=b.ledger.proof(db,run,cp['sequence']);binding=proof['binding'];g=doc['generation'];score=proof['best_fitness']
                    expected=dict(run_id=run,bundle_fingerprint=row['bundle_hash'],configuration_fingerprint=row['config_hash'],optimizer_fingerprint=row['optimizer'],scoring_context_fingerprint=ctx['context']['scoring_configuration_fingerprint'],checkpoint_fingerprint=doc['inner_hash'],checkpoint_sequence=cp['sequence'],optimizer_version='ga-bundle-consumer-v1',verification_status='VERIFIED')
                    if any(binding.get(k)!=v for k,v in expected.items()) or proof['inner_hash']!=doc['inner_hash'] or not number(score) or score>best or type(g) is not int or g<last:raise RunError('EXPERIMENT_PROOF_BINDING_REJECTED')
                    points.append(dict(generation=g,best_so_far_fitness=score,classification='OBSERVED',source='COMMITTED_CHILD_CONSUMPTION_PROOF',checkpoint_sequence=cp['sequence']))
                    last=g;best=score
                if not points or len(points)>256 or points[-1]['generation']!=generation or points[-1]['best_so_far_fitness']!=overview['best_so_far_fitness']:raise RunError('EXPERIMENT_OBSERVATION_MISMATCH')
                initial=points[0]['best_so_far_fitness'] if points[0]['generation']==0 else None
                final=overview['best_so_far_fitness'];delta,percent=improvement(initial,final)
                breakdown=result.get('fitness_breakdown')
                if breakdown is not None and (type(breakdown) is not dict or not set(breakdown)<=BREAKDOWN or any(not number(v) for v in breakdown.values())):raise RunError('EXPERIMENT_BREAKDOWN_INVALID')
                source=json.loads(row['bundle']);settings=b.worker.coordinator._session(row).working['scoring_context']['settings']
                labels={k:getattr(b.permit,k) for k in ['academic_year','term','dataset','catalog']}
                if any(not re.fullmatch(r'FICTIONAL-[A-Za-z0-9 ._-]{1,89}',v) for v in labels.values()):raise RunError('EXPERIMENT_CONTEXT_LABEL_UNSUPPORTED')
                started=row['created'];ended=overview['freshness']['terminal_recorded_at']
                if not number(started) or not number(ended) or not 0<=started<=ended:raise RunError('EXPERIMENT_TIMESTAMPS_INVALID')
                lifecycle=[]
                for e in events:
                    if 'worker_state' not in e:continue
                    reason=e.get('exit_reason')
                    if reason is not None and not re.fullmatch('[A-Z0-9_]{1,100}',reason):raise RunError('EXPERIMENT_REASON_UNSUPPORTED')
                    lifecycle.append(dict(sequence=len(lifecycle)+1,state=e['worker_state'],reason=reason,observed_at=e.get('observed_at'),classification='SIGNED_DURABLE_OBSERVATION'))
                record=dict(schema=VERSION,experiment_id=identity,run_id=run,fictional_context=dict(**labels,department_id=b.permit.department,context_fingerprint=digest(ctx['context'])),
                    provenance=dict(input_bundle_fingerprint=row['bundle_hash'],dataset_source_fingerprint=source['source_identities']['dataset'],configuration_fingerprint=row['config_hash'],engine_fingerprint=ctx['context']['engine_fingerprint'],optimizer_fingerprint=row['optimizer'],optimizer_version='ga-bundle-consumer-v1',fitness_version=ctx['context']['fitness_version'],fitness_direction='MINIMIZE',configuration=source['configuration'],fitness_configuration=safe_settings(settings),execution_limits=json.loads(row['limits']),physical_resources=asdict(b.worker.resources),storage_policy_fingerprint=b.worker.storage.policy),
                    rng_provenance=dict(classification='UNAVAILABLE',reason='PRIVATE_SERVER_GENERATED_INITIAL_RNG_STATE_NOT_EXPORTED',schedule_baseline_mode=source['configuration']['baseline_mode'],exact_replay_from_export=False),
                    admitted_at=observed(started,'ORIGINAL_RUN_CREATED_LOCAL_CLOCK'),terminal_at=observed(ended,'ORIGINAL_TERMINAL_WORKER_EVENT_LOCAL_CLOCK'),
                    elapsed_admission_to_terminal=dict(value=ended-started,classification='DERIVED',unit='seconds',scope='Includes admission, search, validation and I/O; not optimizer-only benchmark time'),
                    actual_generation_count=observed(generation,'VALIDATED_ORIGINAL_RESULT'),initial_fitness=observed(initial,'GENERATION_ZERO_COMMITTED_PROOF') if initial is not None else unavailable('INITIAL_NOT_RECORDED'),
                    final_best_fitness=observed(final,'VALIDATED_ORIGINAL_RESULT'),fitness_improvement=delta,percentage_improvement=percent,
                    original_generation_history=history,checkpoint_observations=points,
                    soft_penalty_breakdown=observed(breakdown,'ORIGINAL_FITNESS_BREAKDOWN_NOT_HARD_CONFLICT_COUNTS') if breakdown is not None else unavailable('NOT_RECORDED'),
                    preference_satisfaction=unavailable('NO_VERIFIED_SATISFACTION_METRIC'),hard_conflict_counts=unavailable('NO_EXPLICIT_RECORDED_COUNTER'),
                    termination=dict(state=overview['state'],reason=overview['reason'],classification='INDEPENDENTLY_CONFIRMED_TERMINAL'),lifecycle=lifecycle,
                    evidence_notice='Technical fictional demonstration only. No institutional approval, publication, Saved Best promotion, convergence or statistical performance claim.')
                if len(canonical(record))>CAPS['json']:raise RunError('EXPERIMENT_EXPORT_TOO_LARGE',413)
                value.update(record=record,record_sha256=digest(record),exportable=True,verification='VERIFIED_RECORDED_FICTIONAL_RESULT',freshness=overview['freshness'])
                return value

    def export(self,p,run,kind):
        if kind not in CAPS:raise RunError('EXPERIMENT_EXPORT_FORMAT_UNSUPPORTED',422)
        view=self.view(p,run)
        if not view['exportable']:raise RunError('EXPERIMENT_EXPORT_NOT_VERIFIED',409)
        record=view['record'];stamp=datetime.fromtimestamp(self.clock(),timezone.utc).isoformat()
        if kind=='json':
            raw=canonical(dict(schema=VERSION,record=record,record_sha256=view['record_sha256'],generated_at=stamp,verification=view['verification'],freshness=view['freshness'],**SAFETY))
        elif kind=='csv':
            ctx=record['fictional_context'];prov=record['provenance'];out=io.StringIO(newline='');writer=csv.writer(out)
            columns=['schema','experiment_id','run_id','record_sha256','export_generated_at','series','generation','best_so_far_fitness','classification','dataset','academic_year','term','department_id','context_fingerprint','input_bundle_fingerprint','engine_fingerprint','optimizer_version','fitness_version','configuration_fingerprint','fitness_direction','termination_state','termination_reason','satisfaction_availability','hard_conflict_count_availability']
            writer.writerow(columns)
            metadata=[ctx['dataset'],ctx['academic_year'],ctx['term'],ctx['department_id'],ctx['context_fingerprint'],prov['input_bundle_fingerprint'],prov['engine_fingerprint'],prov['optimizer_version'],prov['fitness_version'],prov['configuration_fingerprint'],'MINIMIZE',record['termination']['state'],record['termination']['reason'],'UNAVAILABLE_NOT_RECORDED','UNAVAILABLE_NOT_RECORDED']
            for series,items,key in [('checkpoint',record['checkpoint_observations'],'best_so_far_fitness'),('generation',record['original_generation_history'],'best_ever_fitness')]:
                for item in items:writer.writerow([VERSION,record['experiment_id'],run,view['record_sha256'],stamp,series,item['generation'],item[key],'OBSERVED',*metadata])
            raw=out.getvalue().encode('utf-8')
        else:
            lines=['FICTIONAL RESEARCH EVIDENCE — NOT INSTITUTIONAL APPROVAL',f'Schema: {VERSION}',f'Experiment: {record["experiment_id"]}',f'Run: {run}',f'Record SHA-256: {view["record_sha256"]}',f'Export generated at: {stamp}',f'Context: {record["fictional_context"]["dataset"]} / {record["fictional_context"]["term"]}',f'Engine: {record["provenance"]["optimizer_version"]}',f'Input bundle: {record["provenance"]["input_bundle_fingerprint"]}','Fitness direction: MINIMIZE']
            lines.extend(['Fictional context: '+json.dumps(record['fictional_context'],sort_keys=True),'Provenance: '+json.dumps(record['provenance'],sort_keys=True)])
            for key in ['actual_generation_count','initial_fitness','final_best_fitness','fitness_improvement','percentage_improvement','elapsed_admission_to_terminal','soft_penalty_breakdown','preference_satisfaction','hard_conflict_counts']:
                lines.append(key+': '+json.dumps(record[key],sort_keys=True))
            lines.extend(['Termination: '+json.dumps(record['termination'],sort_keys=True),'RNG: private initial state omitted; exact replay from export NOT established.',record['evidence_notice']]);raw=('\n'.join(lines)+'\n').encode('utf-8')
        if len(raw)>CAPS[kind]:raise RunError('EXPERIMENT_EXPORT_TOO_LARGE',413)
        return raw,record['experiment_id']
