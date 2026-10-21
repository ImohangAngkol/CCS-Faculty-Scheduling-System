import {useEffect, useState} from "react";
import type {ReactNode} from "react";
import {useAuth} from "../../context/AuthContext";
import type {FacultySummary} from "../../api/faculty";
import MetadataState from "../../components/dashboard/MetadataState";
import {loadOwnFaculty, metadataError} from "../../services/dashboardMetadata";

type ProfileState = {key: string; data?: FacultySummary | null; error?: string};
function Field({label, children}: {label: string; children: ReactNode}) {
  return <div className="min-w-0"><dt className="text-sm text-slate-500">{label}</dt><dd className="mt-1 break-words font-medium text-slate-900 [overflow-wrap:anywhere]">{children}</dd></div>;
}

export default function Profile() {
  const {user} = useAuth();
  const binding = user?.faculty;
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<ProfileState | null>(null);
  const key = `${user?.id}:${binding?.faculty_id}:${binding?.faculty_code}:${attempt}`;
  useEffect(() => {
    if (!binding) return;
    const controller = new AbortController();
    loadOwnFaculty(binding, controller.signal).then(data => {
      if (!controller.signal.aborted) setResult({key, data});
    }).catch(error => {
      if (!controller.signal.aborted) setResult({key, error: metadataError(error, "Unable to load faculty metadata. Check the backend connection and retry.")});
    });
    return () => controller.abort();
  }, [binding, key]);
  const current = result?.key === key ? result : null;
  const metadata = current?.data;

  return <div className="min-w-0 space-y-6">
    <header><p className="text-sm font-semibold text-teal-800">My Account · Read only</p><h1 className="mt-1 text-2xl font-bold text-slate-900">Faculty Profile</h1><p className="mt-2 text-sm text-slate-600">Account information comes from your verified session. Academic details come from the existing faculty metadata service.</p></header>
    <section className="rounded-xl border border-slate-200 bg-white p-5 sm:p-6" aria-labelledby="account-information">
      <h2 id="account-information" className="text-lg font-semibold text-teal-900">Account information</h2>
      <dl className="mt-4 grid min-w-0 gap-4 sm:grid-cols-2"><Field label="Username">{user?.username}</Field><Field label="Account role">{user?.role === "faculty" ? "Faculty" : "Not available"}</Field><Field label="Account status">{user?.is_active ? "Active" : "Not available"}</Field></dl>
    </section>
    <section className="rounded-xl border border-slate-200 bg-white p-5 sm:p-6" aria-labelledby="faculty-information">
      <h2 id="faculty-information" className="text-lg font-semibold text-teal-900">Faculty information</h2>
      {binding ? <dl className="mt-4 grid min-w-0 gap-4 sm:grid-cols-2"><Field label="Faculty name">{binding.name || "Not provided"}</Field><Field label="Display code">{binding.display_code}</Field><Field label="Stable faculty ID">{binding.faculty_id}</Field><Field label="Legacy faculty code">{binding.faculty_code}</Field></dl>
        : <p className="mt-3 text-sm text-amber-900" role="status">Faculty binding unavailable. Contact an administrator. No faculty record has been selected.</p>}
    </section>
    <section className="space-y-4" aria-labelledby="academic-information">
      <h2 id="academic-information" className="text-lg font-semibold text-slate-900">Academic details · Read only</h2>
      {binding && !current && <MetadataState title="Loading faculty metadata" description="Retrieving academic details for your linked faculty identity…" />}
      {current?.error && <MetadataState title="Academic details unavailable" description={current.error} retry={() => setAttempt(value => value + 1)} />}
      {binding && current?.data === null && <MetadataState title="Faculty metadata not found" description="Your account remains linked, but its academic record was not found. Contact an administrator; no replacement identity has been selected." />}
      {!binding && <MetadataState title="Academic details unavailable" description="A valid faculty binding is required before academic details can be retrieved." />}
      {metadata && <div className="rounded-xl border border-slate-200 bg-white p-5 sm:p-6"><dl className="grid min-w-0 gap-5 sm:grid-cols-2">
        <Field label="Registered faculty name">{metadata.name || "Not provided"}</Field>
        <Field label="Seniority level (source metadata)">{metadata.seniority_level ?? "Not provided"}</Field>
        <Field label="Specializations">{metadata.specializations.length ? metadata.specializations.join(", ") : "Not provided"}</Field>
        <Field label="Explicitly eligible subject codes">{metadata.eligible_subject_codes.length ? metadata.eligible_subject_codes.join(", ") : "None recorded"}</Field>
      </dl></div>}
      <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">These are read-only details from the existing dataset. Formal qualifications, appointments and current-term workload are not supplied by this page. Contact an administrator for corrections.</p>
    </section>
  </div>;
}
