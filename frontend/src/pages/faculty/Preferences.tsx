import FacultyPreferenceEditor
  from "../../components/faculty/FacultyPreferenceEditor";

export default function Preferences() {
  // TEMPORARY TEST VALUE
  // Later this will come from the logged-in faculty account.
  const facultyCode = 0;

  return (
    <div className="p-6 space-y-6">

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