"""Two isolated, versioned validation prototypes; no production symbol changes.

Original source bodies/checks/copies are reused in private namespaces. Only a
validation-local immutable parse cache OR complete-content calendar cache changes.
Experimental checkpoints have a distinct identity and never enter app stores.
"""
import ast
from collections import Counter
import hashlib
import inspect
from pathlib import Path
import textwrap
import types

from benchmarks.retention_runtime import runtime

VERSION='phase6-reconstruction.1'
VARIANTS=('baseline','parse_cache','calendar_cache')


def cloned(function,namespace):
    assert not function.__closure__
    return types.FunctionType(function.__code__,namespace,function.__name__,function.__defaults__)


def versioned_function(function,namespace):
    """Replace only the local identity provider in an isolated code copy.

    All engine validation branches, operators and RNG calls remain original.
    No production store fingerprint is replaced, bypassed or spoofed.
    """
    tree=ast.parse(textwrap.dedent(inspect.getsource(function)))
    imports=[node for node in ast.walk(tree) if isinstance(node,ast.ImportFrom) and node.module=='services.ga_v2_store']
    assert len(imports)==1 and [n.name for n in imports[0].names]==['engine_fingerprint']
    class Identity(ast.NodeTransformer):
        def visit_ImportFrom(self,node):
            if node is imports[0]:
                return ast.copy_location(ast.Assign(targets=[ast.Name(id='engine_fingerprint',ctx=ast.Store())],
                    value=ast.Name(id='_experimental_fingerprint',ctx=ast.Load())),node)
            return node
    tree=Identity().visit(tree);ast.fix_missing_locations(tree)
    ast.increment_lineno(tree,function.__code__.co_firstlineno-1)
    exec(compile(tree,'phase6-experimental/'+function.__name__+'.py','exec'),namespace)
    return namespace[function.__name__]


class Prototype:
    def __init__(self,variant,collect=False):
        if variant not in VARIANTS:raise ValueError('Unknown experimental variant')
        engine=runtime()[0]
        from services import chromosome_service as chromosome
        from services import ga_publication_service as publication
        from services.ga_v2_store import engine_fingerprint
        from genetic_algorithm.models.TimeBlock import TimeBlock
        self.variant=variant;self.stats=Counter() if collect else None
        self.production_fingerprint=engine_fingerprint
        self.original_validator=chromosome._validate_baseline_components
        self.original_parser=chromosome.time_to_minutes
        self.original_payload=chromosome.payload_to_chromosome
        self.TimeBlock=TimeBlock
        self.calendar_code=None
        if variant=='calendar_cache':
            tree=ast.parse(textwrap.dedent(inspect.getsource(self.original_validator)))
            assignments=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and len(n.targets)==1
                and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='allowed' and isinstance(n.value,ast.SetComp)]
            assert len(assignments)==1,'Original validation contract changed'
            assignments[0].value=ast.Call(func=ast.Name(id='_experimental_allowed',ctx=ast.Load()),
                                        args=[ast.Name(id='calendar',ctx=ast.Load())],keywords=[])
            ast.fix_missing_locations(tree);ast.increment_lineno(tree,self.original_validator.__code__.co_firstlineno-1)
            temporary=dict(self.original_validator.__globals__)
            exec(compile(tree,'phase6-experimental/components.py','exec'),temporary)
            self.calendar_code=temporary[self.original_validator.__name__].__code__
        self.version=engine.ENGINE_VERSION if variant=='baseline' else VERSION+':'+variant
        if variant=='baseline':
            self.run=engine.run;self.admit=engine.admit;self.validate_state=engine.validate_state
            self.payload=chromosome.payload_to_chromosome;self.validate_components=self.original_validator
            self.publication=publication.validate_publication
            return
        cg=dict(vars(chromosome))
        cg['_validate_baseline_components']=self.validate_components
        self.payload=cloned(chromosome.payload_to_chromosome,cg)
        pg=dict(vars(publication));pg['payload_to_chromosome']=self.payload
        self.publication=cloned(publication.validate_publication,pg)
        eg=dict(vars(engine));eg['validate_publication']=self.publication
        eg['_experimental_fingerprint']=self.fingerprint;eg['ENGINE_VERSION']=self.version
        self.admit=cloned(engine.admit,eg);eg['admit']=self.admit
        self.validate_state=versioned_function(engine.validate_state,eg);eg['validate_state']=self.validate_state
        self.run=versioned_function(engine.run,eg)

    def count(self,key,amount=1):
        if self.stats is not None:self.stats[key]+=amount

    def fingerprint(self):
        original=self.production_fingerprint()
        if self.variant=='baseline':return original
        digest=hashlib.sha256()
        digest.update(original.encode());digest.update(self.version.encode())
        digest.update(Path(__file__).read_bytes())
        return digest.hexdigest()

    def validate_components(self,chromosome):
        """Cache lifetime is exactly one validation call, success or exception."""
        if self.variant=='baseline':return self.original_validator(chromosome)
        self.count('validation_calls')
        cache={};namespace=dict(self.original_validator.__globals__)
        try:
            if self.variant=='parse_cache':
                sentinel=object();stats=self.stats;original=self.original_parser
                def parse(value):
                    # Non-exact strings retain original coercion/exception behavior.
                    if type(value) is not str or len(value)>32:return original(value)
                    found=cache.get(value,sentinel)
                    if found is not sentinel:
                        if stats is not None:stats['parse_hits']+=1
                        return found
                    if stats is not None:stats['parse_misses']+=1
                    result=original(value)
                    if len(cache)<256:cache[value]=result
                    return result
                namespace['time_to_minutes']=parse
                function=cloned(self.original_validator,namespace)
            else:
                def allowed(calendar):return self.calendar_allowed(calendar,cache)
                namespace['_experimental_allowed']=allowed
                function=types.FunctionType(self.calendar_code,namespace,self.original_validator.__name__)
            return function(chromosome)
        finally:
            self.count('cache_entries_at_exit',len(cache));cache.clear()

    def raw_allowed(self,calendar):
        return {(day,self.original_parser(block.start_time),self.original_parser(block.end_time))
                for day,blocks in calendar.items() for block in blocks}

    def calendar_allowed(self,calendar,cache):
        """Immutable FULL CONTENT key, never identity/availability-based reuse.

        Re-read current contents for every lookup. No calendars/model objects are
        shared or cached, and no cache survives a validation call. Flags ignored
        here are also ignored by the original membership-set computation; all
        separate conflict/fixed/resource checks remain intact.
        """
        if type(calendar) is not dict:return self.raw_allowed(calendar)
        if self.TimeBlock.__getattribute__ is not object.__getattribute__:
            return self.raw_allowed(calendar)
        if any(name in vars(self.TimeBlock) for name in ('start_time','end_time')):
            return self.raw_allowed(calendar)
        content=[]
        for day,blocks in calendar.items():
            if type(day) is not str or type(blocks) is not list:return self.raw_allowed(calendar)
            if len(content)+len(blocks)>512:return self.raw_allowed(calendar)
            for block in blocks:
                if type(block) is not self.TimeBlock:return self.raw_allowed(calendar)
                fields=vars(block)
                if type(fields.get('start_time')) is not str or type(fields.get('end_time')) is not str:
                    return self.raw_allowed(calendar)
                content.append((day,fields['start_time'],fields['end_time']))
        key=tuple(content)
        if key in cache:
            self.count('calendar_hits');return cache[key]
        self.count('calendar_misses')
        result=frozenset((day,self.original_parser(start),self.original_parser(end)) for day,start,end in key)
        if len(cache)<8:cache[key]=result
        return result

    def provenance(self):
        return {'variant':self.variant,'version':self.version,'engine_identity':self.fingerprint(),
                'production_identity':self.production_fingerprint(),
                'prototype_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'original_component_source_sha256':hashlib.sha256(inspect.getsource(self.original_validator).encode()).hexdigest(),
                'source_locations':{'components':self.original_validator.__code__.co_firstlineno,
                                    'payload':self.original_payload.__code__.co_firstlineno},
                'production_symbols_replaced':False,'deepcopy_implementation_changed':False,
                'cache_lifetime':'Single validation call; no checkpoint/store/global cache'}
