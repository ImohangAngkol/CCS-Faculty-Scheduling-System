"""Bounded operator handoff in a freshly owned fictional snapshot only.

No browser controls invoke a worker. The original PB runner is called once
before serving GET-only observations. Private login stays outside the repository.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'backend'))
from services.ga_worker_contract import fictional_source
fictional_source()
from tests.research_console_support import Environment


def main():
    if sys.argv[1:]!=['--fictional-only']:raise SystemExit('Explicit fictional mode required')
    from services.ga_research_continuity import ContinuityObserver
    env=Environment();env.observer=ContinuityObserver(env.bridge);frontend=None
    try:
        os.environ['AUTH_ALLOWED_ORIGINS']=env.origin;os.environ['AUTH_COOKIE_SECURE']='false'
        env.prepare();env.serve()
        login=env.bridge.worker.storage.root/'CONSOLE-LOGIN.json'
        with login.open('x',encoding='utf-8') as f:
            json.dump(dict(scope='FICTIONAL_ONLY_NOT_INSTITUTIONAL',username='research@fictional.invalid',password=env._password,console=env.origin+'/research/runs',backend=env.backend),f)
        child=dict(os.environ,VITE_API_URL=env.backend)
        frontend=subprocess.Popen(['node','tests/researchConsole.host.mjs',str(int(env.origin.rsplit(':',1)[1]))],cwd=Path.cwd().parent/'frontend',env=child,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        from queue import Queue,Empty
        from threading import Thread
        q=Queue();Thread(target=lambda:q.put(frontend.stdout.readline()),daemon=True).start()
        try:ready=q.get(timeout=20)
        except Empty:raise RuntimeError('Owned frontend startup exceeded bound') from None
        if ready.strip()!='OWNED_READ_ONLY_CONSOLE_READY':raise RuntimeError('Owned frontend did not start')
        stop=login.parent/'CONSOLE.stop'
        print(json.dumps(dict(console=env.origin+'/research/runs',private_login_file=str(login),owned_stop_marker=str(stop),expires_in_seconds=300,
            operational_controls=False,institutional_authority=False)),flush=True)
        end=time.monotonic()+300
        while time.monotonic()<end and not stop.exists() and frontend.poll() is None:time.sleep(.25)
    finally:
        if frontend:
            if frontend.poll() is None:frontend.terminate()
            frontend.wait(10);frontend.stdout.close()
        env.close()
    return 0
if __name__=='__main__':raise SystemExit(main())
