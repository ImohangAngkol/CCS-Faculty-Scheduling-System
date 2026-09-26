import { useEffect, useState } from "react";
import axios from "axios";

import FacultyPreferenceEditor
  from "../../components/faculty/FacultyPreferenceEditor";


const API_URL = "http://127.0.0.1:8000";


interface FacultyRecord {
  id?: number;
  faculty_id?: number;
  faculty_code?: number;
  code?: number;

  name?: string;
  faculty_name?: string;
}


interface FacultyOption {
  code: number;
  name: string;
}


export default function PreferencesReview() {

  const [faculty, setFaculty] =
    useState<FacultyOption[]>([]);

  const [
    selectedFacultyCode,
    setSelectedFacultyCode,
  ] = useState<number | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {

    loadFaculty();

  }, []);


  async function loadFaculty() {

    try {

      setLoading(true);
      setError("");

      const response =
        await axios.get(
          `${API_URL}/api/faculty/`
        );


      /*
       * Supports either:
       *
       * [
       *   {...},
       *   {...}
       * ]
       *
       * OR wrapped API responses such as:
       *
       * {
       *   data: [...]
       * }
       */

      const responseData =
        response.data;

      let rows: FacultyRecord[] = [];


      if (Array.isArray(responseData)) {

        rows = responseData;

      } else if (
        Array.isArray(responseData?.data)
      ) {

        rows = responseData.data;

      } else if (
        Array.isArray(responseData?.faculty)
      ) {

        rows = responseData.faculty;

      } else if (
        Array.isArray(responseData?.items)
      ) {

        rows = responseData.items;

      }


      const options: FacultyOption[] =
        rows
          .map((item) => {

            const rawCode =
              item.faculty_code
              ?? item.code
              ?? item.faculty_id
              ?? item.id;


            const code =
              Number(rawCode);


            const name =
              item.faculty_name
              ?? item.name
              ?? `Faculty ${code}`;


            return {
              code,
              name,
            };

          })

          .filter(
            (item) =>
              Number.isFinite(item.code)
          );


      setFaculty(options);


      /*
       * Automatically select
       * the first faculty member.
       */

      if (
        options.length > 0
        && selectedFacultyCode === null
      ) {

        setSelectedFacultyCode(
          options[0].code
        );

      }

    } catch (error) {

      console.error(
        "Failed to load faculty:",
        error
      );

      setError(
        "Unable to load faculty list."
      );

    } finally {

      setLoading(false);

    }

  }


  return (

    <div className="space-y-6">

      {/* ===================================== */}
      {/* PAGE HEADER */}
      {/* ===================================== */}

      <div>

        <h1
          className="
            text-2xl
            font-bold
            text-slate-900
          "
        >
          Faculty Preferences
        </h1>

        <p
          className="
            mt-1
            text-sm
            text-slate-500
          "
        >
          Select a faculty member and manage
          their scheduling preferences.
        </p>

      </div>


      {/* ===================================== */}
      {/* FACULTY SELECTOR */}
      {/* ===================================== */}

      <div
        className="
          rounded-xl
          border
          bg-white
          p-5
        "
      >

        <label
          className="
            mb-2
            block
            font-medium
            text-slate-900
          "
        >
          Select Faculty
        </label>


        {loading ? (

          <p
            className="
              text-sm
              text-slate-500
            "
          >
            Loading faculty...
          </p>

        ) : error ? (

          <p
            className="
              text-sm
              text-red-600
            "
          >
            {error}
          </p>

        ) : faculty.length === 0 ? (

          <p
            className="
              text-sm
              text-slate-500
            "
          >
            No faculty records were found.
          </p>

        ) : (

          <select

            value={
              selectedFacultyCode ?? ""
            }

            onChange={(event) =>
              setSelectedFacultyCode(
                Number(
                  event.target.value
                )
              )
            }

            className="
              w-full
              rounded-lg
              border
              border-slate-300
              bg-white
              px-3
              py-2
            "
          >

            {faculty.map(
              (facultyMember) => (

                <option
                  key={
                    facultyMember.code
                  }
                  value={
                    facultyMember.code
                  }
                >
                 Faculty {facultyMember.code}
                </option>

              )
            )}

          </select>

        )}

      </div>


      {/* ===================================== */}
      {/* PREFERENCE EDITOR */}
      {/* ===================================== */}

      {
        selectedFacultyCode !== null
        && (

          <FacultyPreferenceEditor
            key={selectedFacultyCode}
            facultyCode={
              selectedFacultyCode
            }
          />

        )
      }

    </div>

  );
}