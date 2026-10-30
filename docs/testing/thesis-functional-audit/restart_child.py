"""Schema-only bootstrap for one reviewed owned-SQLite D11 restart fixture."""
from pathlib import Path
import runpy
import socket
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'backend'))
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import scaled_python as bench


def owned_socketpair(sock,address,frame):
    """Windows asyncio uses the stdlib's authenticated loopback self-pipe.

    Permit only that exact stdlib call with its own live listener/client pair;
    an arbitrary loopback connection or PostgreSQL port is not permitted.
    """
    if frame.f_code is not getattr(socket.socketpair,'__code__',None):return False
    listener=frame.f_locals.get('lsock')
    return (frame.f_locals.get('csock') is sock and listener is not None
            and address[0] in ('127.0.0.1','::1') and address[1]!=5432
            and tuple(address[:2])==tuple(listener.getsockname()[:2]))


def main():
    assert len(sys.argv)==2
    database=Path(sys.argv[1]).resolve()
    assert database.is_relative_to(Path(tempfile.gettempdir()).resolve()) and database.is_file()
    runtime()
    import psycopg2
    def deny(*args,**kwargs):raise RuntimeError('POSTGRESQL_REJECTED')
    psycopg2.connect=deny  # private child only; original test uses owned SQLite
    def guard(event,args):
        if event=='socket.connect' and not owned_socketpair(args[0],args[1],sys._getframe(1)):
            raise RuntimeError('NETWORK_REJECTED')
        if event=='sqlite3.connect':assert Path(args[0]).resolve()==database,'UNOWNED_SQLITE_REJECTED'
    sys.addaudithook(guard)
    sys.argv=['tests.dashboard.adjustment_restart_child',str(database)]
    with bench.synthetic_scoring(([],[],[]),[],runtime()[3]().to_dict()),data_guard():
        runpy.run_module('tests.dashboard.adjustment_restart_child',run_name='__main__')


if __name__=='__main__':main()
