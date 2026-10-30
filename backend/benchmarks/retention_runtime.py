"""Private-process, schema-only import bootstrap for Phase 5 fictional tests.

Production source/functions are not replaced. Temporary import-data loaders are
restored before execution. Scheduling inputs/fingerprints remain explicit.
"""
from contextlib import ExitStack,contextmanager
import builtins
import io
import json
from pathlib import Path
import random
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'backend/data'
CSV_SCHEMAS={
    'first_sem_bsit_subjects.csv':['course no.','course title','units','num of lec hours/week','num of lab hours/week','year_level'],
    'BSIT_Consolidated_Subject_Schedules.csv':['Section','Course Number','Schedule'],
    'Faculty Preferences V2.csv':['Faculty','Day(s)','Subject','New Schedule','Room Assignment'],
    'Faculty Admin, Research and Extension.csv':['Faculty','Admin Load','Research Load','Extension Load','Teaching Load'],
    'faculty_qualifications.csv':['faculty_code','specializations'],
    'faculty_subject_eligibility.csv':['faculty_code','course_no','eligibility_status'],
    'subject_domains.csv':['course_no','primary_domain','secondary_domains'],
}
JSON_SCHEMAS={'faculty_identities.json':{'version':1,'faculty':[]},
              'preassigned_assignments.json':{'external_instructors':{},'assignments':[]}}
BOOTSTRAP={'used':False,'csv_reads_substituted':0,'json_reads_substituted':0}


def runtime():
    from benchmarks import scaled_python as bench
    if bench._runtime is not None:
        if not BOOTSTRAP['used']:
            raise RuntimeError('FRESH_FICTIONAL_PROCESS_REQUIRED')
        return bench.runtime()
    import pandas as pd
    original_csv=pd.read_csv; original_open=Path.open; rng=random.getstate()
    def csv(path,*args,**kwargs):
        if Path(path).resolve().parent==DATA:
            name=Path(path).name
            if name not in CSV_SCHEMAS:raise RuntimeError('UNREVIEWED_DATASET_PARSE_REJECTED')
            BOOTSTRAP['csv_reads_substituted']+=1
            return pd.DataFrame(columns=CSV_SCHEMAS[name])
        return original_csv(path,*args,**kwargs)
    def opened(path,mode='r',*args,**kwargs):
        if path.resolve().parent==DATA and 'b' not in mode:
            if path.name not in JSON_SCHEMAS:raise RuntimeError('UNREVIEWED_DATASET_PARSE_REJECTED')
            BOOTSTRAP['json_reads_substituted']+=1
            return io.StringIO(json.dumps(JSON_SCHEMAS[path.name]))
        return original_open(path,mode,*args,**kwargs)
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(pd,'read_csv',csv))
            stack.enter_context(patch.object(Path,'open',opened))
            result=bench.runtime()
        assert not result[0].schedule.list_faculty and not result[0].schedule.list_subjects
        BOOTSTRAP['used']=True
        return result
    finally:random.setstate(rng)


@contextmanager
def data_guard():
    """Reject institutional text parsing; binary fingerprint reads stay genuine."""
    import pandas as pd
    old_csv=pd.read_csv; old_builtin=builtins.open; old_io=io.open
    def inside(path):
        try:return Path(path).resolve().parent==DATA
        except TypeError:return False
    def csv(path,*args,**kwargs):
        if inside(path):raise RuntimeError('INSTITUTIONAL_CSV_PARSE_REJECTED')
        return old_csv(path,*args,**kwargs)
    def opener(original):
        def opened(path,mode='r',*args,**kwargs):
            if inside(path) and 'b' not in mode:raise RuntimeError('INSTITUTIONAL_TEXT_PARSE_REJECTED')
            return original(path,mode,*args,**kwargs)
        return opened
    with patch.object(pd,'read_csv',csv),patch.object(builtins,'open',opener(old_builtin)),patch.object(io,'open',opener(old_io)):
        yield
