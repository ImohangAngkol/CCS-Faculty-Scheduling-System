import axios from "axios";

const API_URL = "http://127.0.0.1:8000";


// =========================================================
// FACULTY PREFERENCE TYPES
// =========================================================

export type GapPreference =
  | "Compact"
  | "Scattered"
  | "No Preference";


export type LectureLabPreference =
  | "Same Day"
  | "Different Day"
  | "No Preference";


export interface FacultyPreference {
  faculty_code: number;

  faculty_priority: number;

  // Subject preference
  preferred_subjects: string[];
  subject_importance: number;

  // Day preference
  preferred_days: string[];
  day_importance: number;

  // Time preference
  preferred_start_time: string | null;
  preferred_end_time: string | null;
  time_importance: number;

  // Schedule style
  gap_preference: GapPreference;
  gap_importance: number;

  // Lecture / laboratory relationship
  lecture_lab_preference: LectureLabPreference;
  lecture_lab_importance: number;

  // Existing enable / disable flags
  use_subject_preference: boolean;
  use_day_preference: boolean;
  use_time_preference: boolean;
  use_gap_preference: boolean;
  use_lecture_lab_preference: boolean;
}


export interface FacultyPreferenceUpdate {
  faculty_priority: number;

  // Subject preference
  preferred_subjects: string[];
  subject_importance: number;

  // Day preference
  preferred_days: string[];
  day_importance: number;

  // Time preference
  preferred_start_time: string | null;
  preferred_end_time: string | null;
  time_importance: number;

  // Schedule style
  gap_preference: GapPreference;
  gap_importance: number;

  // Lecture / laboratory relationship
  lecture_lab_preference: LectureLabPreference;
  lecture_lab_importance: number;

  // Existing enable / disable flags
  use_subject_preference: boolean;
  use_day_preference: boolean;
  use_time_preference: boolean;
  use_gap_preference: boolean;
  use_lecture_lab_preference: boolean;
}


// =========================================================
// API FUNCTIONS
// =========================================================

export async function getFacultyPreference(
  facultyCode: number
): Promise<FacultyPreference> {

  const response = await axios.get<FacultyPreference>(
    `${API_URL}/preferences/${facultyCode}`
  );

  return response.data;
}


export async function updateFacultyPreference(
  facultyCode: number,
  data: FacultyPreferenceUpdate
): Promise<FacultyPreference> {

  const response = await axios.put<FacultyPreference>(
    `${API_URL}/preferences/${facultyCode}`,
    data
  );

  return response.data;
}