import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import axios from "axios";
import { getFacultyPreference, updateFacultyPreference } from "../../api/preferences";
import type { FacultyPreferenceUpdate } from "../../api/preferences";
import { getFacultySubjects } from "../../api/subjects";
import type { AvailableSubject } from "../../api/subjects";
import type { FacultySummary } from "../../api/faculty";
import PreferenceCalendar from "./PreferenceCalendar";
import { CATEGORIES, IMPORTANCE_OPTIONS, editablePreference, filterSubjects, importanceVisible, isDirty, isEligible, rankSubject, validationIssues, withBlocks } from "./preferenceModel";
import "./preferences.css";

interface Props {
  facultyCode: number;
  facultyId?: string;
  adminMode?: boolean;
  onEditStateChange?: (dirty: boolean, saving: boolean) => void;
}
function Importance({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return <label className="preference-label max-w-xs">{label}<select className="preference-input" value={value} onChange={event => onChange(Number(event.target.value))}>
    {IMPORTANCE_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
  </select></label>;
}
function Section({ number, title, description, children }: { number: number; title: string; description?: string; children: ReactNode }) {
  return <section className="preference-section" aria-labelledby={`preference-section-${number}`}>
    <h2 id={`preference-section-${number}`} className="text-lg font-semibold text-slate-900"><span className="mr-2 text-sm text-slate-400">{number.toString().padStart(2, "0")}</span>{title}</h2>
    {description && <p className="mb-4 mt-1 text-sm text-slate-500">{description}</p>}{children}
  </section>;
}
export default function FacultyPreferenceEditor({ facultyCode, facultyId, adminMode = false, onEditStateChange }: Props) {
  const [draft, setDraft] = useState<FacultyPreferenceUpdate | null>(null);
  const [saved, setSaved] = useState<FacultyPreferenceUpdate | null>(null);
  const [faculty, setFaculty] = useState<FacultySummary | null>(null);
  const [subjects, setSubjects] = useState<AvailableSubject[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("ALL");
  const [showAll, setShowAll] = useState(false);
  const [allSubjects, setAllSubjects] = useState<AvailableSubject[] | null>(null);
  const [browsingLoading, setBrowsingLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [message, setMessage] = useState("");
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [dragging, setDragging] = useState<string | null>(null);
  const dirty = !!draft && !!saved && isDirty(draft, saved);
  const saving = saveState === "saving";
  useEffect(() => {
    let cancelled = false;
    Promise.all([getFacultyPreference(facultyCode), getFacultySubjects(facultyId ?? facultyCode)]).then(([preference, metadata]) => {
      if (cancelled) return;
      // Numeric preference route remains a compatibility adapter; metadata uses stable identity.
      const { faculty_code: _code, ...values } = preference;
      void _code;
      const editable = editablePreference(values);
      setDraft(editable); setSaved(editable); setFaculty(metadata.faculty); setSubjects(metadata.data);
    }).catch(() => { if (!cancelled) setLoadError("Unable to load preferences. Refresh this page to try again."); });
    return () => { cancelled = true; };
  }, [facultyCode, facultyId]);
  useEffect(() => { onEditStateChange?.(dirty, saving); }, [dirty, saving, onEditStateChange]);
  useEffect(() => {
    if (!dirty && !saving) return;
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty, saving]);
  useEffect(() => {
    if (!showAll || allSubjects) return;
    let cancelled = false;
    getFacultySubjects(facultyId ?? facultyCode, false).then(metadata => {
      if (!cancelled) { setAllSubjects(metadata.data); setBrowsingLoading(false); }
    }).catch(() => { if (!cancelled) { setMessage("Unable to load all offered subjects. Eligible subjects are still available."); setBrowsingLoading(false); } });
    return () => { cancelled = true; };
  }, [showAll, allSubjects, facultyCode, facultyId]);
  function change(values: Partial<FacultyPreferenceUpdate>) {
    setDraft(current => current ? { ...current, ...values } : current); setSaveState("idle"); setMessage("");
  }
  function reorder(code: string, rank: number) { if (draft) change({ preferred_subjects: rankSubject(draft.preferred_subjects, code, rank) }); }
  function removeSubject(code: string) {
    if (!draft) return;
    const next = withBlocks(draft, draft.preferred_schedule_blocks.filter(block => block.subject_code !== code));
    change({ ...next, preferred_subjects: draft.preferred_subjects.filter(item => item !== code) });
  }
  async function save() {
    if (!draft || !dirty || saving) return;
    if (validationIssues(draft, subjects).length) return;
    setSaveState("saving"); setMessage("");
    try {
      const result = await updateFacultyPreference(facultyCode, draft);
      const { faculty_code: _code, ...values } = result; void _code;
      const editable = editablePreference(values);
      setSaved(editable); setDraft(editable); setSaveState("saved");
    } catch (reason) {
      const detail = axios.isAxiosError(reason) ? reason.response?.data?.detail : null;
      setMessage(typeof detail === "string" ? detail : "Your changes could not be saved. They are still here; please try again."); setSaveState("failed");
    }
  }
  if (loadError) return <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-700">{loadError}</p>;
  if (!draft || !saved || !faculty) return <p role="status" className="p-4 text-slate-500">Loading faculty preferences…</p>;
  const visible = filterSubjects(showAll && allSubjects ? allSubjects : subjects, category, search, showAll);
  const issues = validationIssues(draft, subjects);
  const selected = draft.preferred_subjects.map(code => subjects.find(subject => subject.subject_code === code)).filter((subject): subject is AvailableSubject => !!subject && isEligible(subject));
  const stateLabel = saving ? "Saving…" : saveState === "failed" ? "Save failed" : dirty ? "Unsaved changes" : saveState === "saved" ? "Saved" : "No changes";
  return <div className="preference-editor space-y-4">
    {issues.length > 0 && <div role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <strong>Review older preferences before saving</strong><ul className="mt-2 list-disc space-y-1 pl-5">{issues.map(issue => <li key={issue}>{issue}</li>)}</ul>
      <button type="button" className="preference-button mt-3" disabled={saving} onClick={() => { if (window.confirm("Clear all schedule preferences? Your ranked subjects will be kept.")) change(withBlocks(draft, [])); }}>Clear schedule preferences</button>
    </div>}
    <fieldset disabled={saving} className="min-w-0 space-y-4">
      <Section number={1} title="Preferred Subjects" description="Choose from subjects you are eligible to teach, then put your favorites first.">
        {faculty.specializations.length > 0 && <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-slate-500"><span>Expertise</span>{faculty.specializations.map(domain => <span key={domain} className="preference-tag">{domain}</span>)}<span>Eligibility is confirmed for each course.</span></div>}
        <label className="mb-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.use_subject_preference} onChange={event => change({ use_subject_preference: event.target.checked })} />Consider my subject preferences</label>
        <div className="grid items-start gap-5 lg:grid-cols-2">
          <div className="space-y-3">
            <label className="preference-label">Find a subject<input type="search" className="preference-input" placeholder="Search by code or title" value={search} onChange={event => setSearch(event.target.value)} /></label>
            <div className="flex flex-wrap gap-1" role="group" aria-label="Subject categories">{CATEGORIES.map(item => <button key={item} type="button" className="preference-category" aria-pressed={category === item} onClick={() => setCategory(item)}>{item}</button>)}</div>
            <label className="flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={showAll} onChange={event => { setShowAll(event.target.checked); setBrowsingLoading(event.target.checked && !allSubjects); }} />Show all offered subjects (eligibility still applies)</label>
            {browsingLoading && <p role="status" className="text-sm text-slate-500">Loading offered subjects…</p>}
            {visible.length === 0 ? <p className="preference-empty">{subjects.length === 0 && !showAll ? "No eligible offered subjects are currently available for this faculty member." : "No subjects match these filters."}</p> :
              <ul className="preference-subject-browser divide-y divide-slate-100 rounded-lg border border-slate-200">{visible.map(subject => {
                const preferred = draft.preferred_subjects.includes(subject.subject_code), eligible = isEligible(subject);
                return <li key={subject.course_id} className="flex items-start justify-between gap-3 p-3">
                  <div className="min-w-0"><strong className="text-sm">{subject.subject_code}</strong><p className="text-sm text-slate-600">{subject.subject_title}</p>
                    <div className="mt-1 flex flex-wrap gap-1">{eligible && <span className="preference-tag text-emerald-700">Eligible</span>}{preferred && <span className="preference-tag text-blue-700">Preferred</span>}{subject.preassignment_status !== "none" && <span className="preference-tag">Preassigned{subject.preassignment_status === "some" ? " sections" : ""}</span>}{subject.domains.map(domain => <span key={domain} className="preference-tag">{domain}</span>)}</div>
                    {!eligible && <p className="mt-1 text-xs text-slate-500">{subject.preassignment_status === "all" ? "Reserved for a preassigned instructor" : "Not eligible for this faculty member"}</p>}
                  </div>
                  <button type="button" className="preference-button shrink-0" disabled={!eligible || preferred} aria-label={`Add ${subject.subject_code} to preferred subjects`} onClick={() => { if (isEligible(subject) && !preferred) change({ preferred_subjects: [...draft.preferred_subjects, subject.subject_code] }); }}>{preferred ? "Added" : "Add"}</button>
                </li>;
              })}</ul>}
          </div>
          <div className="space-y-3"><h3 className="text-sm font-semibold">Your ranked preferences</h3><p className="text-xs text-slate-500">Drag to reorder, or choose a rank with the keyboard.</p>
            {draft.preferred_subjects.length === 0 ? <p className="preference-empty">No preferred subjects yet. Add a subject from the list.</p> : <ol className="space-y-2">{draft.preferred_subjects.map((code, index) => {
              const subject = subjects.find(item => item.subject_code === code);
              return <li key={code} className="flex items-center gap-2 rounded-lg border border-slate-200 p-3" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); const source = dragging ?? event.dataTransfer.getData("text/plain"); if (source) reorder(source, index + 1); setDragging(null); }}>
                <span draggable onDragStart={event => { setDragging(code); event.dataTransfer.setData("text/plain", code); event.dataTransfer.effectAllowed = "move"; }} onDragEnd={() => setDragging(null)} className="cursor-grab px-1 text-slate-400" aria-label={`Drag ${code} to reorder`}>⠿</span>
                <label className="sr-only" htmlFor={`rank-${code}`}>Rank for {code}</label><select id={`rank-${code}`} className="preference-input !mt-0 !w-14 !px-2" value={index + 1} onChange={event => reorder(code, Number(event.target.value))}>{draft.preferred_subjects.map((_, rank) => <option key={rank} value={rank + 1}>{rank + 1}</option>)}</select>
                <div className="min-w-0 flex-1"><strong className="text-sm">{code}</strong><p className="text-xs text-slate-500">{subject?.subject_title ?? "Older subject — eligibility needs review"}</p></div>
                <button type="button" className="preference-button" aria-label={`Remove ${code} from preferred subjects`} onClick={() => removeSubject(code)}>Remove</button>
              </li>;
            })}</ol>}
            {importanceVisible(draft.use_subject_preference) && <Importance label="Subject preference importance" value={draft.subject_importance} onChange={value => change({ subject_importance: value })} />}
          </div>
        </div>
      </Section>
      <Section number={2} title="Preferred Schedule">
        <PreferenceCalendar subjects={selected} blocks={draft.preferred_schedule_blocks} onChange={blocks => change(withBlocks(draft, blocks))} />
        {draft.preferred_schedule_blocks.length > 0 && <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div><label className="mb-2 flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.use_day_preference} onChange={event => change({ use_day_preference: event.target.checked })} />Consider preferred days</label>{importanceVisible(draft.use_day_preference) && <Importance label="Day preference importance" value={draft.day_importance} onChange={value => change({ day_importance: value })} />}</div>
          <div><label className="mb-2 flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.use_time_preference} onChange={event => change({ use_time_preference: event.target.checked })} />Consider preferred times</label>{importanceVisible(draft.use_time_preference) && <Importance label="Time preference importance" value={draft.time_importance} onChange={value => change({ time_importance: value })} />}</div>
        </div>}
      </Section>
      <div className="grid gap-4 lg:grid-cols-2">
        <Section number={3} title="Schedule Style" description="Prefer classes close together, or spread across your teaching day.">
          <fieldset className="space-y-2"><legend className="sr-only">Schedule style</legend>{[{ value: "No Preference", label: "No Preference" }, { value: "Compact", label: "Compact" }, { value: "Scattered", label: "Spread Out" }].map(option => <label key={option.value} className="flex items-center gap-2 text-sm"><input type="radio" name="schedule-style" value={option.value} checked={(draft.use_gap_preference ? draft.gap_preference : "No Preference") === option.value} onChange={() => change({ gap_preference: option.value as FacultyPreferenceUpdate["gap_preference"], use_gap_preference: option.value !== "No Preference" })} />{option.label}</label>)}</fieldset>
          {importanceVisible(draft.use_gap_preference, draft.gap_preference) && <div className="mt-3"><Importance label="Schedule style importance" value={draft.gap_importance} onChange={value => change({ gap_importance: value })} /></div>}
        </Section>
        <Section number={4} title="Lecture & Laboratory Preference" description="For subjects with both components, choose how their days relate.">
          <fieldset className="space-y-2"><legend className="sr-only">Lecture and laboratory days</legend>{[{ value: "No Preference", label: "No Preference" }, { value: "Same Day", label: "Same Day" }, { value: "Different Day", label: "Different Days" }].map(option => <label key={option.value} className="flex items-center gap-2 text-sm"><input type="radio" name="lecture-lab" value={option.value} checked={(draft.use_lecture_lab_preference ? draft.lecture_lab_preference : "No Preference") === option.value} onChange={() => change({ lecture_lab_preference: option.value as FacultyPreferenceUpdate["lecture_lab_preference"], use_lecture_lab_preference: option.value !== "No Preference" })} />{option.label}</label>)}</fieldset>
          {importanceVisible(draft.use_lecture_lab_preference, draft.lecture_lab_preference) && <div className="mt-3"><Importance label="Lecture and laboratory preference importance" value={draft.lecture_lab_importance} onChange={value => change({ lecture_lab_importance: value })} /></div>}
        </Section>
      </div>
      {adminMode && <details className="rounded-lg border border-slate-200 bg-white p-3"><summary className="cursor-pointer text-sm font-medium">Advanced administrator settings</summary><label className="preference-label mt-3 max-w-xs">Faculty priority<input className="preference-input" type="number" min={1} step={1} value={draft.faculty_priority} onChange={event => { const value = Number(event.target.value); if (Number.isInteger(value) && value >= 1) change({ faculty_priority: value }); }} /></label></details>}
    </fieldset>
    <div className="preference-save-bar flex flex-wrap items-center justify-between gap-3">
      <div><p role="status" aria-live="polite" className="text-sm font-medium">{stateLabel}</p>{message && <p role="alert" className="mt-1 text-sm text-red-700">{message}</p>}{dirty && issues.length > 0 && <p className="text-xs text-amber-800">Resolve the review warnings above to save.</p>}</div>
      <div className="flex gap-2"><button type="button" className="preference-button" disabled={!dirty || saving} onClick={() => { setDraft(saved); setSaveState("idle"); setMessage(""); }}>Discard</button><button type="button" className="preference-button preference-primary" disabled={!dirty || saving || issues.length > 0} onClick={save}>Save Preferences</button></div>
    </div>
  </div>;
}
