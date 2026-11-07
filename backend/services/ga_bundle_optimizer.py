"""Synchronous, internal, opt-in bundle-bound fixed optimizer release.

No HTTP registration, continuous worker, source loader, institutional authority
or publication. Results/checkpoints/receipts are returned in memory only.
Legacy APIs/engine/checkpoints and U5D observations remain unchanged.
"""
import copy
import json
import threading
import time
from pathlib import Path

from services.ga_input_bundle import InputBundle, BundleError, canonical, digest
from services.ga_bundle_runtime import Runtime, VERSION
from services import ga_bundle_checkpoint as checkpoint
from services.ga_control_service import RunControl


class BundleControl(RunControl):
    def finish_pause(self, reference):
        with self.lock:
            self.checkpoint = reference
            if self.stop_requested:return False
            self.paused_at = "BUNDLE_CHECKPOINT_COMMITTED_IN_MEMORY"
            self.ended_clock = time.monotonic()
            self._state("PAUSED", persist=False)
            return True


class Session:
    def __init__(self, bundle: InputBundle, *, run_id, random_state):
        self.bundle = bundle
        self.working = bundle.materialize(run_id)
        self.run_id = run_id
        doc = json.loads(bundle._raw)
        from services import ga_checkpoint_service as legacy_codec
        from services import ga_input_bundle as bundle_codec
        capture_identity = digest(Path(bundle_codec.__file__).read_bytes()+Path(legacy_codec.__file__).read_bytes())
        if doc["capture_implementation_fingerprint"] != capture_identity:
            raise BundleError("GA_BUNDLE_LOADER_VERSION_MISMATCH")
        self.config_fingerprint = doc["configuration_fingerprint"]
        if self.working["scoring_context"]["preference_scoring_version"] != 2:
            raise BundleError("GA_BUNDLE_SCORING_VERSION_UNSUPPORTED")
        if any(a is not b for a, b in zip(self.working["templates"], self.working["fallback_templates"])):
            raise BundleError("GA_BUNDLE_FALLBACK_GRAPH_MISMATCH")
        if any(a is b for a in self.working["templates"][1] for b in self.working["scoring_context"]["system_faculty"]):
            raise BundleError("GA_BUNDLE_SCORING_GRAPH_SHARED")
        subjects, faculty, rooms = self.working["templates"]
        for keys in [[(str(s.number),str(s.section.code)) for s in subjects],
                     [str(f.code) for f in faculty], [''.join(str(r.name).upper().split()) for r in rooms]]:
            if len(keys) != len(set(keys)):raise BundleError("GA_BUNDLE_AMBIGUOUS_RESOURCE")
        cohort = self.working["scoring_context"]["system_faculty"]
        if len(cohort) != len(faculty) or {str(f.code) for f in cohort} != {str(f.code) for f in faculty}:
            raise BundleError("GA_BUNDLE_SCORING_COHORT_MISMATCH")
        lookup = {str(f.code):f for f in faculty}
        fields = ("eligible_subjects","admin_load","research_load","extension_load","required_teaching_load","absolute_max_teaching_load","seniority_level")
        if any(getattr(f,key)!=getattr(lookup[str(f.code)],key) for f in cohort for key in fields):
            raise BundleError("GA_BUNDLE_SCORING_COHORT_MISMATCH")
        self.scoring_fingerprint = checkpoint.semantic_graph_fingerprint(self.working["scoring_context"])
        from services.ga_checkpoint_service import dataframe_to_state
        self.loaded_fingerprint = checkpoint.semantic_graph_fingerprint({k: dataframe_to_state(v) if k == "legacy_preferences" else v for k, v in self.working.items()})
        self.checkpoint = None
        self.checkpoint_fingerprint = None
        self.parent_fingerprint = None
        self.sequence = 0
        self.resume_state = None
        self.result = None
        self.error_code = None
        self._executed = False
        self._execution = threading.Lock()
        self.control = BundleControl(configuration=self.working["configuration"])
        self.control.run_id = run_id
        self.control.durable = False
        self.runtime = Runtime(self.working, random_state, self._save_checkpoint)
        if doc["source_identities"]["engine"] != self.runtime.source_engine:
            raise BundleError("GA_BUNDLE_ENGINE_SOURCE_MISMATCH")
        self.optimizer_fingerprint = digest(canonical({"runtime": self.runtime.identity,
            "session_source": digest(Path(__file__).read_bytes()),
            "checkpoint_source": digest(Path(checkpoint.__file__).read_bytes())}))
        self._source_document = doc

    def _save_checkpoint(self, control, state, templates):
        self.runtime.validate_state(state, templates)
        raw = checkpoint.encode(state, run_id=self.run_id, bundle_fingerprint=self.bundle.fingerprint,
            optimizer_version=VERSION, optimizer_fingerprint=self.optimizer_fingerprint,
            configuration_fingerprint=self.config_fingerprint, scoring_fingerprint=self.scoring_fingerprint,
            parent_fingerprint=self.checkpoint_fingerprint, sequence=self.sequence + 1)
        # Validate completely before acknowledging a pause.
        restored = checkpoint.decode(raw, expected_fingerprint=digest(raw), run_id=self.run_id,
            bundle_fingerprint=self.bundle.fingerprint, optimizer_version=VERSION,
            optimizer_fingerprint=self.optimizer_fingerprint, configuration_fingerprint=self.config_fingerprint,
            scoring_fingerprint=self.scoring_fingerprint, expected_sequence=self.sequence + 1,
            expected_parent=self.checkpoint_fingerprint)
        self.runtime.validate_state(restored, templates)
        self.parent_fingerprint = self.checkpoint_fingerprint
        self.sequence += 1
        self.checkpoint = raw
        self.checkpoint_fingerprint = digest(raw)
        self.resume_state = restored
        return self.checkpoint_fingerprint

    @classmethod
    def restore(cls, bundle, raw, *, run_id, expected_fingerprint, expected_sequence, expected_parent):
        import random
        instance = cls(bundle, run_id=run_id, random_state=random.Random(0).getstate())
        state = checkpoint.decode(raw, expected_fingerprint=expected_fingerprint, run_id=run_id,
            bundle_fingerprint=bundle.fingerprint, optimizer_version=VERSION,
            optimizer_fingerprint=instance.optimizer_fingerprint,
            configuration_fingerprint=instance.config_fingerprint, scoring_fingerprint=instance.scoring_fingerprint,
            expected_sequence=expected_sequence, expected_parent=expected_parent)
        if state["parameters"] != instance.working["configuration"]:
            raise BundleError("GA_BUNDLE_CHECKPOINT_BINDING")
        from services.ga_checkpoint_service import dataframe_to_state
        if checkpoint.semantic_graph_fingerprint(state["legacy_preferences"]) != checkpoint.semantic_graph_fingerprint(dataframe_to_state(instance.working["legacy_preferences"])):
            raise BundleError("GA_BUNDLE_CHECKPOINT_BINDING")
        instance.runtime.validate_state(state, instance.working["templates"])
        instance.checkpoint = raw
        instance.checkpoint_fingerprint = expected_fingerprint
        instance.parent_fingerprint = expected_parent
        instance.sequence = expected_sequence
        instance.resume_state = state
        instance.control.state = "PAUSED"
        instance.control.execution_active = False
        instance.control.latest_completed_generation = state["generation_completed"]
        return instance

    def run(self, callback=None):
        if not self._execution.acquire(blocking=False):raise BundleError("GA_BUNDLE_EXECUTION_ACTIVE")
        if self.control.state not in {"PAUSED","CREATED","STOP_REQUESTED"}:
            self._execution.release()
            raise BundleError("GA_BUNDLE_EXECUTION_STATE")
        try:
            if digest(canonical(self.working["configuration"])) != self.config_fingerprint:
                raise BundleError("GA_BUNDLE_CONFIGURATION_CHANGED")
            if not self._executed:
                from services.ga_checkpoint_service import dataframe_to_state
                actual = checkpoint.semantic_graph_fingerprint({k: dataframe_to_state(v) if k == "legacy_preferences" else v for k,v in self.working.items()})
                if actual != self.loaded_fingerprint:raise BundleError("GA_BUNDLE_WORKSPACE_CHANGED")
            if self.control.state == "PAUSED":self.control.begin_resume()
            elif self.control.state in {"CREATED", "STOP_REQUESTED"}:self.control.start()
            result = self.runtime.execute(self.working["configuration"], self.control, callback, self.resume_state)
            self._executed = True
            from services.ga_checkpoint_service import PausedRun
            if isinstance(result, PausedRun):
                self.control.execution_active = False
                return None
            self.result = result
            self.control.finish("STOPPED" if self.control.stop_requested else "COMPLETED")
            self.control.execution_active = False
            return copy.deepcopy(result)
        except BaseException:
            self.error_code = "GA_BUNDLE_EXECUTION_FAILED"
            self.control.fail(self.error_code)
            self.control.execution_active = False
            raise
        finally:self._execution.release()

    def receipt(self):
        completed = self._executed and self.control.latest_completed_generation is not None and self.control.state in {"PAUSED", "COMPLETED", "STOPPED"} and not self.error_code
        return {"contract": "ga-bundle-consumption-receipt-v1", "run_id": self.run_id,
            "verification_scope": "TECHNICAL_CONSUMPTION_OF_CAPTURED_BUNDLE_ONLY",
            "verification_status": "VERIFIED" if completed else "UNVERIFIED",
            "bundle_fingerprint": self.bundle.fingerprint, "loaded_model_fingerprint": self.loaded_fingerprint,
            "consumed_entry_fingerprint": self.runtime.consumed_entry_fingerprint,
            "rng_entry_fingerprint": self.runtime.rng_entry_fingerprint,
            "configuration_fingerprint": self.config_fingerprint, "scoring_context_fingerprint": self.scoring_fingerprint,
            "loader_contract": self._source_document["contract"], "optimizer_version": VERSION,
            "optimizer_fingerprint": self.optimizer_fingerprint, "state": self.control.state,
            "checkpoint_fingerprint": self.checkpoint_fingerprint, "checkpoint_sequence": self.sequence,
            "parent_checkpoint_fingerprint": self.parent_fingerprint,
            "bound_functions": len(self.runtime.codes), "function_calls": sum(self.runtime.calls.values()),
            "eligible_for_current": False, "institutional_authorization": "NOT_ESTABLISHED",
            "academic_source_verification": "UNVERIFIED_U5G_CAPTURE_ONLY",
            "saved_best_promotion": False, "publication": False,
            "reasons": [] if completed else [self.error_code or "CONSUMPTION_NOT_COMPLETED"]}
