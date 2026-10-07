import { useCallback, useEffect, useState } from "react";
import { getAllFaculty } from "../../api/faculty";
import type { FacultySummary } from "../../api/faculty";
import FacultyPreferenceEditor from "../../components/faculty/FacultyPreferenceEditor";
import { normalFaculty } from "../../components/faculty/preferenceModel";

export default function PreferencesReview() {
  const [faculty, setFaculty] = useState<FacultySummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [editState, setEditState] = useState({ dirty: false, saving: false });
  const onEditStateChange = useCallback((dirty: boolean, saving: boolean) => setEditState({ dirty, saving }), []);
  useEffect(() => {
    let cancelled = false;
    getAllFaculty().then(rows => {
      if (cancelled) return;
      const normal = normalFaculty(rows); setFaculty(normal); setSelectedId(normal[0]?.faculty_id ?? ""); setLoading(false);
    }).catch(() => { if (!cancelled) { setError("Unable to load faculty. Refresh this page to try again."); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);
  const selected = faculty.find(row => row.faculty_id === selectedId);
  return <div className="preference-page space-y-4">
    <header><h1 className="text-2xl font-bold text-slate-900">Faculty Preferences</h1><p className="mt-1 text-sm text-slate-500">Review teaching preferences for each faculty member.</p></header>
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      {loading ? <p role="status">Loading faculty…</p> : error ? <p role="alert" className="text-red-700">{error}</p> : faculty.length === 0 ? <p>No faculty records are available.</p> :
        <label className="preference-label max-w-sm">Select faculty<select className="preference-input" value={selectedId} disabled={editState.saving} onChange={event => {
          if (editState.dirty && !window.confirm("Discard unsaved preferences and switch faculty?")) return;
          setEditState({ dirty: false, saving: false }); setSelectedId(event.target.value);
        }}>{faculty.map(row => <option key={row.faculty_id} value={row.faculty_id}>{row.display_code}</option>)}</select></label>}
    </div>
    {selected && <FacultyPreferenceEditor key={selected.faculty_id} facultyId={selected.faculty_id} facultyCode={selected.faculty_code} adminMode onEditStateChange={onEditStateChange} />}
  </div>;
}
