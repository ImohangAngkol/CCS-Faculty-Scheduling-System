import FacultyPreferenceEditor
  from "../../components/faculty/FacultyPreferenceEditor";
import {useAuth} from "../../context/AuthContext";

export default function Preferences() {
  const {user} = useAuth();
  const binding = user?.role === "faculty" ? user.faculty : null;

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

      {!binding ? <p role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Your account has no valid faculty binding. Ask an administrator to repair it before editing preferences. No faculty record has been selected.
      </p> : <FacultyPreferenceEditor
        facultyCode={binding.faculty_code}
        facultyId={binding.faculty_id}
      />}

    </div>
  );
}
