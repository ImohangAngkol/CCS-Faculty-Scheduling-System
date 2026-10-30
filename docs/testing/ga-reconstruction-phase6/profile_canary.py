"""Reproduce local cProfile inter-thread attribution without GA or data imports."""
import cProfile
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import pstats
import sys
import threading
import time

BASE=Path(__file__).resolve().parent


def inspect(threaded):
    stop=threading.Event()
    def background():
        while not stop.wait(.0001):time.sleep(.0001)
    def leaf():return 1
    def caller():
        for _ in range(200000):leaf()
    thread=threading.Thread(target=background) if threaded else None
    if thread:thread.start()
    profile=cProfile.Profile();profile.enable();caller();profile.disable()
    stop.set()
    if thread:thread.join()
    for (_,_,name),record in pstats.Stats(profile).stats.items():
        if name=='leaf':
            callers=[key[2] for key in record[4]]
            return {'threaded':threaded,'leaf_calls':record[1],'recorded_callers':callers,
                    'caller_contract_valid':set(callers)=={'caller'}}


def main():
    results=[inspect(True),inspect(False)]
    assert results[1]['caller_contract_valid'] and results[1]['leaf_calls']==200000
    directory=BASE/(datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S%f+0800')+'-profile-canary');directory.mkdir(exist_ok=False)
    (directory/'canary.json').write_bytes((json.dumps({'python':sys.version,'results':results,
        'scope':'Local profiler attribution diagnosis, no assertion of an identified upstream bug; no production or GA failure'},indent=2)+'\n').encode())
    print(directory.as_posix())


if __name__=='__main__':main()
