"""Pure research telemetry-age classification, never a worker-health claim."""
import math

VERSION='research-freshness-v1'
THRESHOLD_SECONDS=30
CLOCK_SKEW_SECONDS=2
TERMINAL={'COMPLETED','STOPPED','FAILED','RESOURCE_LIMITED'}


def timestamp(value):
    return type(value) in (int,float) and math.isfinite(value) and 0<=value<=8640000000000


def evaluate(*,now,times,state,terminal_confirmed=False,terminal_at=None):
    """Times are signed ledger source times in sequence order, not GET times.

    Equal timestamps are permitted. A duplicate cannot renew freshness. Clock
    reversal is UNKNOWN; a source at most two seconds ahead retains signed age.
    Terminal is established independently from durable lifecycle/cleanup state.
    """
    last=times[-1] if times and timestamp(times[-1]) else None
    age=now-last if timestamp(now) and last is not None else None
    status='UNKNOWN';reason='MISSING_TIMESTAMP'
    if not timestamp(now):reason='SERVER_CLOCK_UNVERIFIABLE'
    elif any(t is not None and not timestamp(t) for t in times):reason='INVALID_TIMESTAMP'
    elif not times or any(t is None for t in times):reason='MISSING_TIMESTAMP'
    elif any(t>now+CLOCK_SKEW_SECONDS for t in times):reason='FUTURE_OBSERVATION'
    elif any(b<a for a,b in zip(times,times[1:])):reason='OBSERVATION_TIME_REVERSED'
    else:
        status='FRESH' if age<=THRESHOLD_SECONDS else 'STALE'
        reason='RECENT_DURABLE_OBSERVATION' if status=='FRESH' else 'OBSERVATION_AGE_EXCEEDED'
        if age<0:reason='WITHIN_CLOCK_SKEW_TOLERANCE'
    result=status
    if state in {'INTERRUPTED','RECOVERY_REQUIRED'}:result='UNKNOWN';reason='OWNERSHIP_OR_ORPHAN_UNCERTAIN'
    elif state in TERMINAL:
        if terminal_confirmed and timestamp(terminal_at) and timestamp(now) and terminal_at<=now+CLOCK_SKEW_SECONDS:
            result='TERMINAL';reason='DURABLE_TERMINAL_OUTCOME'
        else:result='UNKNOWN';reason='TERMINAL_OUTCOME_NOT_INDEPENDENTLY_CONFIRMED'
    return dict(contract=VERSION,state=result,telemetry_state=status,reason=reason,
        server_verified_at=now if timestamp(now) else None,last_verified_observation_at=last,
        age_seconds=age,threshold_seconds=THRESHOLD_SECONDS,tolerated_clock_skew_seconds=CLOCK_SKEW_SECONDS,
        terminal_confirmed=bool(result=='TERMINAL'),terminal_recorded_at=terminal_at if result=='TERMINAL' else None,
        worker_health='NOT_ESTABLISHED_BY_OBSERVATION_HTTP',timestamp_source='SIGNED_DURABLE_RESEARCH_LEDGER')
