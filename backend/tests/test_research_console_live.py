"""Actual Edge -> TCP FastAPI/session auth -> owned fictional SQLite/worker."""
import json
import os
from pathlib import Path
import subprocess
import pytest
from services.ga_worker_contract import fictional_source
try:fictional_source()
except ValueError:pytest.skip('Owned fictional source required',allow_module_level=True)
from tests.test_research_bridge import fixture
from tests.test_research_observations import files
from tests.research_console_support import Environment


def test_live_edge_readonly_console(fixture,monkeypatch):
    b,_=fixture(generations=1);env=Environment(b,fixture.allowed.add)
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS',env.origin);monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
    try:
        env.prepare();env.serve();before=files(b)
        # Auth sessions write only the separate disposable auth DB. Compare all
        # research files, excluding that explicitly separate authentication DB.
        research=lambda d:{k:v for k,v in d.items() if not k.startswith('CONSOLE-AUTH.sqlite3')}
        evidence=Path(os.environ['U5PC_EVIDENCE']);child=dict(os.environ,VITE_API_URL=env.backend,U5PC_EVIDENCE=str(evidence))
        result=subprocess.run(['node','tests/researchConsole.live.mjs'],cwd=Path.cwd().parent/'frontend',env=child,
            input=json.dumps(env.private_browser_input())+'\n',capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        # Browser never logs credentials, cookies, URLs with auth, or raw bodies.
        (evidence/'live-browser-command.json').write_text(json.dumps(dict(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr,
            scope='Actual Edge/React/TCP FastAPI/real sessions/private SQLite/real U5L child; interrupted metadata explicitly injected'),indent=2)+'\n')
        assert result.returncode==0,'Live browser failed; sanitized diagnostics retained'
        assert research(files(b))==research(before),'Research store mutated by console reads'
        # Reconstruct the complete API and observer against retained research.
        from services.ga_research_observation import Observer
        from tests.test_research_bridge import reopen
        assert Observer(reopen(b)).detail(__import__('tests.trusted_run_support',fromlist=['PRINCIPAL']).PRINCIPAL,env.runs['completed'])==env.observer.detail(__import__('tests.trusted_run_support',fromlist=['PRINCIPAL']).PRINCIPAL,env.runs['completed'])
        (evidence/'live-preservation.json').write_text(json.dumps(dict(research_files_byte_identical=True,API_reconstruction_equal=True,auth_database_separate=True,all_research_requests_GET=True,worker_completed_before_reads=True,production_authority=False),indent=2)+'\n')
    finally:env.close()


def test_operator_handoff_process():
    """Start the documented host, then stop only its owned marker/process."""
    import sys,time,threading
    from queue import Queue,Empty
    root=Path.cwd().parent
    child=subprocess.Popen([sys.executable,'-B','../docs/testing/dashboard-u5pc/serve_console.py','--fictional-only'],cwd=Path.cwd(),
        env=dict(os.environ),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    lines=Queue()
    def reader():
        for line in child.stdout:lines.put(line)
    threading.Thread(target=reader,daemon=True).start();ready=None
    try:
        end=time.monotonic()+100
        while time.monotonic()<end:
            try:line=lines.get(timeout=.2)
            except Empty:
                if child.poll() is not None:break
                continue
            try:obj=json.loads(line)
            except ValueError:continue
            if obj.get('private_login_file'):ready=obj;break
        if ready is None and child.poll() is not None:
            from services.evidence_sanitization import sanitize
            with (Path(os.environ['U5PC_EVIDENCE'])/'operator-handoff-startup-error.json').open('x') as f:
                json.dump(dict(exit_code=child.returncode,stderr=sanitize(child.stderr.read()),scope='Owned fictional startup only; no credentials printed'),f,indent=2)
        assert ready is not None,'Owned operator handoff did not start; credentials withheld'
        private=Path(ready['private_login_file']);stop=Path(ready['owned_stop_marker'])
        import tempfile
        assert private.parent.parent==Path(tempfile.gettempdir()) and private.parent.name.startswith('ga-u5i-')
        assert stop.parent==private.parent and stop.name=='CONSOLE.stop' and private.name=='CONSOLE-LOGIN.json'
        assert private.is_file() and ready['operational_controls'] is False
        with stop.open('x'):pass
        assert child.wait(25)==0,'Owned handoff did not stop cleanly'
        path=Path(os.environ['U5PC_EVIDENCE'])/'operator-handoff.json'
        path.write_text(json.dumps(dict(scope='Actual separate fictional Python host + native worker + Vite; no institutional authority',
            ready=True,private_credentials_not_archived=True,owned_stop_verified=True,exit_code=0,window_limit_seconds=300),indent=2)+'\n')
    finally:
        if child.poll() is None:child.terminate();child.wait(10)
        child.stdout.close();child.stderr.close()
