import {useEffect, useState} from "react";
import {Link} from "react-router-dom";
import axios from "axios";
import {useAuth} from "../../context/AuthContext";
import WeeklySchedule from "../../components/schedule/WeeklySchedule";
import MetadataState from "../../components/dashboard/MetadataState";
import {getMySchedule} from "../../services/scheduleService";
import type {MySchedule as Timetable} from "../../services/scheduleService";
import type {ScheduleEntry} from "../../types/ga";
import {metadataError} from "../../services/dashboardMetadata";
import {DAY_NAMES} from "../../components/faculty/preferenceModel";

type LoadState = {key: string; data?: Timetable; error?: string; stale?: boolean; denied?: boolean};

export default function MySchedule() {
  const {user} = useAuth();
  const binding = user?.faculty;
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<LoadState | null>(null);
  const key = `${user?.id}:${binding?.faculty_id}:${binding?.faculty_code}:${attempt}`;
  useEffect(() => {
    if (!binding) return;
    const controller = new AbortController();
    getMySchedule(binding, controller.signal).then(data => {
      if (!controller.signal.aborted) setResult({key, data});
    }).catch(error => {
      if (controller.signal.aborted) return;
      const status = axios.isAxiosError(error) ? error.response?.status : undefined;
      const stale = status === 409;
      setResult({key, stale, denied: status === 403,
        error: stale ? "The saved proposal changed or is incompatible with the current scheduling inputs. Refresh or ask an administrator to review it."
          : metadataError(error, "Your timetable is temporarily unavailable. Check the connection and retry.")});
    });
    return () => controller.abort();
  }, [binding, key]);
  const current = result?.key === key ? result : null;
  const data = current?.data;
  const entries: ScheduleEntry[] = data?.assignments.map(row => ({...row, title: row.title ?? "", room: row.room ?? "Not recorded", faculty: String(data.faculty_code)})) ?? [];
  return <div className="min-w-0 space-y-6">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5 sm:p-6">
      <p className="text-sm font-semibold text-teal-800">Faculty timetable · Read only</p>
      <h1 className="mt-1 text-2xl font-bold text-slate-900">My Schedule</h1>
      <p className="mt-2 text-sm font-semibold text-teal-950">GA-generated proposal</p>
      <p className="mt-2 text-sm text-slate-600">Your assignments from the latest completed GA result. This is a proposal, not an approved or official schedule.</p>
      <Link className="text-sm text-teal-800 underline" to="/faculty/adjustments">Request an adjustment (verified schedule source required)</Link>
      {binding && <p className="mt-2 text-sm text-slate-600">{binding.display_code} · {binding.name}</p>}
    </header>
    {!binding && <MetadataState title="Faculty binding unavailable" description="Contact an administrator to verify your account binding. No faculty schedule has been selected." />}
    {binding && !current && <MetadataState title="Loading your timetable" description="Retrieving your own assignments…" />}
    {current?.error && <MetadataState title={current.stale ? "Proposal source requires review" : current.denied ? "Schedule access unavailable" : "Timetable unavailable"} description={current.error} retry={() => setAttempt(value => value + 1)} />}
    {data?.availability === "missing" && <MetadataState title="No GA proposal available" description="No completed GA result has been saved. Ask an administrator to generate a proposal." />}
    {data && data.availability !== "missing" && <>
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950" role="status">
        <p>Source status: compatible with loaded scheduling inputs. Original input freshness was not recorded in this legacy result.</p>
        {data.source.saved_at && <p className="mt-1">Saved source updated: <time dateTime={data.source.saved_at}>{new Date(data.source.saved_at).toLocaleString()}</time></p>}
        <p className="mt-1">The source timestamp is not an approval date. An academic year and official publication status are not recorded.</p>
      </div>
      {data.availability === "empty" ? <MetadataState title="No assignments in this proposal" description="The saved proposal contains no assignments for your verified faculty identity." /> : <>
        <section aria-label="Weekly timetable" className="min-w-0"><WeeklySchedule entries={entries} viewMode="faculty" /></section>
        <section aria-labelledby="assignment-details" className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 id="assignment-details" className="text-lg font-semibold text-teal-900">Assignment details</h2>
          <div className="mt-4 grid min-w-0 gap-3 lg:grid-cols-2">{data.assignments.map((row, index) => <article key={index} className="min-w-0 rounded-lg border border-slate-200 p-4">
            <h3 className="break-words font-bold text-slate-900">{row.subject} · {row.type}</h3>
            <p className="mt-1 break-words text-sm text-slate-600">{row.title || "Subject name not recorded"}</p>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <div><dt className="text-slate-500">Section</dt><dd className="break-words">{row.section}</dd></div>
              <div><dt className="text-slate-500">Day</dt><dd>{DAY_NAMES[row.day] ?? row.day}</dd></div>
              <div><dt className="text-slate-500">Time</dt><dd>{row.start} – {row.end}</dd></div>
              <div><dt className="text-slate-500">Room</dt><dd className="break-words">{row.room || "Not recorded"}</dd></div>
            </dl>
          </article>)}</div>
        </section>
      </>}
    </>}
    <button type="button" className="ccs-btn-secondary" disabled={!binding || !current} onClick={() => setAttempt(value => value + 1)}>Refresh timetable</button>
  </div>;
}
