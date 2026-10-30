"""Repeatable, non-publishing GA V2 Python smoke benchmark.

Place this file at backend/ga_v2_fictional_python_baseline.py and run from the
backend directory. It reuses the deliberately tiny, fictional D10 test catalog.

It does NOT call the API, access PostgreSQL, change the original GA, write GA
checkpoints, or activate institutional authority. The imported GA still reads
its configured input fingerprints and preference settings in the usual manner.

This is a correctness/performance *smoke baseline*, not a representative
institutional-scale performance experiment or a Python-versus-C++ result.
"""

import argparse
from contextlib import redirect_stdout
import cProfile
import gc
import io
import json
import os
import pstats
import random
import statistics
import sys
import time
import tracemalloc

from schemas.ga_constrained import Parameters
from services import ga_v2_engine as engine
from tests.d10.support import preferences, templates
from tests.d10.test_v2_engine import snapshot_for


def measure_one(seed: int, parameters: Parameters, *, profile: bool = False,
                memory: bool = False):
    """Execute one fresh fictional engine run, without persistence callbacks."""
    values = templates(compact=True)
    snapshot = snapshot_for(values)
    frozen_preferences = preferences()
    checkpoints = []
    last_summary = {}

    def boundary(state):
        nonlocal last_summary
        generation = state["generation"]
        history = state["history"]
        assert len(history) == generation + 1
        entry = history[-1]
        assert entry["generation"] == generation
        checkpoints.append({
            "generation": generation,
            "generation_best_fitness": float(entry["generation_best_fitness"]),
            "best_ever_fitness": float(entry["best_ever_fitness"]),
        })

        if generation == parameters.generations:
            loads = {str(member.code): 0 for member in values[1]}
            targets = {str(member.code): member.required_teaching_load
                       for member in values[1]}
            for subject in state["best"]:
                member = subject.assigned_faculty
                if member is not None and str(member.code) in loads:
                    loads[str(member.code)] += subject.credit_units
            last_summary = {
                "best_fitness": float(state["best_fitness"]),
                "zero_assignment_faculty": sum(load == 0 for load in loads.values()),
                "total_offered_units": sum(subject.credit_units for subject in values[0]),
                "total_target_units": sum(targets.values()),
                "underload_units": sum(max(0, targets[code] - load)
                                       for code, load in loads.items()),
                "overload_units": sum(max(0, load - targets[code])
                                      for code, load in loads.items()),
                "loads_by_fictional_faculty": loads,
                "targets_by_fictional_faculty": targets,
                "diagnostics": dict(state["diagnostics"]),
            }
        return None

    prior_random_state = random.getstate()
    profiler = cProfile.Profile() if profile else None
    profile_summary = None
    peak_bytes = None
    try:
        random.seed(seed)
        gc.collect()
        if memory:
            tracemalloc.start()
        begin = time.perf_counter()
        # The original scheduling helper prints successful assignments.
        # Suppress these for readable, repeatable CLI output.
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with redirect_stdout(sink):
                if profiler:
                    profiler.enable()
                try:
                    outcome = engine.run(
                        values, snapshot, parameters, frozen_preferences, boundary
                    )
                finally:
                    if profiler:
                        profiler.disable()
        elapsed = time.perf_counter() - begin
        if memory:
            _, peak_bytes = tracemalloc.get_traced_memory()
        if profiler:
            view = io.StringIO()
            pstats.Stats(profiler, stream=view).strip_dirs().sort_stats(
                "cumulative"
            ).print_stats(20)
            profile_summary = view.getvalue()
    finally:
        if memory and tracemalloc.is_tracing():
            tracemalloc.stop()
        random.setstate(prior_random_state)

    if outcome != "complete":
        raise RuntimeError(f"Unexpected GA result: {outcome!r}")
    if len(checkpoints) != parameters.generations + 1 or not last_summary:
        raise AssertionError("Missing generation history or final result")
    for first, second in zip(checkpoints, checkpoints[1:]):
        if second["best_ever_fitness"] > first["best_ever_fitness"] + 1e-9:
            raise AssertionError("Best-ever fitness worsened during the run")
    if abs(last_summary["best_fitness"] - checkpoints[-1]["best_ever_fitness"]) > 1e-9:
        raise AssertionError("Final best fitness disagrees with history")

    return {
        "seed": seed,
        "seconds": round(elapsed, 6),
        "peak_python_allocated_mib": (
            round(peak_bytes / (1024 * 1024), 3) if peak_bytes is not None else None
        ),
        "history": checkpoints,
        **last_summary,
    }, profile_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=714)
    parser.add_argument("--population", type=int, default=2)
    parser.add_argument("--generations", type=int, default=2)
    parser.add_argument("--profile", action="store_true",
                        help="Profile one EXTRA run; profile time is excluded from timings")
    parser.add_argument("--memory", action="store_true",
                        help="Measure Python allocations on one EXTRA run")
    args = parser.parse_args()
    if not 1 <= args.trials <= 30:
        parser.error("--trials must be between 1 and 30")

    parameters = Parameters(
        population_size=args.population,
        generations=args.generations,
        fresh_chromosomes=0,
        mutation_attempts=1,
        crossover_attempts=1,
        max_restarts=3,
        candidate_attempts=3,
    )

    # Warm-up excludes import and first-run initialization from timed trials.
    measure_one(args.seed, parameters)
    trials = [measure_one(args.seed + index, parameters)[0]
              for index in range(args.trials)]
    times = [item["seconds"] for item in trials]
    result = {
        "label": "GA V2 fictional D10 tiny-fixture Python smoke baseline",
        "scope": "engine search only; no API, DB, checkpoint I/O, or C++",
        "fictional_subjects": 2,
        "fictional_faculty": 2,
        "fictional_rooms": 1,
        "parameters": parameters.model_dump(),
        "python_version": sys.version.split()[0],
        "trial_count": args.trials,
        "mean_seconds": round(statistics.mean(times), 6),
        "median_seconds": round(statistics.median(times), 6),
        "min_seconds": min(times),
        "max_seconds": max(times),
        "trials": trials,
    }
    if args.memory:
        extra, _ = measure_one(args.seed, parameters, memory=True)
        result["separate_instrumented_peak_python_allocated_mib"] = (
            extra["peak_python_allocated_mib"]
        )
    print(json.dumps(result, indent=2))
    if args.profile:
        _, report = measure_one(args.seed, parameters, profile=True)
        print("\nTOP 20 CUMULATIVE-TIME CALLS (PROFILED SEPARATE RUN)", file=sys.stderr)
        print(report, file=sys.stderr)


if __name__ == "__main__":
    main()
