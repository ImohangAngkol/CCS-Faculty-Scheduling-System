# Phase 1: stable identities and scheduling metadata

This phase adds read-only, typed metadata contracts. It does not change fitness,
selection, crossover, mutation, elitism, workload rules, baseline validation,
or preassignment enforcement. No PostgreSQL or frontend redesign is included.

## Faculty identity registry

`backend/data/faculty_identities.json` is the checked-in identity registry.
Each record separates an immutable opaque UUID (`faculty_id`), the frozen legacy
numeric code (`faculty_code`), the privacy label (`display_code`), and the name.
Names currently use the surnames available in the existing source data; no full
names have been invented. Existing faculty-facing privacy rendering is unchanged.

| Legacy code | Source name | Display label | Stable UUID suffix* |
| --- | --- | --- | --- |
| 0 | BALAGA | Faculty 0 | dd00 |
| 1 | BOKINGKITO | Faculty 1 | dd01 |
| 2 | CONOL | Faculty 2 | dd02 |
| 3 | IBRAHIM | Faculty 3 | dd03 |
| 4 | LLAMAS | Faculty 4 | dd04 |
| 5 | LUA | Faculty 5 | dd05 |
| 6 | NAGA | Faculty 6 | dd06 |
| 7 | RARUGAL | Faculty 7 | dd07 |
| 8 | SALA | Faculty 8 | dd08 |
| 9 | TABIGUE | Faculty 9 | dd09 |
| 10 | TINAM-ISAN | Faculty 10 | dd10 |

*Full IDs are stored in the registry; all share the prefix
`a1746741-97b6-4e55-990e-06a4cc98`.

The loader now resolves names against these registered codes instead of
enumerating alphabetically grouped faculty. CSV/JSON eligibility, qualifications,
preferences, saved schedules, and existing GA objects retain their numeric codes.
Loaded normal faculty also carry `stable_id`, `display_code`, and `name` attributes.

Reordering source rows, removing a source name, or reordering registry records
does not renumber remaining faculty. An unregistered name fails with an actionable
error instead of silently shifting mappings. To register a new faculty member,
allocate a fresh UUID, unused numeric code, and unused display label; never reuse
retired identities. This registry is not derived again at startup.

Optional `aliases` preserve old source-name matching when the registry name is
updated. Existing workload/priority sources still need consistent names; aliases
do not implement a full administrative rename workflow. Registry changes require
a backend restart, like the existing imported CSV data.

## Course, offering, section, and external identities

Public metadata uses deterministic UUIDv5 IDs with the fixed namespace in
`services/identity_service.py`:

- Course key: `course:msu-iit:ccs:<normalized code>`.
- Section key: `section:ccs:first-semester-prototype:<normalized section>`.
- Offering key: `offering:ccs:first-semester-prototype:<code>::<section>`.
- External instructor key: catalog scope plus its existing declared internal key.

`CCC100::1A` and `CCC100::1B` share one course ID and have distinct offering IDs
and section IDs. The human-readable `offering_key` is also returned.
Titles, units, row order, and current assignments do not determine identities.

The current files lack a reliable term ID, so the offering scope explicitly means
the existing first-semester prototype dataset. It does not claim an academic year.
Do not reuse this scope for a different semester/year. Before multi-term support,
introduce explicit term scopes and migrate existing IDs unchanged. Catalog codes
and section keys are immutable identity keys in this adapter: a rename requires
an alias/migration preserving the old UUID, rather than recomputing identity from
the new code. Future PostgreSQL records must import these IDs as primary keys.

## Endpoints

| Endpoint | Response |
| --- | --- |
| `GET /api/faculty/` | Existing `{message, data: [...]}` wrapper; normal faculty only |
| `GET /api/faculty/{id}` | `{message, data: faculty}`; accepts UUID or legacy numeric code |
| `GET /api/subjects/available` | `{message, categories, data: [...]}`; course records with nested offerings |
| `GET /api/faculty/{id}/eligible-subjects` | `{message, faculty, eligible_only, data: [...]}` |

`eligible_only` defaults to `true`. Set `?eligible_only=false` to inspect every
offered course with explicit eligible/ineligible status. Unknown IDs, including
external instructor IDs passed to normal faculty routes, return 404.

Faculty fields include `faculty_id`, `faculty_code`, `display_code`, `name`,
`instructor_type`, `seniority_level`, existing nonteaching loads and
`current_teaching_load`, `required_teaching_load`, `absolute_max_teaching_load`,
`specializations`, and `eligible_subject_codes`. Existing names remain available
to administrator clients; privacy views should use `display_code`.
`current_teaching_load` remains the legacy runtime field, not a historical analysis.

Course fields retain `subject_code` and `subject_title` for existing consumers and
add `course_id`, `units`, `lecture_hours`, `laboratory_hours`, `prefix`, `category`,
`primary_domain`, `domains`, `components`, `is_preassigned`,
`preassignment_status` (`none`, `some`, `all`), `offerings`, and `eligibility`.
Eligibility is null on the unscoped available-subject response.

Each offering includes its own course fields plus `offering_id`, `offering_key`,
`offering_scope`, `section_id`, `section`, `year_level`, `is_preassigned`,
`assignment_type`, `preassigned_instructor`, and `can_be_assigned`.
`can_be_assigned` is null without a selected faculty context.

Pydantic schemas in `schemas/faculty.py` and `schemas/subject.py` define these
contracts and appear in the existing FastAPI OpenAPI documentation.

## Eligibility and descriptive tags

`eligibility` contains:

```json
{
  "explicitly_eligible": true,
  "authority": "faculty_subject_eligibility.csv",
  "records": [{
    "status": "eligible",
    "basis": "Current/tentative teaching assignment",
    "source": "Tentative Load First Sem 2026-2027",
    "notes": "Explicit course-level eligibility; specialization alone is not used as a hard qualification."
  }]
}
```

The boolean calls the same explicit-eligibility helper as the GA, using the
faculty's eligibility set loaded from the authoritative CSV. Provenance comes
from that CSV's matching rows. No record means no permission; specialization,
prefix, and domains cannot create permission. Metadata reads do not reload CSVs
independently or modify scheduling state.

Default eligible results contain explicitly eligible courses with at least one
GA-managed offering. A preassigned offering has `can_be_assigned=false` even if
the faculty has explicit course permission. Display-only category choices are
`ALL`, `CCC`, `ITD`, `ITN`, `ITE`, `ISY`, `OTHER`; unknown prefixes map to `OTHER`.
`can_be_assigned` describes qualification and preassignment ownership only;
it does not claim that load, room availability, or a proposed time is feasible.

## Component requirements

Only components whose weekly hours are positive are returned. A zero-hour lab
does not create a Laboratory card; a zero-hour lecture does not create a Lecture
card. Meeting patterns are derived from the scheduler's existing template lists:

| Component | Supported patterns |
| --- | --- |
| 2-hour lecture | One continuous 120-minute meeting |
| 3-hour lecture | One 180-minute meeting, or two 90-minute meetings |
| 3-hour laboratory | One continuous 180-minute meeting |

Each component returns `type`, `weekly_hours`, `metadata_status`,
`duration_minutes`, `meetings_per_week`, `continuous`, `fixed_duration`, and
`meeting_patterns`. Pattern entries include meeting count, fixed minutes,
continuity within each meeting, and supported day combinations.

For multiple alternatives, component-level duration/count are null and the
frontend must use an explicit supported pattern. For unsupported hours, status
is `unsupported`, duration/count/continuity are null, patterns are empty, and
`fixed_duration=false`; this means no known duration, not permission to resize.
No new meeting pattern is inferred or enabled in the GA.

Palad's ITE184 offerings expose a public UUID, `display_name` of
`Atty. Eddie Bouy Palad`, `instructor_type=preassigned_external`, and
`locked_room=ICT3A`. The new metadata responses never serialize the raw internal
external key. Existing saved/GA schedule formats keep their internal keys for
compatibility. Palad remains outside normal faculty endpoints and selectors.

## Follow-up before preference UI cleanup

- Consume these metadata fields in frontend types and eligibility-aware requests.
- Replace the current one-hour drag duration and unconditional lecture/lab cards.
- Select a supported lecture pattern when alternatives exist; keep labs at 180 minutes.
- Disable resizing and derive end times from selected metadata.
- Add matching preference-write validation; metadata alone does not validate saved blocks.
- Render external names/status from metadata while preserving normal privacy labels.
- Decide an explicit term identity before semester-switching or PostgreSQL migration.

These remain later-phase work. No preference records or baseline files were rewritten.
