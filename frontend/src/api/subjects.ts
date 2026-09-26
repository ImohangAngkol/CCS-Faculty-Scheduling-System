import axios from "axios";

const API_URL = "http://127.0.0.1:8000";


export interface AvailableSubject {
  subject_code: string;
  subject_title: string;
}


interface AvailableSubjectsResponse {
  message: string;
  data: AvailableSubject[];
}


export async function getAvailableSubjects():
  Promise<AvailableSubject[]> {

  const response =
    await axios.get<AvailableSubjectsResponse>(
      `${API_URL}/api/subjects/available`
    );

  return response.data.data;
}