import FacultyPreferenceEditor
  from "../../components/faculty/FacultyPreferenceEditor";

export default function PreferencesReview() {
  // TEMPORARY:
  // faculty code 0 while we test the editor.
  // Next we will replace this with a faculty selector.
  const selectedFacultyCode = 0;

  return (
    <div className="space-y-6">

      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Faculty Preferences
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          Review and modify faculty scheduling preferences
          used by the Genetic Algorithm.
        </p>
      </div>

      <FacultyPreferenceEditor
        facultyCode={selectedFacultyCode}
      />

    </div>
  );
}