"""Read-only technical classification of existing V1 history; never admits a GA seed."""
import hashlib
import math
import re
from uuid import UUID

CONTRACT = "ga-result-compatibility-v1"
CURRENT = "CURRENT_COMPATIBLE"
LEGACY = "LEGACY_INCOMPATIBLE"
UNKNOWN = "UNKNOWN_COMPATIBILITY"
MAX_RUNS = 200


def digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def current_identity():
    # These existing readers hash source/input bytes. They do not restore, score or write.
    from services import ga_checkpoint_service as checkpoints
    from services.ga_progress_service import input_fingerprint
    scorer = checkpoints.ROOT / "genetic_algorithm/operators/FitnessFunction.py"
    return {"engine_family": "V1", "engine_version": checkpoints.ENGINE_VERSION,
            "engine_fingerprint": checkpoints.engine_fingerprint(),
            "fitness_policy": "preference-policy-2", "preference_scoring_version": 2,
            "scorer_sha256": hashlib.sha256(scorer.read_bytes()).hexdigest(),
            "constraint_policy": "v1-source-bound-publication-gate",
            "input_fingerprint": input_fingerprint(), "result_schema_version": 1,
            "academic_context": {"kind": "legacy-input-file-set", "academic_year": None, "term": None}}


def classify(index, snapshot, current):
    """Only existing server-read, integrity-checked records may enter this projection.

    CURRENT is technical same-release/input compatibility, not academic approval,
    signature authenticity, current feasibility or permission to resume/use a seed.
    """
    def result(status, reason):
        return {"classification": status, "reason": reason}
    try:
        run = index["run_id"]
        if str(UUID(run)) != run or snapshot["run_id"] != run:
            return result(UNKNOWN, "RUN_IDENTITY_INVALID")
        if index["schema_version"] != 1 or snapshot["schema_version"] != 1:
            return result(UNKNOWN, "RESULT_SCHEMA_UNSUPPORTED")
        engine, inputs = index["engine_fingerprint"], index["input_fingerprint"]
        if not digest(engine) or not digest(inputs):
            return result(UNKNOWN, "MISSING_IMPLEMENTATION_IDENTITY")
        rows = index["generations"]
        if not rows or len(rows) > 10001:
            return result(UNKNOWN, "NO_BOUNDED_VALIDATED_OBSERVATIONS")
        latest = rows[-1]
        config = latest["metrics"]["configuration_fingerprint"]
        if not digest(config):
            return result(UNKNOWN, "CONFIGURATION_IDENTITY_MISSING")
        previous, previous_best = -1, math.inf
        for row in rows:
            metric = row["metrics"]
            generation, penalty = row["generation"], metric["best_ever_fitness"]
            if (type(generation) is not int or generation <= previous
                    or metric["generation"] != generation or metric.get("metrics_comparable") is not True
                    or metric["validation_status"] != "passed"
                    or metric["input_fingerprint"] != inputs or metric["configuration_fingerprint"] != config
                    or type(penalty) not in (int, float) or not math.isfinite(penalty) or penalty > previous_best):
                return result(UNKNOWN, "OBSERVATION_PROVENANCE_INCONSISTENT")
            previous, previous_best = generation, penalty
        if (snapshot["engine_fingerprint"] != engine or snapshot["generation"] != latest["generation"]
                or snapshot["metrics"] != latest["metrics"]
                or not index["configuration"]
                or any(snapshot["ga_configuration"].get(key) != value for key, value in index["configuration"].items())
                or snapshot["validation"]["status"] != "passed"):
            return result(UNKNOWN, "SNAPSHOT_PROVENANCE_INCONSISTENT")
        context = snapshot.get("reporting_context")
        if not isinstance(context, dict) or context.get("version") != 1:
            return result(UNKNOWN, "FITNESS_POLICY_NOT_CAPTURED")
        policy = context.get("preference_scoring_version")
        if type(policy) is not int or policy not in (1, 2):
            return result(UNKNOWN, "FITNESS_POLICY_UNSUPPORTED")
        if (context.get("engine_fingerprint") != engine or context.get("input_fingerprint") != inputs
                or not digest(context.get("scorer_sha256"))
                or not isinstance(context.get("settings"), dict)
                or context["settings"] != snapshot["fitness_configuration"]):
            return result(UNKNOWN, "SCORING_CONTEXT_INCONSISTENT")
        selected = snapshot["best_ever"]
        if (selected["chromosome_id"] != latest["best_ever_id"] or not digest(selected["chromosome_id"])
                or selected["payload"]["best_fitness"] != previous_best):
            return result(UNKNOWN, "CANDIDATE_PROVENANCE_INCONSISTENT")
        # A known explicit difference proves incompatibility for this comparison,
        # not the chronological age or institutional validity of the source.
        if policy != current["preference_scoring_version"]:
            return result(LEGACY, "FITNESS_POLICY_CHANGED")
        if engine != current["engine_fingerprint"] or context["scorer_sha256"] != current["scorer_sha256"]:
            return result(LEGACY, "ENGINE_OR_SCORER_CHANGED")
        if inputs != current["input_fingerprint"]:
            return result(LEGACY, "INPUT_CONTEXT_CHANGED")
        academic = current.get("academic_context")
        if (not isinstance(academic, dict) or not academic.get("academic_year") or not academic.get("term")
                or academic.get("kind") != "verified-recorded-context"):
            return result(UNKNOWN, "ACADEMIC_CONTEXT_NOT_ESTABLISHED")
        if snapshot.get("academic_context") != academic:
            return result(UNKNOWN, "ACADEMIC_CONTEXT_NOT_CAPTURED_OR_MISMATCHED")
        return result(CURRENT, "SAME_RELEASE_POLICY_AND_INPUTS")
    except (KeyError, TypeError, ValueError, AttributeError):
        return result(UNKNOWN, "PROVENANCE_MISSING_OR_MALFORMED")


def evaluation():
    from services import ga_history_service as history
    current = current_identity()
    runs, issues, complete, scanned = [], [], True, 0
    root = history.SNAPSHOTS_DIR
    if root.exists():
        # Never follow an alias outside the configured history store.
        for path in root.iterdir():
            if scanned >= MAX_RUNS:
                complete = False
                issues.append("RUN_SCAN_LIMIT_REACHED")
                break
            if not path.is_dir():
                continue
            scanned += 1
            run_id = None
            try:
                if path.is_symlink() or path.resolve().parent != root.resolve():
                    raise ValueError()
                run_id = str(UUID(path.name))
                if run_id != path.name:
                    raise ValueError()
                index = history.manifest(run_id)
                latest = index["generations"][-1] if index["generations"] else None
                snapshot = history.get_generation(run_id, latest["generation"]) if latest else {}
                finding = classify(index, snapshot, current)
                current_run = finding["classification"] == CURRENT
                runs.append({"run_id": run_id, "state": index["state"], **finding,
                    "generation": latest["generation"] if latest else None,
                    "configuration_fingerprint": latest["metrics"]["configuration_fingerprint"] if latest else None,
                    "fitness": snapshot["metrics"]["best_ever_fitness"] if current_run else None,
                    "chromosome_id": snapshot["best_ever"]["chromosome_id"] if current_run else None})
            except (history.HistoryError, OSError, ValueError, KeyError, TypeError):
                # Keep unreadable records in their original store; never export raw names/paths.
                complete = False
                issues.append("ARCHIVED_RECORD_UNREADABLE")
                if run_id is not None:
                    runs.append({"run_id": run_id, "state": "UNKNOWN", "classification": UNKNOWN,
                        "reason": "ARCHIVED_RECORD_UNREADABLE", "generation": None,
                        "configuration_fingerprint": None, "fitness": None, "chromosome_id": None})
    # Detect input/source drift during this read instead of publishing a mixed projection.
    if current_identity() != current:
        raise history.HistoryError("Implementation or inputs changed during review; retry.", "GA_EVALUATION_CHANGED", 409)
    eligible = [row for row in runs if row["classification"] == CURRENT]
    candidates = [row for row in eligible if row["state"] == "COMPLETED"]
    configurations = {row["configuration_fingerprint"] for row in candidates}
    if len(configurations) > 1:
        issues.append("INCOMPARABLE_CONFIGURATIONS")
    best = min(candidates, key=lambda row: (row["fitness"], row["run_id"])) if candidates and complete and len(configurations) == 1 else None
    return {"schema_version": 1, "contract": CONTRACT, "current_identity": current,
            "coverage_complete": complete, "current_runs": len(eligible) if complete else None,
            "best": best, "runs": sorted(runs, key=lambda row: row["run_id"]), "issues": sorted(set(issues)),
            "saved_chromosome": {"classification": UNKNOWN, "baseline_eligible": False,
                                 "reason": "SAVED_BEST_HAS_NO_CAPTURED_PRODUCER_IDENTITY"},
            "comparison_basis": "Same V1 engine, scoring policy, full inputs, verified recorded academic context and configuration fingerprint only.",
            "institutional_authorization": "NOT_ESTABLISHED"}
