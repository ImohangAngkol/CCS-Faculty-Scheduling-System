"""Bounded empty-import fictional checks. No native worker/browser selectors."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def main():
    selectors = sys.argv[1:] or ['core']
    assert selectors and all(s in {'core', 'parity', 'regressions', 'integrity', 'collection'} for s in selectors)
    for selection in selectors:
        owner = Path(tempfile.mkdtemp(prefix='u5c-r1-snapshot-u5h-'))
        (owner/'OWNED-SNAPSHOT.json').write_text(json.dumps(dict(scope='FICTIONAL_ACCELERATED_3')))
        snapshot = owner/'repository'; snapshot.mkdir()
        hashes = {}
        for folder in ['services', 'schemas', 'routers', 'genetic_algorithm', 'benchmarks', 'tests', 'experiments']:
            for path in (ROOT/'backend'/folder).rglob('*'):
                if not path.is_file() or path.suffix not in {'.py', '.json'} or '__pycache__' in path.parts or '.pytest_cache' in path.parts:
                    continue
                name = path.relative_to(ROOT); target = snapshot/name
                target.parent.mkdir(parents=True, exist_ok=True); raw = path.read_bytes(); target.write_bytes(raw)
                hashes[name.as_posix()] = hashlib.sha256(raw).hexdigest()
        for path in (ROOT/'backend').glob('*.py'):
            (snapshot/'backend'/path.name).write_bytes(path.read_bytes())
        # The existing HTTP regression serves these real static assets. Copy
        # their preserved bytes; a backend-only snapshot is not a full fixture.
        for folder in ['prototypeWorkload', 'prototypeInputs', 'prototypeScheduling', 'prototypeCycle']:
            for path in (ROOT/'frontend/src'/folder).rglob('*'):
                if path.is_file():
                    name = path.relative_to(ROOT); target = snapshot/name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    raw = path.read_bytes(); target.write_bytes(raw)
                    hashes[name.as_posix()] = hashlib.sha256(raw).hexdigest()
        runpy.run_path(str(ROOT/'docs/testing/dashboard-u5c-r1/fictional_bootstrap.py'))['prepare'](snapshot)
        for path in BASE.glob('*.py'):
            name = path.relative_to(ROOT); target = snapshot/name
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = path.read_bytes(); target.write_bytes(raw)
            hashes[name.as_posix()] = hashlib.sha256(raw).hexdigest()
        python = str(ROOT/'.venv/Scripts/python.exe')
        cases = {
            'core': ['tests/test_prototype_research_continuation.py'],
            'collection': ['--collect-only', 'tests/test_prototype_research_continuation.py'],
            'parity': ['tests/test_ga_bundle_parity.py::test_unmodified_fixed_engine_schedule_fitness_history_and_rng_parity',
                       'tests/test_ga_bundle_parity.py::test_nonzero_preferences_and_weights_match_original',
                       'tests/test_ga_bundle_optimizer.py::test_checkpoint_pause_resume_has_exact_rng_best_history_and_schedule_parity'],
            'integrity': ['tests/test_ga_bundle_optimizer.py::test_wrong_checkpoint_binding_and_corruption_fail_closed',
                          'tests/test_ga_bundle_optimizer.py::test_admitted_workspace_or_configuration_drift_is_rejected',
                          'tests/test_ga_bundle_optimizer.py::test_missing_legacy_and_cross_run_checkpoint_are_not_adopted',
                          'tests/test_ga_bundle_optimizer.py::test_stale_checkpoint_rejected_against_trusted_latest_tip',
                          'tests/test_ga_bundle_optimizer.py::test_real_temporary_preference_and_weight_changes_do_not_change_resume'],
            'regressions': ['tests/test_prototype_cycle.py::test_genuine_frozen_consumption_qualification_and_resume_parity',
                            'tests/test_prototype_cycle.py::test_actual_24_unit_generated_demo_uses_original_engine',
                            'tests/test_prototype_cycle.py::test_actual_generated_minimum_violation_cannot_be_approved',
                            'tests/test_prototype_cycle.py::test_input_infeasible24_versus12_is_durable_before_any_GA',
                            'tests/test_prototype_cycle_api.py'],
        }
        command = [python, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no',
                   *cases[selection], '--basetemp', str(owner/'pytest')]
        env = {k: v for k, v in os.environ.items() if k.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC',
            'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PATHEXT', 'SYSTEMDRIVE'}}
        env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        target = BASE/(datetime.now(ZoneInfo('Asia/Manila')).strftime('%Y%m%dT%H%M%S%f+0800')+'-'+selection)
        target.mkdir(); env['SCHEDULING_INCREMENT_EVIDENCE'] = str(target)
        started, tick = datetime.now(ZoneInfo('Asia/Manila')).isoformat(), time.monotonic()
        sanitize = runpy.run_path(str(ROOT/'backend/services/evidence_sanitization.py'))['sanitize']
        try:
            result = subprocess.run(command, cwd=snapshot/'backend', env=env, capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=240)
            code, out, err = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            code, out, err = 124, '', 'BOUNDED_OFFLINE_CHECK_TIMEOUT'
        record = dict(selection=selection, command=command, cwd=str(snapshot/'backend'), snapshot=str(snapshot),
            started_at=started, ended_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(),
            elapsed_seconds=time.monotonic()-tick, exit_code=code, stdout=sanitize(out), stderr=sanitize(err),
            source_sha256={n:h for n,h in hashes.items() if any(x in n for x in ['prototype_', 'ga_bundle_', 'ga_checkpoint_service', 'scheduling-first-accelerated-3', 'frontend/src/prototype'])},
            classification='OFFLINE_IN_PROCESS_ORIGINAL_GA_AND_TEMPORARY_SQLITE', native_workers=0, browsers=0,
            subprocess_application_restart=False, institutional_operations=False)
        with (target/'command.json').open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2); stream.write('\n')
        print(json.dumps(dict(selection=selection, exit_code=code, stdout=sanitize(out), stderr=sanitize(err),
                             evidence=target.relative_to(ROOT).as_posix())), flush=True)
        if code:
            return code
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
