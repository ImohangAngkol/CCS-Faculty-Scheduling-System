"""Explicit demonstration-only catalog, not institutional IT eligibility data."""
import copy
import json
from services.ga_worker_contract import fictional_source


def minimum24_case():
    fictional_source()
    from tests.test_prototype_workload import bundle_for
    from services.ga_input_bundle import capture
    from services.prototype_workload import digest
    source, _ = bundle_for(12)
    data = source.materialize(source.run_id)
    subjects, faculty, rooms = data['templates']
    for i, subject in enumerate(subjects):
        subject.number = 'SYN-WA' if i < 4 else 'SYN-WB'
    faculty[0].eligible_subjects = {'SYN-WA'}
    faculty[1].eligible_subjects = {'SYN-WB'}
    data['scoring_context']['system_faculty'] = copy.deepcopy(faculty)
    sources = dict(json.loads(source._raw)['source_identities'])
    sources['dataset'] = digest(dict(fixture='FICTIONAL-DEADLINE-MIN24-v1', faculty1_units=12,
                                    faculty2_units=24, eligibility='EXPLICIT_DISJOINT_A_B', offerings=12))
    data['scoring_context']['input_fingerprint'] = sources['dataset']
    bundle = capture(run_id=source.run_id, templates=data['templates'], fallback_templates=data['fallback_templates'],
        legacy_preferences=data['legacy_preferences'], scoring_context=data['scoring_context'],
        configuration=data['configuration'], source_identities=sources)
    return bundle, (subjects, faculty, rooms)
