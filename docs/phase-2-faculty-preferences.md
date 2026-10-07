# Phase 2: Faculty Preferences

Implemented only the preference editor, its metadata adapters, and a small preference-write validator. Existing Phase 1 changes remain intact. No fitness formulas, GA operators, workload rules, fixed assignments, or hard constraints were changed. No PostgreSQL, authentication, PMX, run controls, or unrelated page redesign was introduced.

## A. Files changed in Phase 2

| File | Purpose |
| --- | --- |
| `frontend/src/components/faculty/FacultyPreferenceEditor.tsx` | Four-section editor, eligible browsing, ranked list, importance controls, save states |
| `frontend/src/components/faculty/PreferenceCalendar.tsx` | Real component cards, fixed-duration calendar, placement and move dialogs, keyboard alternatives |
| `frontend/src/components/faculty/preferenceModel.ts` | Shared eligibility, ranking, duration, pattern, validation, and dirty-state operations |
| `frontend/src/components/faculty/preferences.css` | Scoped form styles, sticky save bar, accessible focus outlines, responsive preference-page layout |
| `frontend/src/pages/admin/PreferencesReview.tsx` | Privacy selector, normal-pool filtering, dirty-switch confirmation, administrator mode |
| `frontend/src/pages/faculty/Preferences.tsx` | Selector-free reusable self-service wrapper; accepts a faculty code |
| `frontend/src/api/faculty.ts` | Phase 1 stable identity and faculty metadata types |
| `frontend/src/api/subjects.ts` | Component/pattern metadata types and faculty-specific subject request |
| `frontend/package.json` | Two test scripts; no new dependencies |
| `frontend/tests/preferenceFixtures.mjs` | Isolated metadata and preference fixtures |
| `frontend/tests/preferenceModel.test.mjs` | Model behavior tests |
| `frontend/tests/preferences.browser.test.mjs` | Headless browser interaction tests with isolated API responses |
| `backend/routers/preferences.py` | Validate before writing; return HTTP 422 on invalid submissions |
| `backend/services/preference_validation_service.py` | Authoritative eligibility and meeting-pattern validation |
| `backend/tests/test_preference_validation.py` | Real API round trips and rejected-write tests using temporary JSON |
| `docs/phase-2-faculty-preferences.md` | This implementation and verification report |

The pre-existing Phase 1 working-tree changes are separate from this list. The faculty preference data file was not modified by implementation or tests.

## B. Page structure

1. **Preferred Subjects:** expertise context, eligible browsing, category buttons, search, one ranked list, and optional subject importance.
2. **Preferred Schedule:** only real component cards; general preferred periods; a calendar; accessible meeting details and move/remove buttons; optional day/time importance.
3. **Schedule Style:** No Preference, Compact, Spread Out.
4. **Lecture & Laboratory Preference:** No Preference, Same Day, Different Days.

The administrator page adds a collapsed administrator settings panel. A sticky save bar stays available below the four sections. The component can also be mounted without a faculty selector.

The narrow-screen navigation arrangement applies only while a preference page is present. Other pages retain their existing layout.

## C. Eligibility loading and privacy

The administrator selector reads `/api/faculty/`, filters `instructor_type = optimization_faculty`, uses stable faculty IDs internally, and displays only privacy labels such as **Faculty 0**. External instructors are excluded, including when an unexpected external record is supplied in the browser test.

The editor loads `/api/faculty/{faculty_id}/eligible-subjects` with the default eligible-only behavior. A course is selectable only when its explicit eligibility is true and at least one offering has `can_be_assigned = true`. Specialization and domain tags provide context only. The preference GET/PUT route still uses the corresponding legacy faculty code for compatibility.

“Show all offered subjects” makes a separate faculty-specific request with `eligible_only=false`. Ineligible or entirely preassigned courses are visible but their Add buttons are disabled. Normal selectors never show an external instructor's raw identifier or display name.

## D. Categories and subject ranking

ALL, CCC, ITD, ITN, ITE, ISY, and OTHER compare the category returned by metadata. Search matches subject code or title, case-insensitively. Neither category nor search changes eligibility.

Selected subjects appear in one ordered list. Each row has its code/title, drag handle, rank dropdown, and Remove button. Dragging and dropdown changes call the same reorder operation, keeping the persisted ordered code list synchronized. Removing a subject also removes that subject's component placements.

## E. Real component metadata

Cards require both a positive corresponding lecture/laboratory hour count and a matching positive-hour component. A subject without a lab never receives a lab card; a lab-only subject never receives a lecture card. Weekly hours and placement patterns come from Phase 1 metadata.

Unsupported metadata displays “Meeting pattern unavailable” and disables placement. The editor does not guess a duration or invent patterns for unsupported hour counts.

Component cards support FullCalendar external dragging as the primary desktop interaction. Drag a ready card onto a calendar cell to use that exact day/start time. The smaller Add button remains a keyboard fallback. A component with alternative patterns requires a selection before dragging is enabled; durations always come from the selected metadata pattern. General periods retain their separate Add action.

The **02 Preferred Schedule** section contains one short instruction, a small legend, the compact **Draggable Subject Preferences** tray, and **Preferred Weekly Schedule**. Only ranked subjects contribute cards. Cards show code, title, component, metadata duration, and **Drag to preferred time**. The empty tray uses one short sentence without reserving a panel. The academic timetable has a **Time** column, full Monday–Saturday headings, and 29 labeled half-hour ranges, **07:30–08:00** through **21:30–22:00**, ending at a visible 22:00 boundary. FullCalendar uses `height="auto"` instead of a fixed 480px window: the timetable grows vertically, and the page scrolls to later times with no internal vertical calendar scrolling. On narrow screens, horizontal overflow stays within the timetable. Week/Day controls are removed. The general-period action remains separate. Meeting details and keyboard controls use a small, initially collapsed disclosure below the timetable. Multi-meeting pattern controls remain available.

The generated timetable in `frontend/src/components/schedule/WeeklySchedule.tsx` was inspected before this visual change. Preference rendering reuses its centered Tailwind block layout, rounded bordered container, **38px** rows, teal **#115E59** header, and pale blue/teal background-border-text palette. Generated Schedule View files and behavior are unchanged. `eventContent` displays centered subject code, metadata title, component, and exact start/end time; it displays no room or section. Lecture and laboratory styling use distinct existing palette colors; general periods use the existing neutral slate style. Short periods use compact content without changing their height or duration.

The external drag uses `create=false`: only the controlled preference model creates persisted blocks after validating the drop. Completed components display **✓ Placed**, remain visible, disable their source cards and Add button, and reject duplicate insertion in the shared model. Removing a placement makes its source available again. This works after save/reload as well because completion and pattern selection are derived from saved blocks.

## F. Resizing prevention

FullCalendar has `eventStartEditable=true`, `eventDurationEditable=false`, and `eventResizableFromStart=false`. Each event also sets `durationEditable=false`. Move dialogs expose day/start time with a fixed-duration/end-time explanation, not an editable end time.

General periods are created with a start and end because they describe a preferred range, rather than a class requirement. Once placed, their move operation also preserves their existing duration. General periods use neutral styling; component placements use labeled lecture/laboratory colors.

## G. Moving and removing meetings

Drag and keyboard/dialog movement use the same operation. For a subject meeting, it resolves the current complete group against backend component patterns and recomputes the new end from that pattern's duration. It never accepts a dragged end as a new duration. A three-hour lab therefore remains 180 minutes. Moves outside 07:30–22:00 or outside supported day combinations are rejected and calendar drags are reverted.

Each meeting has keyboard-accessible Move and Remove actions. Older invalid placements are shown in meeting details and can be removed. They cannot be moved as if they were valid metadata-based meetings.

## H. Multiple lecture patterns

The existing preference schema can persist several blocks for one subject component. The editor therefore supports complete multi-meeting groups without adding a persistence schema.

For a component with alternatives, its pattern selector starts unselected. Only returned patterns are offered, such as **One 3-hour meeting** or **Two 1.5-hour meetings**. A two-meeting pattern requires a supported day pair, adds both fixed-duration meetings together, and allows each start time to move independently. Both initially use the selected start time.

Pattern and day-pair selectors are also available directly on the source component card. After selecting a two-meeting pattern and supported pair, the card exposes two draggable meeting sources. Dragging either onto its labeled day adds the complete pair atomically, both starting at the dropped time. This behavior is explained on the card and preserves the existing backend rule that incomplete meeting groups cannot be saved. Each meeting can subsequently be moved independently. Dropping on a different day is rejected. There are no provisional or partially saved groups.

The group is identified by subject code and component. Removing either meeting removes the complete component preference. To change the pattern or day pair, remove and add that component again; an intermediate incomplete or invalid pair is not allowed. Backend validation rejects incomplete groups. Existing fitness evaluation of multiple preference blocks remains unchanged.

## I. Importance and Faculty Priority

Numeric values remain unchanged: 0 is **No weight / informational only**, 1 is **Low (legacy minimum)**, 2 Low, 3 Medium, 4 High, and 5 Very High. Legacy value 1 has a distinct option so it can round-trip without silently becoming 2.

Importance controls are hidden when their preference is disabled. Spread Out still saves `Scattered`; Different Days still saves `Different Day`. Editing placements preserves deliberately disabled existing day/time flags; the first placement enables them. Removing the final placement disables them.

Faculty Priority is absent from the faculty-facing editor. It is retained in the payload and exposed only in the administrator page's collapsed **Advanced administrator settings** panel. This is a UI distinction, not role enforcement: authentication was intentionally not implemented.

## J. Save behavior and older data

The sticky bar shows **No changes**, **Unsaved changes**, **Saving…**, **Saved**, or **Save failed**. Discard restores the loaded/saved baseline. Save failures retain the draft. During saving, editing and faculty switching are disabled. Dirty faculty switches require confirmation; cancelling keeps the current faculty and draft. Closing/reloading the browser with a dirty draft invokes its standard unsaved-change warning.

Older eligibility or duration problems are displayed as review warnings; selections and blocks are not silently discarded or rewritten. Save remains disabled until those warnings are resolved. Users can remove an offending subject/component, or explicitly clear schedule preferences while retaining ranked subjects.

Legacy day/time ranges without general blocks are represented as equivalent editable general periods in memory. Loading them does not mark the editor dirty and does not automatically write a migration.

## K. Tests added and run

| Requested behavior | Verification |
| --- | --- |
| A. External instructors excluded | Model test and browser selector with an injected external record |
| B. Faculty-specific eligible subjects | Browser switches faculty and verifies the offered list; existing metadata contracts |
| C. Ineligible selection blocked | Model eligibility checks, disabled browser button, backend HTTP 422 |
| D. Categories/search | Model tests and real browser controls |
| E/F. Missing lab/lecture | Model and browser component-card checks; backend rejects fake lab |
| G. Metadata duration labels | Model label tests and rendered three-hour card |
| H. No resizing | Shared calendar configuration test; real DOM has no resize handles or end-time editor |
| I/J. Move preserves duration/lab 180 | Model movement, real calendar pointer drag, keyboard move, API valid move/rejected stretch |
| K. Ranking synchronization | Model reorder plus browser dropdown and drag/drop |
| L. Conditional importance | Model and browser tests, including legacy zero |
| M. Unsaved state | Dirty model tests; browser save states, discard, faculty-switch cancellation |
| N. Save compatibility | Browser failure/retry/reload; real API round trips for lecture, lab, two meetings and general periods |
| O. GA regression | All five pre-existing targeted suites retained and passing |

Results:

- **19 frontend model tests passed.**
- **22 browser test results passed:** 21 interaction checks plus their parent test. API responses are isolated fixtures; no production preferences are written.
- **24 new backend validation tests passed.** All use temporary persistence files.
- Production TypeScript/Vite build passed.
- ESLint passed for all changed TypeScript/TSX files.
- Full-project lint was also run after the tray correction: it reports four existing errors and eight warnings in unchanged `WeeklySchedule.tsx`, `GAContext.tsx`, `FacultyManagement.tsx`, `RoomAssignments.tsx`, and `ScheduleView.tsx`. The edited calendar and browser-test files pass lint. Those unrelated files were not modified.
- Full-timetable, mobile and 1024px laptop screenshots were visually inspected. Screenshots are generated under the ignored `frontend/.cache` directory. `preferences-reference-timetable.png` shows the complete reference scenario: Tuesday 10:30–12:30 lecture and Thursday 13:30–16:30 laboratory.

The Schedule View visual correction changes only `PreferenceCalendar.tsx`, `preferences.css`, `preferences.browser.test.mjs`, and this report. Model tests, browser tests, the production build, and edited-file lint pass. Browser checks prove the compact empty tray, selected metadata components, full-height grid, page scrolling, and absence of internal scrolling. The exact acceptance scenario passes using the CCC121 metadata fixture: lecture at Tuesday 10:30–12:30 spans four rows; laboratory at Thursday 13:30–16:30 spans six rows; moving the lecture to Friday 08:00 produces 08:00–10:00. Physical bottom-edge drag attempts preserve both event heights/durations, there are no resize handles or editable end times, and deleting the laboratory reactivates its source card. A held drag with mouse-wheel page scrolling places an evening lecture at Tuesday 19:30–21:30; natural edge scrolling also reaches targets below the viewport. Coverage retains duplicate prevention, supported paired patterns, ranking, filters, save/discard, unsaved-change protection, and save/reload. A separate general-period test verifies its neutral styling and one-row height for a 30-minute period. Backend, GA, eligibility, preference scoring, preference persistence, and fixed-duration validation are unchanged by this correction. The complete 153-test backend selection passed during an earlier follow-up; backend tests were not rerun for this UI-only correction.

Commands from `frontend`:

```text
npm.cmd run test:preferences
npm.cmd run test:preferences:browser
npm.cmd run build
node_modules\.bin\eslint.cmd src/components/faculty/FacultyPreferenceEditor.tsx src/components/faculty/PreferenceCalendar.tsx tests/preferences.browser.test.mjs
```

The model tests use Node's built-in TypeScript support (verified with Node 24). Browser tests use a locally installed headless Chromium browser, defaulting to Windows Edge. Set `PREFERENCE_TEST_BROWSER` to another executable if needed. They use local ports 5187 and 9226, temporary browser profiles, and no additional npm dependencies. The in-app Browser tool could not initialize because of a missing `sandboxPolicy` field; local headless verification was used instead.

## L. Existing tests still passing

From the repository root:

```text
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider backend/tests/test_preference_validation.py backend/tests/test_metadata_api.py backend/tests/test_tournament_selection.py backend/tests/test_ga_hard_constraints.py backend/tests/test_preassigned_assignments.py backend/tests/test_ga_api_crossover.py
```

**153 passed:** the existing 129 plus 24 new validation tests. The two existing Starlette/AnyIO deprecation warnings remain. The production build also retains Vite's large-bundle advisory. Neither warning prevented verification.

## M. Remaining backend limitations before Phase 3

New writes now validate faculty identity, explicit offered-course eligibility, unique ranked subjects and block IDs, supported days, clock formats and bounds, real components, complete meeting counts, exact durations, supported day combinations, and separation of general versus subject blocks. Rejected requests do not touch previously saved records. Existing invalid records remain readable for explicit correction.

The following are outside this focused validation change:

- No authenticated ownership or administrator role checks; hiding Faculty Priority is not access control.
- JSON writes still lack concurrent-edit locking/version checks and transactional persistence. Two editors can overwrite one another's changes.
- Existing preference GET behavior can create default records, including for arbitrary numeric codes. PUT now rejects unknown faculty; the legacy GET/reset lifecycle should be tightened in a separate API phase.
- General-period day/time summary fields are derived by the frontend. The server validates their format and range, but does not require a crafted API payload's summary to match its general blocks. The legacy min/max aggregate also cannot represent separate disjoint preferred windows precisely.
- General and component preferences continue to use the current fitness semantics, including precedence and matching rules. This phase does not change how those preferences contribute to a score.
- Internal route navigation is not generally blocked; the implemented loss protection covers faculty switching and browser unload/reload.
- Unsupported metadata is not guessed, and no historical preference migration runs automatically.

These limitations should be addressed deliberately in the relevant later API, persistence, authentication, or fitness-explainability phase, with separate regression coverage.
