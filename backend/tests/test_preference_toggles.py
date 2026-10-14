"""Policy-specific exact scoring, reports and checkpoint provenance."""
import copy
import hashlib
import json
import platform
import random
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from genetic_algorithm.operators.FitnessFunction import _score_exact_subject_schedule_blocks, _normalize_dashboard_preference, faculty_preference_fitness
from genetic_algorithm.utils.FrozenInputs import scoring_inputs, capture_inputs
from services import ga_checkpoint_service as checkpoints, fitness_reporting_service as reports
from services.preference_scoring_policy import legacy_source, scoring_version, MANIFEST
from tests.test_ga_safe_stop import isolated, bounded_run, small_population
from services.ga_control_service import RunControl


def subject():
    return SimpleNamespace(number="CCC121", lecture_time_blocks=[("Monday",SimpleNamespace(start_time="09:00",end_time="11:00"))],laboratory_time_blocks=[])


def preference():
    return {"day_importance":4,"time_importance":3,"preferred_schedule_blocks":[{"kind":"subject","subject_code":"CCC121","component":"Lecture","day":"Tuesday","start_time":"10:30"}]}


@pytest.mark.parametrize("day,time,expected", [(False,False,(0,0)),(True,False,(20,0)),(False,True,(0,30)),(True,True,(20,30))])
@pytest.mark.parametrize("normalized", [False,True])
def test_flags_are_independent_and_importance_is_unchanged(day,time,expected,normalized):
    pref={**preference(),"use_day_preference":day,"use_time_preference":time}
    if normalized:
        pref=_normalize_dashboard_preference(pref)
    state=random.getstate()
    result=_score_exact_subject_schedule_blocks(subject(),pref,SimpleNamespace(day_penalty=5,time_penalty=10),1)
    assert (result["day_penalty"],result["time_penalty"])==expected
    assert random.getstate()==state


def test_legacy_missing_flags_and_zero_importance_policy():
    pref=_normalize_dashboard_preference(preference())
    assert _score_exact_subject_schedule_blocks(subject(),pref,SimpleNamespace(day_penalty=5,time_penalty=10),1)["day_penalty"]==20
    pref["day_importance"]=pref["time_importance"]=0
    result=_score_exact_subject_schedule_blocks(subject(),pref,SimpleNamespace(day_penalty=5,time_penalty=10),1)
    assert result["day_penalty"]==result["time_penalty"]==0


def test_original_frozen_policy_retains_original_scores_and_report_indicators():
    pref={**preference(),"use_day_preference":False,"use_time_preference":False}
    token=scoring_inputs.set({})  # Original checkpoints have no policy marker.
    try:
        result=_score_exact_subject_schedule_blocks(subject(),pref,SimpleNamespace(day_penalty=5,time_penalty=10),1)
    finally:
        scoring_inputs.reset(token)
    assert result["day_penalty"]==20 and result["time_penalty"]==30
    assignments=[{"subject":"CCC121","lecture":[["monday",540,660]],"laboratory":[]}]
    legacy={r["key"]:r for r in reports.preference_indicators(assignments,pref,{},1)}
    corrected={r["key"]:r for r in reports.preference_indicators(assignments,pref,{},2)}
    assert legacy["day_preference"]["affects_fitness"]
    assert corrected["day_preference"]["status"]=="disabled"
    assert corrected["time_preference"]["affects_fitness"] is False


def test_legacy_engine_fingerprint_equals_exact_original_algorithm():
    root=checkpoints.ROOT
    paths=sorted((root/"genetic_algorithm").rglob("*.py"))+[root/"services"/name for name in ("ga_service.py","ga_progress_service.py","ga_publication_service.py","ga_checkpoint_service.py","ga_control_service.py","chromosome_service.py","faculty_analysis_service.py")]
    original=hashlib.sha256()
    for path in paths:
        original.update(str(path.relative_to(root)).encode())
        original.update(legacy_source(path.relative_to(root).as_posix(),path.read_bytes()))
    original.update(checkpoints.canonical([checkpoints.ENGINE_VERSION,platform.python_version(),pd.__version__,np.__version__]))
    assert original.hexdigest()==checkpoints.engine_fingerprint(1)
    assert original.hexdigest()!=checkpoints.engine_fingerprint()
    with pytest.raises(ValueError):
        legacy_source("genetic_algorithm/operators/FitnessFunction.py",b"unverified modified scorer")
    with pytest.raises(ValueError):
        scoring_version({"preference_scoring_version":True})


def test_whole_fitness_breakdown_changes_only_explicitly_disabled_components(small_population):
    candidate=small_population[0][0]
    member=next(s for s in candidate if not getattr(s.assigned_faculty,"is_external",False))
    frozen=capture_inputs()
    raw={**preference(),"faculty_code":member.assigned_faculty.code,"use_day_preference":False,"use_time_preference":False}
    raw["preferred_schedule_blocks"][0]["subject_code"]=member.number
    frozen["preferences"]={member.assigned_faculty.code:raw}
    rng=random.getstate()
    results=[]
    for policy in (1,2):
        token=scoring_inputs.set({**frozen,"preference_scoring_version":policy})
        try:
            results.append(faculty_preference_fitness(candidate,return_breakdown=True))
        finally:
            scoring_inputs.reset(token)
    (old_total,old),(new_total,new)=results
    assert new["day_preference"]==new["time_preference"]==0
    assert all(old[k]==new[k] for k in old if k not in ("day_preference","time_preference"))
    assert old_total-new_total==old["day_preference"]+old["time_preference"]
    assert new_total==sum(new.values()) and random.getstate()==rng


def test_legacy_checkpoint_roundtrip_and_same_population_resume(isolated, monkeypatch):
    from services import ga_service
    from genetic_algorithm.utils import FrozenInputs
    original=FrozenInputs.capture_inputs
    def legacy_inputs():
        inputs=original();inputs.pop("preference_scoring_version")
        return inputs
    monkeypatch.setattr(FrozenInputs,"capture_inputs",legacy_inputs)
    calls = []
    original_score = ga_service.faculty_preference_fitness
    def observed_score(*args, **kwargs):
        calls.append(1)
        return original_score(*args, **kwargs)
    monkeypatch.setattr(ga_service, "faculty_preference_fitness", observed_score)
    random.seed(153)
    plain = ga_service.run_genetic_algorithm(3, 1, 1)
    expected_rng, expected_calls = random.getstate(), len(calls)
    calls.clear()
    random.seed(153)
    control=RunControl(configuration={"population_size":3,"generations":1,"fresh_chromosomes":1,"baseline_mode":"fresh"})
    control.request_pause()
    paused=ga_service.run_genetic_algorithm(3,1,1,run_control=control)
    assert isinstance(paused,checkpoints.PausedRun)
    templates=(ga_service.list_subjects,ga_service.list_faculty,ga_service.lst_rooms)
    state=checkpoints.load_checkpoint(control.run_id,templates)
    assert "preference_scoring_version" not in state["scoring_inputs"]
    before=(checkpoints.run_directory(control.run_id)/control.checkpoint).read_bytes()
    control.execution_active = False
    control.begin_resume()
    result=ga_service.run_genetic_algorithm(3,1,1,run_control=control,resume_state=state)
    assert result["generations_completed"]==1
    assert random.getstate() == expected_rng and len(calls) == expected_calls
    for field in ("schedule", "history", "best_fitness", "fitness_breakdown", "faculty_analysis"):
        assert result[field] == plain[field]
    assert (checkpoints.run_directory(control.run_id)/control.checkpoint).read_bytes()==before
