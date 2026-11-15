"""Fictional input preparation only. No optimizer, file settings or publication.

Existing preferences and penalty coefficients enter the existing captured-bundle
contract. Nothing here supplies a production authority or authorizes execution.
"""
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field
from schemas.faculty_preference import FacultyPreferenceUpdate
from services.prototype_workload import Store, WorkloadService, canonical, digest, require

VERSION = 'fictional-input-preparation-v1'
PENALTIES = frozenset({'subject_penalty', 'time_penalty', 'day_penalty', 'preparation_penalty',
    'load_balance_penalty', 'daily_load_penalty', 'gap_penalty', 'lecture_lab_penalty',
    'underload_penalty', 'overload_penalty', 'heavy_overload_penalty'})
FLAGS = dict(prototype_only=True, production_admission='BLOCKED', institutional_saved_best_promotion=False,
             institutional_publication=False, continuous_optimization='DISABLED', active_restore=False,
             seven_day='NO_GO', optimizer_executed=False)


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    request_id: str
    expected_revision: int = Field(ge=0)


class Weights(Command):
    penalties: dict[str, int]


class Preference(Command):
    preference: FacultyPreferenceUpdate


class Freeze(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    request_id: str
    minimum_revision: int = Field(ge=0)
    minimum_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    weights_revision: int = Field(ge=0)
    weights_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    preferences_digest: str = Field(pattern=r'^[a-f0-9]{64}$')


@dataclass(frozen=True)
class Grant:
    """Server directory output, never accepted from an HTTP request."""
    actor_id: str
    scope_digest: str
    action: str
    faculty_code: int | None
    capacity: str
    reference: str
    expires_at: float


class Inputs:
    def __init__(self, workload, directory=None, *, root=None, clock=time.time):
        require(type(workload) is WorkloadService, 'INPUTS_CAPTURED_WORKLOAD_REQUIRED')
        self.workload, self.directory, self.clock = workload, directory, clock
        self.scope_digest = digest(workload.scope.model_dump())
        self.binding = digest(dict(contract=VERSION, scope=self.scope_digest, base_bundle=workload.bundle.fingerprint,
                                   implementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        self.storage = Store.create(self.binding) if root is None else Store(root, self.binding)
        self.path = self.storage.root/'inputs.sqlite3'
        if root is None:
            with self.path.open('xb'):
                pass
            with closing(self.connection()) as db, db:
                db.executescript('''
CREATE TABLE metadata(binding TEXT NOT NULL);
CREATE TABLE revisions(stream TEXT NOT NULL,version INTEGER NOT NULL,actor TEXT NOT NULL,nonce TEXT NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,PRIMARY KEY(stream,version),UNIQUE(actor,nonce));
CREATE TABLE frozen(id TEXT PRIMARY KEY,actor TEXT NOT NULL,nonce TEXT NOT NULL,raw TEXT NOT NULL,hash TEXT NOT NULL,bundle BLOB NOT NULL,UNIQUE(actor,nonce));
CREATE TRIGGER immutable_revision_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER immutable_revision_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER immutable_frozen_update BEFORE UPDATE ON frozen BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER immutable_frozen_delete BEFORE DELETE ON frozen BEGIN SELECT RAISE(ABORT,'immutable'); END;
''')
                db.execute('INSERT INTO metadata VALUES(?)', (self.binding,))
        with closing(self.connection()) as db:
            require(db.execute('SELECT binding FROM metadata').fetchall() == [(self.binding,)], 'INPUTS_STORAGE_BINDING')
        self.data = workload.bundle.materialize(workload.bundle.run_id)
        self.faculty, self.subjects = workload.catalog()
        from genetic_algorithm.operators.FitnessFunction import _legacy_preferences_to_map
        self.priorities = _legacy_preferences_to_map(self.data['legacy_preferences'])

    def connection(self):
        self.storage.check()
        require(self.path.is_file() and not self.path.is_symlink() and not self.path.is_junction()
                and self.path.stat().st_size < 128*1024*1024, 'INPUTS_STORAGE_INVALID')
        db = sqlite3.connect(self.path.as_uri()+'?mode=rw', uri=True, timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        return db

    def authorize(self, principal, action, code=None):
        actor = getattr(principal, 'user_id', None)
        try:
            require(type(actor) is str and str(UUID(actor)) == actor, 'INPUTS_PRINCIPAL_REQUIRED', 403)
            grant = self.directory.grant(actor, self.workload.scope, action, code) if self.directory else None
            require(type(grant) is Grant and grant.actor_id == actor and grant.scope_digest == self.scope_digest
                and grant.action == action and grant.faculty_code == code and grant.reference.startswith('FICTIONAL-')
                and self.clock() < grant.expires_at <= self.clock()+300, 'INPUTS_SCOPED_GRANT_REQUIRED', 403)
            allowed = {'weights.approve': {'DEPARTMENT_CHAIR'}, 'preferences.write': {'FACULTY_SELF'},
                       'preferences.read': {'FACULTY_SELF'}, 'prepare': {'SCHEDULER'}, 'prepared.read': {'SCHEDULER'},
                       'weights.read': {'DEPARTMENT_CHAIR', 'FACULTY_SELF', 'SCHEDULER'}}
            require(grant.capacity in allowed[action], 'INPUTS_CAPACITY_REQUIRED', 403)
            return grant
        except (ValueError, TypeError, AttributeError, KeyError):
            require(False, 'INPUTS_SCOPED_GRANT_REQUIRED', 403)

    def _recheck(self, principal, grant):
        fresh = self.authorize(principal, grant.action, grant.faculty_code)
        require((fresh.capacity, fresh.reference) == (grant.capacity, grant.reference), 'INPUTS_AUTHORITY_CHANGED')

    def _head(self, db, stream, default):
        tip = dict(revision=0, body=default, digest=digest(dict(binding=self.binding, stream=stream, baseline=default)),
                   approval='BASELINE_UNCHANGED_NO_NEW_APPROVAL')
        for version, raw, identity in db.execute('SELECT version,raw,hash FROM revisions WHERE stream=? ORDER BY version', (stream,)):
            doc = json.loads(raw)
            require(doc['binding'] == self.binding and doc['stream'] == stream and doc['revision'] == version == tip['revision']+1
                    and doc['parent'] == tip['digest'] and digest(doc) == identity, 'INPUTS_REVISION_CORRUPT')
            tip = dict(revision=version, body=doc['body'], digest=identity, actor=doc['actor'],
                       at=doc['at'], approval=doc['approval'])
        return tip

    def _write(self, principal, grant, command, stream, default, body, approval):
        require(str(UUID(command.request_id)) == command.request_id, 'INPUTS_REQUEST_ID_INVALID', 422)
        command_hash = digest(dict(stream=stream, command=command.model_dump()))
        with closing(self.connection()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                current = self._head(db, stream, default)
                old = db.execute('SELECT raw,hash FROM revisions WHERE actor=? AND nonce=?', (grant.actor_id, command.request_id)).fetchone()
                if old:
                    doc = json.loads(old[0])
                    require(digest(doc) == old[1] and doc['command_hash'] == command_hash, 'INPUTS_NONCE_REUSE_MISMATCH')
                    return dict(revision=doc['revision'], body=doc['body'], digest=old[1], actor=doc['actor'], at=doc['at'], approval=doc['approval'])
                require(current['revision'] == command.expected_revision, 'INPUTS_REVISION_STALE')
                require(current['revision'] < 100 and db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0] < 1000, 'INPUTS_REVISION_LIMIT')
                doc = dict(binding=self.binding, stream=stream, revision=current['revision']+1, actor=grant.actor_id,
                           command_hash=command_hash, parent=current['digest'], body=body, approval=approval,
                           at=datetime.now(timezone.utc).isoformat())
                raw = canonical(doc)
                require(len(raw.encode()) <= 64*1024, 'INPUTS_DOCUMENT_TOO_LARGE', 413)
                db.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?)', (stream, doc['revision'], grant.actor_id, command.request_id, raw, digest(doc)))
                self._recheck(principal, grant)
                db.commit()
                return self._head(db, stream, default)
            except Exception:
                db.rollback()
                raise

    def weights(self, principal):
        self.authorize(principal, 'weights.read')
        with closing(self.connection()) as db:
            tip = self._head(db, 'weights', self.data['scoring_context']['settings'])
        from genetic_algorithm.models.ga_setting import GASetting
        effective = GASetting.from_dict(tip['body']).to_dict()
        return dict(contract=VERSION, **FLAGS, scope=self.workload.scope.model_dump(), policy=tip,
                    configurable_penalties={k: effective[k] for k in sorted(PENALTIES)},
                    formula='UNCHANGED_ORIGINAL_PREFERENCE_SCORING_V2', non_penalty_settings_editable=False)

    def approve_weights(self, principal, command):
        require(type(command) is Weights, 'INPUTS_COMMAND_INVALID', 422)
        grant = self.authorize(principal, 'weights.approve')
        require(bool(command.penalties) and set(command.penalties) <= PENALTIES
                and all(type(v) is int and 0 <= v <= 100000 for v in command.penalties.values()), 'INPUTS_PENALTY_INVALID', 422)
        with closing(self.connection()) as db:
            current = self._head(db, 'weights', self.data['scoring_context']['settings'])
        body = current['body'] | command.penalties
        return self._write(principal, grant, command, 'weights', self.data['scoring_context']['settings'], body,
                           'FICTIONAL_DEPARTMENT_CHAIR_APPROVED_COEFFICIENTS_NOT_INSTITUTIONAL')

    def _default_preference(self, code):
        require(code in self.faculty, 'INPUTS_FACULTY_UNKNOWN', 404)
        return self.data['scoring_context']['preferences'].get(code)

    def preference(self, principal, code):
        self.authorize(principal, 'preferences.read', code)
        with closing(self.connection()) as db:
            tip = self._head(db, 'preference:'+str(code), self._default_preference(code))
        return dict(contract=VERSION, **FLAGS, faculty_code=code, scope=self.workload.scope.model_dump(), preference=tip)

    def save_preference(self, principal, code, command):
        require(type(command) is Preference, 'INPUTS_COMMAND_INVALID', 422)
        grant = self.authorize(principal, 'preferences.write', code)
        default = self._default_preference(code)
        value = command.preference
        priority = (default or self.priorities.get(code, {})).get('faculty_priority', 1)
        require(value.faculty_priority == priority, 'INPUTS_FACULTY_PRIORITY_NOT_EDITABLE', 422)
        require(not value.preferred_schedule_blocks, 'INPUTS_EXACT_MEETING_BLOCK_EDITOR_NOT_QUALIFIED', 422)
        eligible = self.faculty[code]['eligible_subjects'] & {str(s.number).strip().upper() for s in self.subjects}
        require(len(value.preferred_subjects) == len(set(value.preferred_subjects))
                and set(value.preferred_subjects) <= eligible, 'INPUTS_PREFERENCE_SUBJECT_NOT_ELIGIBLE', 422)
        from services.preference_validation_service import DAYS, _time_range
        require(len(value.preferred_days) == len(set(value.preferred_days)) and set(value.preferred_days) <= DAYS,
                'INPUTS_PREFERENCE_DAY_INVALID', 422)
        if value.preferred_start_time is not None or value.preferred_end_time is not None:
            try:
                _time_range(value.preferred_start_time, value.preferred_end_time)
            except ValueError:
                require(False, 'INPUTS_PREFERENCE_TIME_INVALID', 422)
        return self._write(principal, grant, command, 'preference:'+str(code), default,
                           value.model_dump() | {'faculty_code': code}, 'FACULTY_SELF_SUBMITTED_NOT_ACADEMIC_APPROVAL')

    def _preference_heads(self, db):
        return {str(code): self._head(db, 'preference:'+str(code), self._default_preference(code)) for code in self.faculty}

    def selection(self, principal):
        self.authorize(principal, 'prepare')
        self.workload.authorize(principal, 'read')
        with closing(self.workload.store.connection()) as minimum_db, closing(self.connection()) as db:
            minima = self.workload.store.read(minimum_db)
            weights = self._head(db, 'weights', self.data['scoring_context']['settings'])
            preferences = self._preference_heads(db)
        return dict(contract=VERSION, **FLAGS, scope=self.workload.scope.model_dump(),
            minimum_revision=minima['revision'], minimum_digest=minima['digest'],
            weights_revision=weights['revision'], weights_digest=weights['digest'], preferences_digest=digest(preferences),
            base_bundle_fingerprint=self.workload.bundle.fingerprint)

    def prepare(self, principal, command):
        require(type(command) is Freeze, 'INPUTS_COMMAND_INVALID', 422)
        grant = self.authorize(principal, 'prepare')
        self.workload.authorize(principal, 'read')
        require(str(UUID(command.request_id)) == command.request_id, 'INPUTS_REQUEST_ID_INVALID', 422)
        command_hash = digest(command.model_dump())
        with closing(self.workload.store.connection()) as minimum_db, closing(self.connection()) as db:
            try:
                # Pin BOTH disposable policy stores. No locks on institutional
                # tables, no existing data writes and no source-file reload.
                minimum_db.execute('BEGIN IMMEDIATE')
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT id,raw,hash,bundle FROM frozen WHERE actor=? AND nonce=?', (grant.actor_id, command.request_id)).fetchone()
                if old:
                    doc = self._checked_frozen(old[1:])
                    require(doc['command_hash'] == command_hash, 'INPUTS_NONCE_REUSE_MISMATCH')
                    return self._public_frozen(doc)
                minima = self.workload.store.read(minimum_db)
                weights = self._head(db, 'weights', self.data['scoring_context']['settings'])
                preferences = self._preference_heads(db)
                require((command.minimum_revision, command.minimum_digest, command.weights_revision, command.weights_digest, command.preferences_digest) ==
                    (minima['revision'], minima['digest'], weights['revision'], weights['digest'], digest(preferences)), 'INPUTS_SELECTION_STALE')
                require(db.execute('SELECT COUNT(*) FROM frozen').fetchone()[0] < 32, 'INPUTS_PREPARATION_LIMIT')
                data = self.workload.bundle.materialize(self.workload.bundle.run_id)
                require(data['configuration']['baseline_mode'] == 'fresh' and data['seed'] is None, 'INPUTS_SEED_RESCORING_NOT_QUALIFIED')
                scoring = data['scoring_context']
                scoring['settings'] = copy.deepcopy(weights['body'])
                for code, head in preferences.items():
                    if head['body'] is not None:
                        scoring['preferences'][int(code)] = copy.deepcopy(head['body'])
                provenance = dict(contract=VERSION, scope=self.workload.scope.model_dump(), base_bundle=self.workload.bundle.fingerprint,
                    minimum_policy=minima, weights_policy=weights, preferences_digest=digest(preferences),
                    preference_revisions={c: dict(revision=h['revision'], digest=h['digest']) for c, h in preferences.items()},
                    original_source_dataset=json.loads(self.workload.bundle._raw)['source_identities']['dataset'])
                sources = dict(json.loads(self.workload.bundle._raw)['source_identities'])
                sources.update(dataset=digest(provenance), preparation=digest(provenance))
                scoring['input_fingerprint'] = sources['dataset']
                from services.ga_input_bundle import capture
                bundle = capture(run_id=str(uuid4()), templates=data['templates'], fallback_templates=data['fallback_templates'],
                    legacy_preferences=data['legacy_preferences'], scoring_context=scoring, configuration=data['configuration'],
                    source_identities=sources, academic_context_reference=digest(self.workload.scope.model_dump()))
                doc = dict(id=str(uuid4()), binding=self.binding, actor=grant.actor_id, command_hash=command_hash,
                    at=datetime.now(timezone.utc).isoformat(), provenance=provenance, prepared_bundle_fingerprint=bundle.fingerprint,
                    template_run_id=bundle.run_id, optimizer_consumption='NOT_ESTABLISHED', configuration_fingerprint=json.loads(bundle._raw)['configuration_fingerprint'])
                db.execute('INSERT INTO frozen VALUES(?,?,?,?,?,?)', (doc['id'], grant.actor_id, command.request_id, canonical(doc), digest(doc), bundle._raw))
                self._recheck(principal, grant)
                db.commit()
                return self._public_frozen(doc)
            except Exception:
                db.rollback()
                raise
            finally:
                minimum_db.rollback()

    def _checked_frozen(self, row):
        raw, identity, bundle_raw = row
        doc = json.loads(raw)
        require(digest(doc) == identity and doc['binding'] == self.binding, 'INPUTS_PREPARATION_CORRUPT')
        from services.ga_input_bundle import InputBundle
        InputBundle.from_bytes(bytes(bundle_raw), doc['template_run_id'], doc['prepared_bundle_fingerprint'])
        return doc

    def prepared(self, principal, identity, *, internal_bundle=False):
        grant = self.authorize(principal, 'prepared.read')
        with closing(self.connection()) as db:
            row = db.execute('SELECT raw,hash,bundle FROM frozen WHERE id=? AND actor=?', (identity, grant.actor_id)).fetchone()
            require(row is not None, 'INPUTS_PREPARATION_NOT_FOUND', 404)
            doc = self._checked_frozen(row)
            if internal_bundle:
                from services.ga_input_bundle import InputBundle
                return InputBundle.from_bytes(bytes(row[2]), doc['template_run_id'], doc['prepared_bundle_fingerprint'])
            return self._public_frozen(doc)

    def _public_frozen(self, doc):
        return dict(contract=VERSION, **FLAGS, preparation_id=doc['id'], prepared_bundle_fingerprint=doc['prepared_bundle_fingerprint'],
                    configuration_fingerprint=doc['configuration_fingerprint'], provenance=doc['provenance'],
                    optimizer_consumption='NOT_ESTABLISHED', worker_started=False,
                    execution_handoff='SERVER_CATALOG_REQUALIFICATION_REQUIRED_NO_AUTOMATIC_ADMISSION')
