"""Private, pinned fictional service bootstrap. Not authority or a native adapter.

The pin must be retained by a trusted server/operator outside restored stores.
Neither this local pin nor the local tip witness authenticates the entire host.
"""
from dataclasses import dataclass
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path

from services.prototype_workload import Store, WorkloadService, Scope, canonical, digest, require
from services.prototype_inputs import Inputs
from services.prototype_cycle import Cycle
from services.prototype_tip_witness import TipWitness

VERSION = 'fictional-cold-bootstrap-v1'
MAX_BYTES = 8*1024*1024


@dataclass(frozen=True)
class Pin:
    root: str
    storage_binding: str
    document_sha256: str
    witness_key_fingerprint: str
    cycle_binding: str
    run_id: str


def capture(cycle, principal, run):
    require(type(cycle) is Cycle, 'BOOTSTRAP_CYCLE_REQUIRED')
    cycle.inspect(principal, run)  # Current owner, authority and witness.
    actor = cycle.authorize(principal, 'run.recover').actor_id
    require(cycle._owner(run) == actor, 'BOOTSTRAP_OWNER_REQUIRED', 403)
    workload = cycle.inputs.workload
    binding = digest(dict(version=VERSION, cycle=cycle.binding, run=run))
    store = Store.create(binding)
    document = dict(version=VERSION, run_id=run, binding=binding,
        scope=workload.scope.model_dump(), base_run_id=workload.bundle.run_id,
        base_fingerprint=workload.bundle.fingerprint,
        base_bundle=workload.bundle._raw.decode('utf-8'),
        policy_root=str(workload.store.root), policy_binding=workload.binding,
        inputs_root=str(cycle.inputs.storage.root), inputs_binding=cycle.inputs.binding,
        cycle_root=str(cycle.storage.root), cycle_binding=cycle.binding,
        witness_root=str(cycle.witness.storage.root), witness_binding=cycle.witness.binding,
        owner=actor, implementation={
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ['prototype_recovery_bootstrap.py', 'prototype_cycle.py', 'prototype_inputs.py',
                         'prototype_workload.py', 'prototype_tip_witness.py']})
    raw = canonical(document).encode()
    require(len(raw) <= MAX_BYTES, 'BOOTSTRAP_SIZE_LIMIT')
    temporary, final = store.root/'new-bootstrap.tmp', store.root/'bootstrap.json'
    with temporary.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    require(not final.exists(), 'BOOTSTRAP_ALREADY_EXISTS')
    os.replace(temporary, final)  # New owned namespace only, never old records.
    return Pin(str(store.root), binding, hashlib.sha256(raw).hexdigest(),
               cycle.witness.key_fingerprint, cycle.binding, run)


def reopen(pin, principal, *, workload_authority=None, input_directory=None,
           workflow_directory=None, offline_qualification=False, clock=None):
    """No authority is reconstructed from stored actors/roles or bundle labels.

    All three fresh server providers and the externally retained pin are needed.
    Defaults cannot execute. Exact old engine/checkpoint identities stay intact.
    """
    require(type(pin) is Pin, 'BOOTSTRAP_EXTERNAL_PIN_REQUIRED')
    require(workload_authority is not None and input_directory is not None and workflow_directory is not None,
            'BOOTSTRAP_FRESH_AUTHORITY_PROVIDERS_REQUIRED', 503)
    store = Store(pin.root, pin.storage_binding)
    path = store.root/'bootstrap.json'
    store.check()
    require(path.is_file() and not path.is_symlink() and not path.is_junction()
            and path.stat().st_size <= MAX_BYTES, 'BOOTSTRAP_FILE_INVALID')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin.document_sha256, 'BOOTSTRAP_PIN_MISMATCH')
    doc = json.loads(raw)
    require(doc['version'] == VERSION and doc['binding'] == pin.storage_binding
            and doc['cycle_binding'] == pin.cycle_binding and doc['run_id'] == pin.run_id,
            'BOOTSTRAP_CONTEXT_MISMATCH')
    for name, expected in doc['implementation'].items():
        require(name in {'prototype_recovery_bootstrap.py', 'prototype_cycle.py', 'prototype_inputs.py',
                        'prototype_workload.py', 'prototype_tip_witness.py'}
                and hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() == expected,
                'BOOTSTRAP_IMPLEMENTATION_CHANGED')
    require(len(doc['implementation']) == 5, 'BOOTSTRAP_IMPLEMENTATION_SET')
    from services.ga_input_bundle import InputBundle
    bundle = InputBundle.from_bytes(doc['base_bundle'].encode(), doc['base_run_id'], doc['base_fingerprint'])
    workload = WorkloadService(Scope.model_validate(doc['scope']), bundle, workload_authority,
                               Store(doc['policy_root'], doc['policy_binding']))
    # A provider must independently authorize the actual caller and context.
    workload.authorize(principal, 'read')
    kwargs = {} if clock is None else dict(clock=clock)
    inputs = Inputs(workload, input_directory, root=doc['inputs_root'], **kwargs)
    require(inputs.binding == doc['inputs_binding'], 'BOOTSTRAP_INPUT_CONTEXT_CHANGED')
    witness = TipWitness(root=doc['witness_root'], key_fingerprint=pin.witness_key_fingerprint)
    require(witness.binding == doc['witness_binding'], 'BOOTSTRAP_WITNESS_IDENTITY_CHANGED')
    cycle = Cycle(inputs, workflow_directory, witness, root=doc['cycle_root'],
                  offline_qualification=offline_qualification, **kwargs)
    require(cycle.binding == pin.cycle_binding, 'BOOTSTRAP_CYCLE_CHANGED')
    view = cycle.inspect(principal, pin.run_id)  # Owner, bundle, source and live tip check.
    frozen = inputs.prepared(principal, view['preparation_id'], internal_bundle=True)
    with closing(cycle.db()) as db:
        admission, _row, _control, _segments = cycle._read(db, pin.run_id, doc['owner'])
        require(frozen.fingerprint == admission['bundle_fingerprint'], 'BOOTSTRAP_FROZEN_INPUT_MISMATCH')
    return cycle
