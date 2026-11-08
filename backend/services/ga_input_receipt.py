"""Run-bound, immutable V1 input OBSERVATIONS; not full consumption attestation.

Only the existing server execution wrapper calls this service. It never installs
a loader, scorer, profiler, provider, global symbol replacement or GA seed.
"""
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import tempfile
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from services.ga_history_service import HistoryError

RECEIPTS_DIR = Path(__file__).resolve().parents[1]/"run_input_receipts_v1"
CONTRACT = "ga-run-input-observation-v1"
HASH = r"^[0-9a-f]{64}$"
MAX_BYTES = 32768
MAX_GRAPH_BYTES = 16*1024*1024
PARAMETERS = ("population_size","generations","fresh_chromosomes","baseline_mode","mutation_attempts","max_restarts")
Reason = Literal["CONSUMPTION_NOT_ESTABLISHED", "CACHED_MUTABLE_MODELS", "ACADEMIC_CONTEXT_NOT_CAPTURED",
    "MODEL_OBSERVATION_UNAVAILABLE", "SCORING_CONTEXT_NOT_OBSERVED", "SCORING_CONTEXT_CHANGED",
    "SCORING_CONTEXT_UNAVAILABLE", "DATASET_CHANGED", "CONFIGURATION_DRIFT", "CROSS_RUN_EVENT",
    "CALL_INTERRUPTED", "FINAL_RECORD_MISSING", "RECEIPT_MISSING", "RESUME_NOT_ATTESTED", "OBSERVATION_LIMIT_REACHED", "SEED_INPUT_NOT_BOUND"]


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def digest(value):return hashlib.sha256(canonical(value)).hexdigest()


def now():return datetime.now(timezone.utc).isoformat()


class Configuration(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)
    population_size:int
    generations:int
    fresh_chromosomes:int
    baseline_mode:str
    mutation_attempts:int
    max_restarts:int


class Receipt(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,frozen=True)
    schema_version:Literal[1]=1
    loader_contract:Literal["ga-run-input-observation-v1"]=CONTRACT
    run_id:str
    captured_at:str
    verification_status:Literal["UNVERIFIED"]="UNVERIFIED"
    eligible_for_current:Literal[False]=False
    institutional_authorization:Literal["NOT_ESTABLISHED"]="NOT_ESTABLISHED"
    reasons:list[Reason]

    @field_validator("schema_version",mode="before")
    @classmethod
    def version(cls,value):
        if type(value) is not int or value!=1:raise ValueError("Unsupported receipt schema")
        return value

    @field_validator("run_id")
    @classmethod
    def identifier(cls,value):
        if str(UUID(value))!=value:raise ValueError("Canonical run identity required")
        return value

    @field_validator("captured_at")
    @classmethod
    def timestamp(cls,value):
        if datetime.fromisoformat(value).tzinfo is None:raise ValueError("Aware receipt time required")
        return value

    @field_validator("reasons")
    @classmethod
    def fail_closed(cls,value):
        if "CONSUMPTION_NOT_ESTABLISHED" not in value or len(set(value))!=len(value):
            raise ValueError("Observation cannot grant consumption verification")
        return value


class Start(Receipt):
    stage:Literal["BEFORE_OPTIMIZER_CALL"]="BEFORE_OPTIMIZER_CALL"
    fingerprint_scope:Literal["PRE_CALL_ALIASES_NOT_CONSUMPTION_PROOF"]="PRE_CALL_ALIASES_NOT_CONSUMPTION_PROOF"
    graph_codec:Literal["checkpoint-graph-v1-order-sensitive"]="checkpoint-graph-v1-order-sensitive"
    run_started_at:str
    academic_context_reference:dict[str,str]|None=None
    loaded_model_fingerprint:str|None=Field(default=None,pattern=HASH)
    dataset_fingerprint:str=Field(pattern=HASH)
    engine_fingerprint:str=Field(pattern=HASH)
    observer_source_fingerprint:str=Field(pattern=HASH)
    configuration:Configuration
    configuration_fingerprint:str=Field(pattern=HASH)
    input_source_identities:list[Literal["runtime-model-aliases","legacy-preference-frame","data-file-byte-set","effective-run-parameters","optional-u5b-record"]]

    @field_validator("run_started_at")
    @classmethod
    def started(cls,value):
        if datetime.fromisoformat(value).tzinfo is None:raise ValueError("Aware server start required")
        return value

    @field_validator("academic_context_reference")
    @classmethod
    def reference(cls,value):
        if value is not None and (set(value)!={"provenance_sha256","academic_context_sha256"} or
            any(len(v)!=64 or any(c not in "0123456789abcdef" for c in v) for v in value.values())):
            raise ValueError("Invalid academic reference")
        return value

    @field_validator("input_source_identities")
    @classmethod
    def source_set(cls,value):
        if len(value)!=5 or len(set(value))!=5:raise ValueError("Complete observation source labels required")
        return value


class End(Receipt):
    stage:Literal["AFTER_OPTIMIZER_CALL"]="AFTER_OPTIMIZER_CALL"
    scoring_observation_scope:Literal["ACTIVE_CONTEXT_AT_GENERATION_CALLBACK_ONLY"]="ACTIVE_CONTEXT_AT_GENERATION_CALLBACK_ONLY"
    start_receipt_sha256:str=Field(pattern=HASH)
    outcome:Literal["CALL_RETURNED","CALL_INTERRUPTED","PAUSED","STOPPED_WITHOUT_RESULT"]
    model_fingerprint_after:str|None=Field(default=None,pattern=HASH)
    scoring_context_first:str|None=Field(default=None,pattern=HASH)
    scoring_context_last:str|None=Field(default=None,pattern=HASH)
    generation_observations:int=Field(ge=0,le=32)
    first_generation:int|None=None
    last_generation:int|None=None
    monitor_configuration_fingerprint:str|None=Field(default=None,pattern=HASH)


def error(message="Input receipt is invalid or unavailable.",code="GA_INPUT_RECEIPT_INVALID",status=422):
    return HistoryError(message,code,status)


def directory(run_id):
    try:
        if str(UUID(run_id))!=run_id:raise ValueError()
    except (TypeError,ValueError,AttributeError):raise error("Invalid receipt run identity.",status=404)
    root_path=RECEIPTS_DIR
    target=root_path/run_id
    if any(p.is_symlink() or p.is_junction() for p in (root_path,target)):
        raise error()
    parent=target.resolve().parent;root=root_path.resolve()
    if parent!=root:
        # Windows can retain an extended namespace prefix during concurrent
        # creation. Require filesystem identity, never strip arbitrary prefixes.
        try:
            if not parent.samefile(root):raise error()
        except OSError:raise error() from None
    # Preserve reparse rejection if a path changed while it was resolved.
    if any(p.is_symlink() or p.is_junction() for p in (root_path,target)):
        raise error()
    return target


def write(run_id,name,value):
    # Initialize the writer-owned root before observing its physical identity.
    # Reads stay non-writing; invalid run IDs must not create even an empty root.
    try:
        if str(UUID(run_id))!=run_id:raise ValueError()
    except (TypeError,ValueError,AttributeError):raise error("Invalid receipt run identity.",status=404)
    root_path=RECEIPTS_DIR
    if root_path.is_symlink() or root_path.is_junction():raise error()
    root_path.mkdir(parents=True,exist_ok=True)
    target=directory(run_id)
    if target.parent!=root_path:raise error()
    target.mkdir(parents=True,exist_ok=True)
    data=value.model_dump();raw=canonical({"data":data,"sha256":digest(data)})
    if len(raw)>MAX_BYTES:raise error()
    fd,temp=tempfile.mkstemp(prefix=".receipt-",suffix=".tmp",dir=target)
    try:
        with os.fdopen(fd,"wb") as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        try:os.link(temp,target/name)
        except FileExistsError:raise error("Immutable input receipt already exists; no overwrite attempted.","GA_INPUT_RECEIPT_EXISTS",409)
        if os.name!="nt":
            fd=os.open(target,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
    finally:Path(temp).unlink(missing_ok=True)


def load(run_id,name,model):
    path=directory(run_id)/name
    if path.is_symlink() or path.is_junction():raise error()
    try:
        with path.open("rb") as stream:raw=stream.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise ValueError()
        def pairs(items):
            result={}
            for key,value in items:
                if key in result:raise ValueError()
                result[key]=value
            return result
        envelope=json.loads(raw,object_pairs_hook=pairs)
        if set(envelope)!={"data","sha256"} or digest(envelope["data"])!=envelope["sha256"]:raise ValueError()
        checked=model.model_validate(envelope["data"])
        # Serialized fields must be explicit; never fill omitted version/status
        # or scope fields by interpreting Pydantic constructor defaults as proof.
        if checked.run_id!=run_id or canonical(checked.model_dump())!=canonical(envelope["data"]):raise ValueError()
        return checked
    except FileNotFoundError:return None
    except (OSError,ValueError,TypeError,KeyError,RecursionError) as exc:raise error() from exc


def graph_digest(value):
    # Reuse the exact passive checkpoint graph codec; never decode, score or save.
    from services.ga_checkpoint_service import encode_graph
    graph=encode_graph(value)
    if len(graph["nodes"])>100000:raise ValueError("Observation graph limit")
    raw=canonical(graph)
    if len(raw)>MAX_GRAPH_BYTES:raise ValueError("Observation byte limit")
    return hashlib.sha256(raw).hexdigest()


def runtime_digest():
    from services import ga_service as engine,ga_checkpoint_service as checkpoint
    return graph_digest((engine.list_subjects,engine.list_faculty,engine.lst_rooms,
        checkpoint.dataframe_to_state(engine.df_faculty_pref)))


class Observation:
    def __init__(self,start):
        self.start=start;self.reasons=set(start.reasons)
        self.first=self.last=self.monitor=None;self.count=0;self.first_generation=self.last_generation=None

    def progress(self,kind,data):
        if kind not in {"initial_population_ready","generation_completed"}:return
        if self.count>=32:
            self.reasons.add("OBSERVATION_LIMIT_REACHED");return
        try:
            from genetic_algorithm.utils.FrozenInputs import scoring_inputs
            from services.ga_run_provenance import configuration_fingerprint
            if data.get("run_id",self.start.run_id)!=self.start.run_id:
                self.reasons.add("CROSS_RUN_EVENT");return
            generation=data["generation"]
            if type(generation) is not int or generation<0 or self.last_generation is not None and generation<=self.last_generation:raise ValueError()
            frozen=scoring_inputs.get()
            if not isinstance(frozen,dict):raise ValueError()
            monitor=data["configuration_fingerprint"]
            if type(monitor) is not str or len(monitor)!=64 or any(c not in "0123456789abcdef" for c in monitor):raise ValueError()
            fingerprint=graph_digest(frozen)
            if self.first is not None and fingerprint!=self.first:self.reasons.add("SCORING_CONTEXT_CHANGED")
            self.first=self.first or fingerprint;self.last=fingerprint;self.count+=1
            self.first_generation=generation if self.first_generation is None else self.first_generation;self.last_generation=generation
            self.monitor=monitor
            if frozen.get("input_fingerprint")!=self.start.dataset_fingerprint or data["input_fingerprint"]!=self.start.dataset_fingerprint:self.reasons.add("DATASET_CHANGED")
            if self.start.configuration.baseline_mode=="fresh" and self.monitor!=configuration_fingerprint(self.start.dataset_fingerprint,self.start.configuration.model_dump()):self.reasons.add("CONFIGURATION_DRIFT")
        except Exception:self.reasons.add("SCORING_CONTEXT_UNAVAILABLE")

    def finish(self,outcome):
        # Failure never replaces the primary engine result/exception. An absent
        # final record remains explicitly INCOMPLETE, never verified/successful.
        try:
            from services.ga_progress_service import input_fingerprint
            after=None
            try:after=runtime_digest()
            except Exception:self.reasons.add("MODEL_OBSERVATION_UNAVAILABLE")
            if input_fingerprint()!=self.start.dataset_fingerprint:self.reasons.add("DATASET_CHANGED")
            if self.first is None:self.reasons.add("SCORING_CONTEXT_NOT_OBSERVED")
            if outcome=="CALL_INTERRUPTED":self.reasons.add("CALL_INTERRUPTED")
            if outcome=="PAUSED":self.reasons.add("RESUME_NOT_ATTESTED")
            end=End(run_id=self.start.run_id,captured_at=now(),reasons=sorted(self.reasons),start_receipt_sha256=digest(self.start.model_dump()),
                outcome=outcome,model_fingerprint_after=after,scoring_context_first=self.first,scoring_context_last=self.last,
                generation_observations=self.count,first_generation=self.first_generation,last_generation=self.last_generation,
                monitor_configuration_fingerprint=self.monitor)
            write(self.start.run_id,"end.json",end)
        except Exception:return False
        return True


def begin(control,parameters):
    from services import ga_service as engine,ga_checkpoint_service as checkpoint,ga_history_service as history,ga_run_provenance as provenance
    from services.ga_progress_service import input_fingerprint
    # No backfill, resume reinterpretation or changes to an existing run record.
    if parameters.get("resume_state") is not None or control.latest_completed_generation is not None or (history.directory(control.run_id)/"index.json").exists():return None
    signature=inspect.signature(engine.run_genetic_algorithm)
    config=Configuration(**{key:parameters.get(key,signature.parameters[key].default) for key in PARAMETERS})
    reasons={"CONSUMPTION_NOT_ESTABLISHED","CACHED_MUTABLE_MODELS"};loaded=None;reference=None
    if config.baseline_mode!="fresh":reasons.add("SEED_INPUT_NOT_BOUND")
    try:loaded=runtime_digest()
    except Exception:reasons.add("MODEL_OBSERVATION_UNAVAILABLE")
    try:
        record=provenance.read(control.run_id)
        if record:reference={"provenance_sha256":digest(record),"academic_context_sha256":record["context_sha256"]}
    except Exception:pass
    if reference is None:reasons.add("ACADEMIC_CONTEXT_NOT_CAPTURED")
    start=Start(run_id=control.run_id,run_started_at=control.started_at,captured_at=now(),reasons=sorted(reasons),academic_context_reference=reference,
        loaded_model_fingerprint=loaded,dataset_fingerprint=input_fingerprint(),engine_fingerprint=checkpoint.engine_fingerprint(),
        observer_source_fingerprint=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        configuration=config,configuration_fingerprint=digest(config.model_dump()),
        input_source_identities=["runtime-model-aliases","legacy-preference-frame","data-file-byte-set","effective-run-parameters","optional-u5b-record"])
    try:write(control.run_id,"start.json",start)
    except HistoryError:raise
    except OSError as exc:raise error("Immutable receipt storage is unavailable; optimization was not started.","GA_INPUT_RECEIPT_UNAVAILABLE",503) from exc
    return Observation(start)


def read(run_id):
    start=load(run_id,"start.json",Start);end=load(run_id,"end.json",End)
    if start is None:
        if end is not None:raise error()
        return {"loader_contract":CONTRACT,"run_id":run_id,"verification_status":"UNVERIFIED","eligible_for_current":False,
            "record_state":"MISSING","reasons":["CONSUMPTION_NOT_ESTABLISHED","RECEIPT_MISSING"]}
    if digest(start.configuration.model_dump())!=start.configuration_fingerprint:raise error()
    if datetime.fromisoformat(start.captured_at)<datetime.fromisoformat(start.run_started_at):raise error()
    if end is not None and (end.start_receipt_sha256!=digest(start.model_dump()) or datetime.fromisoformat(end.captured_at)<datetime.fromisoformat(start.captured_at)):raise error()
    return {"loader_contract":CONTRACT,"run_id":run_id,"verification_status":"UNVERIFIED","eligible_for_current":False,
        "record_state":"RECORDED" if end else "INCOMPLETE","start":start.model_dump(),"end":end.model_dump() if end else None,
        "reasons":end.reasons if end else sorted(set(start.reasons)|{"FINAL_RECORD_MISSING"})}
