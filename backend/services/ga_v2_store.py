"""One atomic V2 envelope per run; no writes to V1 best/latest/history/checkpoints."""
import gzip
import hashlib
import json
import zlib
import os
import tempfile
from pathlib import Path
from uuid import UUID

from services import ga_checkpoint_service as legacy
from services.ga_progress_service import input_fingerprint
from services.ga_v2_constraints import Snapshot, reject
from services.ga_v2_engine import ENGINE_VERSION, validate_state

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "constrained_runs_v2"
MAX_BYTES = 64*1024*1024


def engine_fingerprint():
    digest=hashlib.sha256(legacy.engine_fingerprint().encode())
    for name in ("ga_v2_constraints.py","ga_v2_engine.py","ga_v2_store.py","ga_v2_service.py"):
        digest.update(name.encode()); digest.update(Path(__file__).with_name(name).read_bytes())
    for relative in ("schemas/ga_constrained.py","routers/ga_constrained.py","confirmation_models.py",
                     "services/external_confirmation_service.py","services/external_schedule_verification_service.py",
                     "services/confirmation_authority_service.py","services/external_schedule_readiness_service.py",
                     "schemas/external_evidence.py","schemas/external_readiness.py","schemas/external_schedule.py"):
        digest.update(relative.encode()); digest.update((ROOT/relative).read_bytes())
    return digest.hexdigest()


def path_for(run_id):
    if str(UUID(run_id))!=run_id:
        reject("V2_RUN_ID_INVALID", "Use a canonical V2 run identifier.")
    return STORE / run_id / "state.json.gz"


def write(run_id, state, snapshot, authority, templates, status, result):
    # Authority locks include the entire atomic commit. No partial sidecar exists.
    with authority.pinned(snapshot):
        validate_state(state,snapshot,templates)
        payload={"version":2,"engine_version":ENGINE_VERSION,"run_id":run_id,"engine_fingerprint":state["engine_identity"],
            "input_fingerprint":input_fingerprint(),"snapshot":snapshot.model_dump(mode="json"),"constraint_digest":snapshot.digest,
            "status":status,"graph":legacy.encode_graph(state),"result":result}
        body=legacy.canonical(payload)
        if len(body)>MAX_BYTES:
            reject("V2_CHECKPOINT_LIMIT", "V2 checkpoint exceeds the bounded envelope size.")
        envelope={"sha256":hashlib.sha256(body).hexdigest(),"payload":payload}
        path=path_for(run_id)
        compressed=gzip.compress(legacy.canonical(envelope),mtime=0)
        path.parent.mkdir(parents=True,exist_ok=True)
        descriptor,temporary=tempfile.mkstemp(prefix=".v2-",suffix=".tmp",dir=path.parent)
        try:
            with os.fdopen(descriptor,"wb") as stream:
                stream.write(compressed);stream.flush();os.fsync(stream.fileno())
            # Recheck fresh provider lifecycle after validation/compression/I/O,
            # immediately before the single atomic public checkpoint commit.
            authority.recheck(snapshot)
            if engine_fingerprint()!=state["engine_identity"] or input_fingerprint()!=payload["input_fingerprint"]:
                reject("V2_CHECKPOINT_INCOMPATIBLE", "V2 source or scheduling inputs changed before atomic publication.")
            os.replace(temporary,path)
            if os.name!="nt":
                directory=os.open(path.parent,os.O_RDONLY)
                try:os.fsync(directory)
                finally:os.close(directory)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)


def read(run_id):
    try:
        with gzip.open(path_for(run_id),"rb") as stream:
            raw=stream.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise ValueError()
        envelope=json.loads(raw); payload=envelope["payload"]
        if hashlib.sha256(legacy.canonical(payload)).hexdigest()!=envelope["sha256"]:
            raise ValueError()
        if payload["version"]!=2 or payload["engine_version"]!=ENGINE_VERSION or payload["run_id"]!=run_id:
            reject("V2_CHECKPOINT_INCOMPATIBLE", "V2 checkpoint version or run identity is incompatible.")
        if payload["engine_fingerprint"]!=engine_fingerprint() or payload["input_fingerprint"]!=input_fingerprint():
            reject("V2_CHECKPOINT_INCOMPATIBLE", "V2 engine or scheduling input fingerprint changed.")
        snapshot=Snapshot.model_validate_json(legacy.canonical(payload["snapshot"]))
        if snapshot.digest!=payload["constraint_digest"]:
            raise ValueError()
        state=legacy.decode_graph(payload["graph"])
        if state["engine_identity"]!=payload["engine_fingerprint"]:
            reject("V2_CHECKPOINT_INCOMPATIBLE", "V2 graph and envelope engine identities differ.")
        return payload,snapshot,state
    except (OSError, ValueError, KeyError, TypeError, EOFError, RecursionError,zlib.error) as error:
        from services.ga_v2_constraints import ConstraintError
        if isinstance(error,ConstraintError):
            raise
        reject("V2_CHECKPOINT_INVALID", "V2 checkpoint is missing, corrupted or incomplete; no legacy fallback was attempted.")
