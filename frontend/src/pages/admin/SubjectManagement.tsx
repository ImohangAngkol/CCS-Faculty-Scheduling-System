import {useEffect, useState} from "react";
import type {AvailableSubject} from "../../api/subjects";
import MetadataState from "../../components/dashboard/MetadataState";
import {loadSubjectCatalog, metadataError, searchSubjects, meetingPatternLabel} from "../../services/dashboardMetadata";

type CatalogState = {attempt: number; rows?: AvailableSubject[]; error?: string};

export default function SubjectManagement() {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<CatalogState | null>(null);
  const [search, setSearch] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    loadSubjectCatalog(controller.signal).then(rows => {
      if (!controller.signal.aborted) setResult({attempt, rows});
    }).catch(error => {
      if (!controller.signal.aborted) setResult({attempt, error: metadataError(error, "Unable to load subjects. Check the backend connection and retry.")});
    });
    return () => controller.abort();
  }, [attempt]);
  const current = result?.attempt === attempt ? result : null;
  const rows = current?.rows;
  const visible = rows ? searchSubjects(rows, search) : [];

  return <div className="min-w-0 space-y-6">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5 sm:p-6">
      <p className="text-sm font-semibold text-teal-800">Academic reference · Read only</p>
      <h1 className="mt-1 text-2xl font-bold text-slate-900">Subject Management</h1>
      <p className="mt-2 text-sm text-slate-600">Browse subjects and their lecture/laboratory requirements from the existing academic dataset. This catalog does not create or edit subjects.</p>
      <p className="mt-2 text-sm text-teal-900">Dataset: first-semester prototype. An academic year has not been established.</p>
    </header>
    <section aria-label="Subject catalog" className="space-y-4">
      <label className="block text-sm font-semibold text-slate-700" htmlFor="catalog-search">Search by subject code or title</label>
      <input id="catalog-search" type="search" value={search} onChange={event => setSearch(event.target.value)}
        disabled={!rows} placeholder="Search subjects" className="w-full rounded-lg border border-slate-300 bg-white p-3 focus:outline-2 focus:outline-teal-700 disabled:bg-slate-100" />
      {!current && <MetadataState title="Loading subject catalog" description="Retrieving the current subject metadata…" />}
      {current?.error && <MetadataState title="Subject catalog unavailable" description={current.error} retry={() => setAttempt(value => value + 1)} />}
      {rows && rows.length === 0 && <MetadataState title="No subjects available" description="The API returned an empty catalog. No academic records have been created." />}
      {rows && rows.length > 0 && visible.length === 0 && <MetadataState title="No matching subjects" description="Try another subject code or title, or clear the search." />}
      {rows && rows.length > 0 && <p role="status" className="text-sm text-slate-600">Showing {visible.length} of {rows.length} subjects</p>}
      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        {visible.map(subject => <article key={subject.course_id} className="min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h2 className="break-words text-lg font-bold text-teal-900">{subject.subject_code}</h2>
            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900">{subject.category}</span>
          </div>
          <p className="mt-1 break-words font-medium text-slate-900">{subject.subject_title || "Title not provided"}</p>
          <p className="mt-3 text-sm text-slate-600">Lecture: {subject.lecture_hours} hours/week · Laboratory: {subject.laboratory_hours} hours/week</p>
          <p className="mt-1 break-words text-sm text-slate-600">Domains: {subject.domains.length ? subject.domains.join(", ") : "Not provided"}</p>
          <p className="mt-1 text-sm text-slate-600">{subject.offerings.length} recorded {subject.offerings.length === 1 ? "offering" : "offerings"}{subject.offerings.some(row => row.is_preassigned) ? " · Includes external preassignments (not fixed meeting times)" : ""}</p>
          <details className="mt-4 border-t border-slate-100 pt-3">
            <summary className="cursor-pointer font-semibold text-teal-800 focus-visible:outline-2 focus-visible:outline-teal-700">View component details</summary>
            <div className="mt-3 space-y-3">
              {subject.components.length === 0 && <p className="text-sm text-slate-600">Component details not provided.</p>}
              {subject.components.map(component => <section key={component.type} className="rounded-lg bg-slate-50 p-3" aria-label={`${subject.subject_code} ${component.type}`}>
                <h3 className="font-semibold text-slate-900">{component.type} · {component.weekly_hours} hours/week</h3>
                {component.metadata_status === "supported" && component.meeting_patterns.length > 0
                  ? <ul className="mt-2 space-y-2 text-sm text-slate-600">{component.meeting_patterns.map((pattern, index) => <li key={index}>{meetingPatternLabel(pattern)}</li>)}</ul>
                  : <p className="mt-2 text-sm text-amber-900">Meeting pattern unavailable or unsupported by the current scheduler. No duration has been inferred.</p>}
              </section>)}
            </div>
          </details>
        </article>)}
      </div>
    </section>
  </div>;
}
