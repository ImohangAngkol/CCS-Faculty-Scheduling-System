"""Bounded Windows-path characterization only; no engine, data or receipts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import tempfile
import threading
import time
from uuid import uuid4

BASE=Path(__file__).resolve().parent

def main():
    start=datetime.now().astimezone().isoformat();tick=time.perf_counter()
    root=Path(tempfile.mkdtemp(prefix='ga-u5i-path-probe-')).resolve()
    assert root.parent==Path(tempfile.gettempdir()).resolve()
    results=[]
    for _ in range(250):
        parent=root/uuid4().hex;barrier=threading.Barrier(2)
        def observe(_):
            target=parent/str(uuid4());barrier.wait()
            mismatch=target.resolve().parent!=parent.resolve()
            # Reproduces the pre-directory-creation path guard and concurrent
            # parent creation, without any private receipt or optimizer state.
            target.mkdir(parents=True,exist_ok=True)
            return mismatch
        with ThreadPoolExecutor(2) as pool:results.extend(pool.map(observe,[1,2]))
    value=dict(started_at=start,ended_at=datetime.now().astimezone().isoformat(),elapsed_seconds=time.perf_counter()-tick,
        path_checks=len(results),mismatches=sum(results),scope='Independent path-only characterization. Not a reproduction of the complete U5D observer or concurrent GA execution.',
        historical_failure_preserved=True,root_cause='UNCONFIRMED' if not any(results) else 'PATH_GUARD_INCONSISTENCY_REPRODUCED',
        production_source_changed=False)
    target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-receipt-path-probe.json')
    with target.open('x',encoding='utf-8') as f:f.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps(value))

if __name__=='__main__':main()
