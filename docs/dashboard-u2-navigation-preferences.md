# U2: sticky sidebar and modern preference controls

Implemented 2026-11-02 on `main`, starting HEAD `f5262637acfb2d4d063cad1b0de80779a10bcba3`. Frontend UI/UX only. The [manifest](testing/dashboard-u2/manifest.json) lists the exact U2 inventory, command records, screenshot hashes and preservation results. All U1 work and pre-existing user modifications are retained.

## Implemented interface

The desktop sidebar now uses CSS `position: sticky; top: 0`, retains its 16rem width, and has a viewport-height independently scrollable navigation area. Content scrolls beside it using the document's **single page scrollbar**. There is no second nested page scrollbar. On short laptop screens the sidebar itself scrolls to all links and the MSU-IIT/CCS footer. Header and content remain in the adjacent column and do not overlap the sidebar. The header retains its ordinary document flow; this milestone does not make the topbar sticky.

On narrow screens, a compact sticky CCS/portal header has a native Menu/Close disclosure button. Its `aria-controls` and `aria-expanded` reflect the collapsible panel. Closed links are removed from layout and the accessibility tree. Space/Enter operate the button; Escape inside navigation closes it and returns focus; selecting a route closes it. Expanded navigation has a bounded scroll area. This is an inline disclosure, not a modal drawer: no overlay or modal focus trap is claimed. Native links and NavLink active-page highlighting are preserved. A keyboard-visible skip link focuses the page content. Segmented controls and filters wrap on narrow screens.

Preferred Subjects now has two teal/gray pill switches with white thumbs and visible ON/OFF indicators. They remain controlled native checkbox inputs with switch semantics and explicit accessible names:

- **Consider my subject preferences** updates only the existing `use_subject_preference` draft flag.
- **Show all offered subjects (eligibility still applies)** updates the existing browsing-only `showAll` state. It never grants course eligibility or changes a draft preference by itself.

Category filters remain the existing mutually exclusive ALL/CCC/ITD/ITN/ITE/ISY/OTHER buttons, styled as CCS pills. Existing category/search behavior is unchanged. Eligibility is a separate noninteractive rectangular badge; disabled Add buttons and the original `isEligible` click guard remain intact. Search, Add, ranked preferences, reordering, importance selectors and component-calendar interactions are retained.

Schedule Style and Lecture & Laboratory Preference use native radio inputs behind segmented pills, grouped by the existing names. Each group permits **exactly one active option** for valid loaded form values. Native arrow-key navigation and focus indication are retained. Display labels and payload enums are unchanged:

| Group | Display labels | Stored values |
|---|---|---|
| Schedule Style | No Preference / Compact / Spread Out | `No Preference` / `Compact` / `Scattered` |
| Lecture/lab | No Preference / Same Day / Different Days | `No Preference` / `Same Day` / `Different Day` |

Selections use the original draft/enable-flag handlers. Nothing auto-saves. Explicit Save uses the original API workflow; Discard restores the saved draft. Importance values, including zero, retain their original meaning. The existing disabled-fieldset behavior applies to the new native controls while saving. No preference score, eligibility rule, API enum or validation policy changed.

Colors reuse the existing teal/gold identity. Controls have focus-visible outlines, 40–44px principal targets, reduced-motion overrides and forced-color selected-state outlines. Automated contrast calculations cover white/teal text and the OFF-track border. Native browser accessibility-tree checks verify switch names/checked state, six radios with two selected across two named groups, and hidden collapsed mobile links. These checks are not a full screen-reader or WCAG conformance audit.

## Calendar compatibility and retained failed experiments

An initial viewport-frame prototype put content in a nested `main` scroll area. Although the new controls worked, the original calendar wheel-drag regression did not. That implementation was not retained.

The diagnostic comparison tool serves the five pre-U2 UI files from the entry Git revision through temporary Vite load hooks, using the actual React/Tailwind plugins and original utility classes. It does not restore repository files or contact a backend. That comparison passed all **22 original preference browser scenarios**, showing the nested-scroll failure was a U2 integration regression. A first, incorrectly styled baseline probe omitted the normal plugins and failed a text-alignment assertion; it remains recorded and is not compatibility evidence.

Inspection of installed FullCalendar interaction code confirmed that automatic drag scrolling discovers the window and `.fc-scroller` elements. A temporary preference-pane marker recovered some automatic-scroll cases but did not preserve the original held-card wheel drop. Measurements confirmed an active fictional drag, correct visible target coordinates and no resulting placement. No production library or calendar code was patched, and no duration, conflict or drop-validation assertion was removed. Instrumented debug images/records remain historical failed evidence; they are not final acceptance screenshots.

The final CSS-sticky layout preserves document scrolling, eliminating that nested-scroll integration problem while keeping navigation independently available. The final original-calendar run passed all 22 scenarios with the **original wheel gesture and original placement/duration assertions**. Temporary pane markers, wheel-detent experiments, private-library inspection and calendar diagnostics are absent from the final application and calendar test path. A pre-U2 baseline utility remains as standalone diagnostic tooling only.

The existing browser harness was made bounded and isolated: it discovers Edge's debug port from its owned temporary profile, has debug-command deadlines, stops on the first failed scenario, foregrounds captures and writes generated captures under that owned profile instead of overwriting `.cache` files. No test was disabled or deleted. One initial harness timeout occurred before it could write its command record; the retained, explicitly attributed supplement records the observed 300-second timeout and unavailable output/timestamps. Subsequent timeout output is retained where captured. Ownership inspection after the initial timeout found no remaining preference-test worker; no unrelated service or user process was stopped.

Other retained failed checks include the early nested-scroll layout, its accessibility-label containment diagnosis, a visual assertion sampled before the 120ms color transition completed, and subpixel sticky geometry initially compared to exact zero. The final visual test waits for the selected paint; layout checks allow less than one CSS pixel of rounding. No timeout was increased to conceal an application failure.

## Validation

Final authoritative command records are identified individually in the manifest; earlier failures remain listed separately.

| Check | Final result and scope |
|---|---|
| U2 models/source contracts/contrast | 9 passed |
| Existing frontend plus U1 contracts | 112 passed |
| U2 rendered browser scenarios | 17 passed; Node counts 18 including parent |
| Original preference/calendar browser scenarios | 22 passed; Node counts 23 including parent |
| U1 rendered browser scenarios | 12 passed; Node counts 13 including parent |
| Existing GA browser scenarios | 51 passed; Node counts 52 including parent |
| TypeScript | `tsc -b` passed |
| Production bundle | Vite build passed |
| Focused ESLint | Exit 0, no errors/warnings in the selected U2 components/layouts |
| Privacy, preservation, whitespace and artifact hashes | See replayable manifest audit |

Browser evidence is actual headless Edge/React rendering and native pointer/keyboard interaction with **fictional intercepted API responses**. U2's save/reload verification uses a process-local mock preference store. It does not prove FastAPI persistence, database transactions, real account authorization or institutional acceptance. No GA run or database connection was executed. Existing U1 sorting, compatibility presentation and charts pass their regressions and retain their original artifact hashes.

Vite still reports the existing externalReadiness mixed static/dynamic import and large bundle warnings. No unrelated chunking or general cleanup was performed. Screen-reader software, touch-device hardware, Safari/Firefox and unusual browser zoom combinations were not tested. The sidebar scroll owner is intentionally distinct from the content/document scroll owner; browser scroll restoration itself is unchanged.

## Exact source changes

Modified existing files:

1. `frontend/src/components/common/Sidebar.tsx` — sticky navigation structure, mobile disclosure, focus return, existing branding/links.
2. `frontend/src/layouts/AdminLayout.tsx` — common layout classes and skip-link target; routes and GA provider remain unchanged.
3. `frontend/src/layouts/FacultyLayout.tsx` — same shared layout and skip-link target.
4. `frontend/src/components/faculty/FacultyPreferenceEditor.tsx` — bind existing flags/enums to the new visual controls; retain all policy, eligibility, save and discard handlers.
5. `frontend/src/components/faculty/preferences.css` — CCS switches/pills/focus/motion styling; remove the superseded preference-only mobile-navigation workaround.
6. `frontend/tests/preferences.browser.test.mjs` — owned browser discovery/capture safety, bounded commands and fail-fast reporting; all original calendar/form assertions retained.

New frontend files:

- `frontend/src/components/common/dashboardLayout.css`
- `frontend/src/components/faculty/PreferenceControls.tsx`
- `frontend/tests/dashboardControls.test.mjs`
- `frontend/tests/dashboardControls.browser.test.mjs`

New documentation/tooling: this report, `docs/testing/dashboard-u2/preservation-baseline.json`, `run_checks.py`, `audit_evidence.py`, `baseline_preferences.mjs`, `manifest.json`, and uniquely named command/browser/PNG evidence directories. The manifest provides the full per-file inventory rather than treating pre-existing unrelated research files as U2 changes.

## Reproduce and review

Use the existing environment and dependencies from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py focused
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py regressions
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py preferences-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py u1-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py ga-browser
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py build
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py bundle
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/run_checks.py lint
.\.venv\Scripts\python.exe -B docs/testing/dashboard-u2/audit_evidence.py
```

New runs create fresh evidence directories; they never replace previous command records. Edge may need permission to launch outside a restricted execution host. No backend/credentials are needed for the fixtures. Evidence additions require a reviewed manifest update; replaying the audit does not silently bless new hashes.

For interface review in an already authorized fictional environment: scroll a long administrator page, scroll the short-height sidebar separately, resize to mobile and operate Menu/Escape using the keyboard. On Faculty Preferences, use Space on both switches, browse an ineligible offering, change category/search, add/rank eligible subjects, and arrow through both segmented groups. Check the unsaved indicator, Discard, then explicitly Save and reload. The evidence captures are fictional examples, not institutional records. Avoid performing review actions against real protected preferences or publication workflows.

## Preservation and stop

The U2 baseline contains **2,778 entry paths**. Only the six named existing frontend/test paths may differ; **2,772 baseline paths remain byte-identical**. This includes all 23 academic files, both protected local preference/settings modifications, original GA/scoring/RNG sources, migrations, checkpoint/saved-schedule trees, previous evidence, U1 files, development-terminal configuration and Git index. U1's 56 artifact hashes are independently rechecked. HEAD remains the entry commit. Unrelated existing research artifacts are preserved.

No dependency was installed. No database operation, migration, permission change, institutional activation, data overwrite, staging, commit or push occurred. The UI is ready for the user's interface review; Git checkpoint authorization remains separate. Production institutional authority and U1's missing authoritative current-evaluation compatibility contract remain blocked exactly as before.
