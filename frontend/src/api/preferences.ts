import axios from "axios";

const API_URL = "http://127.0.0.1:8000";

export interface FacultyPreference {
  faculty_code: number;
  faculty_priority: number;

  preferred_subjects: string[];
  preferred_days: string[];

  preferred_start_time: string | null;
  preferred_end_time: string | null;

  gap_preference: string;

  use_subject_preference: boolean;
  use_day_preference: boolean;
  use_time_preference: boolean;
  use_gap_preference: boolean;
}

export interface FacultyPreferenceUpdate {
  faculty_priority: number;

  preferred_subjects: string[];
  preferred_days: string[];

  preferred_start_time: string | null;
  preferred_end_time: string | null;

  gap_preference: string;

  use_subject_preference: boolean;
  use_day_preference: boolean;
  use_time_preference: boolean;
  use_gap_preference: boolean;
}

export async function getFacultyPreference(
  facultyCode: number
): Promise<FacultyPreference> {
  const response = await axios.get(
    `${API_URL}/preferences/${facultyCode}`
  );

  return response.data;
}

export async function updateFacultyPreference(
  facultyCode: number,
  data: FacultyPreferenceUpdate
): Promise<FacultyPreference> {
  const response = await axios.put(
    `${API_URL}/preferences/${facultyCode}`,
    data
  );

  return response.data;
}