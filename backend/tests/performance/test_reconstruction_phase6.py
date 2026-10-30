"""Isolated cache parity and strict versioned continuation, fictional inputs only."""
import copy
import gc
import json
import random

import pytest
from benchmarks.retention_runtime import runtime,data_guard
from benchmarks import scaled_python as bench
from benchmarks.reconstruction_phase6 import Prototype,VARIANTS
from benchmarks.reconstruction_benchmark import PARAMETERS,matrix,verify_state
from benchmarks.retention_ownership import mutable_nodes
from benchmarks.scenarios import build,snapshot


@pytest.fixture(autouse=True)
def restore_rng():
    before=random.getstate();enabled=gc.isenabled();thresholds=gc.get_threshold()
    yield
    random.setstate(before)
    assert gc.isenabled()==enabled and gc.get_threshold()==thresholds


def outcome(function,*args):
    try:return ('return',function(*args))
    except Exception as error:return ('exception',type(error).__name__,getattr(error,'code',None),str(error))


def reporting_graph(value):
    """Reporting only: sets have no iteration-order continuation contract.

    Keep every graph node, ordered container, field and alias reference intact.
    Only sort primitive set items in a fresh encoded representation. Never feed
    this representation back into an engine, decoder, validator or store.
    """
    from services.ga_checkpoint_service import canonical,encode_graph
    graph=encode_graph(value)
    for node in graph['nodes']:
        if node['kind']=='set':
            assert all(type(item) in (str,int,bool,float) or item is None for item in node['items'])
            node['items'].sort(key=lambda item:json.dumps(item,sort_keys=True))
    return canonical(graph)


@pytest.fixture
def sample():
    from tests.d10.support import templates
    from tests.d10.test_v2_engine import arranged,snapshot_for
    values=templates(compact=True)
    return values,arranged(values,'7:30','9:30'),snapshot_for(values,start=570,end=630)


def test_original_symbols_not_replaced_and_versions_are_distinct():
    engine=runtime()[0]
    from services import chromosome_service as c,ga_publication_service as p
    originals=(engine.run,engine.admit,engine.validate_state,c.payload_to_chromosome,c._validate_baseline_components,p.validate_publication)
    bundles=[Prototype(v) for v in VARIANTS]
    assert len({b.fingerprint() for b in bundles})==3
    assert originals==(engine.run,engine.admit,engine.validate_state,c.payload_to_chromosome,c._validate_baseline_components,p.validate_publication)
    assert all(b.run.__defaults__==engine.run.__defaults__ for b in bundles)
    assert all(b.run.__kwdefaults__==engine.run.__kwdefaults__ for b in bundles)


@pytest.mark.parametrize('change',['none','missing','duplicate','malformed','duration','room','outside','unknown_day','lab_zero'])
@pytest.mark.parametrize('variant',VARIANTS[1:])
def test_component_failures_have_exact_original_return_or_exception(sample,variant,change):
    _,candidate,_=sample
    subject=candidate[0];block=subject.lecture_time_blocks[0][1]
    if change=='missing':subject.lecture_time_blocks=[]
    if change=='duplicate':subject.lecture_time_blocks.append(subject.lecture_time_blocks[0])
    if change=='malformed':block.start_time='bad:time'
    if change=='duration':block.end_time='08:00'
    if change=='room':subject.lecture_room.type='Laboratory'
    if change=='outside':
        subject.assigned_faculty.time_blocks_monday=[]
    if change=='unknown_day':subject.lecture_time_blocks[0]=('SUN',block)
    if change=='lab_zero':subject.laboratory_time_blocks=list(subject.lecture_time_blocks)
    bundle=Prototype(variant,collect=True)
    before=copy.deepcopy(candidate)
    from services.ga_checkpoint_service import canonical,encode_graph
    encoded=canonical(encode_graph(candidate));rng=random.getstate()
    assert outcome(bundle.validate_components,candidate)==outcome(bundle.original_validator,before)
    assert encoded==canonical(encode_graph(candidate)) and random.getstate()==rng
    # A failed call must never poison the next independent valid validation.
    _,valid,_=sample if change=='none' else _fresh_sample()
    assert outcome(bundle.validate_components,valid)==outcome(bundle.original_validator,copy.deepcopy(valid))


def _fresh_sample():
    from tests.d10.support import templates
    from tests.d10.test_v2_engine import arranged,snapshot_for
    values=templates(compact=True)
    return values,arranged(values,'7:30','9:30'),snapshot_for(values,start=570,end=630)


@pytest.mark.parametrize('variant',VARIANTS[1:])
@pytest.mark.parametrize('bad',['empty','metadata','faculty','times','extra','valid'])
def test_payload_and_admission_failure_fingerprints(sample,variant,bad):
    from services.chromosome_service import chromosome_to_payload
    values,candidate,pinned=sample;bundle=Prototype(variant);original=Prototype('baseline')
    payload=chromosome_to_payload(candidate,0)
    if bad=='empty':payload={'schedule':[]}
    if bad=='metadata':candidate[0].credit_units=99
    if bad=='faculty':candidate[0].assigned_faculty.eligible_subjects=set()
    if bad=='times':candidate[0].lecture_time_blocks[0][1].start_time='broken'
    if bad=='extra':candidate.append(copy.deepcopy(candidate[0]))
    assert outcome(bundle.admit,candidate,pinned,values)==outcome(original.admit,copy.deepcopy(candidate),pinned,values)
    # Raw payload reconstruction preserves exceptions too; metadata cases above
    # exercise admission, and the original valid payload exercises reconstruction.
    left=outcome(bundle.payload,payload,*values);right=outcome(original.payload,payload,*values)
    if left[0]=='exception':assert left==right
    else:
        assert right[0]=='return'
        from services.ga_checkpoint_service import canonical,encode_graph
        assert canonical(encode_graph(left[1]))==canonical(encode_graph(right[1]))
        assert not mutable_nodes(left[1])[0]&mutable_nodes(values)[0]


def test_calendar_cache_tracks_full_content_and_bounds_without_shared_models(sample):
    _,candidate,_=sample;bundle=Prototype('calendar_cache',collect=True);cache={}
    calendar=candidate[0].assigned_faculty.get_day_map()
    expected=bundle.raw_allowed(calendar)
    assert bundle.calendar_allowed(calendar,cache)==expected
    assert bundle.calendar_allowed(calendar,cache)==expected and bundle.stats['calendar_hits']==1
    block=calendar['monday'][0];original=block.start_time
    block.start_time='06:30'
    assert bundle.calendar_allowed(calendar,cache)==bundle.raw_allowed(calendar)
    block.start_time=original
    for n in range(12):
        block.start_time=f'{n:02}:30'
        assert bundle.calendar_allowed(calendar,cache)==bundle.raw_allowed(calendar)
    assert len(cache)==8
    assert all(type(key) is tuple and type(value) is frozenset for key,value in cache.items())
    assert not mutable_nodes(cache)[0]&mutable_nodes(candidate)[0]


@pytest.mark.parametrize('kind',['tuple','subclass','coercion','malformed','oversize'])
def test_calendar_fallback_keeps_original_behavior(sample,kind):
    _,candidate,_=sample;bundle=Prototype('calendar_cache');calendar=candidate[0].assigned_faculty.get_day_map()
    if kind=='tuple':calendar={d:tuple(blocks) for d,blocks in calendar.items()}
    if kind=='subclass':
        class Special(bundle.TimeBlock):pass
        block=calendar['monday'][0];new=Special.__new__(Special);vars(new).update(vars(block));calendar['monday'][0]=new
    if kind=='coercion':
        class Value:
            def __str__(self):return '07:30'
        calendar['monday'][0].start_time=Value()
    if kind=='malformed':calendar['monday'][0].start_time='bad'
    if kind=='oversize':calendar={'M':calendar['monday']*100}
    cache={}
    assert outcome(bundle.calendar_allowed,calendar,cache)==outcome(bundle.raw_allowed,calendar)
    assert not cache


@pytest.mark.parametrize('value',[' 07:30 ','24:00','7:5','-1:00','bad','07:xx',None,7])
def test_parse_cache_retains_permissive_original_parser_and_errors(sample,value):
    _,candidate,_=sample;candidate[0].lecture_time_blocks[0][1].start_time=value
    bundle=Prototype('parse_cache')
    assert outcome(bundle.validate_components,candidate)==outcome(bundle.original_validator,copy.deepcopy(candidate))


def test_parse_cache_bounded_successes_and_custom_coercion_fallback(sample):
    _,candidate,_=sample;bundle=Prototype('parse_cache',collect=True)
    # The original parser accepts these values; the membership check ultimately
    # rejects the meeting. More than 256 keys must fall back without truncation.
    faculty=candidate[0].assigned_faculty
    blocks=faculty.time_blocks_monday
    faculty.time_blocks_monday=[]
    for n in range(300):
        block=copy.copy(blocks[0]);block.start_time=f'{n}:00';block.end_time=f'{n}:30'
        faculty.time_blocks_monday.append(block)
    assert outcome(bundle.validate_components,candidate)==outcome(bundle.original_validator,copy.deepcopy(candidate))
    assert bundle.stats['cache_entries_at_exit']==256 and bundle.stats['parse_misses']>256


@pytest.mark.parametrize('variant',VARIANTS[1:])
def test_deterministic_malformed_interval_corpus_exactly_matches_original(sample,variant):
    _,original,_=sample;bundle=Prototype(variant);generator=random.Random(8021)
    values=('07:30','08:00','08:30','09:30','24:00','-1:30',' 8:30 ','bad','08:xx','08:30:00',None,0,False)
    global_rng=random.getstate()
    for _ in range(40):
        candidate=copy.deepcopy(original);block=candidate[0].lecture_time_blocks[0][1]
        block.start_time=generator.choice(values);block.end_time=generator.choice(values)
        assert outcome(bundle.validate_components,candidate)==outcome(bundle.original_validator,copy.deepcopy(candidate))
    assert random.getstate()==global_rng


@pytest.mark.parametrize('variant',VARIANTS)
def test_actual_checkpoint_continuation_full_graph_rng_and_copy_ownership(variant):
    from services import ga_checkpoint_service as codec
    from services.ga_v2_constraints import ConstraintError
    values,legacy,rows,settings,metadata=build('small');pinned=snapshot(values,metadata)
    params=runtime()[-1](**PARAMETERS);bundle=Prototype(variant);holder={}
    def final(state):holder['state']=state
    def pause(state):holder['encoded']=codec.canonical(codec.encode_graph(state));return 'pause'
    with bench.synthetic_scoring(values,rows,settings),data_guard(),bench.no_io():
        random.seed(714);assert bundle.run(values,pinned,params,legacy,final)=='complete'
        expected=holder.pop('state');expected_rng=random.getstate()
        random.seed(714);assert bundle.run(values,pinned,params,legacy,pause)=='pause'
        restored=codec.decode_graph(json.loads(holder.pop('encoded')))
        bundle.validate_state(restored,pinned,values)
        for field,value in [('engine_identity','0'*64),('generation',-1),('best_fitness',float('inf'))]:
            altered=copy.deepcopy(restored);altered[field]=value
            with pytest.raises(ConstraintError) as caught:bundle.validate_state(altered,pinned,values)
            assert caught.value.code==('V2_CHECKPOINT_INCOMPATIBLE' if field=='engine_identity' else 'V2_CHECKPOINT_INVALID')
        for other in VARIANTS:
            if other!=variant:
                with pytest.raises(ConstraintError) as caught:Prototype(other).validate_state(restored,pinned,values)
                assert caught.value.code=='V2_CHECKPOINT_INCOMPATIBLE'
        random.seed(999);assert bundle.run(values,pinned,params,legacy,final,state=restored)=='complete'
        resumed=holder.pop('state');assert random.getstate()==expected_rng
        assert reporting_graph(expected)==reporting_graph(resumed)
        result=verify_state(resumed,values,pinned,legacy)
        assert result['hard_constraints'].startswith('PASS')
        assert not mutable_nodes(resumed['best'])[0]&mutable_nodes(resumed['population'])[0]
        cloned=copy.deepcopy(resumed['best']);assert not mutable_nodes(cloned)[0]&mutable_nodes(resumed['best'])[0]
        cloned_block=cloned[0].lecture_time_blocks[0][1]
        assert cloned_block.subject is cloned[0] and cloned_block.faculty is cloned[0].assigned_faculty
        cloned_block.is_available=not cloned_block.is_available
        assert reporting_graph(expected)==reporting_graph(resumed)


@pytest.mark.parametrize('variant',VARIANTS[1:])
def test_cache_does_not_retain_validated_model_graphs(variant):
    import weakref
    bundle=Prototype(variant,collect=True);values,candidate,pinned=_fresh_sample()
    refs=[weakref.ref(candidate[0]),weakref.ref(candidate[0].assigned_faculty),weakref.ref(candidate[0].lecture_room)]
    bundle.admit(candidate,pinned,values)
    del candidate,values,pinned;gc.collect()
    assert all(ref() is None for ref in refs)


@pytest.mark.parametrize('variant',VARIANTS)
def test_bounded_invalid_factory_same_rejection_no_io_or_rng_change(sample,variant):
    from services.ga_v2_constraints import ConstraintError
    from tests.d10.support import preferences
    values,candidate,pinned=sample;bundle=Prototype(variant);candidate[0].lec_hours=99
    params=runtime()[-1](**PARAMETERS);calls=[]
    def invalid(*args):calls.append(1);return copy.deepcopy(candidate)
    before=random.getstate()
    with bench.no_io(),pytest.raises(ConstraintError) as caught:
        bundle.run(values,pinned,params,preferences(),lambda state:pytest.fail('No partial state'),factory=invalid)
    assert caught.value.code=='SEARCH_EXHAUSTED' and len(calls)==6
    assert caught.value.diagnostics=={'construction:INVALID_CANDIDATE':6}
    assert before==random.getstate()


@pytest.mark.parametrize('variant',VARIANTS[1:])
def test_original_teaching_hard_ceiling_not_relaxed(sample,variant):
    values,candidate,pinned=sample
    values[0][0].credit_units=41;candidate[0].credit_units=41
    baseline=outcome(Prototype('baseline').admit,candidate,pinned,values)
    assert baseline[0]=='exception' and baseline[2]=='INVALID_CANDIDATE'
    assert outcome(Prototype(variant).admit,candidate,pinned,values)==baseline


@pytest.mark.parametrize('variant',VARIANTS[1:])
@pytest.mark.parametrize('resource',['section','faculty','room','adjacent'])
def test_fixed_resource_conflicts_and_adjacent_intervals_match_oracle(variant,resource):
    from tests.d10.support import templates
    from tests.d10.test_v2_engine import arranged,snapshot_for
    engine=runtime()[0];values=templates(compact=True)
    changes={'sections':('section-b',),'faculty':None,'room':None}
    if resource=='section':changes['sections']=('section-a',)
    if resource=='faculty':changes['faculty']='faculty-a'
    if resource=='room':changes['room']='room-a'
    if resource=='adjacent':changes.update(sections=('section-a',),start=570,end=630)
    pinned=snapshot_for(values,**changes)
    publication=engine.reduced_templates(pinned,values)
    candidate=arranged(publication if resource=='adjacent' else values,'7:30' if resource=='adjacent' else '09:30','9:30' if resource=='adjacent' else '11:30')
    original=outcome(engine.admit,candidate,pinned,publication)
    actual=outcome(Prototype(variant).admit,candidate,pinned,publication)
    assert actual==original
    assert actual[0]==('return' if resource=='adjacent' else 'exception')


def test_benchmark_separates_measurements_and_rotates_variants():
    assert len(matrix('timing'))==54 and len(matrix('memory'))==27 and len(matrix('profile'))==9
    jobs=matrix('timing')
    assert {j['seed'] for j in jobs}=={714,715,716}
    assert {j['repetition'] for j in jobs}=={1,2}
    assert {tuple(j['variant'] for j in jobs[i:i+3]) for i in range(0,len(jobs),3)}=={
        ('baseline','parse_cache','calendar_cache'),('parse_cache','calendar_cache','baseline'),('calendar_cache','baseline','parse_cache')}
