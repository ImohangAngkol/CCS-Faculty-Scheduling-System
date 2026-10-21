import {API_BASE, apiClient, apiFetch as fetch} from "../services/apiSession.ts";
const API_URL =
  API_BASE;


export interface FacultySummary {
  faculty_id: string;
  display_code: string;
  instructor_type: "optimization_faculty" | "preassigned_external";
  specializations: string[];
  eligible_subject_codes: string[];
  required_teaching_load: number;
  absolute_max_teaching_load: number;

  faculty_code: number;

  name: string;

  seniority_level:
    number | string | null;

  admin_load: number;

  research_load: number;

  extension_load: number;

  current_teaching_load: number;
}


type FacultyListResponse = {

  message: string;

  data:
    FacultySummary[];
};


export async function getAllFaculty():
  Promise<FacultySummary[]> {

  const response =
    await fetch(
      `${API_URL}/api/faculty/`
    );


  if (!response.ok) {

    throw new Error(
      "Failed to load faculty list."
    );

  }


    const payload:
        FacultyListResponse =
            await response.json();


  return Array.isArray(
    payload.data
  )
    ? payload.data
    : [];
}

/** Read only the identity supplied by the authenticated account. */
export async function getFacultyDetail(facultyId: string, signal?: AbortSignal): Promise<FacultySummary> {
  const response = await apiClient.get<{data: FacultySummary}>(
    `${API_URL}/api/faculty/${encodeURIComponent(facultyId)}`, {signal},
  );
  return response.data.data;
}
