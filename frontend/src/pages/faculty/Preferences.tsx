import FacultyPreferenceEditor
  from "../../components/faculty/FacultyPreferenceEditor";

export default function Preferences({ facultyCode = 0 }: { facultyCode?: number }) {
  // The prototype defaults to Faculty 0; future authenticated callers supply identity.

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

      <FacultyPreferenceEditor
        facultyCode={facultyCode}
      />

    </div>
  );
}
