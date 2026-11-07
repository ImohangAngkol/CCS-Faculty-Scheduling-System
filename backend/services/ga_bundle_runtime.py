"""Explicit, versioned dependency binding for the unchanged finite V1 code.

No production module/global/sys.modules is replaced. Each execution gets new
function namespaces, bundle working graphs and a private Random instance. This
is a new optimizer release, never an assertion of legacy engine identity.
"""
import builtins
import ast
import copy
import dis
import functools
import hashlib
import importlib
import inspect
import json
import marshal
import random
import types
from contextvars import ContextVar
from collections import Counter
from pathlib import Path

from services.ga_input_bundle import BundleError, canonical, digest

VERSION = "ga-bundle-consumer-v1"


class ForbiddenInputPath:
    def __getattr__(self, _name):
        def rejected(*_a, **_k):raise BundleError("GA_BUNDLE_EXTERNAL_IO_REJECTED")
        return rejected


def code_digest(code):
    constants = tuple(code_digest(item) if isinstance(item, types.CodeType) else item for item in code.co_consts)
    # Code filenames differ in clean temporary checkouts; executable bytecode,
    # constants and logical function identity remain part of this fingerprint.
    normalized = code.replace(co_filename="<bundle-release>", co_consts=constants)
    return hashlib.sha256(marshal.dumps(normalized)).hexdigest()


def global_reads(code):
    result = {i.argval for i in dis.get_instructions(code) if i.opname in {"LOAD_GLOBAL", "LOAD_NAME"}}
    for item in code.co_consts:
        if isinstance(item, types.CodeType):result.update(global_reads(item))
    return result


def default_identity(value):
    if value is None or type(value) in (str,int,bool):return value
    if type(value) is float:return {"float":repr(value)}
    if isinstance(value,type):return {"class":value.__module__+":"+value.__qualname__}
    raise BundleError("GA_BUNDLE_UNBOUND_FUNCTION_DEFAULT")


def profile_fingerprint(templates):
    from services.ga_bundle_checkpoint import semantic_graph_fingerprint
    state={"subjects_assigned","current_teaching_load","assigned_faculty","assigned_room","scheduled_time_blocks",
        "lecture_room","laboratory_room","lecture_time_blocks","laboratory_time_blocks","lecture_room_time_blocks",
        "laboratory_room_time_blocks","section","preassigned_instructor"}
    def resource(actor,section=False):
        fields={k:v for k,v in vars(actor).items() if k not in state and not k.startswith('time_blocks_')}
        calendars={}
        for day in ('monday','tuesday','wednesday','thursday','friday','saturday'):
            calendars[day]=[{k:getattr(b,k,None) for k in (('start_time','end_time','preferred','fixed_schedule','fixed_course','is_available') if section else ('start_time','end_time','preferred','fixed_schedule','fixed_course'))}
                for b in getattr(actor,'time_blocks_'+day,[])]
        return {'fields':fields,'calendar_contract':calendars}
    subjects,faculty,rooms=templates
    return semantic_graph_fingerprint({'faculty':[resource(f) for f in faculty],'rooms':[resource(r) for r in rooms],
        'subjects':[{'fields':resource(s),'section':resource(s.section,True),
                     'external':None if s.preassigned_instructor is None else resource(s.preassigned_instructor)} for s in subjects]})


class RandomBinding:
    Random = random.Random  # Passive checkpoint-state validation uses Random(0).
    def __init__(self, state):
        self.owned = random.Random(0)
        self.owned.setstate(state)
    def __getattr__(self, name):
        if name not in {"getstate", "setstate", "choice", "sample", "shuffle", "random", "randint", "randrange", "uniform", "choices"}:
            raise BundleError("GA_BUNDLE_UNBOUND_RNG_OPERATION")
        return getattr(self.owned, name)


class Runtime:
    def __init__(self, working, rng_state, save_checkpoint):
        from services import ga_service, ga_checkpoint_service, ga_progress_service
        self.working = working
        self.random = RandomBinding(rng_state)
        self.namespaces = {}
        self.memo = {}
        self.codes = {}
        self.calls = Counter()
        self.consumed_entry_fingerprint = None
        self.rng_entry_fingerprint = None
        self.constants = {}
        self.expected_configuration = digest(canonical(working["configuration"]))
        self.active_templates = working["templates"]
        self.expected_profile = profile_fingerprint(self.active_templates)
        self.source_engine = ga_checkpoint_service.engine_fingerprint()
        self.overrides = {
            ("services.ga_service", "save_checkpoint"): save_checkpoint,
            ("services.ga_service", "save_best_if_better"): lambda *_a, **_k: (False, None),
            ("services.ga_service", "load_saved_best_payload"): lambda: copy.deepcopy(working["seed"]),
            ("services.ga_service", "load_uploaded_payload"): lambda: copy.deepcopy(working["seed"]),
            ("services.ga_progress_service", "input_fingerprint"): lambda: working["scoring_context"]["input_fingerprint"],
        }
        self.monitor = self._monitor(ga_progress_service.GenerationMonitor)
        self.overrides[("services.ga_service", "GenerationMonitor")] = self.monitor
        self.overrides[("services.ga_progress_service", "input_fingerprint")] = lambda: working["scoring_context"]["input_fingerprint"]
        # inspect.unwrap removes only the outer input/observation decorators.
        # The original score-observation decorator is re-applied below; the
        # outer file-loading decorator is replaced by the explicit bundle scope.
        self.engine = self.bind_function(inspect.unwrap(ga_service.run_genetic_algorithm))
        self.validate_state = self.bind_function(ga_checkpoint_service.validate_state)
        self.validate_publication = self.bind_function(importlib.import_module("services.ga_publication_service").validate_publication)
        self.model_codes = {}
        for cls in ga_checkpoint_service.CLASSES.values():
            for name, member in vars(cls).items():
                function = member.__func__ if isinstance(member,(staticmethod,classmethod)) else member.fget if isinstance(member,property) else member
                if isinstance(function,types.FunctionType):self.model_codes[cls.__name__+":"+name] = {
                    'code':code_digest(function.__code__),'defaults':[default_identity(v) for v in function.__defaults__ or ()],
                    'keyword_defaults':{k:default_identity(v) for k,v in (function.__kwdefaults__ or {}).items()}}
        self.code_identity = digest(canonical({"functions":self.codes,"models":self.model_codes}))
        self.identity = digest(canonical({"version": VERSION, "legacy_source_engine": self.source_engine,
            "loaded_function_code": self.code_identity, "adapter_source": digest(Path(__file__).read_bytes()),
            "bundle_codec_source": digest(Path(__file__).with_name("ga_input_bundle.py").read_bytes())}))

    def _monitor(self, original):
        # Methods use private globals; no dynamic source-file fingerprint reads.
        # The legacy monitor is not edited; this version separately binds the
        # bundle and validates the scoring context at every check boundary.
        methods = {name: self.bind_function(value) for name, value in vars(original).items() if isinstance(value, types.FunctionType)}
        ordinary_check = methods["check_inputs"]
        from services.ga_bundle_checkpoint import semantic_graph_fingerprint
        expected_scoring = semantic_graph_fingerprint(self.working["scoring_context"])
        def check_inputs(monitor):
            from genetic_algorithm.utils.FrozenInputs import scoring_inputs
            ordinary_check(monitor)
            if profile_fingerprint(self.active_templates) != self.expected_profile:
                raise BundleError("GA_BUNDLE_RESOURCE_PROFILE_CHANGED")
            if digest(canonical(self.working["configuration"])) != self.expected_configuration:
                raise BundleError("GA_BUNDLE_CONFIGURATION_CHANGED")
            if semantic_graph_fingerprint(scoring_inputs.get()) != expected_scoring:
                raise BundleError("GA_BUNDLE_SCORING_CONTEXT_CHANGED")
        methods["check_inputs"] = check_inputs
        return type("BundleGenerationMonitor", (object,), methods)

    def _namespace(self, original):
        key = id(original)
        if key not in self.namespaces:
            private_builtins = dict(vars(builtins))
            private_builtins.update(open=self.forbidden_io, print=lambda *_a, **_k: None, __import__=self._import)
            subjects, faculty, rooms = self.working["templates"]
            self.namespaces[key] = {"__builtins__": private_builtins, "__name__": original.get("__name__", "") + ".bundle",
                "list_subjects": subjects, "lst_subjects": subjects, "list_faculty": faculty,
                "lst_rooms": rooms, "df_faculty_pref": self.working["legacy_preferences"]}
        return self.namespaces[key]

    @staticmethod
    def forbidden_io(*_a, **_k):
        raise BundleError("GA_BUNDLE_EXTERNAL_IO_REJECTED")

    def _import(self, name, globals=None, locals=None, fromlist=(), level=0):
        if level:raise BundleError("GA_BUNDLE_UNBOUND_IMPORT")
        if name == "genetic_algorithm.utils.Functions":
            original = importlib.import_module(name)
            proxy = types.ModuleType(name)
            namespace = self._namespace(vars(original))
            for attr in fromlist:
                if attr in {"list_subjects", "lst_subjects", "list_faculty", "lst_rooms", "df_faculty_pref"}:
                    setattr(proxy, attr, namespace[attr])
                else:
                    raise BundleError("GA_BUNDLE_UNBOUND_IMPORT")
            return proxy
        if name == "genetic_algorithm.utils.FrozenInputs":
            # A ContextVar is deliberately shared; its value is owned per call.
            if set(fromlist) != {"scoring_inputs"}:raise BundleError("GA_BUNDLE_UNBOUND_IMPORT")
            return importlib.import_module(name)
        if name.startswith(("genetic_algorithm.", "services.")):
            # No silent dynamic import of another cached scheduling module.
            raise BundleError("GA_BUNDLE_UNBOUND_IMPORT")
        return builtins.__import__(name, globals, locals, fromlist, level)

    def bind_value(self, value, source_globals=None, symbol=None):
        if isinstance(value, types.FunctionType) and value.__module__.startswith(("genetic_algorithm.", "services.")):
            return self.bind_function(value)
        if value is random:return self.random
        if isinstance(value,Path):return ForbiddenInputPath()
        if isinstance(value, (list, dict, set, tuple)) or (source_globals is not None and (value is None or type(value) in (str,int,float,bool))):
            def passive(item):
                if item is None or type(item) in (str, int, float, bool):return True
                if type(item) in (list, tuple, set):return all(passive(v) for v in item)
                if type(item) is dict:return all(passive(k) and passive(v) for k, v in item.items())
                return False
            if not passive(value):raise BundleError("GA_BUNDLE_UNBOUND_GLOBAL_DATA")
            # Only source-declared literal constants may enter from a module.
            # A primitive dict/frame derived from institutional data is still
            # external input; it is not made safe merely by deepcopy.
            if source_globals is None:raise BundleError("GA_BUNDLE_UNBOUND_GLOBAL_DATA")
            filename = source_globals.get("__file__")
            if filename not in self.constants:
                literals = {}
                for statement in ast.parse(Path(filename).read_bytes()).body:
                    if isinstance(statement, ast.Assign):
                        try:literal = ast.literal_eval(statement.value)
                        except (ValueError, TypeError, SyntaxError):continue
                        for target in statement.targets:
                            if isinstance(target, ast.Name):literals[target.id] = literal
                self.constants[filename] = literals
            if symbol not in self.constants[filename] or value != self.constants[filename][symbol]:
                raise BundleError("GA_BUNDLE_UNBOUND_GLOBAL_DATA")
            return copy.deepcopy(value)
        if type(value).__module__.startswith(("pandas.", "numpy.")):
            raise BundleError("GA_BUNDLE_UNBOUND_GLOBAL_DATA")
        if isinstance(value, types.ModuleType) and value.__name__.startswith(("genetic_algorithm.", "services.")):
            raise BundleError("GA_BUNDLE_UNBOUND_MODULE")
        if isinstance(value,ContextVar):
            from genetic_algorithm.utils.FrozenInputs import scoring_inputs
            from genetic_algorithm.utils.FitnessObservation import observed_scores
            if value is not scoring_inputs and value is not observed_scores:raise BundleError('GA_BUNDLE_UNBOUND_CONTEXT')
            return value
        if value is None or type(value) in (str,int,float,bool) or isinstance(value,(type,types.FunctionType,types.BuiltinFunctionType,types.ModuleType)):
            return value
        raise BundleError("GA_BUNDLE_UNBOUND_GLOBAL_DATA")

    def bind_function(self, original):
        if id(original) in self.memo:return self.memo[id(original)]
        namespace = self._namespace(original.__globals__)
        cells = tuple((lambda value: lambda: value)(None).__closure__[0] for _ in (original.__closure__ or ()))
        private = types.FunctionType(original.__code__, namespace, original.__name__, None, cells or None)
        key = original.__globals__.get("__name__", original.__module__) + ":" + original.__qualname__ + ":" + code_digest(original.__code__)
        self.codes[key] = {"code":code_digest(original.__code__),
            "defaults":[default_identity(v) for v in original.__defaults__ or ()],
            "keyword_defaults":{k:default_identity(v) for k,v in (original.__kwdefaults__ or {}).items()}}
        @functools.wraps(private)
        def observed(*args, **kwargs):
            self.calls[key] += 1
            return private(*args, **kwargs)
        self.memo[id(original)] = observed
        if original.__closure__:
            for target, source in zip(cells, original.__closure__):target.cell_contents = self.bind_value(source.cell_contents)
        private.__defaults__ = tuple(self.bind_value(v) for v in original.__defaults__) if original.__defaults__ else None
        private.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
        for name in global_reads(original.__code__):
            override = self.overrides.get((original.__globals__.get("__name__"), name))
            if override is not None:namespace[name] = override
            elif name not in namespace and name in original.__globals__:namespace[name] = self.bind_value(original.__globals__[name],original.__globals__,name)
        return observed

    def execute(self, parameters, control, callback, resume_state=None):
        from genetic_algorithm.utils.FrozenInputs import scoring_inputs
        from genetic_algorithm.utils.FitnessObservation import collect_run_scores
        from services.ga_bundle_checkpoint import semantic_graph_fingerprint
        from services.ga_checkpoint_service import dataframe_from_state, dataframe_to_state, rng_to_json
        templates = self.working["templates"] if resume_state is None else resume_state["working_templates"]
        self.active_templates = templates
        if profile_fingerprint(templates) != self.expected_profile:raise BundleError('GA_BUNDLE_RESOURCE_PROFILE_CHANGED')
        frame = self.working["legacy_preferences"] if resume_state is None else dataframe_from_state(resume_state["legacy_preferences"])
        # Every fallback and the engine-local alias must refer to the same
        # active working graph, including after checkpoint reconstruction.
        for namespace in self.namespaces.values():
            namespace.update(list_subjects=templates[0],lst_subjects=templates[0],list_faculty=templates[1],
                             lst_rooms=templates[2],df_faculty_pref=frame)
            if resume_state is not None and "dataframe_from_state" in namespace:
                namespace["dataframe_from_state"] = lambda state: frame if state is resume_state["legacy_preferences"] else self.forbidden_io()
        expected = semantic_graph_fingerprint(self.working["scoring_context"])
        context = self.working["scoring_context"] if resume_state is None else resume_state["scoring_inputs"]
        if semantic_graph_fingerprint(context) != expected:
            raise BundleError("GA_BUNDLE_SCORING_CONTEXT_CHANGED")
        self.consumed_entry_fingerprint = semantic_graph_fingerprint({"templates":templates,
            "legacy_preferences":dataframe_to_state(frame),"scoring_context":context,"configuration":parameters,"seed":self.working["seed"]})
        self.rng_entry_fingerprint = digest(canonical(rng_to_json(self.random.getstate() if resume_state is None else resume_state["random_state"])))
        token = scoring_inputs.set(context)
        def progress(kind, data):
            actual = semantic_graph_fingerprint(scoring_inputs.get())
            if actual != expected:raise BundleError("GA_BUNDLE_SCORING_CONTEXT_CHANGED")
            control.capture_progress(kind, data)
            if callback:callback(kind, copy.deepcopy(data))
        try:
            return collect_run_scores(self.engine)(**parameters, run_control=control, progress_callback=progress, resume_state=resume_state)
        finally:
            scoring_inputs.reset(token)
