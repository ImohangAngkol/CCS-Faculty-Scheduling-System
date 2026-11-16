"""Opt-in finite Windows exchange. No installed preservation authority.

No worker can launch from the checkout or without a fresh server-owned gate.
The separate in-process transport is qualification only, never native evidence.
"""
from dataclasses import dataclass, asdict
import json
import math
import os
import queue
import shutil
import threading
import time

from services.prototype_workload import PolicyError, require
from services.ga_worker_contract import fictional_source
from services.ga_input_bundle import canonical as wire
from services.ga_windows_supervisor import Process, Resources, alive

VERSION = 'prototype-frozen-native-exchange-v1'
MAX_MESSAGE = 64*1024*1024
SEGMENT_SECONDS = 60  # Existing finite profile, not a raised lifetime/guard.


@dataclass(frozen=True)
class PreservationFinding:
    """Fresh output of an independently configured SERVER provider, not HTTP."""
    baseline_fingerprint: str
    approval_reference: str
    verified_at: float
    expires_at: float
    current_preservation_qualified: bool
    historical_uncertainty: str


class ExchangeError(PolicyError):
    def __init__(self, primary, cleanup=None):
        super().__init__(primary)
        self.primary_code, self.cleanup_code = primary, cleanup


class InProcessQualification:
    kind = 'OFFLINE_IN_PROCESS_TRANSPORT_NOT_NATIVE'
    native = False

    def validate(self):
        fictional_source()

    def execute(self, request, *, remaining, heartbeat, started, exited, ownership):
        self.validate(); heartbeat()
        started(None, None, self.kind)
        tick = time.monotonic()
        try:
            from services.ga_worker_child import batch
            response = batch(request)  # Real unchanged GA, same private protocol.
            require(time.monotonic()-tick < remaining, 'NATIVE_ORACLE_TIME_BUDGET')
            heartbeat()
            return response
        finally:
            exited(dict(kind=self.kind, pid=None, created_100ns=None, exit_code=None,
                        active_processes=None, exit_verified=False, no_process_created=True))

    def prove_dead(self, pid, created):
        require(pid is None and created is None, 'NATIVE_OFFLINE_PROCESS_ID_REJECTED')
        return True  # No OS process ever existed; not worker termination proof.


class WindowsTransport:
    kind = 'WINDOWS_JOB_NATIVE_PROCESS'
    native = True

    def __init__(self, *, preservation_provider=None, resources=Resources()):
        self.provider, self.resources = preservation_provider, resources
        self.last_cleanup_error = None

    def validate(self):
        fictional_source()
        require(self.provider is not None, 'NATIVE_PRESERVATION_PROVIDER_UNCONFIGURED', 503)
        try:
            finding = self.provider.current()
        except Exception:
            raise PolicyError('NATIVE_PRESERVATION_PROVIDER_UNAVAILABLE',503) from None
        now = time.time()
        require(type(finding) is PreservationFinding and finding.current_preservation_qualified is True
                and type(finding.baseline_fingerprint) is str and len(finding.baseline_fingerprint) == 64
                and all(c in '0123456789abcdef' for c in finding.baseline_fingerprint)
                and type(finding.approval_reference) is str and finding.approval_reference.startswith('FICTIONAL-OPERATOR-')
                and all(type(v) in {float,int} and math.isfinite(v) for v in [finding.verified_at,finding.expires_at])
                and now-30 <= finding.verified_at <= now < finding.expires_at <= now+60,
                'NATIVE_CURRENT_PRESERVATION_NOT_QUALIFIED', 503)
        from services.prototype_scheduling import resource_snapshot
        require(resource_snapshot()['passed'] is True, 'NATIVE_RAM_BELOW_3_GIB', 503)
        require(shutil.disk_usage(fictional_source()).free >= 64*1024*1024, 'NATIVE_DISK_HEADROOM', 503)
        self.resources.validate()
        return finding

    def execute(self, request, *, remaining, heartbeat, started, exited, ownership):
        finding=self.validate()
        require(0 < remaining <= SEGMENT_SECONDS <= 600, 'NATIVE_SEGMENT_TIME_LIMIT')
        from services.ga_supervised_worker import arguments
        backend = fictional_source()
        raw = wire(request)+b'\n'
        require(len(raw) <= MAX_MESSAGE, 'NATIVE_REQUEST_TOO_LARGE')
        allowed = {'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
        env = {k:v for k,v in os.environ.items() if k.upper() in allowed}
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        process, threads, output = None, [], queue.Queue(1)
        tick, primary, cleanup, response = time.monotonic(), None, None, None
        try:
            heartbeat()
            require(set(ownership) == {'store', 'run'} and len(ownership['store']) == 64, 'NATIVE_OWNER_NAMESPACE')
            process = Process(arguments(backend), cwd=backend, env=env,
                store_id=ownership['store'], run_id=ownership['run'], resources=self.resources)
            # A common immutable run namespace also fences multiple adapters.
            # The caller binds the logical run identity in the durable intent.
            started(process.pid, process.identity, self.kind, preservation=asdict(finding))
            def writer():
                try:
                    position = 0
                    while position < len(raw):
                        count = process.stdin.write(raw[position:])
                        if not count:
                            break
                        position += count
                    process.stdin.close()
                except (OSError, ValueError):
                    pass
            def reader():
                try:
                    output.put(process.stdout.readline(MAX_MESSAGE+1), timeout=1)
                except (OSError, ValueError, queue.Full):
                    pass
            threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
            for thread in threads:
                thread.start()
            received = None
            while True:
                require(time.monotonic()-tick < remaining, 'NATIVE_SEGMENT_WALL_TIME')
                heartbeat()  # Fresh authority and original fence; Stop is recorded.
                code = process.poll()
                require(code in (None, 0), 'NATIVE_CHILD_NONZERO_EXIT')
                if received is None:
                    try:
                        received = output.get(timeout=.05)
                    except queue.Empty:
                        continue
                    require(received and len(received) <= MAX_MESSAGE and received.endswith(b'\n'), 'NATIVE_RESPONSE_SIZE_OR_FORMAT')
                if code is not None:
                    break
            response = json.loads(received)
            require(wire(response)+b'\n' == received, 'NATIVE_NONCANONICAL_RESPONSE')
        except BaseException as error:
            primary = getattr(error, 'code', 'NATIVE_EXCHANGE_FAILED')
        finally:
            if process is not None:
                try:
                    observation = process.close()  # Owned handles only; never kill stored PIDs.
                    for thread in threads:
                        thread.join(self.resources.grace_seconds)
                    require(not any(t.is_alive() for t in threads), 'NATIVE_IO_CLEANUP_UNVERIFIED')
                    require(observation is not None and observation['pid'] == process.pid
                            and observation['created_100ns'] == process.identity and observation['active_processes'] == 0
                            and observation['exit_code'] is not None, 'NATIVE_EXIT_NOT_VERIFIED')
                    exited(dict(kind=self.kind, **observation, exit_verified=True,preservation=asdict(finding)))
                except BaseException as error:
                    cleanup = getattr(error, 'code', 'NATIVE_CLEANUP_UNVERIFIED')
                    self.last_cleanup_error = cleanup
                    try:
                        exited(dict(kind=self.kind, pid=process.pid, created_100ns=process.identity,
                            exit_verified=False, cleanup_code=cleanup,preservation=asdict(finding)))
                    except Exception:
                        pass
        if primary or cleanup:
            raise ExchangeError(primary or 'NATIVE_CLEANUP_UNVERIFIED', cleanup)
        return response

    def prove_dead(self, pid, created):
        require(type(pid) is int and pid > 0 and type(created) is int and created > 0, 'NATIVE_PROCESS_IDENTITY_REQUIRED')
        return alive(pid, created) is False
