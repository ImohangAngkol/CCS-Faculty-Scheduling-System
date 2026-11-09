"""Fictional provenance and private temporary files; no GA or institution IO."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from services import saved_best_policy as policy

_snapshot=Path(__file__).resolve().parents[2]
pytestmark=pytest.mark.skipif(
    _snapshot.name!="repository" or not _snapshot.parent.name.startswith("u5c-r1-snapshot-")
    or not (_snapshot.parent/"OWNED-SNAPSHOT.json").is_file(),
    reason="Use the U5PA fictional snapshot runner; do not import academic fixtures from the working repository")


def inputs(**changes):
    value={k: "a" * 64 for k in policy.HASHES}
    value.update(version=policy.VERSION,academic_year="FICTIONAL-YEAR",term="FICTIONAL-TERM",
        department_id="fictional-it",dataset_identity="fictional-v1",fitness_version="original-min-v2",chromosome_version="subject-graph-v1")
    value.update(changes)
    return value


def payload(score):
    return dict(format="ccs-ga-chromosome",version=1,best_fitness=score,subject_keys=["FIC101::FIC-A"],
        schedule=[dict(subject="FIC101",section="FIC-A",day="M",start="07:30",end="08:00")])


class FictionalVerifier:
    """Explicit fictional test provider, not deployment configuration."""
    def __init__(self,ctx=None):self.ctx=ctx or inputs()
    def guard(self):return nullcontext()  # Explicit fictional validity lease only.
    def snapshot(self):return deepcopy(self.ctx)
    def attest(self,ctx,fingerprint):return "FICTIONAL-PROVIDER-"+policy.digest([ctx,fingerprint])
    def verify(self,ctx,fingerprint,attestation):return attestation==self.attest(ctx,fingerprint)


@pytest.mark.parametrize("old,new,updated",[(100,90,True),(100,110,False),(100,100,False),(1,0,True),(0,1,False),(0,0,False)])
def test_same_context_minimizes_and_preserves_zero(tmp_path,old,new,updated):
    path=tmp_path/"best.json";v=FictionalVerifier()
    assert policy.consider(path,payload(old),v).updated
    before=path.read_bytes();result=policy.consider(path,payload(new),v)
    assert result.classification=="ELIGIBLE" and result.updated is updated
    assert json.loads(path.read_bytes())["best_fitness"]==min(old,new)
    if not updated:assert path.read_bytes()==before


@pytest.mark.parametrize("dimension",sorted(policy.HASHES|policy.LABELS))
def test_every_changed_context_dimension_declines_without_numeric_ranking(tmp_path,dimension):
    path=tmp_path/"best.json";assert policy.consider(path,payload(100),FictionalVerifier()).updated
    before=path.read_bytes();ctx=inputs();ctx[dimension]="b"*64 if dimension in policy.HASHES else "different-fictional-context"
    result=policy.consider(path,payload(0),FictionalVerifier(ctx))
    expected="UNVERIFIED" if dimension in policy.PROVENANCE_ONLY else "INCOMPATIBLE"
    assert result.classification==expected and not result.updated and result.payload is None
    assert path.read_bytes()==before


@pytest.mark.parametrize("malformation",["missing","context_hash","content_hash","attestation","score","schedule","json"])
def test_unverified_or_tampered_incumbent_is_never_overwritten(tmp_path,malformation):
    path=tmp_path/"best.json";v=FictionalVerifier();assert policy.consider(path,payload(100),v).updated
    record=json.loads(path.read_bytes())
    if malformation=="missing":record.pop("saved_best_context")
    elif malformation=="context_hash":record["saved_best_context"]["context_fingerprint"]="b"*64
    elif malformation=="content_hash":record["saved_best_context"]["content_fingerprint"]="b"*64
    elif malformation=="attestation":record["saved_best_context"]["attestation"]="forged-fictional-proof"
    elif malformation=="score":record["best_fitness"]=9
    elif malformation=="schedule":record["schedule"][0]["day"]="T"
    path.write_bytes(b"{" if malformation=="json" else policy.canonical(record));before=path.read_bytes()
    result=policy.consider(path,payload(0),v)
    assert result.classification=="UNVERIFIED" and not result.updated and path.read_bytes()==before


def test_unconfigured_deployment_performs_no_file_io(tmp_path):
    assert policy.configured_verifier() is None
    with patch.object(Path,"open",side_effect=AssertionError("No store access")):
        assert policy.consider(tmp_path/"absent"/"best.json",payload(0)).classification=="UNVERIFIED"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("score",[float("nan"),float("inf"),True,None,"0"])
def test_invalid_numeric_claims_declined(tmp_path,score):
    assert policy.consider(tmp_path/"best.json",payload(score),FictionalVerifier()).classification=="UNVERIFIED"
    assert not (tmp_path/"best.json").exists()


def test_threads_and_repetition_do_not_regress(tmp_path):
    path=tmp_path/"best.json";v=FictionalVerifier()
    with ThreadPoolExecutor(max_workers=6) as pool:
        decisions=list(pool.map(lambda n:policy.consider(path,payload(n),v),[80,100,60,90,40,20]))
    assert all(d.classification=="ELIGIBLE" for d in decisions)
    assert json.loads(path.read_bytes())["best_fitness"]==20
    before=path.read_bytes()
    for _ in range(3):assert not policy.consider(path,payload(20),v).updated
    assert path.read_bytes()==before


def test_process_restart_and_concurrent_comparison(tmp_path):
    path=tmp_path/"best.json";v=FictionalVerifier();assert policy.consider(path,payload(100),v).updated
    code="from pathlib import Path; from tests.test_saved_best_context import *; import sys; d=policy.consider(Path(sys.argv[1]),payload(int(sys.argv[2])),FictionalVerifier()); assert d.classification=='ELIGIBLE'"
    processes=[subprocess.Popen([sys.executable,"-B","-c",code,str(path),str(n)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for n in (70,50,90)]
    for process in processes:
        out,err=process.communicate(timeout=30);assert process.returncode==0,err.decode(errors="replace")
    assert json.loads(path.read_bytes())["best_fitness"]==50
    assert not policy.consider(path,payload(60),FictionalVerifier()).updated


def test_context_revocation_and_interrupted_write_leave_record_unchanged(tmp_path):
    path=tmp_path/"best.json";v=FictionalVerifier();policy.consider(path,payload(100),v);before=path.read_bytes()
    with patch.object(policy.os,"replace",side_effect=OSError("Fictional interruption")):
        assert policy.consider(path,payload(0),v).classification=="UNVERIFIED"
    assert path.read_bytes()==before and not list(tmp_path.glob("*.tmp"))
    class Revoked(FictionalVerifier):
        def verify(self,*args):return False
    assert policy.consider(path,payload(0),Revoked()).classification=="UNVERIFIED"
    assert path.read_bytes()==before


def test_search_strategy_is_not_part_of_scoring_context():
    assert not {"population_size","generations","seed","mutation_attempts","max_restarts"}&(policy.HASHES|policy.LABELS)
    with pytest.raises(ValueError):policy.context({**inputs(),"generations":10})


def test_actual_fixed_save_declines_without_reading_or_serializing(monkeypatch):
    from services import chromosome_service as service
    def forbidden(*_a,**_k):raise AssertionError("Unverified archive IO forbidden")
    monkeypatch.setattr(service,"chromosome_to_payload",forbidden)
    monkeypatch.setattr(service,"load_saved_best_payload",forbidden)
    monkeypatch.setattr(service,"write_payload",forbidden)
    assert service.save_best_if_better(object(),0)==(False,None)


def test_actual_fixed_save_supports_independently_verified_provider_in_isolation(tmp_path,monkeypatch):
    from services import chromosome_service as service
    path=tmp_path/"best.json"
    monkeypatch.setattr(service,"BEST_CHROMOSOME_PATH",path)
    monkeypatch.setattr(service,"chromosome_to_payload",lambda _chromosome,score:payload(score))
    monkeypatch.setattr(policy,"configured_verifier",lambda:FictionalVerifier())
    assert service.save_best_if_better(object(),100)[0]
    assert service.save_best_if_better(object(),90)[0]
    monkeypatch.setattr(policy,"configured_verifier",lambda:FictionalVerifier(inputs(department_id="other-fictional-department")))
    before=path.read_bytes()
    assert service.save_best_if_better(object(),0)==(False,None)
    assert path.read_bytes()==before


def test_storage_and_attestation_errors_are_unverified(tmp_path):
    class Unavailable(FictionalVerifier):
        def snapshot(self):raise RuntimeError("Fictional provider unavailable")
    assert policy.consider(tmp_path/"best.json",payload(0),Unavailable()).classification=="UNVERIFIED"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("change",[{"version":True},{"subject_keys":["FIC101::FIC-A","FIC101::FIC-A"]},{"schedule":[]}])
def test_malformed_candidate_does_not_enter_storage(tmp_path,change):
    assert policy.consider(tmp_path/"best.json",{**payload(0),**change},FictionalVerifier()).classification=="UNVERIFIED"
    assert not list(tmp_path.iterdir())


def test_different_offering_set_never_replaces_the_archive(tmp_path):
    path=tmp_path/"best.json";v=FictionalVerifier();assert policy.consider(path,payload(100),v).updated
    before=path.read_bytes();candidate={**payload(0),"subject_keys":["FIC202::FIC-B"]}
    result=policy.consider(path,candidate,v)
    assert result.classification=="INCOMPATIBLE" and not result.updated
    assert path.read_bytes()==before


def test_legacy_zero_fitness_archive_remains_readable_and_unchanged(tmp_path,monkeypatch):
    from services import chromosome_service as service
    path=tmp_path/"best.json";raw=json.dumps(payload(0),indent=2).encode();path.write_bytes(raw)
    monkeypatch.setattr(service,"BEST_CHROMOSOME_PATH",path)
    assert service.load_saved_best_payload()["best_fitness"]==0
    assert service.get_saved_best_metadata()==dict(exists=True,fitness=0,created_at=None)
    assert service.save_best_if_better(object(),0)==(False,None)
    assert path.read_bytes()==raw


def test_real_verified_h_output_can_enter_only_an_explicit_fictional_store(tmp_path,monkeypatch):
    import random
    from tests.test_ga_bundle_optimizer import make_bundle,start
    from services.ga_bundle_checkpoint import semantic_graph_fingerprint
    # This fixture builds fictional models and forbids every SQLAlchemy connect;
    # it is not an institutional source, authority or database initialization gate.
    bundle=make_bundle.__wrapped__(monkeypatch)(generations=1)
    session=start(bundle);before=random.getstate()
    subjects,faculty,_rooms=session.working['templates']
    ctx=inputs(bundle_fingerprint=bundle.fingerprint,loaded_model_fingerprint=session.loaded_fingerprint,
        faculty_fingerprint=semantic_graph_fingerprint(faculty),subject_fingerprint=semantic_graph_fingerprint(subjects),
        preferences_fingerprint=policy.digest(session.working['scoring_context']['preferences']),
        scoring_configuration_fingerprint=policy.digest(session.working['scoring_context']['settings']),
        engine_fingerprint=session.runtime.source_engine,
        constraints_fingerprint=policy.digest({'bundle':bundle.fingerprint,'contract':'fictional-H-constraints'}))
    result=session.run();receipt=session.receipt()
    assert receipt['verification_status']=='VERIFIED' and not receipt['eligible_for_current']
    assert receipt['institutional_authorization']=='NOT_ESTABLISHED' and not result['saved_best_updated']
    class ConsumedFictionalVerifier(FictionalVerifier):
        def snapshot(self):
            assert session.receipt()==receipt
            return super().snapshot()
    provider=ConsumedFictionalVerifier(ctx)
    candidate=dict(format='ccs-ga-chromosome',version=1,best_fitness=result['best_fitness'],
        subject_keys=sorted(str(s.number)+'::'+str(s.section.code) for s in subjects),schedule=result['schedule'])
    path=tmp_path/'explicit-fictional-best.json';first=policy.consider(path,candidate,provider)
    assert first.updated and first.classification=='ELIGIBLE'
    raw=path.read_bytes();second=policy.consider(path,candidate,provider)
    assert second.classification=='ELIGIBLE' and not second.updated and path.read_bytes()==raw
    assert json.loads(raw)['best_fitness']==result['best_fitness']==0
    # A second actual run changes only an irrelevant search limit. Its raw
    # bundle and loaded hash differ; a guarded proof, not those scalar scores,
    # must establish identical complete evaluation inputs before comparison.
    from services.ga_input_bundle import capture
    from services.ga_checkpoint_service import dataframe_to_state
    working=bundle.materialize(bundle.run_id)
    projection=lambda data:semantic_graph_fingerprint({k:dataframe_to_state(v) if k=='legacy_preferences' else v for k,v in data.items() if k!='configuration'})
    evaluation_projection=projection(working)
    bundle2=capture(run_id='00000000-0000-4000-8000-000000000802',
        templates=working['templates'],fallback_templates=working['fallback_templates'],
        legacy_preferences=working['legacy_preferences'],scoring_context=working['scoring_context'],
        configuration={**working['configuration'],'generations':2},
        source_identities=json.loads(bundle._raw)['source_identities'])
    later=start(bundle2)
    assert projection(later.working)==evaluation_projection
    later_result=later.run();later_receipt=later.receipt()
    later_ctx={**ctx,'bundle_fingerprint':bundle2.fingerprint,'loaded_model_fingerprint':later.loaded_fingerprint}
    class EquivalentConsumedFixture(FictionalVerifier):
        def snapshot(self):
            assert session.receipt()==receipt and later.receipt()==later_receipt
            assert later_receipt['verification_status']=='VERIFIED'
            return super().snapshot()
        def equivalent_inputs(self,new,old):
            return new==later_ctx and old==ctx and projection(bundle2.materialize(bundle2.run_id))==evaluation_projection
    later_candidate={**candidate,'best_fitness':later_result['best_fitness'],'schedule':later_result['schedule']}
    tied=policy.consider(path,later_candidate,EquivalentConsumedFixture(later_ctx))
    assert tied.classification=='ELIGIBLE' and not tied.updated and path.read_bytes()==raw
    assert bundle.fingerprint!=bundle2.fingerprint and later.loaded_fingerprint!=session.loaded_fingerprint
    assert random.getstate()==before


def test_different_bundle_requires_explicit_equivalence_proof(tmp_path):
    path=tmp_path/"best.json";original=inputs();changed=inputs(bundle_fingerprint='b'*64)
    assert policy.consider(path,payload(100),FictionalVerifier(original)).updated
    before=path.read_bytes()
    assert policy.consider(path,payload(90),FictionalVerifier(changed)).classification=='UNVERIFIED'
    assert path.read_bytes()==before
    class EquivalentFixture(FictionalVerifier):
        def equivalent_inputs(self,new,old):
            # An explicit fictional proof for this exact pair, not a deployment
            # fallback or an assertion that every bundle difference is harmless.
            return new==changed and old==original
    result=policy.consider(path,payload(90),EquivalentFixture(changed))
    assert result.classification=='ELIGIBLE' and result.updated
    assert json.loads(path.read_bytes())['best_fitness']==90


def test_fingerprinted_caller_rejects_changed_helper_before_admission(monkeypatch):
    from services import chromosome_service as service
    original=Path.read_bytes
    monkeypatch.setattr(Path,'read_bytes',lambda p:b'changed helper source' if p.name=='saved_best_policy.py' else original(p))
    def forbidden():raise AssertionError('Changed source must not reach authority/candidate IO')
    monkeypatch.setattr(policy,'configured_verifier',forbidden)
    assert service.save_best_if_better(object(),0)==(False,None)
