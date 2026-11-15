"""Fresh owned fictional source and frontend checks; no institutional stores."""
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
    selections = sys.argv[1:] or ['core']
    assert all(s in {'core', 'parity', 'frontend', 'lint', 'api', 'http', 'faults', 'minimum24', 'revision'} for s in selections)
    if len(selections) > 1:
        # Legacy parity tests intentionally edit their OWN fictional import
        # inputs. Never carry that fixture state into another guarded phase.
        for selection in selections:
            result = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), selection], timeout=240)
            if result.returncode:
                return result.returncode
        return 0
    if 'native' in selections:
        import ctypes
        class Memory(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong), *[(n, ctypes.c_ulonglong) for n in ['total','available','tc','ac','tv','av','ex']]]
        m = Memory(); m.length = ctypes.sizeof(m)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)) or m.available < 3*2**30:
            print('NATIVE_NOT_RUN_RESOURCE_GATE_BELOW_3_GIB'); return 3
    owner = Path(tempfile.mkdtemp(prefix='u5c-r1-snapshot-u5h-'))
    (owner / 'OWNED-SNAPSHOT.json').write_text(json.dumps({'scope': 'FICTIONAL_SCHEDULING_ACCELERATED_2'}))
    snapshot = owner / 'repository'
    snapshot.mkdir()
    copied = {}
    # Source bytes come from the preserved working tree, never historical data.
    # No existing application databases/runtime directories or .env are copied.
    for folder in ['backend/services', 'backend/schemas', 'backend/routers', 'backend/genetic_algorithm',
                   'backend/benchmarks', 'backend/tests', 'backend/experiments', 'frontend/src', 'frontend/tests']:
        for path in (ROOT / folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or '.pytest_cache' in path.parts:
                continue
            if folder.startswith('backend') and path.suffix not in {'.py', '.json'}:
                continue
            relative = path.relative_to(ROOT)
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            copied[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in list((ROOT / 'backend').glob('*.py')) + list((ROOT / 'frontend').glob('*.json')) + list((ROOT / 'frontend').glob('*.ts')) + list((ROOT / 'frontend').glob('*.html')):
        target = snapshot / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    if (ROOT / 'frontend/public').is_dir():
        shutil.copytree(ROOT / 'frontend/public', snapshot / 'frontend/public')
    runpy.run_path(str(ROOT / 'docs/testing/dashboard-u5c-r1/fictional_bootstrap.py'))['prepare'](snapshot)
    for path in BASE.glob('*.py'):
        target = snapshot / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    frontend = any(s in {'frontend', 'lint'} for s in selections)
    if frontend:
        subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(snapshot / 'frontend/node_modules'), str(ROOT / 'frontend/node_modules')], capture_output=True, check=True)
        runpy.run_path(str(ROOT / 'docs/testing/dashboard-u5pa/isolate_vite_cache.py'))['prepare'](snapshot, owner)
    env = {k: v for k, v in os.environ.items() if k.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC',
        'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PATHEXT', 'SYSTEMDRIVE'}}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
    sanitizer = runpy.run_path(str(ROOT / 'backend/services/evidence_sanitization.py'))['sanitize']
    for selection in selections:
        target = BASE / (datetime.now(ZoneInfo('Asia/Manila')).strftime('%Y%m%dT%H%M%S%f+0800') + '-' + selection)
        target.mkdir()
        cwd = snapshot / ('frontend' if selection in {'frontend', 'lint'} else 'backend')
        commands = {
            'core': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no',
                        'tests/test_prototype_cycle.py', '--basetemp', str(owner / 'pytest')],
            'frontend': ['node', '--test', 'tests/prototypeCycle.test.mjs', 'tests/prototypeInputs.test.mjs', 'tests/prototypeScheduling.test.mjs'],
            'types': ['node', 'node_modules/typescript/bin/tsc', '-b'],
            'build': ['node', 'node_modules/vite/bin/vite.js', 'build'],
            'lint': ['node', 'node_modules/eslint/bin/eslint.js', '--config', 'prototype-eslint.config.mjs',
                     'src/prototypeCycle/console.mjs', 'src/prototypeCycle/model.mjs', 'tests/prototypeCycle.test.mjs', 'tests/prototypeCycle.live.mjs'],
            'api': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no',
                    'tests/test_prototype_cycle_api.py', '--basetemp', str(owner/'pytest-api')],
            'parity': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no', 'tests/test_ga_bundle_parity.py::test_unmodified_fixed_engine_schedule_fitness_history_and_rng_parity', 'tests/test_ga_bundle_parity.py::test_nonzero_preferences_and_weights_match_original', 'tests/test_ga_bundle_optimizer.py::test_checkpoint_pause_resume_has_exact_rng_best_history_and_schedule_parity', '--basetemp', str(owner/'pytest-parity')],
            'collection': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '--collect-only', '-q', 'tests/test_prototype_cycle.py'],
            'http': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '../docs/testing/scheduling-first-accelerated-2/http_probe.py'],
            'faults': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no',
                'tests/test_prototype_cycle.py::test_execution_failure_is_durable_and_preserves_primary_error',
                'tests/test_prototype_cycle.py::test_witness_commit_uncertainty_retains_checkpoint_and_blocks_recovery',
                'tests/test_prototype_cycle.py::test_quota_check_rejects_before_writes_and_does_not_delete_history',
                'tests/test_prototype_cycle.py::test_source_revision_changes_do_not_replace_captured_input',
                'tests/test_prototype_cycle.py::test_approval_requires_separate_chair_grant_and_creates_immutable_version',
                'tests/test_prototype_cycle.py::test_genuine_frozen_consumption_qualification_and_resume_parity',
                '--basetemp', str(owner/'pytest-faults')],
            'minimum24': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no',
                'tests/test_prototype_cycle.py::test_actual_24_unit_generated_demo_uses_original_engine', '--basetemp', str(owner/'pytest-minimum24')],
            'revision': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no',
                'tests/test_prototype_cycle.py::test_new_frozen_revision_creates_version2_without_mutating_version1', '--basetemp', str(owner/'pytest-revision')],
            'demo': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no',
                     'tests/test_prototype_inputs.py::test_explicit_fictional_demonstration_has_24_eligible_units_and_hard_valid_witness', '--basetemp', str(owner/'pytest-demo')],
            'native': [str(ROOT / '.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--show-capture=no', 'tests/test_prototype_scheduling_native.py', '--basetemp', str(owner / 'pytest-native')],
        }
        if selection == 'native':
            cwd = snapshot / 'backend'
        if selection == 'lint':
            (snapshot / 'frontend/prototype-eslint.config.mjs').write_text("import js from '@eslint/js';import globals from 'globals';export default [js.configs.recommended,{files:['src/prototypeCycle/*.mjs'],languageOptions:{globals:globals.browser}},{files:['tests/*.mjs'],languageOptions:{globals:globals.node}}];\n")
        command = commands[selection]
        start, tick = datetime.now(ZoneInfo('Asia/Manila')).isoformat(), time.perf_counter()
        child = dict(env, SCHEDULING_INCREMENT_EVIDENCE=str(target))
        try:
            result = subprocess.run(command, cwd=cwd, env=child, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=180)
            code, out, err = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            code, out, err = 124, '', 'ISOLATED_CHECK_BOUND_EXCEEDED'
        record = dict(selection=selection, command=command, cwd=str(cwd), snapshot=str(snapshot),
                      started_at=start, ended_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(),
                      elapsed_seconds=time.perf_counter()-tick, exit_code=code,
                      stdout=sanitizer(out), stderr=sanitizer(err),
                      source_sha256={n: h for n, h in copied.items() if any(x in n for x in ['prototype_cycle', 'prototype_tip_witness', 'prototypeCycle', 'prototype_inputs'])},
                      scope='Fictional original GA in-process qualification only; private SQLite and original codec; no native worker, browser, ACL changes or institutional operations')
        with (target / 'command.json').open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
        print(json.dumps(dict(selection=selection, exit_code=code, stdout=sanitizer(out), stderr=sanitizer(err), evidence=target.relative_to(ROOT).as_posix())), flush=True)
        if code:
            return code
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
