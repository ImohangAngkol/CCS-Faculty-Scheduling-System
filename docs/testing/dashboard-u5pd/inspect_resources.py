"""Read-only instantaneous resource/power-policy evidence; changes no setting."""
import ctypes as C
from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import shutil
import subprocess

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]


def main():
    class Memory(C.Structure):
        _fields_=[('length',C.c_ulong),('load',C.c_ulong)]+[(n,C.c_ulonglong) for n in ['physical_total','physical_available','pagefile_total','pagefile_available','virtual_total','virtual_available','extended_available']]
    m=Memory();m.length=C.sizeof(m)
    assert C.windll.kernel32.GlobalMemoryStatusEx(C.byref(m))
    row=dict(recorded_at=datetime.now(ZoneInfo('Asia/Manila')).isoformat(),physical_memory_total_bytes=m.physical_total,physical_memory_available_bytes=m.physical_available,memory_load_percent=m.load,
        system_commit_limit_bytes=m.pagefile_total,system_commit_available_bytes=m.pagefile_available,repository_volume_free_bytes=shutil.disk_usage(ROOT).free,
        interpretation='Instantaneous host resource snapshot only, not process allocation/RSS, enforced filesystem quota, worker feasibility or seven-day safety.')
    r=subprocess.run(['powercfg','/query','SCHEME_CURRENT','SUB_SLEEP'],capture_output=True,text=True,errors='replace',timeout=15)
    row['power_policy_query']=dict(command=['powercfg','/query','SCHEME_CURRENT','SUB_SLEEP'],exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,read_only=True)
    p=BASE/(datetime.now(ZoneInfo('Asia/Manila')).strftime('%Y%m%dT%H%M%S%f%z')+'-resources.json')
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(row,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in row.items() if k!='power_policy_query'}))
if __name__=='__main__':main()
