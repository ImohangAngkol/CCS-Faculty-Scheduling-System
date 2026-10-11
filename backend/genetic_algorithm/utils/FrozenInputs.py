"""Context-local input snapshots. No fitness calculation or GA RNG consumption."""
import copy
from contextvars import ContextVar
from functools import wraps

scoring_inputs = ContextVar("ga_scoring_inputs", default=None)


def capture_inputs():
    from genetic_algorithm.operators.FitnessFunction import _load_ga_settings, _load_dashboard_preferences
    from genetic_algorithm.utils.Functions import list_faculty
    from services.ga_progress_service import input_fingerprint
    fingerprint = input_fingerprint()
    inputs = {"settings": _load_ga_settings().to_dict(),
              "preferences": _load_dashboard_preferences(),
              "system_faculty": copy.deepcopy(list_faculty),
              "input_fingerprint": fingerprint}
    if input_fingerprint() != fingerprint:
        raise ValueError("GA inputs changed while freezing the evaluation context; no run can continue.")
    return inputs


def with_frozen_inputs(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        restored = kwargs.get("resume_state")
        inputs = restored["scoring_inputs"] if restored is not None else capture_inputs()
        token = scoring_inputs.set(inputs)
        try:
            return function(*args, **kwargs)
        finally:
            scoring_inputs.reset(token)
    return wrapped
