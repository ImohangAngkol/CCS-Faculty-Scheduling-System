"""Explicit FICTIONAL issuer/catalog, never installed by an application import."""
from contextlib import contextmanager
from dataclasses import asdict
import copy
import threading
import time
from services.ga_run_authority import Grant,digest,RunError
from services.ga_trusted_runs import Capture
from services.ga_input_bundle import capture
from services.preference_authorization import PreferencePrincipal

ACTOR='00000000-0000-4000-8000-000000000901'
OTHER='00000000-0000-4000-8000-000000000902'
DEPT='00000000-0000-4000-8000-000000000903'
OTHER_DEPT='00000000-0000-4000-8000-000000000904'
PRINCIPAL=PreferencePrincipal('admin',user_id=ACTOR)
CATALOG='FICTIONAL-ONLY-v1'

class FictionalAuthority:
    def __init__(self,clock=time.time):
        self.clock=clock;self.lock=threading.RLock();self.revoked=False;self.policy='e'*64;self.denied=set()
    @contextmanager
    def guard(self,context):
        with self.lock:yield
    def authorize(self,c):
        if self.revoked or (c.actor_id,c.department_id)!=(ACTOR,DEPT) or c.action in self.denied:return None
        return Grant(digest(asdict(c)),c.actor_id,c.department_id,c.action,'department_optimization_control',self.policy,self.clock()-1,self.clock()+60)

class FictionalSource:
    def __init__(self,generations=0):self.lock=threading.RLock();self.calls=0;self.generations=generations;self.offset=0
    @contextmanager
    def guard(self,actor,department,catalog):
        if (actor,department,catalog)!=(ACTOR,DEPT,CATALOG):raise RunError('GA_FICTIONAL_CATALOG_UNKNOWN')
        with self.lock:yield self
    def capture(self,run_id,actor,department,catalog):
        from tests.d10.support import templates,preferences
        from genetic_algorithm.models.ga_setting import GASetting
        from services.ga_checkpoint_service import engine_fingerprint
        self.calls+=1;models=templates(compact=True);frame=preferences()
        for f in models[1]:f.code+=self.offset
        frame['Faculty_Code']+=self.offset
        bundle=capture(run_id=run_id,templates=models,fallback_templates=models,legacy_preferences=frame,
            scoring_context={'preference_scoring_version':2,'settings':GASetting().to_dict(),'preferences':{},
                'system_faculty':copy.deepcopy(models[1]),'input_fingerprint':'a'*64},
            configuration=dict(population_size=2,generations=self.generations,fresh_chromosomes=0,baseline_mode='fresh',mutation_attempts=1,max_restarts=5),
            source_identities=dict(dataset='a'*64,engine=engine_fingerprint(),loader='c'*64,transformation='d'*64))
        return Capture(bundle,department,catalog)
