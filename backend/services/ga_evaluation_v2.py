"""Version-two projection: CURRENT needs trusted context AND immutable run-start provenance."""
import hashlib
from services import ga_result_compatibility as legacy
from services import ga_academic_context as academic, ga_run_provenance as provenance
from services.ga_history_service import HistoryError

CONTRACT = "ga-result-compatibility-v2"


def identity():
    technical = legacy.current_identity()
    verified = academic.verified_context(technical)
    return {**technical,
        "academic_context": verified.context.public() if verified else technical["academic_context"],
        "context_verification": "VERIFIED" if verified else "UNAVAILABLE"}


def classify(index, snapshot, current):
    # Preserve U5A's actual metadata/validation checks. Raw snapshot context alone
    # cannot qualify a result in contract v2.
    base = legacy.classify(index, snapshot, current)
    if base["classification"] == legacy.LEGACY:
        return base
    if base["classification"] == legacy.UNKNOWN and base["reason"] not in {
            "ACADEMIC_CONTEXT_NOT_ESTABLISHED", "ACADEMIC_CONTEXT_NOT_CAPTURED_OR_MISMATCHED"}:
        return base
    if current["context_verification"] != "VERIFIED":
        return {"classification": legacy.UNKNOWN, "reason": "ACADEMIC_CONTEXT_UNAVAILABLE"}
    try:
        record = provenance.read(index["run_id"])
    except HistoryError:
        return {"classification": legacy.UNKNOWN, "reason": "RUN_START_PROVENANCE_INVALID"}
    if record is None:
        return {"classification": legacy.UNKNOWN, "reason": "RUN_START_PROVENANCE_NOT_CAPTURED"}
    captured = academic.AcademicContext.model_validate(record["academic_context"])
    public = captured.public()
    details = {"academic_context": public, "provenance": {
        "contract": provenance.CONTRACT, "run_start_sha256": hashlib.sha256(academic.canonical(record)).hexdigest(),
        "context_sha256": captured.digest, "started_at": record["started_at"]}}
    if public != current["academic_context"]:
        return {"classification": legacy.LEGACY, "reason": "ACADEMIC_CONTEXT_CHANGED", **details}
    technical = record["technical_identity"]
    keys = ("engine_family", "engine_version", "engine_fingerprint", "fitness_policy", "preference_scoring_version",
            "scorer_sha256", "constraint_policy", "input_fingerprint", "result_schema_version")
    if (any(technical.get(key) != current.get(key) for key in keys)
            or record["configuration"] != snapshot["ga_configuration"]
            or record["configuration_fingerprint"] != snapshot["metrics"]["configuration_fingerprint"]
            or snapshot["metrics"]["generation_limit"] != record["configuration"]["generations"]
            or snapshot["metrics"]["population_requested"] != record["configuration"]["population_size"]
            or index.get("started_at") != record["started_at"]):
        return {"classification": legacy.UNKNOWN, "reason": "RUN_START_PROVENANCE_MISMATCH", **details}
    # An ephemeral projection copy supplies the independently checked context;
    # never write this field into an original history snapshot or checkpoint.
    checked = legacy.classify(index, {**snapshot, "academic_context": public}, current)
    return {**checked, **details}


def evaluation():
    result = legacy.evaluation(identity_reader=identity, classifier=classify)
    result.update(schema_version=2, contract=CONTRACT,
                  comparison_basis="Same engine, scoring policy, inputs, verified academic context and exact run-start configuration only.")
    for row in result["runs"]:
        if row["classification"] == legacy.CURRENT:
            row["classification"] = "CURRENT"
    # best references the same row within the shared projection, not a new score.
    return result
