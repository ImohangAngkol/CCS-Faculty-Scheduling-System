"""Record isolated benchmark/D10 test evidence; never runs PostgreSQL cases."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
SELECTIONS = {
    'benchmark': ['tests/performance/test_scaled_python.py'],
    'd10': ['tests/d10/test_v2_engine.py', 'tests/d10/test_v2_api.py'],
    'fitness': ['tests/test_fitness_reporting.py', 'tests/test_preassigned_assignments.py'],
}


def main():
    key = sys.argv[1]
    selected = SELECTIONS[key]
    zone = timezone(timedelta(hours=8))
    stamp = datetime.now(zone).strftime('%Y%m%dT%H%M%S%f+0800')+'-'+key
    directory = ROOT/'docs/testing/ga-performance-phase2'/stamp
    directory.mkdir(exist_ok=False)
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'PATH','SYSTEMROOT','WINDIR','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA',
        'PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA','SYSTEMDRIVE','PATHEXT'}}
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', PYTHONUTF8='1', PYTHONHASHSEED='0')
    command = [str(ROOT/'.venv/Scripts/python.exe'), '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
               *selected, '-q', '--tb=short', '--show-capture=no',
               '--basetemp', str(Path(tempfile.gettempdir())/('scaled-ga-tests-'+stamp))]
    started = datetime.now(zone).isoformat()
    tick = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT/'backend', env=env, capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
    sys.path.insert(0, str(ROOT/'backend'))
    from services.evidence_sanitization import sanitize_tree
    record = sanitize_tree({'selection': key, 'command': command, 'cwd': 'backend', 'started_at': started,
                            'finished_at': datetime.now(zone).isoformat(), 'elapsed_seconds': time.perf_counter()-tick,
                            'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
                            'scope': 'Fictional tests / owned SQLite / original engine; no PostgreSQL or publication authority',
                            'environment': 'Whitelisted OS only; database URLs and approval flags excluded; hash seed 0'})
    (directory/'command.json').write_bytes((json.dumps(record, indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'evidence': directory.relative_to(ROOT).as_posix(), 'exit_code': result.returncode,
                      'output_tail': record['stdout'][-5500:]}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
