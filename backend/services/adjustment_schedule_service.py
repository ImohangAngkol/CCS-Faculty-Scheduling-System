"""Read-only, server-owned schedule/version boundary for D11.

Production stays blocked until a coherent term/resource/constraint source is
installed. A client cannot install it. Legacy files alone have no sourced term.
Providers must hold their version/authority guard for the entire context,
including request commit. This module never writes a schedule or runs a GA.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable
import copy
import hashlib
import json
from services.schedule_service import _read, _check_unchanged, problem
from services.ga_v2_constraints import Commitment, minutes, overlap


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    kind: str


@dataclass(frozen=True)
class Meeting:
    id: str
    faculty_id: str
    subject_id: str
    section_id: str
    subject: str
    title: str
    section: str
    component: str
    day: str
    start: str
    end: str
    room_id: str


@dataclass(frozen=True)
class ReviewSchedule:
    schedule_id: str
    revision: str
    academic_year: str
    term: str
    constraint_digest: str
    meetings: tuple[Meeting, ...]
    rooms: tuple[Room, ...]
    # (kind, authoritative ID, day, available start, available end).
    windows: tuple[tuple[str, str, str, str, str], ...]
    commitments: tuple[Commitment, ...]
    check_current: Callable[[], None]
    check_proposal: Callable[[Meeting, object], None]


def institutional_schedule_source():
    """Return a guarded ReviewSchedule context, or None. No env/client bypass."""
    return None


@contextmanager
def current_source():
    provider = institutional_schedule_source()
    if provider is None:
        raise problem(503, 'ADJUSTMENT_SOURCE_UNAVAILABLE', 'Requests are blocked until a verified schedule revision, academic term, resource catalog and current GEC constraint source are configured. My Schedule remains read only.')
    try:
        with provider as source:
            if (not isinstance(source, ReviewSchedule) or not source.academic_year or not source.term
                    or len(source.revision) != 64 or len(source.constraint_digest) != 64
                    or len({m.id for m in source.meetings}) != len(source.meetings)
                    or len({r.id for r in source.rooms}) != len(source.rooms)):
                raise ValueError('Invalid authoritative schedule contract')
            yield source
    except (ValueError, KeyError, TypeError, AttributeError):
        raise problem(503, 'ADJUSTMENT_SOURCE_UNAVAILABLE', 'The current schedule context could not be verified. No schedule or request transition was applied.') from None


def legacy_projection(path, *, academic_year, term, faculty_ids, subject_ids, section_ids,
                      rooms, windows, constraint_snapshot):
    """Reusable adapter for a caller-guarded source with explicit trusted maps.

    IDs are supplied by the server catalog, never derived from names/row order.
    Meeting keys are content addresses within one exact source revision, not
    invented academic IDs. Duplicate meetings reject the source.
    Caller must keep the source and D10 authority pinned through the transaction.
    """
    from services.ga_service import validate_saved_result
    payload, stat = _read(path)
    if not stat or payload.get('status', 'COMPLETED') != 'COMPLETED':
        raise problem(409, 'ADJUSTMENT_SOURCE_STALE', 'A completed schedule proposal is required.')
    validate_saved_result(copy.deepcopy(payload))
    revision = digest(payload)
    from uuid import UUID
    from services.identity_service import resolve_faculty_identity
    for row in payload['schedule']:
        code = str(row['faculty'])
        mapped = str(faculty_ids[code])
        try:
            registered_id = UUID(mapped)
        except ValueError:
            # External resource IDs cannot authorize an application faculty
            # account. Numeric GA faculty codes require a registered UUID.
            if code.isdecimal(): raise ValueError('Unregistered faculty mapping')
        else:
            registered = resolve_faculty_identity(str(registered_id))
            if str(registered.faculty_code) != code:
                raise ValueError('Faculty UUID/code mapping mismatch')
    if (constraint_snapshot.catalog.academic_year, constraint_snapshot.catalog.term) != (academic_year, term):
        raise ValueError('Constraint term mismatch')
    room_ids = {r.name: r.id for r in rooms}
    meetings = tuple(Meeting(digest(row), str(faculty_ids[str(row['faculty'])]), subject_ids[row['subject']],
        section_ids[row['section']], row['subject'], row.get('title') or '', row['section'], row['type'].title(),
        row['day'], row['start'], row['end'], room_ids[row['room']]) for row in payload['schedule'])
    _check_unchanged(path, stat)
    maps = constraint_snapshot.catalog
    # Map D10 authoritative IDs through its exact runtime mapping into the D11
    # catalog. Do not compare independent identity namespaces by display label.
    fixed = tuple(c.model_copy(update={
        'faculty': str(faculty_ids[dict(maps.faculty)[c.faculty]]) if c.faculty else None,
        'sections': tuple(section_ids[dict(maps.sections)[s]] for s in c.sections),
        'room': room_ids[dict(maps.rooms)[c.room]] if c.room else None,
    }) for c in constraint_snapshot.commitments)
    def check_proposal(original, proposal):
        changed = copy.deepcopy(payload)
        row = next(r for r in changed['schedule'] if digest(r) == original.id)
        row.update(day=proposal.day, start=proposal.start, end=proposal.end,
                   room=next(r.name for r in rooms if r.id == proposal.room_id))
        validate_saved_result(changed)
    return ReviewSchedule('legacy-latest', revision, academic_year, term, constraint_snapshot.digest,
                          meetings, tuple(rooms), tuple(windows), fixed, lambda: _check_unchanged(path, stat), check_proposal)


def owned(source, identity):
    return tuple(m for m in source.meetings if m.faculty_id == identity.faculty_id)


def public_meeting(meeting):
    from dataclasses import asdict
    data = asdict(meeting)
    del data['faculty_id']
    return data


def validate(source, identity, body):
    if (body.schedule_id, body.revision) != (source.schedule_id, source.revision):
        raise problem(409, 'STALE_SCHEDULE_REFERENCE', 'This schedule revision was superseded. Reload assignments; the original request remains unchanged.')
    if (body.academic_year, body.term) != (source.academic_year, source.term):
        raise problem(409, 'TERM_MISMATCH', 'The academic year or semester does not match the verified schedule.')
    original = next((m for m in owned(source, identity) if m.id == body.assignment_id), None)
    if original is None:
        raise problem(404, 'ASSIGNMENT_NOT_FOUND', 'No authorized assignment matches this reference.')
    p = body.proposal
    try:
        start, end = minutes(p.start), minutes(p.end)
        duration = minutes(original.end) - minutes(original.start)
        if start >= end or start % 30 or end % 30 or end - start != duration:
            raise ValueError()
    except (ValueError, TypeError):
        raise problem(422, 'INVALID_TIME_OR_DURATION', 'Use valid half-hour times and preserve the original lecture/laboratory meeting duration.') from None
    room = next((r for r in source.rooms if r.id == p.room_id), None)
    if room is None:
        raise problem(422, 'MISSING_RESOURCE', 'Select an existing recognized room.')
    if room.kind != original.component:
        raise problem(422, 'ROOM_COMPONENT_MISMATCH', 'The room must support this lecture/laboratory component.')
    if (p.day, p.start, p.end, p.room_id) == (original.day, original.start, original.end, original.room_id):
        raise problem(422, 'NO_ADJUSTMENT', 'Change a day, time or room before creating a request.')
    findings = set()
    resources = (('faculty', identity.faculty_id), ('section', original.section_id), ('room', p.room_id))
    for kind, key in resources:
        windows = [w for w in source.windows if w[0] == kind and w[1] == key and w[2] == p.day]
        # Union contiguous windows; adjacent original slots are valid coverage.
        cursor = start
        for w in sorted(windows, key=lambda w: minutes(w[3])):
            a, b = minutes(w[3]), minutes(w[4])
            if a <= cursor < b: cursor = max(cursor, b)
        if cursor < end:
            findings.add('MISSING_' + kind.upper() + '_AVAILABILITY' if not windows else kind.upper() + '_UNAVAILABLE')
    for other in source.meetings:
        if other.id == original.id or other.day != p.day or not overlap(start, end, minutes(other.start), minutes(other.end)):
            continue
        if other.faculty_id == identity.faculty_id: findings.add('FACULTY_CONFLICT')
        if other.section_id == original.section_id: findings.add('SECTION_CONFLICT')
        if other.room_id == p.room_id: findings.add('ROOM_CONFLICT')
    for fixed in source.commitments:
        if fixed.day != p.day or not overlap(start, end, fixed.start, fixed.end): continue
        # D10 commitments use authoritative IDs, not public labels.
        if (identity.faculty_id == fixed.faculty or original.section_id in fixed.sections or p.room_id == fixed.room):
            findings.add('CONFIRMED_GEC_CONFLICT')
    try:
        # Reconstruct detached inputs using the original validation boundary.
        # Multi-meeting component patterns, preassignments and existing fixed
        # section restrictions remain review findings rather than silent repairs.
        source.check_proposal(original, p)
    except (ValueError, RuntimeError):
        findings.add('SCHEDULING_RULE_REVIEW_REQUIRED')
    codes = sorted(findings)
    return {'original': public_meeting(original), 'proposal': p.model_dump(),
            'validation': {'outcome': 'REQUIRES_REVIEW' if codes else 'VALID_PROPOSAL',
                           'findings': [{'code': c, 'message': c.replace('_', ' ').capitalize() + '; authorized review is required.'} for c in codes],
                           'conflict_free': not codes, 'approval': 'AWAITING_FUTURE_D12_CHAIR_DECISION'},
            'constraint_digest': source.constraint_digest}
