"""Resume owned copies of the actual supported V1 fixtures made BEFORE V2 edits.

No historical checkpoint is migrated or made compatible. No fingerprint override,
operator substitution, database or raw academic/checkpoint evidence export.
"""
from contextlib import redirect_stdout, redirect_stderr
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"backend"))


def run():
    candidates=[]
    for record in sorted(Path(__file__).parent.glob("*-v1-fixtures/command.json")):
        value=json.loads(record.read_text(encoding="utf-8"))
        fixtures=sorted(record.parent.glob("fixture-*.json"))
        if value["exit_code"]==0 and len(fixtures)==3:
            candidates.append((record,value,fixtures))
    if not candidates:
        raise RuntimeError("Supported pre-V2 fixtures are unavailable; no compatibility is claimed")
    record,command,fixtures=candidates[0]
    private_root=Path(command["command"][command["command"].index("--basetemp")+1]).resolve()
    temp_parent=Path(tempfile.gettempdir()).resolve()
    if private_root.parent!=temp_parent or not private_root.name.startswith("d10-compat-pytest-"):
        raise RuntimeError("Unexpected supported fixture location")
    documents=[json.loads(path.read_text(encoding="utf-8")) for path in fixtures]
    sources={hashlib.sha256(p.read_bytes()).hexdigest():p for p in private_root.rglob("checkpoint-*.json.gz")}
    with open(os.devnull,"w",encoding="utf-8") as sink,redirect_stdout(sink),redirect_stderr(sink):
        from services import ga_service as engine,ga_checkpoint_service as checkpoints,chromosome_service
        from genetic_algorithm.utils import Functions
        from tests.d10.support import templates,preferences
        engine_identity=checkpoints.engine_fingerprint();input_identity=checkpoints.input_fingerprint()
        if any(d["engine_fingerprint"]!=engine_identity or d["input_fingerprint"]!=input_identity for d in documents):
            raise RuntimeError("The supported V1 baseline identity changed; no compatibility bypass is permitted")
        previous_rng=random.getstate();findings=[]
        with tempfile.TemporaryDirectory(prefix="d10-supported-v1-copy-") as directory:
            owned=Path(directory).resolve()
            if owned.parent!=temp_parent or not owned.name.startswith("d10-supported-v1-copy-"):
                raise RuntimeError("Unexpected owned copy directory")
            checkpoints.CHECKPOINTS_DIR=owned/"checkpoints"
            chromosome_service.SAVED_CHROMOSOME_DIR=owned
            chromosome_service.BEST_CHROMOSOME_PATH=owned/"best.json"
            def configure():
                values=templates(compact=True)
                for key,value in zip(("list_subjects","list_faculty","lst_rooms"),values):setattr(engine,key,value)
                engine.df_faculty_pref=preferences();Functions.list_faculty=values[1]
                return copy.deepcopy(values)
            configure();random.seed(710)
            expected=engine.run_genetic_algorithm(**documents[0]["parameters"])
            expected_rng=random.getstate()
            for document in documents:
                source=sources.get(document["checkpoint_sha256"])
                if source is None:
                    raise RuntimeError("The actual recorded pre-V2 checkpoint is missing")
                destination=checkpoints.CHECKPOINTS_DIR/source.parent.name/source.name
                destination.parent.mkdir(parents=True,exist_ok=False);shutil.copyfile(source,destination)
                current=configure()
                state=checkpoints.load_checkpoint(source.parent.name,current,source.name)
                random.seed(999)
                resumed=engine.run_genetic_algorithm(**state["parameters"],resume_state=state)
                fields=("schedule","history","best_fitness","fitness_breakdown","faculty_analysis")
                if any(resumed[k]!=expected[k] for k in fields) or random.getstate()!=expected_rng:
                    raise RuntimeError("Supported V1 continuation differs from the reproducible uninterrupted fixture")
                if hashlib.sha256(source.read_bytes()).hexdigest()!=document["checkpoint_sha256"] or destination.read_bytes()!=source.read_bytes():
                    raise RuntimeError("A supported source/copy checkpoint changed")
                findings.append({"pause_generation":document["pause_generation"],"checkpoint_sha256":document["checkpoint_sha256"],
                    "actual_pre_V2_fixture_restored":True,"real_original_operator_continuation":True,
                    "schedule_history_fitness_analysis_and_RNG_equivalent":True,"source_and_copy_unchanged":True})
        random.setstate(previous_rng)
    return {"scope":"Actual current-release V1 pre-V2 checkpoint copies, original operators and real continuation; not six historical artifact acceptance",
        "source_fixture_record":record.relative_to(ROOT).as_posix(),"engine_version":"ga-continuation-v1",
        "engine_fingerprint":engine_identity,"input_fingerprint":input_identity,
        "standalone_continuation_checks_passed":len(findings),"failed":0,"findings":findings,
        "raw_checkpoints_archived":False,"temporary_copies_removed":not owned.exists(),"database_connections":0}


if __name__=="__main__":
    print(json.dumps(run(),ensure_ascii=True))
