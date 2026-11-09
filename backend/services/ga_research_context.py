"""Fictional research qualification only; never a configured production provider."""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import json
import random
from services.ga_run_authority import RunError, canonical, digest, uuid
from services.ga_input_bundle import InputBundle
from services.ga_bundle_checkpoint import semantic_graph_fingerprint
from services.ga_bundle_optimizer import Session
from services.ga_checkpoint_service import dataframe_to_state, rng_to_json
from services import saved_best_policy

VERSION = 'fictional-research-context-v1'


@dataclass(frozen=True)
class ResearchPermit:
    actor: str
    department: str
    catalog: str
    prepared_fingerprint: str
    academic_year: str
    term: str
    dataset: str

    def validate(self):
        uuid(self.actor); uuid(self.department)
        if not all(type(v) is str and v.startswith('FICTIONAL-') and len(v) <= 100
                   for v in [self.catalog, self.academic_year, self.term, self.dataset]):
            raise RunError('RESEARCH_FICTIONAL_SCOPE_REQUIRED')
        if not __import__('re').fullmatch('[0-9a-f]{64}', self.prepared_fingerprint):
            raise RunError('RESEARCH_SOURCE_APPROVAL_REQUIRED')
        return self


def derive(row, permit):
    """Full graph fingerprint includes rooms/sections/calendars/eligibility/seed.

    Only search configuration is excluded from numerical equivalence; exact
    configuration and bundle fingerprints remain durable run provenance.
    Labels come from the server-owned fictional permit, never an HTTP body.
    """
    permit.validate()
    if (row['actor'], row['department'], row['catalog']) != (permit.actor, permit.department, permit.catalog):
        raise RunError('RESEARCH_SCOPE_MISMATCH', 403)
    bundle = InputBundle.from_bytes(bytes(row['bundle']), row['id'], row['bundle_hash'])
    doc = json.loads(bundle._raw)
    if doc['source_identities'].get('prepared') != permit.prepared_fingerprint:
        raise RunError('RESEARCH_PREPARED_INPUT_CHANGED')
    session = Session(bundle, run_id=row['id'], random_state=random.Random(0).getstate())
    if session.optimizer_fingerprint != row['optimizer'] or session.config_fingerprint != row['config_hash']:
        raise RunError('RESEARCH_OPTIMIZER_OR_CONFIGURATION_CHANGED')
    data = session.working
    full = {k: dataframe_to_state(v) if k == 'legacy_preferences' else v
            for k, v in data.items() if k != 'configuration'}
    graph = semantic_graph_fingerprint(full)
    ctx = dict(version=saved_best_policy.VERSION, academic_year=permit.academic_year, term=permit.term,
        department_id=permit.department, dataset_identity=permit.dataset,
        bundle_fingerprint=bundle.fingerprint, loaded_model_fingerprint=session.loaded_fingerprint,
        faculty_fingerprint=semantic_graph_fingerprint(data['templates'][1]),
        subject_fingerprint=semantic_graph_fingerprint(data['templates'][0]),
        preferences_fingerprint=semantic_graph_fingerprint(dict(legacy=full['legacy_preferences'],
            preferences=data['scoring_context']['preferences'])),
        scoring_configuration_fingerprint=session.scoring_fingerprint,
        engine_fingerprint=digest(dict(source=doc['source_identities']['engine'], optimizer=row['optimizer'])),
        constraints_fingerprint=digest(dict(complete_evaluation_graph=graph, optimizer=row['optimizer'])),
        fitness_version='original-penalty-preference-v2', chromosome_version='checkpoint-graph-v1-observed-order')
    return dict(contract=VERSION, run_id=row['id'], context=saved_best_policy.context(ctx),
        evaluation_fingerprint=graph, configuration_fingerprint=session.config_fingerprint,
        permit_fingerprint=digest(asdict(permit)), qualification='UNVERIFIED_UNTIL_COMMITTED_CONSUMPTION',
        institutional_authorization=False)


def verify_consumption(worker, row, response):
    """Validate the original child receipt against exact admitted/resume inputs.

    Called only after the real U5L child exited and was reaped. The unchanged K
    supervisor still independently validates checkpoint/projection before save.
    """
    receipt = response.get('receipt')
    if type(receipt) is not dict:
        raise RunError('RESEARCH_CONSUMPTION_MISSING')
    initial = worker.coordinator._session(row)
    if row['tip']:
        with worker.storage.connection() as db:
            doc, raw = worker.store.checkpoint(db, row)
        entry = worker._validate(row, doc, raw)
        state = entry.resume_state
        templates = state['working_templates']; frame = state['legacy_preferences']
        scoring = state['scoring_inputs']; rng = state['random_state']
    else:
        templates = initial.working['templates']; frame = dataframe_to_state(initial.working['legacy_preferences'])
        scoring = initial.working['scoring_context']; rng = initial.runtime.random.getstate()
    expected_entry = semantic_graph_fingerprint(dict(templates=templates, legacy_preferences=frame,
        scoring_context=scoring, configuration=initial.working['configuration'], seed=initial.working['seed']))
    expected = dict(contract='ga-bundle-consumption-receipt-v1', run_id=row['id'],
        verification_status='VERIFIED', verification_scope='TECHNICAL_CONSUMPTION_OF_CAPTURED_BUNDLE_ONLY',
        bundle_fingerprint=row['bundle_hash'], loaded_model_fingerprint=initial.loaded_fingerprint,
        consumed_entry_fingerprint=expected_entry, rng_entry_fingerprint=digest(rng_to_json(rng)),
        configuration_fingerprint=row['config_hash'], scoring_context_fingerprint=initial.scoring_fingerprint,
        optimizer_fingerprint=row['optimizer'], optimizer_version='ga-bundle-consumer-v1',
        checkpoint_fingerprint=response['inner_hash'], checkpoint_sequence=response['sequence'],
        parent_checkpoint_fingerprint=response['inner_parent'], state='PAUSED', eligible_for_current=False,
        institutional_authorization='NOT_ESTABLISHED', saved_best_promotion=False, publication=False)
    if any(receipt.get(k) != v for k, v in expected.items()) or type(receipt.get('function_calls')) is not int or receipt['function_calls'] <= 0:
        raise RunError('RESEARCH_CONSUMPTION_TAMPERED')
    return dict(run_id=row['id'], sequence=response['sequence'], inner_hash=response['inner_hash'],
        receipt_fingerprint=digest(receipt), binding=expected, projection_fingerprint=digest(response['projection']),
        best_fitness=response['projection']['best_fitness'])


class ResearchComparison:
    """Server-internal attestation adapter. No client payload admission method."""
    def __init__(self, bridge, principal, run):
        self.bridge=bridge; self.principal=principal; self.run=run

    @contextmanager
    def guard(self):
        with self.bridge.qualified(self.principal, self.run, 'result'):
            yield

    def snapshot(self):
        return self.bridge.qualified_result(self.principal, self.run)[0]['context']

    def attest(self, ctx, binding):
        if ctx != self.snapshot(): raise RunError('RESEARCH_COMPARISON_CONTEXT_CHANGED')
        trusted=self.bridge.candidate(self.principal,self.run)
        expected=saved_best_policy.digest(dict(context_fingerprint=saved_best_policy.digest(ctx),
            content_fingerprint=saved_best_policy.digest(saved_best_policy.content(trusted)),
            storage_policy_fingerprint=__import__('hashlib').sha256(__import__('pathlib').Path(saved_best_policy.__file__).read_bytes()).hexdigest()))
        if binding!=expected:raise RunError('RESEARCH_FORGED_CANDIDATE_REJECTED')
        return self.bridge.ledger.mac(dict(kind='research-saved-best', context=ctx, binding=binding))

    def verify(self, ctx, binding, signature):
        return self.bridge.ledger.matches(dict(kind='research-saved-best', context=ctx, binding=binding), signature)

    def equivalent_inputs(self, new, old):
        # Authenticated contexts alone are not equality proof. Require both
        # complete materialized input fingerprints, currently authorized runs,
        # committed checkpoints and their original child-consumption evidence.
        a=self.bridge.qualified_result(self.principal, self.run)[0]
        for run in self.bridge.ledger.runs():
            try:b=self.bridge.qualified_result(self.principal, run)[0]
            except RunError:continue
            if b['context']==old and a['context']==new:
                return a['evaluation_fingerprint']==b['evaluation_fingerprint']
        return False
