"""Fictional F2C contract tests. No application dispatcher is installed."""
from dataclasses import replace
import ast
from datetime import datetime,timedelta,timezone
from fractions import Fraction
import copy
import importlib.util
import json
from pathlib import Path
import random

import pytest
from contract_model import (CAPABILITY,ContractError,Evaluation,Score,ExceptionContext,Grant,
    Mandate,canonical,digest,encode_score,decode_score,ratio,parse_ratio,workload_exact,zero_admission)

ROOT=Path(__file__).resolve().parents[3]
NOW=datetime(2026,10,30,8,tzinfo=timezone.utc)
H=lambda label:digest({'fictional':label})


def identity():
    return Evaluation('fictional-run',*[H(x) for x in ('policy','engine','input','cohort','constraints','exceptions')])


def fixture():
    context=ExceptionContext('FICT-F1','FICT-IT','FICT-YEAR','FICT-TERM','fictional-run',
        H('policy'),H('input'),H('profile'),H('constraints'),('FICT-S1',))
    grant=Grant('FICT-APPROVAL',1,'FICT-EVENT',context.binding,'FICT-ISSUER',H('issuer-policy'),CAPABILITY,
        6,NOW-timedelta(minutes=1),NOW+timedelta(minutes=5))
    mandate=Mandate('FICT-ISSUER',H('issuer-policy'),(CAPABILITY,),('FICT-IT',),
        NOW-timedelta(minutes=1),NOW+timedelta(minutes=5))
    return context,grant,mandate


class FictionalProvider:
    """No signatures, tokens, deployment configuration or institutional status."""
    def __init__(self,grant,mandate):self.grant,self.mandate=grant,mandate
    def attest(self,context,now):return self.grant,self.mandate


def admit(context,grant,mandate,**kwargs):
    return zero_admission(context,kwargs.pop('actual',3),kwargs.pop('used',('FICT-S1',)),
        FictionalProvider(grant,mandate),kwargs.pop('now',NOW),hard_findings=kwargs.pop('hard',()),**kwargs)


def test_exact_counterexample():
    assert workload_exact([2,2],[24,24])==Fraction(121,3)
    assert workload_exact([4,0],[24,24])==Fraction(122,3)
    assert workload_exact([0,4],[0,20])==Fraction(64,5)


@pytest.mark.parametrize('actual,targets', [([True],[1]),([1.5],[2]),([41],[24]),([1],[25]),([1],[]),([-1],[1])])
def test_numeric_domain_fail_closed(actual,targets):
    with pytest.raises(ContractError):workload_exact(actual,targets)


@pytest.mark.parametrize('value',[Fraction(0),Fraction(-1,3),Fraction(2**80+1,7),Fraction(121,3)])
def test_deterministic_roundtrip(value):
    expected=identity();score=Score(expected,H('candidate'),value)
    encoded=encode_score(score)
    assert encode_score(decode_score(encoded,expected))==encoded
    assert encoded==encode_score(copy.deepcopy(score))
    assert decode_score(encoded,expected)==score


@pytest.mark.parametrize('bad',[
    {'numerator':'2','denominator':'4'}, {'numerator':'-0','denominator':'1'},
    {'numerator':'01','denominator':'1'}, {'numerator':'1','denominator':'0'},
    {'numerator':1,'denominator':'1'}, {'numerator':'1','denominator':'-2'},
    {'numerator':'1','denominator':'1','extra':0}, {'numerator':'1'*1235,'denominator':'1'}])
def test_malformed_rational(bad):
    with pytest.raises(ContractError):parse_ratio(bad)


@pytest.mark.parametrize('field',['run_id','policy_digest','engine_fingerprint','input_fingerprint',
    'cohort_digest','constraint_digest','exception_set_digest','evaluation_scope'])
def test_mixed_identity_and_continuation_rejected(field):
    expected=identity();other=replace(expected,**{field:'different' if field in ('run_id','evaluation_scope') else H('changed')})
    a,b=Score(expected,H('a'),Fraction(1)),Score(other,H('b'),Fraction(2))
    for operation in (lambda:a<b,lambda:a==b,lambda:a<=b,lambda:decode_score(encode_score(a),other)):
        with pytest.raises(ContractError):operation()


@pytest.mark.parametrize('bad',[b'{}',b'[]',b'{"schema_version":1,"schema_version":1}',b'NaN',b'x'*16385])
def test_bad_score_payload(bad):
    with pytest.raises(ContractError):decode_score(bad,identity())


def test_untagged_and_changed_candidate_cache_key():
    score=Score(identity(),H('before-mutation'),Fraction(1))
    with pytest.raises(ContractError):score<1.0
    assert (score.evaluation,score.candidate_digest)!=(score.evaluation,H('after-mutation'))


def test_best_ever_ties_and_rng():
    state=random.getstate()
    try:
        random.seed(779);before=random.getstate()
        best=None;history=[]
        for i,value in enumerate([3,2,2,Fraction(1,3),2]):
            candidate=Score(identity(),H(str(i)),Fraction(value))
            if best is None or candidate<best:best=copy.deepcopy(candidate)
            history.append(best.value)
        assert best.candidate_digest==H('3') and history==[3,2,2,Fraction(1,3),Fraction(1,3)]
        assert before==random.getstate()
    finally:random.setstate(state)


def load_selector(name):
    path=ROOT/'backend/genetic_algorithm/operators'/f'{name}.py'
    spec=importlib.util.spec_from_file_location('f2c_'+name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_original_selectors_same_policy_and_copy_isolation():
    # These two source files import no data loaders. No global application patch.
    tournament=load_selector('TournamentSelection');elitism=load_selector('ElitisimSelection')
    population=[[{'fictional':i}] for i in range(3)]
    scores=[Score(identity(),H(str(i)),Fraction(v)) for i,v in enumerate([3,1,2])]
    state=random.getstate()
    try:
        random.seed(9)
        assert tournament.tournament_selection(population,scores,3) is population[1]
        elites,elite_scores,_,_=elitism.elitism_selection(population,scores,.1)
        assert elite_scores==[scores[1]] and elites==[population[1]]
        elites[0][0]['fictional']='mutated'
        assert population[1][0]['fictional']==1
    finally:random.setstate(state)


def test_original_selectors_reject_mixed_scores():
    scores=[Score(identity(),H('a'),Fraction(1)),Score(replace(identity(),policy_digest=H('other')),H('b'),Fraction(2))]
    state=random.getstate()
    try:
        for module,function in [('TournamentSelection','tournament_selection'),('ElitisimSelection','elitism_selection')]:
            with pytest.raises(ContractError):getattr(load_selector(module),function)([['a'],['b']],scores)
    finally:random.setstate(state)


def test_zero_no_assignment_no_authority_needed():
    context,_,_=fixture()
    assert zero_admission(context,0,(),None,NOW,hard_findings=()) is None
    assert workload_exact([0],[0])==0


def test_zero_approved_admission_preserves_target_but_math_unresolved():
    context,grant,mandate=fixture();pin=admit(context,grant,mandate)
    assert pin.approval_id=='FICT-APPROVAL' and context.target==0
    with pytest.raises(ContractError,match='NUMERIC_POLICY_UNRESOLVED'):workload_exact([3],[0])


def test_zero_no_provider_and_failure_sanitized():
    context,_,_=fixture()
    class Broken:
        def attest(self,*args):raise RuntimeError('FICTIONAL_PRIVATE_DIAGNOSTIC')
    for provider in (None,Broken()):
        with pytest.raises(ContractError,match='^EXCEPTION_AUTHORITY_UNAVAILABLE$'):
            zero_admission(context,3,('FICT-S1',),provider,NOW,hard_findings=())


@pytest.mark.parametrize('change',[
    {'state':'PENDING'},{'state':'REVOKED'},{'capability':'schedule.publish'},
    {'expires_at':NOW},{'issued_at':NOW+timedelta(seconds=1)},
    {'issued_at':NOW.replace(tzinfo=None)},{'max_teaching_units':2},{'max_teaching_units':True},
    {'context_digest':H('other')},{'revision':0},{'event_id':''},{'issuer':'FICT-OTHER'}])
def test_zero_unapproved_expired_or_invalid_grants(change):
    context,grant,mandate=fixture()
    with pytest.raises(ContractError):admit(context,replace(grant,**change),mandate)


@pytest.mark.parametrize('change',[
    {'state':'REVOKED'},{'capabilities':('schedule_application',)},
    {'department_ids':('FICT-IS',)},{'policy_digest':H('other')},{'expires_at':NOW}])
def test_zero_distinct_authority_not_inherited(change):
    context,grant,mandate=fixture()
    with pytest.raises(ContractError):admit(context,grant,replace(mandate,**change))


@pytest.mark.parametrize('change',[
    {'faculty_id':'FICT-F2'},{'department_id':'FICT-IS'},{'academic_year':'FICT-NEXT-YEAR'},
    {'term_id':'FICT-NEXT-TERM'},{'run_id':'another-run'},{'faculty_profile_digest':H('new-profile')},
    {'input_fingerprint':H('new-input')},{'constraint_digest':H('new-constraint')},
    {'policy_digest':H('new-policy')},{'allowed_offerings':('FICT-S2',)}])
def test_zero_invalidated_context(change):
    context,grant,mandate=fixture()
    with pytest.raises(ContractError):admit(replace(context,**change),grant,mandate)


@pytest.mark.parametrize('hard', [('ineligible',),('faculty_overlap',),('room_overlap',),('section_overlap',),('invalid_time',)])
def test_authorization_never_overrides_hard_findings(hard):
    context,grant,mandate=fixture()
    with pytest.raises(ContractError,match='HARD_CONSTRAINT_REJECTED'):admit(context,grant,mandate,hard=hard)


def test_zero_units_offerings_hard_ceiling_and_revision_pin():
    context,grant,mandate=fixture();pin=admit(context,grant,mandate)
    assert admit(context,grant,mandate,previous=pin)==pin
    for kwargs in ({'actual':41},{'used':('FICT-S2',)},{'actual':True}):
        with pytest.raises(ContractError):admit(context,grant,mandate,**kwargs)
    with pytest.raises(ContractError,match='EXCEPTION_REVISION_CHANGED'):
        admit(context,replace(grant,revision=2,event_id='FICT-EVENT2'),mandate,previous=pin)


def test_passive_json_schema_has_no_activation_hook():
    schema=json.loads((Path(__file__).parent/'policy-contract.schema.json').read_text(encoding='utf-8'))
    assert schema['additionalProperties'] is False
    assert schema['properties']['status']['const']=='PROPOSAL_NOT_ACTIVATABLE'
    assert schema['properties']['zero_target']['properties']['positive_assignment']['const']=='EXPLICIT_AUTHORIZATION_REQUIRED'
    assert all(name in schema['required'] for name in ['numeric','zero_target','overload','implementation_digest','workload_policy','preference_policy'])


@pytest.mark.parametrize('module,function',[
    ('chair_authority_service','institutional_chair_directory'),
    ('application_authority_service','institutional_application_directory'),
    ('confirmation_authority_service','authorization_for'),
    ('published_schedule_source','institutional_publication_source')])
def test_production_authority_factory_remains_unconfigured(module,function):
    tree=ast.parse((ROOT/'backend/services'/f'{module}.py').read_bytes())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function)
    statements=[n for n in fn.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant))]
    assert len(statements)==1 and isinstance(statements[0],ast.Return)
    assert isinstance(statements[0].value,ast.Constant) and statements[0].value.value is None


def test_original_operator_aliases_and_internal_scoring_calls():
    for filename,count in [('Swap',3),('mutation',2)]:
        tree=ast.parse((ROOT/'backend/genetic_algorithm/operators'/f'{filename}.py').read_bytes())
        assert any(isinstance(n,ast.ImportFrom) and n.module=='genetic_algorithm.operators.FitnessFunction'
            and any(alias.name=='faculty_preference_fitness' for alias in n.names) for n in ast.walk(tree))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='faculty_preference_fitness']
        assert len(calls)==count


def test_real_legacy_source_bridge_rejects_changed_installed_bytes():
    spec=importlib.util.spec_from_file_location('f2c_legacy_bridge',ROOT/'backend/services/preference_scoring_policy.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    relative='genetic_algorithm/operators/FitnessFunction.py';source=(ROOT/'backend'/relative).read_bytes()
    assert isinstance(module.legacy_source(relative,source),bytes)
    with pytest.raises(ValueError,match='not the verified legacy-compatible release'):
        module.legacy_source(relative,source+b'\n# hypothetical in-memory change\n')


def test_policy_descriptor_hash_is_complete_and_deterministic():
    descriptor={'version':1,'preference':2,'workload':'proposed','weight':ratio(Fraction(1,3)),
        'zero':'unresolved-positive-math','overload':'unresolved','numeric':'exact','implementation':H('source')}
    assert digest(descriptor)==digest(dict(reversed(list(descriptor.items()))))
    for name in descriptor:
        changed=dict(descriptor);changed[name]='different'
        assert digest(changed)!=digest(descriptor)
