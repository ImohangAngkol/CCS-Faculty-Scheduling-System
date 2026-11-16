"""Run-bound minimum preflight and result qualification around unchanged E/B/L/H.

No minimum-aware search, candidate repair, new fitness or Saved Best promotion.
"""
from contextlib import closing
import ctypes
import hashlib
import json
import math
from pathlib import Path
import threading
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from services.prototype_workload import PolicyError, WorkloadService, digest, require
from services.prototype_run_store import RunStore
from services.ga_run_authority import RunError

VERSION = 'prototype-minimum-qualified-execution-v1'
SAFE = dict(prototype_only=True, production_admission='BLOCKED', institutional_saved_best_promotion=False,
            continuous_optimization='DISABLED', active_restore=False, seven_day='NO_GO')


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    request_id: str
    academic_year: str
    term: str
    catalog_revision: str
    minimum_revision: int = Field(ge=0)
    minimum_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    prepared_bundle_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    configuration_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')


def resource_snapshot():
    """Same retained3GiB prelaunch gate; no settings/limits are changed."""
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                    *[(name, ctypes.c_ulonglong) for name in ['total', 'available', 'tc', 'ac', 'tv', 'av', 'ex']]]
    try:
        value = Memory()
        value.length = ctypes.sizeof(value)
        require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)), 'PROTOTYPE_RESOURCE_CHECK_FAILED')
        return dict(available_bytes=value.available, required_bytes=3 * 2**30,
                    source='WINDOWS_GLOBAL_MEMORY_STATUS', passed=value.available >= 3 * 2**30)
    except Exception:
        return dict(available_bytes=None, required_bytes=3 * 2**30, source='UNAVAILABLE', passed=False)


def assess_snapshot(workload, snapshot, candidate):
    """Frozen policy, independent of the current mutable policy head."""
    from services.ga_publication_service import validate_publication
    data = workload.bundle.materialize(workload.bundle.run_id)
    validate_publication(candidate, *data['templates'])
    faculty, minima = workload.minimums(snapshot['policy'])
    loads = {code: 0 for code in faculty}
    for subject in candidate:
        if subject.preassigned_assignment is None:
            loads[subject.assigned_faculty.code] += subject.credit_units
    rows = [dict(faculty_code=c, assigned_units=loads[c], minimum_teaching_units=minima.get(c),
                 soft_target_teaching_units=row['soft_target_teaching_units'], maximum_teaching_units=row['maximum_teaching_units'],
                 minimum_deficit=max(0, minima[c]-loads[c]) if c in minima else None) for c, row in faculty.items()]
    violation = any(x['minimum_deficit'] is not None and x['minimum_deficit'] > 0 for x in rows)
    return dict(faculty=rows, minimum_status='MINIMUM_WORKLOAD_VIOLATION' if violation else 'EXPLICIT_MINIMA_SATISFIED',
                original_hard_constraints='VALIDATED', fully_feasible_under_captured_policy=not violation,
                subject_coverage='COMPLETE', minimum_revision=snapshot['policy']['revision'],
                minimum_digest=snapshot['policy']['digest'])


class MinimumRuns:
    def __init__(self, workload, operator, *, initialize=False, resources=resource_snapshot):
        from services.ga_research_operator import Operator
        require(type(workload) is WorkloadService and type(operator) is Operator, 'PROTOTYPE_SUPPORTED_EXECUTION_REQUIRED')
        permit = operator.bridge.permit
        require((permit.department, permit.academic_year, permit.term, permit.catalog, permit.prepared_fingerprint) ==
                (workload.scope.department_id, workload.scope.academic_year, workload.scope.term,
                 workload.scope.catalog_revision, workload.bundle.fingerprint), 'PROTOTYPE_EXECUTION_SCOPE_MISMATCH')
        self.workload, self.operator, self.resources = workload, operator, resources
        self.version = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.binding = digest(dict(contract=VERSION, implementation=self.version, workload=workload.binding,
                                   worker_store=operator.bridge.worker.storage.store_id, operator=operator.binding))
        self.store = RunStore(workload.store, self.binding, initialize=initialize)
        self.lock = threading.RLock()

    def actor(self, principal, action):
        actor = self.workload.authorize(principal, action)
        require(actor == self.operator.bridge.actor(principal), 'PROTOTYPE_RUN_OWNER_REQUIRED', 403)
        return actor

    def context(self, principal):
        self.actor(principal, 'read')
        view = self.workload.view(principal)
        document = json.loads(self.workload.bundle._raw)
        return dict(contract=VERSION, **SAFE, workload=view,
                    configuration_fingerprint=document['configuration_fingerprint'],
                    parameters=document['configuration'], limits=self.operator.capabilities(principal)['limits'],
                    optimizer_contract='ga-bundle-consumer-v1', search_time_minimum_enforcement=False)

    def lookup(self, principal, nonce):
        UUID(nonce)
        record = self.store.find(self.actor(principal, 'read'), nonce)
        require(record is not None, 'PROTOTYPE_REQUEST_NOT_FOUND', 404)
        return self.inspect(principal, record['id'])

    def snapshot(self, principal, request):
        UUID(request.request_id)
        current = self.workload.view(principal)
        scope = self.workload.scope
        require((request.academic_year, request.term, request.catalog_revision) ==
                (scope.academic_year, scope.term, scope.catalog_revision), 'PROTOTYPE_SELECTED_TERM_MISMATCH')
        doc = json.loads(self.workload.bundle._raw)
        require(request.prepared_bundle_fingerprint == self.workload.bundle.fingerprint
                and request.configuration_fingerprint == doc['configuration_fingerprint'], 'PROTOTYPE_SELECTED_INPUT_CHANGED')
        require((request.minimum_revision, request.minimum_digest) ==
                (current['policy']['revision'], current['policy']['digest']), 'PROTOTYPE_POLICY_STALE')
        return dict(contract=VERSION, implementation=self.version, scope=scope.model_dump(),
                    policy=current['policy'], prepared_bundle_fingerprint=self.workload.bundle.fingerprint,
                    input_fingerprint=doc['source_identities']['dataset'],
                    configuration_fingerprint=doc['configuration_fingerprint'], parameters=doc['configuration'],
                    engine_fingerprint=doc['source_identities']['engine'],
                    fitness_policy_version='original-penalty-preference-v2',
                    preflight=current['preflight'], faculty_capacity=current['faculty'],
                    meaning='Integer credit units once per normal GA-managed offering; fixed external offerings excluded')

    def _verify_record(self, record):
        snapshot = record['snapshot']
        require(record['snapshot_hash'] == digest(snapshot) and snapshot['implementation'] == self.version
                and snapshot['prepared_bundle_fingerprint'] == self.workload.bundle.fingerprint
                and snapshot['scope'] == self.workload.scope.model_dump(), 'PROTOTYPE_RUN_SNAPSHOT_CHANGED')
        # Validate the whole immutable policy chain, then the captured old row.
        # A later policy revision is permitted and never substituted.
        with closing(self.workload.store.connection()) as db:
            self.workload.store.read(db)
            version = snapshot['policy']['revision']
            if version:
                row = db.execute('SELECT doc,digest FROM revisions WHERE version=?', (version,)).fetchone()
                require(row is not None and row[1] == snapshot['policy']['digest']
                        and json.loads(row[0])['minimums'] == snapshot['policy']['minimums'], 'PROTOTYPE_CAPTURED_POLICY_CHANGED')
            else:
                require(snapshot['policy'] == dict(revision=0, minimums=[],
                    digest=digest(dict(contract='prototype-explicit-minimum-v1', binding=self.workload.binding))),
                    'PROTOTYPE_CAPTURED_POLICY_CHANGED')

    def submit(self, principal, request):
        actor = self.actor(principal, 'execute')
        require(type(request) is Submission, 'PROTOTYPE_REQUEST_INVALID', 422)
        UUID(request.request_id)
        selector = request.model_dump()
        with self.lock:
            existing = self.store.find(actor, request.request_id)
            if existing:
                require(existing['selector'] == selector, 'PROTOTYPE_REQUEST_REUSE_MISMATCH')
                return self.inspect(principal, existing['id'])
            snapshot = self.snapshot(principal, request)
            record, created = self.store.create(actor, selector, snapshot)
            run = record['id']
            if not created:
                return self.inspect(principal, run)
            if snapshot['preflight'] == 'MINIMUM_WORKLOAD_INFEASIBLE':
                self.store.append(run, actor, 'INPUT_INFEASIBLE', dict(code='MINIMUM_WORKLOAD_INFEASIBLE',
                    shortages=[x for x in snapshot['faculty_capacity'] if x['proven_shortfall']]), terminal=True)
                return self.inspect(principal, run)
            resources = self.resources()
            if not (resources.get('passed') is True and type(resources.get('available_bytes')) is int
                    and resources['available_bytes'] >= 3 * 2**30):
                self.store.append(run, actor, 'RESOURCE_BLOCKED', resources, terminal=True)
                return self.inspect(principal, run)
            self.store.append(run, actor, 'EXECUTION_REQUESTED', dict(resources=resources))
            try:
                response = self.operator.control(principal, request.request_id, 'start')
                self._link(principal, record, response['run_id'])
            except (RunError, PolicyError, OSError) as exc:
                self.store.append(run, actor, 'EXECUTION_UNCERTAIN', dict(code=getattr(exc, 'code', 'PROTOTYPE_EXECUTION_UNAVAILABLE')))
            return self.inspect(principal, run)

    def _link(self, principal, record, worker_run):
        row = self.operator.bridge.worker.coordinator.inspect(principal, worker_run, 'status')
        document = json.loads(row['bundle'])
        snapshot = record['snapshot']
        require(document['source_identities'].get('prepared') == snapshot['prepared_bundle_fingerprint']
                and row['config_hash'] == snapshot['configuration_fingerprint']
                and row['request_key'] == record['selector']['request_id'], 'PROTOTYPE_ADMITTED_INPUT_MISMATCH')
        self.store.append(record['id'], record['actor'], 'WORKER_BOUND', dict(worker_run_id=worker_run,
            admitted_bundle_fingerprint=row['bundle_hash'], optimizer_fingerprint=row['optimizer'],
            initial_rng_fingerprint=hashlib.sha256(bytes(row['initial_rng'])).hexdigest(),
            RNG_origin='SERVER_GENERATED_PRIVATE_RNG_STATE_NOT_EXPORTED', exact_replay_from_public_record=False))

    def inspect(self, principal, run):
        UUID(run)
        actor = self.actor(principal, 'read')
        with self.lock:
            record, events = self.store.get(run, actor)
            self._verify_record(record)
            if events and events[-1]['terminal']:
                return self._public(record, events)
            linked = next((x for x in reversed(events) if x['kind'] == 'WORKER_BOUND'), None)
            if linked is None:
                # Recover only an existing nonce mapping, never execute/resume.
                try:
                    mapping = self.operator.request_status(principal, record['selector']['request_id'])
                    if mapping['run_id']:
                        self._link(principal, record, mapping['run_id'])
                        record, events = self.store.get(run, actor)
                        linked = next(x for x in reversed(events) if x['kind'] == 'WORKER_BOUND')
                except RunError:
                    return self._public(record, events)
            if linked:
                worker_run = linked['data']['worker_run_id']
                try:
                    runtime = self.operator.runtime(principal, worker_run)
                    thread = self.operator.bridge.worker.threads.get(worker_run)
                    if runtime['recorded_state'] in {'INTERRUPTED', 'RECOVERY_REQUIRED'}:
                        self.store.append(run, actor, 'INTERRUPTED', dict(runtime=runtime), terminal=True)
                    elif runtime['terminal_cleanup_recorded'] and not (thread and thread.is_alive()):
                        if runtime['recorded_state'] in {'COMPLETED', 'STOPPED'}:
                            self._qualify(principal, record, linked['data'], runtime)
                        else:
                            self.store.append(run, actor, 'RUN_FAILED', dict(runtime=runtime), terminal=True)
                    else:
                        public = self._public(record, events)
                        return public | dict(execution_state=runtime['recorded_state'], runtime=runtime)
                except (RunError, PolicyError, ValueError, RuntimeError) as exc:
                    public = self._public(record, events)
                    return public | dict(evidence_error=getattr(exc, 'code', 'PROTOTYPE_RESULT_QUALIFICATION_FAILED'),
                                         candidate_status='UNVERIFIED', fully_feasible=False)
            return self._public(*self.store.get(run, actor))

    def _qualify(self, principal, record, linked, runtime):
        from services.chromosome_service import payload_to_chromosome
        bridge = self.operator.bridge
        context, result = bridge.qualified_result(principal, linked['worker_run_id'])
        payload = bridge.candidate(principal, linked['worker_run_id'])
        templates = self.workload.bundle.materialize(self.workload.bundle.run_id)['templates']
        candidate = payload_to_chromosome(payload, *templates)
        assessment = assess_snapshot(self.workload, record['snapshot'], candidate)
        score = result['best_fitness']
        require(type(score) in (int, float) and math.isfinite(score), 'PROTOTYPE_FITNESS_INVALID')
        status = 'CANDIDATE_FULLY_FEASIBLE' if assessment['fully_feasible_under_captured_policy'] else 'CANDIDATE_CONSTRAINT_VIOLATING'
        observed = dict(original_GA_fitness=score, fitness_breakdown=result.get('fitness_breakdown'),
                        generation_history=result.get('history'), schedule=result['schedule'],
                        actual_generations=result.get('generations_completed'), qualification=assessment,
                        runtime=runtime, technical_consumption='VERIFIED_BY_ORIGINAL_COMMITTED_CHILD_PROOF',
                        research_context_fingerprint=digest(context), admitted=linked,
                        termination_status=runtime['recorded_state'],
                        Saved_Best_or_approved_promotion=False)
        self.store.append(record['id'], record['actor'], status, observed, terminal=True)

    def _public(self, record, events):
        last = events[-1] if events else None
        result = last['data'] if last and last['kind'].startswith('CANDIDATE_') else None
        linked = next((x['data'] for x in reversed(events) if x['kind'] == 'WORKER_BOUND'), None)
        snapshot = record['snapshot']
        return dict(contract=VERSION, **SAFE, run_id=record['id'], request_id=record['selector']['request_id'],
                    state=last['kind'] if last else 'ADMISSION_INDETERMINATE', terminal=bool(last and last['terminal']),
                    execution_state=(result or {}).get('termination_status'),
                    scope=snapshot['scope'], minimum_revision=snapshot['policy']['revision'],
                    minimum_digest=snapshot['policy']['digest'], snapshot_fingerprint=record['snapshot_hash'],
                    prepared_bundle_fingerprint=snapshot['prepared_bundle_fingerprint'],
                    input_fingerprint=snapshot['input_fingerprint'], configuration_fingerprint=snapshot['configuration_fingerprint'],
                    captured_policy=snapshot['policy'], provenance=snapshot,
                    worker=linked, result=result, details=last['data'] if last else None,
                    fully_feasible=bool(result and result['qualification']['fully_feasible_under_captured_policy']),
                    candidate_status=result['qualification']['minimum_status'] if result else 'NOT_GENERATED_OR_UNVERIFIED',
                    live_authority_and_latest_policy='NOT_RECHECKED_FOR_STORED_TERMINAL_RESULT',
                    worker_admitted=linked is not None,
                    physical_execution='VERIFIED_COMMITTED_CHILD_RESULT' if result else 'NOT_ESTABLISHED_BY_THIS_RECORD',
                    search_time_minimum_enforcement=False)
