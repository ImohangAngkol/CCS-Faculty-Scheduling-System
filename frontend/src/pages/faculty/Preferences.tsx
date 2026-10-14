import FacultyPreferenceEditor
  from "../../components/faculty/FacultyPreferenceEditor";

export default function Preferences({ facultyCode }: { facultyCode?: number }) {
  // A future verified server account must supply faculty identity. Never assume 0.

  return (
    <div className="preference-page space-y-4">

      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Faculty Preferences
        </h1>

        <p className="text-sm text-gray-500 mt-1">
          Set your preferred subjects, teaching days,
          teaching time, and schedule style.
        </p>
      </div>

      {facultyCode === undefined ? <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Faculty sign-in is not configured. Your faculty identity must be verified before opening personal preferences. No faculty record has been selected.
      </p> : <FacultyPreferenceEditor
        facultyCode={facultyCode}
      />}

    </div>
  );
}
