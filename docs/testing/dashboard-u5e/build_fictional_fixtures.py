"""Export schema fixtures from real read-only projections, never institutional rows."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"backend"))
from sqlalchemy.engine import Engine
Engine.connect=lambda *_a,**_k:(_ for _ in ()).throw(AssertionError("Fixture export forbids database access"))
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    from tests.test_advanced_ga_analysis import fixture,RUN
    from services import ga_history_service as history,advanced_ga_analysis as analysis,ga_run_provenance
    owned=Path(tempfile.mkdtemp(prefix="ga-u5e-schema-"))
    assert owned.resolve().parent==Path(tempfile.gettempdir()).resolve()
    history.SNAPSHOTS_DIR=owned/"history";ga_run_provenance.PROVENANCE_DIR=owned/"provenance"
    try:
        from services import ga_input_receipt
        ga_input_receipt.RECEIPTS_DIR=owned/"receipts"
    except ModuleNotFoundError:pass
    fixture();current=analysis.project(RUN,0);second=analysis.project(RUN,1);comparison=analysis.compare(RUN,0,"generation_best",1,"generation_best");runs=analysis.runs()
    fixture(generations=1,empty=True);empty=analysis.project(RUN)
    fixture(context=False);legacy=analysis.project(RUN)
    fixture(generations=1);one=analysis.project(RUN)
target=Path(__file__).with_name("fictional-api.json")
value={"scope":"Explicitly fictional stored DTO fixtures; real projection code; no GA optimization, database or institutional authorization", "run_id":RUN,"runs":runs,"current":current,"second":second,"comparison":comparison,"empty":empty,"legacy":legacy,"one":one}
with target.open("x",encoding="utf-8",newline="\n") as stream:stream.write(json.dumps(value,indent=2)+"\n")
print(json.dumps({"output":target.relative_to(ROOT).as_posix(),"scope":"fictional DTOs only","variants":6}))
