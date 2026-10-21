import axios from "axios";
import {z} from "zod";
import {getAvailableSubjects} from "../api/subjects.ts";
import type {AvailableSubject, MeetingPattern} from "../api/subjects.ts";
import {getFacultyDetail} from "../api/faculty.ts";
import type {FacultySummary} from "../api/faculty.ts";
import type {Account} from "./auth.ts";

const positive = z.number().finite().positive();
const pattern = z.object({
  meetings_per_week: positive.int(), duration_minutes: positive.int(),
  continuous: z.boolean(), day_combinations: z.array(z.array(z.string().min(1)).min(1)),
});
const catalog = z.array(z.object({
  course_id: z.string().min(1), subject_code: z.string().min(1), subject_title: z.string(),
  category: z.string(), lecture_hours: z.number().finite().nonnegative(),
  laboratory_hours: z.number().finite().nonnegative(), domains: z.array(z.string()),
  components: z.array(z.object({
    type: z.enum(["Lecture", "Laboratory"]), weekly_hours: z.number().finite().nonnegative(),
    metadata_status: z.enum(["supported", "unsupported"]), meeting_patterns: z.array(pattern),
  })),
  offerings: z.array(z.object({is_preassigned: z.boolean()})),
}));
const faculty = z.object({
  faculty_id: z.string().min(1), faculty_code: z.number().int().nonnegative(),
  display_code: z.string().min(1), name: z.string(),
  instructor_type: z.literal("optimization_faculty"),
  specializations: z.array(z.string()), eligible_subject_codes: z.array(z.string()),
  seniority_level: z.union([z.number().finite(), z.string(), z.null()]),
});

export async function loadSubjectCatalog(signal?: AbortSignal): Promise<AvailableSubject[]> {
  const rows = await getAvailableSubjects(signal);
  if (!catalog.safeParse(rows).success || new Set(rows.map(row => row.course_id)).size !== rows.length)
    throw new Error("Subject metadata is incomplete or inconsistent. Retry or contact an administrator.");
  return rows;
}

export async function loadOwnFaculty(binding: NonNullable<Account["faculty"]>, signal?: AbortSignal): Promise<FacultySummary | null> {
  let row: FacultySummary;
  try { row = await getFacultyDetail(binding.faculty_id, signal); }
  catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
  if (!faculty.safeParse(row).success || row.faculty_id !== binding.faculty_id || row.faculty_code !== binding.faculty_code)
    throw new Error("Faculty metadata does not match your account binding. Contact an administrator; no other profile has been selected.");
  return row;
}

export function metadataError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    if (status === 401) return "Your session could not be verified. Sign in again to continue.";
    if (status === 403) return "You do not have permission to view this information. Contact an administrator.";
    if (status === 503) return "The metadata service is temporarily unavailable. Retry when it is available.";
    return fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

export function searchSubjects(rows: AvailableSubject[], search: string): AvailableSubject[] {
  const query = search.trim().toLocaleLowerCase();
  return rows.filter(row => `${row.subject_code} ${row.subject_title}`.toLocaleLowerCase().includes(query));
}

const days: Record<string, string> = {M: "Monday", T: "Tuesday", W: "Wednesday", TH: "Thursday", F: "Friday", S: "Saturday", SU: "Sunday"};
export function meetingPatternLabel(value: MeetingPattern): string {
  const alternatives = value.day_combinations.map(group => group.map(day => days[day] ?? day).join(" / ")).join("; ");
  return `${value.meetings_per_week} ${value.meetings_per_week === 1 ? "meeting" : "meetings"} per week · ${value.duration_minutes} minutes each${value.continuous ? " · Continuous" : ""}${alternatives ? ` · ${alternatives}` : " · Days not provided"}`;
}
