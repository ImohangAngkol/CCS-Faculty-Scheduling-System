"""Opt-in fictional workload qualification; no GA search or institutional storage.

Original targets, fitness, operators and bundle contracts are never changed.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

CONTRACT = 'prototype-explicit-minimum-v1'
FLAGS = dict(prototype_only=True, production_admission='BLOCKED',
             institutional_saved_best_promotion=False, continuous_optimization='DISABLED',
             active_restore=False, seven_day='NO_GO', optimizer_executed=False)


class PolicyError(ValueError):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


def require(value, code, status=409):
    if not value:
        raise PolicyError(code, status)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Minimum(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    faculty_code: int = Field(ge=0)
    minimum_teaching_units: int = Field(ge=0, le=40)


class Change(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_revision: int = Field(ge=0)
    minimums: list[Minimum] = Field(max_length=200)


class Scope(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    department_id: str
    academic_year: str = Field(pattern=r'^FICTIONAL-[A-Za-z0-9_-]{1,60}$')
    term: str = Field(pattern=r'^FICTIONAL-[A-Za-z0-9_-]{1,60}$')
    catalog_revision: str = Field(pattern=r'^FICTIONAL-[A-Za-z0-9_-]{1,60}$')


class Store:
    """New owned disposable SQLite only; immutable revisions and atomic CAS.

    Hash chaining detects inconsistent/corrupted records, not a hostile OS owner
    who rewrites all hashes. This is not an institutional signed ledger.
    """
    @classmethod
    def create(cls, binding):
        from services.ga_worker_contract import fictional_source
        fictional_source()
        root = Path(tempfile.mkdtemp(prefix='ccs-prototype-workload-'))
        with (root / 'OWNED.json').open('x', encoding='utf-8') as stream:
            json.dump(dict(contract=CONTRACT, binding=binding), stream)
        with closing(sqlite3.connect(root / 'policy.sqlite3')) as db, db:
            db.execute('CREATE TABLE revisions(version INTEGER PRIMARY KEY, doc TEXT NOT NULL, digest TEXT NOT NULL)')
            db.execute("CREATE TRIGGER immutable_update BEFORE UPDATE ON revisions BEGIN SELECT RAISE(ABORT,'immutable'); END")
            db.execute("CREATE TRIGGER immutable_delete BEFORE DELETE ON revisions BEGIN SELECT RAISE(ABORT,'immutable'); END")
        return cls(root, binding)

    def __init__(self, root, binding):
        self.root, self.binding = Path(root), binding
        self.check()

    def check(self):
        p = self.root
        require(not p.is_symlink() and not p.is_junction(), 'PROTOTYPE_STORAGE_LINK')
        require(p.resolve().parent == Path(tempfile.gettempdir()).resolve()
                and p.name.startswith('ccs-prototype-workload-'), 'PROTOTYPE_OWNED_STORAGE_REQUIRED')
        for name in ['OWNED.json', 'policy.sqlite3']:
            require((p / name).is_file() and not (p / name).is_symlink()
                    and not (p / name).is_junction(), 'PROTOTYPE_STORAGE_INVALID')
        require(json.loads((p / 'OWNED.json').read_text()) == dict(contract=CONTRACT, binding=self.binding),
                'PROTOTYPE_STORAGE_BINDING_CHANGED')
        require((p / 'policy.sqlite3').stat().st_size < 4 * 1024 * 1024, 'PROTOTYPE_STORAGE_LIMIT', 413)

    def connection(self):
        self.check()
        db = sqlite3.connect((self.root / 'policy.sqlite3').as_uri() + '?mode=rw', uri=True, timeout=5)
        db.execute('PRAGMA synchronous=FULL')
        return db

    def read(self, db):
        tip = dict(revision=0, minimums=[], digest=digest(dict(contract=CONTRACT, binding=self.binding)))
        rows = db.execute('SELECT version,doc,digest FROM revisions ORDER BY version').fetchall()
        require(len(rows) <= 100, 'PROTOTYPE_REVISION_LIMIT', 413)
        for version, raw, identity in rows:
            doc = json.loads(raw)
            require(set(doc) == {'contract', 'binding', 'revision', 'minimums', 'actor', 'at', 'parent'},
                    'PROTOTYPE_HISTORY_INVALID')
            require(type(version) is int and type(doc['revision']) is int
                    and version == tip['revision'] + 1 == doc['revision']
                    and doc['contract'] == CONTRACT and doc['binding'] == self.binding
                    and doc['parent'] == tip['digest'] and identity == digest(doc), 'PROTOTYPE_HISTORY_INVALID')
            UUID(doc['actor'])
            require(datetime.fromisoformat(doc['at']).tzinfo is not None, 'PROTOTYPE_HISTORY_INVALID')
            parsed = [Minimum.model_validate(x).model_dump() for x in doc['minimums']]
            require(len({x['faculty_code'] for x in parsed}) == len(parsed), 'PROTOTYPE_HISTORY_INVALID')
            tip = dict(revision=version, minimums=parsed, digest=identity, actor=doc['actor'], at=doc['at'])
        return tip

    def current(self):
        with closing(self.connection()) as db:
            return self.read(db)

    def append(self, actor, change):
        with closing(self.connection()) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                tip = self.read(db)
                require(change.expected_revision == tip['revision'], 'PROTOTYPE_POLICY_STALE')
                require(tip['revision'] < 100, 'PROTOTYPE_REVISION_LIMIT', 413)
                doc = dict(contract=CONTRACT, binding=self.binding, revision=tip['revision'] + 1,
                           minimums=sorted([x.model_dump() for x in change.minimums], key=lambda x: x['faculty_code']),
                           actor=actor, at=datetime.now(timezone.utc).isoformat(), parent=tip['digest'])
                db.execute('INSERT INTO revisions VALUES(?,?,?)', (doc['revision'], canonical(doc), digest(doc)))
                db.commit()
            except Exception:
                db.rollback()
                raise
        return self.current()


class WorkloadService:
    def __init__(self, scope, bundle, authority, store=None):
        from services.ga_worker_contract import fictional_source
        from services.ga_input_bundle import InputBundle
        fictional_source()
        require(type(scope) is Scope, 'PROTOTYPE_SCOPE_REQUIRED')
        require(type(bundle) is InputBundle, 'PROTOTYPE_CAPTURED_BUNDLE_REQUIRED')
        UUID(scope.department_id)
        self.scope, self.bundle, self.authority = scope, bundle, authority
        self.binding = digest(dict(contract=CONTRACT, scope=scope.model_dump(), bundle=bundle.fingerprint))
        self.store = store or Store.create(self.binding)
        require(self.store.binding == self.binding, 'PROTOTYPE_STORAGE_BINDING_CHANGED')
        # An immutable captured bundle is not a VERIFIED consumption receipt.
        self.catalog()

    def authorize(self, principal, action):
        actor = getattr(principal, 'user_id', None)
        try:
            UUID(actor)
            allowed = self.authority is not None and self.authority.allows(actor, self.scope, action) is True
        except Exception:
            allowed = False
        require(allowed, 'PROTOTYPE_SCOPED_AUTHORITY_REQUIRED', 403)
        return actor

    def catalog(self):
        data = self.bundle.materialize(self.bundle.run_id)
        subjects, members, _rooms = data['templates']
        require(len(members) <= 200 and len(subjects) <= 1000, 'PROTOTYPE_CATALOG_LIMIT')
        faculty = {}
        for member in members:
            require(not getattr(member, 'is_external', False) and type(member.code) is int
                    and member.code not in faculty, 'PROTOTYPE_CATALOG_INVALID')
            require(type(member.required_teaching_load) is int and member.required_teaching_load >= 0
                    and type(member.absolute_max_teaching_load) is int
                    and 0 <= member.absolute_max_teaching_load <= 40, 'PROTOTYPE_CATALOG_INVALID')
            faculty[member.code] = dict(faculty_code=member.code,
                soft_target_teaching_units=member.required_teaching_load,
                maximum_teaching_units=member.absolute_max_teaching_load,
                eligible_subjects={str(s).strip().upper() for s in member.eligible_subjects}, eligible_units=0)
        seen = set()
        for subject in subjects:
            key = str(subject.number), str(subject.section.code)
            require(key not in seen and type(subject.credit_units) is int and subject.credit_units >= 0,
                    'PROTOTYPE_CATALOG_INVALID')
            seen.add(key)
            if subject.preassigned_assignment is not None:
                continue
            for row in faculty.values():
                if str(subject.number).strip().upper() in row['eligible_subjects']:
                    row['eligible_units'] += subject.credit_units
        return faculty, subjects

    def minimums(self, tip):
        faculty, _ = self.catalog()
        values = {x['faculty_code']: x['minimum_teaching_units'] for x in tip['minimums']}
        require(len(values) == len(tip['minimums']) and set(values) <= set(faculty), 'PROTOTYPE_MINIMUM_INVALID', 422)
        require(all(value <= faculty[code]['maximum_teaching_units'] for code, value in values.items()),
                'PROTOTYPE_MINIMUM_ABOVE_MAXIMUM', 422)
        return faculty, values

    def view(self, principal):
        self.authorize(principal, 'read')
        tip = self.store.current()
        faculty, minima = self.minimums(tip)
        rows = []
        for code, row in faculty.items():
            minimum = minima.get(code)
            rows.append({k: v for k, v in row.items() if k != 'eligible_subjects'} | dict(
                minimum_teaching_units=minimum,
                minimum_exceeds_soft_target=minimum is not None and minimum > row['soft_target_teaching_units'],
                proven_shortfall=max(0, minimum-row['eligible_units']) if minimum is not None else None))
        infeasible = any(x['proven_shortfall'] is not None and x['proven_shortfall'] > 0 for x in rows)
        return dict(contract=CONTRACT, **FLAGS, scope=self.scope.model_dump(), policy=tip,
                    bundle_fingerprint=self.bundle.fingerprint, input_capture_verification='UNVERIFIED',
                    optimizer_consumption='NOT_ESTABLISHED', faculty=rows,
                    can_configure=self.authority.allows(principal.user_id, self.scope, 'configure') is True,
                    preflight='MINIMUM_WORKLOAD_INFEASIBLE' if infeasible else 'NOT_PROVEN_INFEASIBLE',
                    explanation='Eligible units are an upper bound; calendars, shared resources and joint minima can further restrict feasibility.')

    def save(self, principal, change):
        actor = self.authorize(principal, 'configure')
        self.authorize(principal, 'read')
        require(type(change) is Change, 'PROTOTYPE_MINIMUM_INVALID', 422)
        self.minimums(dict(minimums=[x.model_dump() for x in change.minimums]))
        self.store.append(actor, change)
        return self.view(principal)

    def assess(self, principal, candidate, policy_digest):
        """Server-internal supplemental assessment; NEVER a client schedule API.

        The caller must separately apply existing academic publication validation.
        No scoring, candidate admission, search, persistence or repair occurs.
        """
        self.authorize(principal, 'read')
        tip = self.store.current()
        require(tip['digest'] == policy_digest, 'PROTOTYPE_POLICY_STALE')
        faculty, minima = self.minimums(tip)
        _, subjects = self.catalog()
        expected = {(str(s.number), str(s.section.code)): s for s in subjects}
        seen, loads = set(), {code: 0 for code in faculty}
        for subject in candidate:
            key = str(subject.number), str(subject.section.code)
            require(key in expected and key not in seen and subject.credit_units == expected[key].credit_units,
                    'PROTOTYPE_CANDIDATE_COVERAGE_INVALID')
            seen.add(key)
            if expected[key].preassigned_assignment is not None:
                require(subject.preassigned_assignment == expected[key].preassigned_assignment,
                        'PROTOTYPE_PREASSIGNMENT_CHANGED')
                continue
            code = getattr(subject.assigned_faculty, 'code', None)
            require(code in faculty and str(subject.number).strip().upper() in faculty[code]['eligible_subjects'],
                    'PROTOTYPE_ELIGIBILITY_VIOLATION')
            loads[code] += subject.credit_units
        require(seen == set(expected), 'PROTOTYPE_CANDIDATE_COVERAGE_INVALID')
        require(all(loads[c] <= row['maximum_teaching_units'] for c, row in faculty.items()),
                'PROTOTYPE_MAXIMUM_VIOLATION')
        rows = [dict(faculty_code=c, minimum_teaching_units=m, assigned_units=loads[c],
                     deficit=max(0, m-loads[c])) for c, m in minima.items()]
        return dict(policy_digest=tip['digest'], bundle_fingerprint=self.bundle.fingerprint, faculty=rows,
                    minimum_status='MINIMUM_WORKLOAD_VIOLATION' if any(x['deficit'] for x in rows) else 'EXPLICIT_MINIMA_SATISFIED',
                    full_academic_validation='SEPARATE_ORIGINAL_VALIDATION_REQUIRED', **FLAGS)
