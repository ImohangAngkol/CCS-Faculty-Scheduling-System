"""Optional, context-local observation of scores already computed by the GA."""
from contextvars import ContextVar
from functools import wraps


observed_scores = ContextVar("ga_observed_scores", default=None)


def record_fitness(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        result = function(*args, **kwargs)
        scores = observed_scores.get()
        scope = kwargs.get("faculty_scope", args[4] if len(args) > 4 else None)
        if scores is not None and scope is None:
            chromosome = args[0] if args else kwargs["chromosome"]
            # Retain the object with its score: Python can otherwise reuse IDs.
            scores[id(chromosome)] = (chromosome, result[0] if isinstance(result, tuple) else result)
        return result
    return wrapped


def collect_run_scores(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        callback = kwargs.get("progress_callback", args[6] if len(args) > 6 else None)
        token = observed_scores.set({} if callback is not None else None)
        try:
            return function(*args, **kwargs)
        finally:
            observed_scores.reset(token)
    return wrapped
