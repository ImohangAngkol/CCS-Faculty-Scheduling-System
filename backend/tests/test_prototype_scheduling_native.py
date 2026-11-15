"""Genuine existing Windows worker; NOT a diagnostic replacement or mock."""
import json
import os
from pathlib import Path
import time
import pytest
from services.ga_worker_contract import fictional_source
try:
    fictional_source()
except ValueError:
    pytest.skip('Owned fictional snapshot required', allow_module_level=True)
from services.prototype_scheduling import resource_snapshot
from tests.test_prototype_scheduling import setup, selected, change, PRINCIPAL


def test_genuine_worker_original_result_and_captured_minimum():
    resources = resource_snapshot()
    assert resources['passed'], 'Native acceptance resource gate: at least3GiB available required'
    s, _ = setup(8)
    s.workload.save(PRINCIPAL, change(**{'2': 24}))
    request = selected(s)
    started = time.perf_counter()
    response = s.submit(PRINCIPAL, request)
    assert response['worker_admitted'], response['state']
    worker = s.operator.bridge.worker
    run = response['worker']['worker_run_id']
    try:
        # Same original90s outer join; original60s worker cap is unchanged.
        thread = worker.threads[run]
        thread.join(90)
        assert not thread.is_alive(), 'Owned supervisor did not finish'
        s.workload.save(PRINCIPAL, change(1, **{'2': 0}))
        response = s.inspect(PRINCIPAL, response['run_id'])
        public = dict(resources=resources, elapsed_seconds=time.perf_counter()-started, result=response)
        with worker.storage.connection() as db:
            public['process_status'] = [x['status'] for x in db.execute('SELECT status FROM l_processes WHERE run=?', (run,))]
        folder = os.environ.get('SCHEDULING_INCREMENT_EVIDENCE')
        if folder:
            (Path(folder)/'native-result.json').write_text(json.dumps(public, indent=2)+'\n', encoding='utf-8')
        assert response['state'] in {'CANDIDATE_FULLY_FEASIBLE', 'CANDIDATE_CONSTRAINT_VIOLATING'}, response.get('evidence_error', response['state'])
        result = response['result']
        assert result['runtime']['terminal_cleanup_recorded'] and all(x == 'EXIT_VERIFIED' for x in public['process_status'])
        assert result['technical_consumption'] == 'VERIFIED_BY_ORIGINAL_COMMITTED_CHILD_PROOF'
        assert response['minimum_revision'] == 1 and s.workload.store.current()['revision'] == 2
        assert result['qualification']['original_hard_constraints'] == 'VALIDATED'
        assert not result['Saved_Best_or_approved_promotion']
        assert s.submit(PRINCIPAL, request) == response
    finally:
        worker.close(PRINCIPAL, timeout=20)
