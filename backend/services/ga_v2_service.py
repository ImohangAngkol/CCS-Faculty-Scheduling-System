"""Versioned V2 admission/control service, blocked without a server deployment.

Every durable/public boundary rechecks D8/D9 under ledger locks. V1 execution
keeps its existing sources and storage. One shared execution lock protects the
original global RNG; no V1 or V2 worker runs concurrently through these routes.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import copy
from pathlib import Path
import threading
import random
from uuid import uuid4

from schemas.ga_constrained import Parameters
from services import ga_v2_engine as engine, ga_v2_store as storage
from services.ga_v2_constraints import Catalog, LedgerAuthority, ConstraintError, reject
from services.chromosome_service import load_saved_best_payload, load_uploaded_payload, payload_to_chromosome
from services.ga_checkpoint_service import dataframe_to_state
from services.external_confirmation_service import digest
from genetic_algorithm.operators.FitnessFunction import faculty_preference_fitness
from genetic_algorithm.utils.FrozenInputs import scoring_inputs
from genetic_algorithm.utils.Functions import get_subject_schedule_entries


@dataclass(frozen=True)
class Deployment:
    catalog: Catalog
    authority: LedgerAuthority
    templates: tuple
    preferences: object


def institutional_deployment(academic_year, term):
    """Server-owned integration point. No provider/env flag/client override exists."""
    return None


def deployment_for(year, term):
    try:
        deployment=institutional_deployment(year,term)
        if not isinstance(deployment,Deployment):
            reject("INSTITUTIONAL_AUTHORITY_UNAVAILABLE", "Constrained V2 remains blocked: no genuine term/resource and institutional authority integration is configured.")
        if (deployment.catalog.academic_year,deployment.catalog.term)!=(year,term):
            reject("TERM_MISMATCH", "The trusted catalog does not cover the requested year and term.")
        return deployment
    except ConstraintError:
        raise
    except Exception:
        reject("INSTITUTIONAL_AUTHORITY_UNAVAILABLE", "The institutional deployment is unavailable; constrained execution is blocked.")


def constraints(year,term):
    deployment=deployment_for(year,term)
    with deployment.authority.pinned() as snapshot:
        return {"execution_mode":"CONSTRAINED_V2","status":"CURRENT","academic_year":year,"term":term,
            "constraint_digest":snapshot.digest,"revisions":[h.model_dump() for h in snapshot.heads],
            "commitments":len(snapshot.commitments),"activated":False}


def result_for(state,snapshot,status):
    token=scoring_inputs.set(state["scoring_inputs"])
    try:
        from services.ga_checkpoint_service import dataframe_from_state
        preferences=dataframe_from_state(state["preferences"])
        fitness,breakdown=faculty_preference_fitness(state["best"],preferences,return_breakdown=True)
    finally:
        scoring_inputs.reset(token)
    return {"execution_mode":"CONSTRAINED_V2","engine_version":engine.ENGINE_VERSION,"status":status,
        "source":"GA-generated proposal","approved":False,"academic_year":snapshot.catalog.academic_year,"term":snapshot.catalog.term,
        "constraint_digest":snapshot.digest,"constraint_status":"CURRENT_AT_PUBLICATION",
        "revisions":[h.model_dump(mode="json") for h in snapshot.heads],"commitments":[c.model_dump(mode="json") for c in snapshot.commitments],
        "diagnostics":state["diagnostics"],"feasibility":"VALIDATED_CANDIDATE","generation":state["generation"],
        "population_size":len(state["population"]),"best_fitness":fitness,"fitness_breakdown":breakdown,
        "history":state["history"],"schedule":[entry for subject in state["best"] for entry in get_subject_schedule_entries(subject)]}


class Job:
    def __init__(self,run_id,year,term):
        self.run_id,self.year,self.term=run_id,year,term
        self.lock=threading.RLock(); self.requested=None; self.active=True
        self.status="INITIALIZING"; self.error=None; self.generation=None; self.diagnostics={}

    def public(self):
        with self.lock:
            return {"run_id":self.run_id,"execution_mode":"CONSTRAINED_V2","status":self.status,
                "execution_active":self.active,"generation":self.generation,"error":self.error,"diagnostics":dict(self.diagnostics)}


JOBS={}
REGISTRY_LOCK=threading.RLock()
EXECUTOR=ThreadPoolExecutor(max_workers=1,thread_name_prefix="constrained-v2")


def execution_lock():
    from routers.genetic_algorithm import _ga_execution_lock
    return _ga_execution_lock


def _worker(job,deployment,snapshot,parameters,seed=None,state=None):
    legacy_rng=random.getstate()
    if state is None:
        # The original operators consume the module RNG. Isolate V2's state
        # under the shared execution lock, restoring V1's exact prior state.
        random.setstate(random.Random().getstate())
    def boundary(current):
        with job.lock:
            action=job.requested
            status="STOPPED" if action=="stop" else "PAUSED" if action=="pause" else "COMPLETED" if current["generation"]==parameters.generations else "RUNNING"
            result=result_for(current,snapshot,status)
            storage.write(job.run_id,current,snapshot,deployment.authority,deployment.templates,status,result)
            job.status,job.generation,job.diagnostics=status,current["generation"],dict(current["diagnostics"])
            return action
    try:
        engine.run(deployment.templates,snapshot,parameters,deployment.preferences,boundary,seed=seed,state=state)
    except Exception as error:
        with job.lock:
            job.status="FAILED"
            if isinstance(error,ConstraintError) and hasattr(error,"diagnostics"):
                job.diagnostics=dict(error.diagnostics)
            job.error={"code":error.code,"message":str(error)} if isinstance(error,ConstraintError) else {
                "code":"V2_EXECUTION_FAILED","message":"V2 execution failed safely; no successful result is claimed."}
    finally:
        random.setstate(legacy_rng)
        execution_lock().release()
        with job.lock:
            job.active=False


def _claim(job):
    if not execution_lock().acquire(blocking=False):
        reject("GA_EXECUTION_BUSY", "A V1 or V2 execution already owns the GA. Wait before retrying.")
    with REGISTRY_LOCK:
        if len(JOBS)>=100:
            # Bound scalar registry memory; durable paused/results remain on disk.
            for key in list(JOBS):
                if not JOBS[key].active:
                    del JOBS[key]
                    break
            if len(JOBS)>=100:
                execution_lock().release()
                reject("V2_REGISTRY_BUSY", "V2 run capacity is occupied; retry later.")
        JOBS[job.run_id]=job


def start(request):
    deployment=deployment_for(request.academic_year,request.term)
    with deployment.authority.pinned() as snapshot:
        if snapshot.digest!=request.constraint_digest:
            reject("CONSTRAINT_SET_CHANGED", "The reviewed constraint set changed; check the current term again before starting.")
        seed=None
        if request.seed!="fresh":
            payload=(load_saved_best_payload if request.seed=="saved" else load_uploaded_payload)()
            if payload is None:
                reject("REQUESTED_SEED_UNAVAILABLE", "The explicitly requested baseline is unavailable; no fresh fallback was used.")
            try:
                publication=engine.reduced_templates(snapshot,deployment.templates)
                seed=payload_to_chromosome(payload,*publication)
                engine.admit(seed,snapshot,publication)
            except (ValueError,RuntimeError):
                reject("INCOMPATIBLE_REQUESTED_SEED", "The explicitly requested baseline is incompatible with this term and constraint set.")
    job=Job(str(uuid4()),request.academic_year,request.term)
    _claim(job)
    try:
        EXECUTOR.submit(_worker,job,deployment,snapshot,request.parameters,seed)
    except Exception:
        execution_lock().release()
        with REGISTRY_LOCK:
            JOBS.pop(job.run_id,None)
        reject("V2_WORKER_UNAVAILABLE", "No V2 worker was started. Retry later.")
    return job.public()


def restored(run_id):
    payload,snapshot,state=storage.read(run_id)
    deployment=deployment_for(snapshot.catalog.academic_year,snapshot.catalog.term)
    with deployment.authority.pinned(snapshot):
        engine.validate_state(state,snapshot,deployment.templates)
        if digest(state["preferences"])!=digest(dataframe_to_state(deployment.preferences)):
            reject("V2_CHECKPOINT_INCOMPATIBLE", "Authoritative legacy preference metadata changed.")
        if payload["status"] not in {"RUNNING","PAUSED","STOPPED","COMPLETED"} or payload["result"]!=result_for(state,snapshot,payload["status"]):
            reject("V2_CHECKPOINT_INVALID", "Stored V2 result does not match its validated checkpoint population and provenance.")
    return payload,snapshot,state,deployment


def inspect(run_id):
    with REGISTRY_LOCK:
        job=JOBS.get(run_id)
    if job is not None:
        public=job.public()
        if public["execution_active"] or public["status"]=="FAILED":
            return public
    payload,snapshot,state,_=restored(run_id)
    if payload["status"]=="RUNNING":
        return {"run_id":run_id,"execution_mode":"CONSTRAINED_V2","status":"FAILED","execution_active":False,
            "generation":state["generation"],"diagnostics":state["diagnostics"],"error":{"code":"V2_INTERRUPTED",
            "message":"The worker is no longer present and no durable pause was committed. No automatic continuation or completed result is claimed."}}
    return {"run_id":run_id,"execution_mode":"CONSTRAINED_V2","status":payload["status"],"execution_active":False,
        "generation":state["generation"],"error":None,"diagnostics":state["diagnostics"],"result":payload["result"]}


def control(run_id,action):
    with REGISTRY_LOCK:
        job=JOBS.get(run_id)
    if job is not None and job.active:
        with job.lock:
            if job.status in {"PAUSED","STOPPED","COMPLETED","FAILED"}:
                reject("V2_FINALIZING", "The V2 boundary is finalizing; reload its status.")
            if action=="resume":
                reject("V2_NOT_PAUSED", "Only an idle durable V2 checkpoint can resume.")
            if job.requested!="stop":
                job.requested=action
            return job.public()
    payload,snapshot,state,deployment=restored(run_id)
    if payload["status"]!="PAUSED":
        reject("V2_NOT_PAUSED", "Only an idle durable V2 checkpoint can be continued or stopped.")
    if action=="pause":
        return inspect(run_id)
    if action=="stop":
        if not execution_lock().acquire(False):
            reject("GA_EXECUTION_BUSY", "Another execution owns admission; reload the paused V2 status.")
        try:
            payload,snapshot,state,deployment=restored(run_id)
            if payload["status"]!="PAUSED":
                reject("V2_NOT_PAUSED", "The durable paused boundary changed before stop.")
            result=result_for(state,snapshot,"STOPPED")
            storage.write(run_id,state,snapshot,deployment.authority,deployment.templates,"STOPPED",result)
            if job:
                with job.lock:
                    job.status="STOPPED"
        finally:
            execution_lock().release()
        return inspect(run_id)
    job=Job(run_id,snapshot.catalog.academic_year,snapshot.catalog.term)
    _claim(job)
    try:
        # Reload under the shared lock: competing resume and V1 RNG draws cannot
        # interleave with validation/restoration. No registry cache is trusted.
        payload,snapshot,state,deployment=restored(run_id)
        if payload["status"]!="PAUSED":
            reject("V2_NOT_PAUSED", "The durable paused boundary changed before resume.")
        EXECUTOR.submit(_worker,job,deployment,snapshot,Parameters.model_validate(state["parameters"]),None,state)
    except Exception:
        with job.lock:
            job.active=False; job.status="FAILED"
        execution_lock().release()
        raise
    return job.public()
