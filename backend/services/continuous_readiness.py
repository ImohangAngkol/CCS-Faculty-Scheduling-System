"""Read-only release contract. This module cannot admit a GA worker.

There is deliberately no configuration/provider switch for activating execution.
Complete consumption, authority, versioned workers and resource enforcement must
be implemented and qualified in a later release before this contract can change.
"""
CONTRACT = "ga-continuous-foundation-v1"
STATES = ("IDLE", "STARTING", "RUNNING", "PAUSING", "PAUSED", "RESUMING", "STOPPING", "STOPPED", "COMPLETED", "FAILED", "INTERRUPTED")


def readiness():
    return {
        "schema_version": 1, "contract": CONTRACT, "availability": "BLOCKED", "executable": False,
        "supported_datasets": [], "input_consumption": "NOT_ESTABLISHED", "receipt_capability": "UNVERIFIED_ONLY",
        "institutional_authorization": "NOT_ESTABLISHED", "fixed_generations": "EXISTING_PATH_UNCHANGED",
        "requirements": [
            {"code": "IMMUTABLE_CONSUMPTION_REQUIRED", "message": "The optimizer still consumes cached/mutable models. A fingerprint or U5D observation is not proof of immutable input consumption."},
            {"code": "SCOPED_AUTHORITY_REQUIRED", "message": "A verified run-to-department optimization mandate is not established. Administrator access does not grant Department Chair optimization authority."},
            {"code": "VERSIONED_WORKER_REQUIRED", "message": "No continuous worker or continuous checkpoint format is installed. Existing checkpoints retain their fixed-generation parameters and strict fingerprints."},
            {"code": "RESOURCE_ENFORCEMENT_REQUIRED", "message": "Continuous CPU/memory/time/storage limits and shutdown ownership are not implemented; planned safeguards are not active limits."},
            {"code": "RUN_LOCAL_PERSISTENCE_REQUIRED", "message": "A continuous run needs isolated best-so-far/history persistence without invoking the existing fixed engine's historical Saved Best finalization."},
        ],
        "lifecycle": {"states": list(STATES), "implementation": "CONTRACT_ONLY_NO_CONTINUOUS_WORKER", "commands": "UNAVAILABLE"},
        "safeguards": {"enforcement": "NOT_IMPLEMENTED", "required": ["SCOPED_SINGLE_RUN_OWNERSHIP", "CPU_AND_PRIVATE_MEMORY_BUDGET", "WALL_CLOCK_DEADLINE", "BOUNDED_RETRIES_AND_COOPERATIVE_CANCELLATION", "CHECKPOINT_AND_HISTORY_QUOTAS", "FREE_DISK_CHECK_AND_ATOMIC_WRITES", "BACKEND_SHUTDOWN_JOIN_AND_INTERRUPTION", "EXPLICIT_CHECKPOINT_VERSION_AND_INPUT_REVALIDATION"]},
        "existing_fixed_controls": "Existing backend-confirmed pause/resume/stop and recovery remain separate; no continuous run is implied.",
        "best_so_far": "No continuous chromosome exists. Existing generation best, run best ever and historical Saved Best remain distinct.",
    }
