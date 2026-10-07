import axios from "axios";
import type { FacultySummary } from "./faculty";

const API_URL = "http://127.0.0.1:8000";
export type ComponentType = "Lecture" | "Laboratory";
export interface MeetingPattern {
  meetings_per_week: number;
  duration_minutes: number;
  continuous: boolean;
  day_combinations: string[][];
}
export interface SubjectComponent {
  type: ComponentType;
  weekly_hours: number;
  metadata_status: "supported" | "unsupported";
  duration_minutes: number | null;
  meetings_per_week: number | null;
  continuous: boolean | null;
  fixed_duration: boolean;
  meeting_patterns: MeetingPattern[];
}
export interface AvailableSubject {
  course_id: string;
  subject_code: string;
  subject_title: string;
  category: "CCC" | "ITD" | "ITN" | "ITE" | "ISY" | "OTHER";
  lecture_hours: number;
  laboratory_hours: number;
  domains: string[];
  components: SubjectComponent[];
  preassignment_status: "none" | "some" | "all";
  eligibility: { explicitly_eligible: boolean } | null;
  offerings: { can_be_assigned: boolean | null; is_preassigned: boolean }[];
}
export interface FacultySubjectsResponse {
  faculty: FacultySummary;
  eligible_only: boolean;
  data: AvailableSubject[];
}
export async function getAvailableSubjects(): Promise<AvailableSubject[]> {
  const response = await axios.get<{ data: AvailableSubject[] }>(`${API_URL}/api/subjects/available`);
  return response.data.data;
}
export async function getFacultySubjects(reference: string | number, eligibleOnly = true): Promise<FacultySubjectsResponse> {
  const response = await axios.get<FacultySubjectsResponse>(
    `${API_URL}/api/faculty/${encodeURIComponent(reference)}/eligible-subjects`,
    { params: { eligible_only: eligibleOnly } },
  );
  return response.data;
}
