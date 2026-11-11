"""Finite fictional handoff; private credentials never enter repository/logs."""
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'backend'))
from services.ga_worker_contract import fictional_source
fictional_source()
from tests.research_console_support import Environment
from services.ga_research_operator import Operator
from routers.research_operator import create_app
from tests.trusted_run_support import PRINCIPAL


def main():
    if sys.argv[1:] not in [['--fictional-only'],['--fictional-only','--probe']]:raise SystemExit('Explicit fictional mode required')
    probe='--probe' in sys.argv;env=Environment();operator=Operator(env.bridge,initialize=True);original=env.app
    def app():
        a=create_app(operator);a.dependency_overrides.update(original().dependency_overrides);return a
    env.app=app
    try:
        os.environ['AUTH_COOKIE_SECURE']='false';env.serve();os.environ['AUTH_ALLOWED_ORIGINS']=env.backend
        login=env.bridge.worker.storage.root/'OPERATOR-LOGIN.json';stop=login.parent/'OPERATOR.stop'
        with login.open('x',encoding='utf-8') as f:json.dump(dict(username='research@fictional.invalid',password=env._password,console=env.backend+'/research/operator'),f)
        if not probe:print(json.dumps(dict(console=env.backend+'/research/operator',private_login_file=str(login),owned_stop_marker=str(stop),expires_in_seconds=300,institutional_authority=False)),flush=True)
        end=time.monotonic()+(2 if probe else 300)
        while time.monotonic()<end and not stop.exists():time.sleep(.1)
        result=env.bridge.worker.shutdown(PRINCIPAL,grace=5)
        if not result['quiescent']:raise RuntimeError('Owned shutdown unverified')
        login.unlink()
        print(json.dumps(dict(finite_handoff_closed=True,owned_worker_quiescent=True,private_login_removed=True,production_admission='BLOCKED')),flush=True)
    finally:env.close()


if __name__=='__main__':main()
