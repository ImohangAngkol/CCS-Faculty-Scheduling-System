import type { FacultySummary } from "../../api/faculty";
import type { FacultyPreferenceUpdate, PreferenceScheduleBlock } from "../../api/preferences";
import type { AvailableSubject, SubjectComponent, MeetingPattern } from "../../api/subjects";

export const CATEGORIES = ["ALL", "CCC", "ITD", "ITN", "ITE", "ISY", "OTHER"] as const;
export const DAYS = ["M", "T", "W", "TH", "F", "S"];
export const DAY_NAMES: Record<string, string> = { M: "Monday", T: "Tuesday", W: "Wednesday", TH: "Thursday", F: "Friday", S: "Saturday" };
export const REFERENCE_DATES: Record<string, string> = { M: "2026-09-28", T: "2026-09-29", W: "2026-09-30", TH: "2026-10-01", F: "2026-10-02", S: "2026-10-03" };
export const CALENDAR_EDITING = { eventStartEditable: true, eventDurationEditable: false, eventResizableFromStart: false };
export const IMPORTANCE_OPTIONS = [
  { value: 0, label: "No weight / informational only" },
  { value: 1, label: "Low (legacy minimum)" },
  { value: 2, label: "Low" }, { value: 3, label: "Medium" },
  { value: 4, label: "High" }, { value: 5, label: "Very High" },
];
export const normalFaculty = (rows: FacultySummary[]) => rows.filter(row => row.instructor_type === "optimization_faculty");
export const isEligible = (subject: AvailableSubject) => subject.eligibility?.explicitly_eligible === true && subject.offerings.some(offering => offering.can_be_assigned === true);
export function filterSubjects(rows: AvailableSubject[], category: string, search: string, showAll = false) {
  const query = search.trim().toLowerCase();
  return rows.filter(subject => (showAll || isEligible(subject)) && (category === "ALL" || subject.category === category)
    && `${subject.subject_code} ${subject.subject_title}`.toLowerCase().includes(query));
}
export function rankSubject(codes: string[], code: string, rank: number) {
  if (!codes.includes(code)) return codes;
  const next = codes.filter(item => item !== code);
  next.splice(Math.max(0, Math.min(next.length, rank - 1)), 0, code);
  return next;
}
export const realComponents = (subject: AvailableSubject) => subject.components.filter(component => component.weekly_hours > 0
  && (component.type === "Lecture" ? subject.lecture_hours > 0 : subject.laboratory_hours > 0));
export function minutes(time: string) {
  if (!/^\d{2}:\d{2}$/.test(time)) return NaN;
  const [hour, minute] = time.split(":").map(Number);
  return hour < 24 && minute < 60 ? hour * 60 + minute : NaN;
}
export const timeString = (value: number) => `${Math.floor(value / 60).toString().padStart(2, "0")}:${(value % 60).toString().padStart(2, "0")}`;
export const durationLabel = (duration: number) => `${duration / 60} ${duration === 60 ? "hour" : "hours"}`;
export const patternLabel = (pattern: MeetingPattern) => `${pattern.meetings_per_week === 1 ? "One" : pattern.meetings_per_week === 2 ? "Two" : pattern.meetings_per_week} ${pattern.duration_minutes / 60}-hour ${pattern.meetings_per_week === 1 ? "meeting" : "meetings"}`;
export const sameComponent = (a: PreferenceScheduleBlock, b: PreferenceScheduleBlock) => a.kind === "subject" && b.kind === "subject" && a.subject_code === b.subject_code && a.component === b.component;
export function matchingPattern(blocks: PreferenceScheduleBlock[], component: SubjectComponent) {
  return component.meeting_patterns.find(pattern => pattern.meetings_per_week === blocks.length
    && blocks.every(block => minutes(block.end_time) - minutes(block.start_time) === pattern.duration_minutes)
    && pattern.day_combinations.some(days => days.length === blocks.length && days.every(day => blocks.some(block => block.day === day))));
}
export function createComponentBlocks(subject: AvailableSubject, component: SubjectComponent, pattern: MeetingPattern, days: string[], start: string): PreferenceScheduleBlock[] {
  if (!isEligible(subject) || !realComponents(subject).includes(component) || !component.meeting_patterns.includes(pattern)
    || !pattern.day_combinations.some(option => JSON.stringify(option) === JSON.stringify(days))) throw new Error("Select a supported meeting pattern and days.");
  const end = minutes(start) + pattern.duration_minutes;
  if (minutes(start) < 450 || end > 1320 || !Number.isFinite(end)) throw new Error("Choose a start time between 7:30 AM and the latest start that ends by 10 PM.");
  return days.map(day => ({ id: crypto.randomUUID(), kind: "subject", day, start_time: start, end_time: timeString(end), subject_code: subject.subject_code, subject_title: subject.subject_title, component: component.type }));
}
export function addComponentPreference(blocks: PreferenceScheduleBlock[], subject: AvailableSubject, component: SubjectComponent, pattern: MeetingPattern, days: string[], start: string) {
  if (blocks.some(block => block.kind === "subject" && block.subject_code === subject.subject_code && block.component === component.type)) {
    throw new Error("This component preference is already placed. Remove it before placing another pattern.");
  }
  return [...blocks, ...createComponentBlocks(subject, component, pattern, days, start)];
}
export function moveBlock(blocks: PreferenceScheduleBlock[], id: string, day: string, start: string, subjects: AvailableSubject[]) {
  const original = blocks.find(block => block.id === id);
  if (!original || !DAYS.includes(day)) throw new Error("Choose a teaching day.");
  let duration = minutes(original.end_time) - minutes(original.start_time);
  let component: SubjectComponent | undefined;
  if (original.kind === "subject") {
    component = subjects.find(subject => subject.subject_code === original.subject_code)?.components.find(item => item.type === original.component);
    const pattern = component && matchingPattern(blocks.filter(block => sameComponent(block, original)), component);
    if (!pattern) throw new Error("Remove this older component preference and place it again using a supported pattern.");
    duration = pattern.duration_minutes;
  }
  const end = minutes(start) + duration;
  if (!Number.isFinite(end) || duration <= 0 || minutes(start) < 450 || end > 1320) throw new Error("This meeting must fit between 7:30 AM and 10 PM.");
  const next = blocks.map(block => block.id === id ? { ...block, day, start_time: start, end_time: timeString(end) } : block);
  if (component && !matchingPattern(next.filter(block => sameComponent(block, original)), component)) throw new Error("Keep both meetings on one of the supported day pairs. Remove and add the component to change its pattern.");
  return next;
}
export function removeBlock(blocks: PreferenceScheduleBlock[], block: PreferenceScheduleBlock) {
  return blocks.filter(item => block.kind === "subject" ? !sameComponent(item, block) : item.id !== block.id);
}
export function generalSummary(blocks: PreferenceScheduleBlock[]) {
  const general = blocks.filter(block => block.kind === "general");
  return { preferred_days: DAYS.filter(day => general.some(block => block.day === day)),
    preferred_start_time: general.length ? timeString(Math.min(...general.map(block => minutes(block.start_time)))) : null,
    preferred_end_time: general.length ? timeString(Math.max(...general.map(block => minutes(block.end_time)))) : null };
}
export function withBlocks(draft: FacultyPreferenceUpdate, blocks: PreferenceScheduleBlock[]): FacultyPreferenceUpdate {
  const summary = generalSummary(blocks);
  // The existing fitness engine uses these day/time flags for both general and exact component preferences.
  const hasBlocks = blocks.length > 0;
  const firstPlacement = draft.preferred_schedule_blocks.length === 0;
  return { ...draft, preferred_schedule_blocks: blocks, ...summary,
    use_day_preference: hasBlocks && (firstPlacement || draft.use_day_preference),
    use_time_preference: hasBlocks && (firstPlacement || draft.use_time_preference) };
}
export function editablePreference(saved: FacultyPreferenceUpdate): FacultyPreferenceUpdate {
  const blocks = saved.preferred_schedule_blocks ?? [];
  const legacy = !blocks.some(block => block.kind === "general") && saved.preferred_start_time && saved.preferred_end_time
    ? saved.preferred_days.map(day => ({ id: `legacy-general-${day}`, kind: "general" as const, day, start_time: saved.preferred_start_time!, end_time: saved.preferred_end_time! })) : [];
  return { ...saved, preferred_subjects: [...saved.preferred_subjects], preferred_schedule_blocks: [...blocks, ...legacy] };
}
export const isDirty = (draft: FacultyPreferenceUpdate, saved: FacultyPreferenceUpdate) => JSON.stringify(draft) !== JSON.stringify(saved);
export const importanceVisible = (enabled: boolean, preference?: string) => enabled && preference !== "No Preference";
export function validationIssues(draft: FacultyPreferenceUpdate, subjects: AvailableSubject[]) {
  const issues: string[] = [];
  if (new Set(draft.preferred_subjects).size !== draft.preferred_subjects.length) issues.push("Each subject can appear only once in the ranked list.");
  if (new Set(draft.preferred_days).size !== draft.preferred_days.length || draft.preferred_days.some(day => !DAYS.includes(day))) issues.push("Older preferred days need review. Clear schedule preferences and add your periods again.");
  if (draft.preferred_start_time !== null || draft.preferred_end_time !== null) {
    const start = minutes(draft.preferred_start_time ?? ""), end = minutes(draft.preferred_end_time ?? "");
    if (!Number.isFinite(start) || !Number.isFinite(end) || start < 450 || end > 1320 || start >= end) issues.push("The older general time range needs review. Clear schedule preferences and add your periods again.");
  }
  const known = new Map(subjects.map(subject => [subject.subject_code, subject]));
  for (const code of draft.preferred_subjects) if (!known.has(code) || !isEligible(known.get(code)!)) issues.push(`${code} is no longer an eligible offered subject. Remove it from your ranked list.`);
  const seen = new Set<string>();
  for (const block of draft.preferred_schedule_blocks) {
    if (seen.has(block.id) || !block.id.trim()) issues.push("Each preference period must have a unique identifier.");
    seen.add(block.id);
    const start = minutes(block.start_time), end = minutes(block.end_time);
    if (!DAYS.includes(block.day) || !Number.isFinite(start) || !Number.isFinite(end) || start < 450 || end > 1320 || end <= start) issues.push("An older period has invalid days or times. Remove it and add a new period.");
    if (block.kind === "general") {
      if (block.subject_code || block.component || block.subject_title) issues.push("A general period cannot contain subject information. Remove it and add a new period.");
      continue;
    }
    const subject = known.get(block.subject_code ?? "");
    const component = subject && realComponents(subject).find(item => item.type === block.component);
    if (!subject || !isEligible(subject) || !draft.preferred_subjects.includes(subject.subject_code) || !component
      || !matchingPattern(draft.preferred_schedule_blocks.filter(item => sameComponent(item, block)), component)) {
      issues.push(`${block.subject_code ?? "Older subject"} ${block.component ?? "meeting"} has an unsupported placement. Remove the component preference and add it again.`);
    }
  }
  return [...new Set(issues)];
}
