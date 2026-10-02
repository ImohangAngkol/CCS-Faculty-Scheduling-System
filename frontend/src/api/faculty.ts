const API_URL =
  "http://127.0.0.1:8000";


export interface FacultySummary {

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
