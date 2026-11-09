"""Evidence-indexed audit conclusions, not application code or a demo profile."""
from pathlib import Path
import collections
import json
import re

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
def new(name,value):
    with (BASE/name).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,indent=2)+'\n')
def latest(pattern):return sorted(BASE.glob(pattern))[-1]

def main():
    frontend=json.loads((BASE/'frontend-static-inventory-r3.json').read_text())
    backend=json.loads(latest('*/backend-route-inventory.json').read_text())
    survey=json.loads(latest('*/captures/route-survey.json').read_text())
    rows=[]
    def feature(name,status,evidence,limitation):rows.append(dict(id=f'F{len(rows)+1:02}',feature=name,status=status,evidence=evidence,limitation=limitation))
    feature('Login','WORKING','D16-L01/I01 live Edge/FastAPI/SQLite; identity regressions','Fictional users; not institutional SSO')
    feature('Logout and session reload','WORKING','Live preference reload, repeated sign-out/login and owned server-loss case','Session lifecycle is not a seven-day research-worker lifetime')
    feature('Role and own-faculty enforcement','WORKING','100 protected anonymous endpoints return 401; actual cross-faculty live/API denials','Not an exhaustive security assessment or verified department directory')
    feature('Administrator accounts','PARTIALLY WORKING','Real account list response in route survey; identity lifecycle tests','No fresh full UI account creation/binding journey in U5O')
    feature('Faculty profile','PARTIALLY WORKING','Own profile GET 200 and route load; dashboard backend metadata cases','Read-only; complete institutional roster/allowance metadata unqualified')
    feature('Faculty preferences save and reload','WORKING','D16-I01 real Compact/importance write, reload and read','Calendar editing/ranking permutations are not all browser exercised')
    feature('Eligibility metadata and preference validation','PARTIALLY WORKING','458-case dashboard suite and actual eligible-subject reads','Institutional eligibility completeness is not established')
    feature('Read-only subject catalog','WORKING','D16-I02 actual API-backed SYN101 displayed','Fictional catalog; not academic CRUD')
    feature('Catalog search, filters and all sort modes','NOT TESTED','385 contracts and prior intercepted-browser evidence reviewed','Fresh live journey reads catalog; does not click every filter')
    feature('Temporary subject drafts','PARTIALLY WORKING','Working-tree source and frontend contracts','React page memory only; no server persistence or GA activation')
    feature('Faculty assignment viewer','PARTIALLY WORKING','Actual route survey and source schedule-derived selector','Not a roster editor; zero-assignment faculty are absent from selector')
    feature('Room assignment viewer','PARTIALLY WORKING','Actual route survey; WeeklySchedule rendering elsewhere','Not room catalog/closure administration')
    feature('Academic resource preparation','PARTIALLY WORKING','Phase 4C foundation, metadata APIs, validators and planner','No integrated authoritative resource editing/intake activation journey')
    feature('External CSV/XLSX intake preview','PARTIALLY WORKING','Dashboard parser, auth and discrepancy regressions; UI contracts','Fresh live journey does not enter/import every preview format')
    feature('External calendar and reconciliation','PARTIALLY WORKING','Dashboard validation/reconciliation regressions','Not every actual calendar/resource-selection control was clicked')
    feature('Printable handoff','PARTIALLY WORKING','Preview integrity regressions and existing print stylesheet','Native browser print dialog and physical output NOT TESTED')
    feature('Durable GEC ledger read','WORKING','D16-I02 real confirmed record selector and history read','Historical trust explicitly NOT_RECHECKED; fictional issuer')
    feature('GEC confirmation/revisions UI writes','PARTIALLY WORKING','Real API fixture setup and dashboard transaction tests','No fresh complete confirmation authoring UI journey; production providers absent')
    feature('Fixed V1 dashboard execution','PARTIALLY WORKING','Original engine/checkpoint parity and intercepted control browser tests','No fresh actual V1 stream-to-Live-Center browser run in U5O')
    feature('Fixed constrained V2 execution','WORKING','D16-I03 actual confirmed scope -> V2 generation UI/API','Explicitly fictional independent trust/capture providers')
    feature('Generated proposal timetable','WORKING','D16-I04 actual V2 result and timetable rendered','Not every timetable filter/library toolbar action verified')
    feature('Own faculty timetable after application','WORKING','D16-L07/I05 actual refresh, exact published version and empty-cohort case','Production publication directory unavailable')
    feature('Adjustment draft/submit/status/history','WORKING','D16-L02/L07 actual UI/HTTP/SQLite lifecycle','No claim that submission approves or changes schedule')
    feature('Withdrawal and reject UI variants','PARTIALLY WORKING','Backend state/ownership tests; rejection via real API','Not all UI variants clicked')
    feature('Chair filtering and approval','WORKING','D16-L03 real filtered queue, preview, explanation and confirmation','Independent fictional Chair appointment, not admin authority inference')
    feature('Controlled application and refresh','WORKING','D16-L04-L12 real rollback, confirmation, concurrency and published versions','First publication source was an explicit fixture handoff')
    feature('Application preview during history outage','BROKEN','U5O-A01 real HTTP/browser characterization','Ancillary history failure clears valid preview/action controls')
    feature('First publication designation','PARTIALLY WORKING','Fixture handoff and immutable D13 version chain','No normal production authority/UI designation workflow')
    feature('Advanced analysis and workload charts','PARTIALLY WORKING','Actual V2 original-fitness view; analysis/contracts tests','No empirical satisfaction or universal continuous-worker analysis bridge')
    feature('Historical comparisons and export','PARTIALLY WORKING','Backend archive/export regressions and read-only route survey','No complete native download/CSV research-package browser acceptance')
    feature('Live Optimization Center','PARTIALLY WORKING','Working-tree UI contracts/intercepted browser; source uses GAContext','Presentation over V1; not K/L continuous worker integration')
    feature('Legacy Saved Best cross-context comparison','BROKEN','Actual save decision with mocked incompatible payloads','No real Saved Best altered; shared-context integrity risk')
    feature('Immutable bundle/H optimizer consumption','WORKING','Actual engine, strict checkpoint, source and RNG integration tests','Internal contract; not public institutional CURRENT eligibility')
    feature('Continuous HTTP/UI execution','INTENTIONALLY DISABLED','Readiness GET only; no executable worker bridge configured','Must remain disabled in existing application')
    feature('Bounded K/L worker internals','WORKING','Native worker, ownership, fencing, SQLite and parity acceptance','Fictional SDK profile, not user-accessible seven-day application')
    feature('Institutional restore/deployment storage','INTENTIONALLY DISABLED','Missing approved root/issuer/anti-rollback activation contract','Quarantine is not writable restoration of an active worker')
    feature('Authorized quarantine','PARTIALLY WORKING','U5N recovery acceptance rerun with fictional authority','No active-worker restoration, deletion or automatic reconciliation')
    feature('Institutional academic context/CURRENT','INTENTIONALLY DISABLED','U5A-C compatibility and default provider source','No verified academic year/term/dataset source; no silent inference')
    feature('Authoritative faculty cohort completeness','PARTIALLY WORKING','F1/F1.5 and current Functions.py loader','GA pool still comes from legacy preference CSV; not all accounts')
    feature('Current Option B target/load ceiling','WORKING','Faculty constructor, synthetic scoring/constraint regressions','Developer/project interpretation; no new institutional approval claimed')
    feature('Target-relative fairness','PARTIALLY WORKING','Preserved policy counterexample and scorer source','Alternative fitness dispatch remains experimental; baseline rounding can favor concentration')
    feature('Specialization objective/metric','PARTIALLY WORKING','Eligibility enforced; descriptive domains and F3 qualification','No approved alignment rubric or production soft objective')
    feature('Authoritative availability persistence','PARTIALLY WORKING','F4 qualification, reset source and fictional resource tests','V1 reset clears faculty/room booleans; preassignment is not fixed time')
    feature('Seven-day optimization experiment','INTENTIONALLY DISABLED','K maximum 600s/20 generations and deployment readiness findings','No 30min/6h/24h/168h gate executed')
    feature('Unreferenced legacy source stubs','PLACEHOLDER','Fourteen empty TS/TSX modules; import reachability checked','Not fourteen visible placeholder pages; no cleanup in audit')
    feature('Empirical usability/faculty satisfaction','NOT TESTED','No institutional participants or approved instrument','Preference matching metrics are not empirical satisfaction scores')
    feature('Owned backend outage and retry','WORKING','D16-I06 actual server stop and protected portal clearing','Not a physical PostgreSQL outage or seven-day reconnect test')
    feature('Complete research-result export package','PARTIALLY WORKING','Existing per-history JSON/CSV plus research benchmark artifacts','No integrated seed/config/candidate/events/metrics export for continuous worker')
    new('feature-matrix.json',dict(unit='48 capability groups, distinct from 366 static JSX sites',scope='WORKING only in explicitly tested isolated context; institutional authorization remains unavailable',counts=dict(collections.Counter(r['status'] for r in rows)),rows=rows))
    controls=[]
    for original in frontend['interactive_sites']:
        r=dict(original);file=r['file'];label=r['label'];status='NOT TESTED';proof='No matching actual end-to-end control action asserted'
        if file.endswith('/Login.tsx') and r['tag'] in {'input','button','form'}:status='WORKING';proof='Actual repeated login form interaction, not all invalid-input combinations'
        elif file.endswith('/AccountMenu.tsx') and r['tag']=='button':status='WORKING';proof='Actual sign-out and session retry contexts'
        elif file.endswith('/FacultyPreferenceEditor.tsx') and 'Save Preferences' in label:status='WORKING';proof='D16-I01 actual write and reload'
        elif file.endswith('/ConstrainedRunPanel.tsx') and ('Start constrained V2' in label or 'Check confirmed constraints' in label or str(r['attributes'].get('aria-label','')).startswith('"V2')):status='WORKING';proof='D16-I03 actual fictional confirmed-scope generation'
        elif file.endswith('/Requests.tsx') and ('Approve pending application' in label or 'Confirm decision' in label):status='WORKING';proof='D16-L03 actual independent Chair approval'
        elif file.endswith('/AdjustmentRequests.tsx') and any(k in label for k in ['Validate proposal','Save draft request','Submit for Chair review','Confirm submission']):status='WORKING';proof='D16-L02 actual own request workflow'
        elif file.endswith('/ScheduleApplications.tsx') and 'Revalidate application' in label:status='BROKEN';proof='U5O-A01 valid preview cleared by history-only 503'
        elif file.endswith('/ScheduleApplications.tsx') and any(k in label for k in ['Apply adjustment','Confirm application']):status='WORKING';proof='D16-L05/L06 actual rollback/recovery and atomic apply'
        elif file.endswith('/OptimizationMode.tsx'):status='INTENTIONALLY DISABLED' if 'Start Optimization' in label else 'PARTIALLY WORKING';proof='Public continuous execution disabled; intercepted UI/readiness evidence only'
        elif r['tag'] in {'FullCalendar','LineChart','BarChart','ComposedChart'}:status='PARTIALLY WORKING';proof='Rendering/contracts in selected contexts; not every calendar/chart action exercised'
        r.update(status=status,verification_basis=proof);controls.append(r)
    new('control-classification.json',dict(unit='Static JSX sites, including generated-list definitions once; library-generated DOM controls and repeated mounted instances are different counts',counts=dict(collections.Counter(r['status'] for r in controls)),rows=controls))
    empty=[p.relative_to(ROOT).as_posix() for p in (ROOT/'frontend/src').rglob('*') if p.is_file() and p.suffix in {'.ts','.tsx'} and not p.stat().st_size]
    reachable=set()
    def visit(n):
        if n in reachable:return
        reachable.add(n)
        for p in frontend['imports'].get(n,[]):visit(p)
    visit('frontend/src/main.tsx')
    new('empty-source-stubs.json',dict(files=[dict(path=p,reachable_from_main=p in reachable) for p in empty],scope='Source placeholders only, not visible page count'))
    # Connect static URL templates to the actual effective backend registry.
    traces=[]
    for row in frontend['page_traceability']:
        calls=[]
        for req in frontend['http_callsites']:
            if req['file'] not in row['source_files']:continue
            url=req['url_template'];normalized=re.sub(r'^\$\{(?:API_BASE|API_BASE_URL)\}','',url).split('?')[0]
            candidates=[]
            if normalized.startswith('/'):
                concrete=re.sub(r'\$?\{[^}]*\}','x',normalized)
                for endpoint in backend['rows']:
                    pattern='^'+re.sub(r'\{[^}]+\}','[^/]+',endpoint['path'])+'/?$'
                    if re.fullmatch(pattern,concrete) and (req['method']==endpoint['method'] or req['method']=='GET_OR_DYNAMIC_OPTIONS'):
                        candidates.append(dict(method=endpoint['method'],path=endpoint['path'],backend_file=endpoint['file'],backend_line=endpoint['line'],dependencies=endpoint['dependencies'],service_calls=endpoint['direct_calls']))
            calls.append({**req,'candidate_backend_routes':candidates,'link_status':'STATIC_MATCH' if candidates else 'DYNAMIC_OR_MANUAL_REVIEW_REQUIRED'})
        traces.append(dict(page=row['page'],component_closure=row['source_files'],handler_http_links=calls,scope='Potential import reachability, not per-control causality. Ancestor Auth/GA providers add calls. Live route observations are separately retained.'))
    new('frontend-backend-traceability.json',dict(pages=traces,endpoint_method_pairs=backend['endpoint_method_pairs'],runtime_route_survey=str(latest('*/captures/route-survey.json').relative_to(ROOT)),route_urls=frontend['distinct_route_urls']))
    issues=[]
    def issue(id,severity,kind,area,expected,actual,cause,reproduce,fix,accept,tests,complexity,milestone,deps):
        issues.append(dict(id=id,severity=severity,kind=kind,affected_workflow=area,expected_behavior=expected,actual_behavior=actual,root_cause=cause,reproduction_steps=reproduce,proposed_fix=fix,acceptance_criteria=accept,tests_required=tests,estimated_complexity=complexity,recommended_milestone=milestone,dependencies=deps))
    issue('O-P0-01','P0','CONDITIONAL_DATA_INTEGRITY_RISK','Legacy Saved Best','Compare or replace only within a verified compatible evaluation context','Subject-key equality permits comparison across incompatible inputs/configurations','save_best_if_better checks subject sets and raw numeric fitness, not policy/input/configuration provenance',
        ['Run u5o-audit; inspect legacy-saved-best-characterization.json','Same fictional subject keys, different input/configuration fingerprints: score 90 saves against 100; 110 does not'],
        'Keep new research realm away from legacy stores; separately approve and version persistence eligibility before changing legacy save behavior',['No comparison/replacement across incompatible contexts','Zero preserved exactly','Existing historical bytes retained'],['Mocked decision regression','Actual compatible/incompatible isolated payload/store tests','Saved-seed and checkpoint regressions'],'L','U5P contract / separate versioned persistence milestone',['U5B/F2C compatibility contract','Explicit persistence-change approval'])
    issue('O-P1-01','P1','INTENTIONAL_SAFETY_GATE','Research-demo admission and HTTP/UI','A server-owned fictional realm can run without genuine institutional authority','Public readiness remains disabled; K/L workers are internal; no research operator/profile exists','configured_service returns None; institutional providers cannot be replaced by role flags',
        ['GET bound-runs capabilities/readiness in isolated tests','Inspect worker module registration and mode selector'],
        'Design a separately gated loopback fictional-only app factory with fresh stores, explicit demo identity and frozen server-created bundle; preserve production defaults',['Cannot reach institutional paths, data or issuers','No main-route redirection or Saved Best promotion','Persistent fictional banner and finite scope'],['Cross-realm/department/owner negatives','Real browser start/status/pause/resume/stop','No institutional dependency access'],'L','U5P design, U5Q bounded bridge',['Demo authority contract','Immutable input capture','Storage namespace'])
    issue('O-P1-02','P1','LONG_RUN_CONTRACT_GAP','168-hour controller','One continuing population/RNG/best under an explicit bounded experiment deadline','K caps wall at 600 seconds and total generations at 20','Worker is a short fictional qualification profile, not a seven-day release',
        ['Inspect Limits.validate and WorkerStore deadlines','Do not start a seven-day run through fixed-generation controls'],
        'Specify a separately versioned long-duration continuation/stopping contract; do not fake continuous mode with repeated fresh runs or arbitrarily large generation settings',['Deadline/paused time and clock jumps defined','Exact population/RNG/best continuity','Bounded safe and forced stop behavior'],['Batch equivalence and RNG parity','Pause/restart/deadline/clock tests','Increasing stability gates'],'XL','U5R',['U5Q bounded integration','Version/checkpoint policy review'])
    issue('O-P1-03','P1','LONG_RUN_STORAGE_GAP','Checkpoint/backup/restore retention','Bounded storage with durable fresh recovery for full experiment','K defaults eight checkpoints, L one backup/64 process attempts; N chain at most eight and quarantine only','No approved rotation/activation or independent host freshness/fencing contract',
        ['Inspect K/L/N limits and retention-disabled responses'],
        'Design versioned retention, telemetry and restore reconciliation with independently anchored ownership; never delete old chain elements under current codecs',['No invalid lineage or rollback','Post-commit uncertain quarantine stays inert','Disk-full recovery and owner fencing'],['Real quota exhaustion','Crash windows','Concurrent replay/cross-run recovery','Backup freshness and old-owner denial'],'XL','U5R',['Independent freshness anchor','Explicit recovery/retention policy'])
    issue('O-P1-04','P1','HOST_READINESS_GAP','Windows seven-day host','Sufficient measured headroom and an approved supervised/power plan','1.69 GiB free RAM at inspection; AC idle hibernate 12h; lid closure sleeps; parent/host quotas unqualified','Default laptop policy and short child-only resource profile',
        ['Read machine-readiness.json','Review U5N parent findings and development --reload launcher'],
        'Before a later experiment, obtain explicit power/deployment approval, freeze source, budget helper processes and monitor host memory/disk; change no setting in U5O',['No unowned process termination','Lid/sleep/update/restart plan','Resource thresholds measured on representative fictional fixtures'],['Parent/child and helper topology','RAM/disk pressure','Interrupted/resumed long-run tests'],'L','U5R/U5S',['User approval for any OS changes','Representative scale data'])
    issue('O-P1-05','P1','RESEARCH_TELEMETRY_GAP','Continuous research exports','Durable exact generation/configuration/seed/constraint/event metrics and exports','Existing history/analysis APIs target legacy namespaces; K/L are not wired to them; logs truncate','No continuous DTO/export bridge; fitness evaluation count is null',
        ['Inspect metrics-availability.json and Worker.status','Compare K/L store to ga_history/advanced analysis routes'],
        'Version a read-only metric/export contract over the same bound checkpoint/results with explicit time bases and missing-data semantics',['No rescore or incompatible comparison','Full history despite UI display windows','Failures and missing observations exported'],['Exact zero and monotonicity','Reload/restart telemetry','CSV/JSON schema and download parity','No credential/raw-checkpoint exposure'],'L','U5R',['U5Q HTTP boundary','Frozen metric definitions'])
    issue('O-P1-06','P1','INSTITUTIONAL_DATA_DEPENDENCY','IT cohort and historical comparator','Approved term-specific IT roster, eligibility, resources and comparison schedule','Legacy preference CSV still determines GA pool; complete IT/IS dependencies and historical comparison are unqualified','No authoritative roster producer or approved complete benchmark record',
        ['Read F1/F1.5 and R1 packages','Inspect Functions.py cohort construction; do not expose faculty rows'],
        'Obtain and qualify institutional data for thesis/institutional claims; use explicit complete fictional cohorts for demo research meanwhile',['No fabricated IS records','No silent missing allowances or identities','Term/revision/source bound'],['Roster completeness without preferences','Eligibility edge cases','Approved historical schedule mapping'],'L','Separate data qualification',['Adviser/department data and use approval; not prerequisite for fictional demo'])
    issue('O-P1-07','P1','POLICY_QUALIFICATION_GAP','Workload fairness and zero-target exceptions','Explicitly approved, versioned workload interpretation and comparisons','Legacy quantized workload score can favor concentration; experimental policy/zero-target authority not integrated','Original scoring intentionally preserved; shared dispatch/authority integration remains gated',
        ['Read fairness counterexample and F2C-F2I reports','Inspect current scorer and Faculty required target calculation'],
        'Record legacy policy limitations in experiments; integrate only after versioned dispatch, zero-target authority and compatibility approval',['No mixed-policy comparisons','No unauthorized zero-target teaching exception','No silent academic policy changes'],['Unequal targets/underload/overload/zero assignments','Operators and best/checkpoint consistency'],'XL','Separate F2 implementation',['Adviser/department policy as applicable','Approved scoring integration'])
    issue('O-P1-08','P1','AVAILABILITY_CONTRACT_GAP','Authoritative room/faculty closures','Permanent commitments survive restart while temporary bookings reset','Legacy reset reopens room/faculty flags; V2 explicit fixed snapshots are separate','Temporary and authoritative boolean state share legacy calendars',
        ['Read F4A/F4B and reset helpers','Compare section blocks and V2 immutable external commitments'],
        'Implement the reviewed versioned availability contract in a separately authorized milestone; do not treat preassigned resources as fixed meeting times',['Faculty/room/section commitments all enforced','Adjacent intervals allowed','No grandfathered checkpoint reinterpretation'],['All reset/reconstruction/restart/operator boundaries','Source changes and invalid commitments'],'L','Separate F4 integration',['Approved availability authority and semantics'])
    issue('O-P2-01','P2','REPRODUCED_UI_DEFECT','Schedule application revalidation','History-only failure leaves independently valid preview usable with separate error/retry','open awaits publishedVersions; run catch clears detail and Apply control','Coupled preview/history request chain in ScheduleApplications.tsx',
        ['Run d16-live --working-ui','U5O-A01: inject history-only 503, click Revalidate; API preview still can_apply=true while UI clears it'],
        'Separate ancillary history state/error/retry from authoritative preview; retain fail-closed behavior for actual preview/authority/staleness failures',['History outage does not erase valid review','Fresh apply command/approval checks remain mandatory','No stale review after filter/account changes'],['Real browser history-only failure and recovery','Preview/authority failure negatives','Concurrent revision change'],'M','U5P',['Independent history state'])
    issue('O-P2-02','P2','WORKFLOW_DEPENDENCY','First baseline publication','Clear authorized designation before adjustment/application workflow','D16 uses an explicit fictional file handoff; no normal first-publication UI/provider','Institutional designation policy/provider intentionally absent',
        ['Inspect D16-I04 and published source providers'],
        'Provide explicit fictional-only designation in an isolated demo; obtain real first-publication policy separately',['Printing/generation/Chair review never imply publication','Prior versions immutable'],['Unauthorized/replayed designation','Published head consistency'],'L','U5Q demo / separate institutional policy',['Independent designation authority'])
    issue('O-P2-03','P2','SCOPE_LIMITATION','Faculty/room pages and academic preparation','Users understand catalog/availability versus assigned timetable views','Faculty/rooms derive selectors from GA schedule; draft subjects are memory-only','Existing pages are result viewers, not authoritative resource administration',
        ['Visit /admin/faculty and /admin/rooms without GA result','Inspect SubjectDrafts notice and state'],
        'Clarify labels and plan bounded read-only cohort/resource overview before approved durable academic CRUD',['Zero-assignment faculty not misrepresented as absent roster','Drafts never imply persistence or eligibility'],['Empty/loading/error and complete-cohort view tests'],'M','U5P usability / later approved resource work',['Authoritative metadata for institutional editing'])
    issue('O-P2-04','P2','AUDIT_INFRASTRUCTURE_DEFECT','Endpoint inventory tests','Inventory all included routes and inherited dependencies','Flat app.routes scans miss lazy _IncludedRouter entries in installed FastAPI','Old APIRoute-only introspection assumption',
        ['Inspect first failed u5o-audit record','Compare effective route contexts against OpenAPI: 103 method/path pairs'],
        'Adopt a shared tested effective-route inventory utility in later test maintenance; U5O uses correct traversal only in its new audit',['OpenAPI paths covered','Inherited auth dependencies preserved','Absence tests do not vacuously pass'],['Installed framework traversal regression'],'S','U5P test repair',['FastAPI version-aware testing'])
    issue('O-P2-05','P2','INTEGRATION_NOT_TESTED','Actual V1 Live Center','Real fixed stream/result reaches Overview/Research/Console under a bound run','Working UI passes 385 contracts and intercepted controls; live journey exercises V2 branch','V1 GAContext, V2 views and internal continuous worker are separate paths',
        ['Compare source imports and actual route-survey responses','Do not interpret intercepted HTTP as live worker evidence'],
        'Add a complete isolated actual V1 HTTP/browser fixture, then version the continuous bridge without conflating result formats',['Actual data/progress/logs/reconnect verified','No synthetic fallback metrics'],['Start/pause/resume/stop, disconnect/reload and result validation'],'M','U5Q',['Complete fictional fixed-input fixture'])
    issue('O-P2-06','P2','METHODOLOGY_DEPENDENCY','Specialization evaluation','Approved rubric distinguishes specialization alignment from eligibility','Hard eligibility exists; no approved soft specialization metric/objective','F3 policy/data qualification remains incomplete',
        ['Read F3C and metrics inventory'],
        'Define rubric/data/denominator with adviser/department; do not fabricate scores or silently change fitness',['Unknown stays unavailable','Alignment not equated with eligibility'],['Multiple eligible candidates','Unknown/ambiguous domain mappings'],'M','Separate F3 qualification',['Adviser/department rubric approval'])
    issue('O-P3-01','P3','UNTESTED_SCALE_USABILITY','Charts/history/console long-run use','Bounded responsive presentation with complete exported evidence','UI windows/log buffers bound visible history; 168h UI behavior untested','Short-run presentation and retention contracts',
        ['Inspect Live chart limit 240 and log limits','Review full versus display-window semantics'],
        'After correctness, measure long-history rendering and provide clear omitted-data/export affordances',['No invented points','Missing/dropped logs explicit','No performance claim without measurement'],['Large synthetic histories and browser memory/reconnect'],'M','After U5R',['Durable telemetry contract'])
    issue('O-P3-02','P3','USABILITY_GAP','Admin preference metadata error','Consistent retry without losing safe edits','PreferencesReview requires page refresh after initial faculty-load failure','One-shot effect and refresh text rather than inline retry',
        ['Inspect PreferencesReview error path'],
        'Add a guarded explicit retry if separately scoped; preserve dirty/saving protections',['Retry does not change faculty binding or discard edits silently'],['Error/retry and dirty-form cases'],'S','U5P optional',['No policy change'])
    issue('O-P4-01','P4','UNREFERENCED_PLACEHOLDERS','Legacy source modules','No confusion about unused skeletons','Fourteen empty TS/TSX files; no active placeholder page found','Unreferenced old scaffolding',
        ['Read empty-source-stubs.json'],
        'Leave unchanged now; remove only in later authorized cleanup after import checks',['No behavior change'],['Import/build regression'],'S','Deferred cleanup',['Separate cleanup authorization'])
    new('repair-backlog.json',dict(priority_order=['P0','P1','P2','P3','P4'],new_production_fixes_implemented=False,issues=issues))
    metrics=[
        ('Initial fitness','RECORDED','V1 generation-zero telemetry / H history','Must bind input/policy/config and treat zero exactly'),
        ('Best-so-far fitness','RECORDED','V1/H/K result/history','Not shared Saved Best across incompatible contexts'),
        ('Fitness versus generation','RECORDED','GenerationMonitor/history','UI window is not full history'),
        ('Fitness versus elapsed time','PARTIAL','elapsed_ms and generation_elapsed_ms','Define active/paused/wall/validation time; no continuous export bridge'),
        ('Improvement events','RECORDED_OR_DERIVED','best_ever_improvement and history differences','Stagnation is not proof of optimality'),
        ('Generation throughput','DERIVABLE','Generation and elapsed deltas','Do not call null fitness_evaluations_total an evaluation rate'),
        ('Hard-constraint violation count','PARTIAL','Publication validation / advanced analysis categories','Unknown/unvalidated capacity/source constraints must not become zero'),
        ('Unassigned offerings','PARTIAL','Validated coverage against required captured offerings','Not just displayed schedule row count; failed search is not zero unassigned'),
        ('Specialization alignment','UNAVAILABLE','Descriptive domains and F3 experimental evidence','No approved rubric; eligibility is distinct'),
        ('Subject preference satisfaction','PARTIAL','Candidate-bound advanced analysis','Mechanical matching, not empirical satisfaction; H/K API bridge absent'),
        ('Time/day preference satisfaction','PARTIAL','Frozen preference-context analysis','Never recompute historical quality from changed live preferences'),
        ('Teaching-load distribution','RECORDED','faculty_analysis/workload observations','Denominator is supplied cohort, not automatically all registered faculty'),
        ('Workload balance','PARTIAL','Targets/deviations in analysis and legacy workload score','Legacy score has known fairness counterexample; report policy version'),
        ('Convergence/stagnation','PARTIAL','generations_without_improvement','No global optimality or seven-day evidence'),
        ('Approved IT historical comparison','UNAVAILABLE','Same-context generation comparison exists','Approved complete term-specific comparison schedule unavailable'),
        ('Experiment configuration','PARTIAL','Configuration/input/engine fingerprints and bundles','Academic source qualification and complete experiment manifest absent'),
        ('Seed/reproducibility','PARTIAL','Initial RNG and checkpoint state','No normal seed export/control; keep source release and inputs fixed'),
        ('Checkpoint/interruption history','PARTIAL','I/K/L events, checkpoints and native recovery','Not continuous dashboard telemetry; N restore quarantines only'),
        ('Full research CSV/summary','UNAVAILABLE','Existing history CSV/JSON and independent benchmark reports','No integrated full trial/config/failure/seed/faculty/events package')]
    new('metrics-availability.json',dict(rows=[dict(metric=a,status=b,current_source=c,limitation=d) for a,b,c,d in metrics],proposed_outputs=['experiment_manifest.json','generations.csv','improvements.csv','faculty_metrics.csv','violations.csv','checkpoint_events.csv','failures.csv','thesis-summary.md','plots with axes/units/policy/provenance'],proposal_only=True))
    gates=[]
    for hours,label in [(.5,'30-minute functional'),(6,'6-hour stability'),(24,'24-hour soak'),(168,'168-hour research')]:
        gates.append(dict(name=label,duration_hours=hours,status='NOT_RUN; CURRENT_RELEASE_NO_GO',prerequisites=['Separately approved fictional research realm and versioned duration/continuation policy','Prior shorter gate passed','Measured representative input/host headroom','Owned persistent storage, telemetry/export and recovery contract','Reviewed user power/update/restart plan'],pass_criteria=['One continuing population/RNG/best and one owner','No hard-invalid successful candidate, lost required observations or mixed contexts','Authorized pause/resume/browser reconnect and process restart where specified','Bounded memory/disk and exact exported record consistency'],stop_conditions=['Identity/bundle/config/lineage mismatch','Unauthorized action or unexpected path/database access','NaN or best-ever regression','Missing required metrics or corrupt checkpoint','Resource/disk floor exceeded or unsupported power/resume state'],measurements=['Generation and wall/CPU time','Process working set and private commit separately','Checkpoint bytes/write duration','Disk/telemetry growth and loss','Interruptions/authority and operator actions']))
    new('seven-day-gates.json',dict(current_status='NO_GO',gates=gates,engineering_budget_proposals_not_enforced=dict(available_physical_memory_start_floor_bytes=2*1024**3,available_disk_start_floor_bytes=10*1024**3,free_disk_floor_bytes=5*1024**3,one_active_worker=True),limitations='Provisional engineering floors require representative measurement; no OS setting or worker limit changed. Existing profile supports at most 600s, not even the 30-minute gate.'))
    print(json.dumps(dict(feature_groups=len(rows),feature_status_counts=dict(collections.Counter(r['status'] for r in rows)),static_controls=len(controls),control_status_counts=dict(collections.Counter(r['status'] for r in controls)),backlog_issues=len(issues),empty_modules=len(empty),runtime_page_visits=len(survey['rows']),runtime_dom_occurrences=sum(len(r['controls']) for r in survey['rows']),metrics=len(metrics))))

if __name__=='__main__':main()
