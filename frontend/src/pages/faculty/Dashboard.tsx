import {Link} from "react-router-dom";
import {useAuth} from "../../context/AuthContext";

const links = [
  {to: "/faculty/preferences", title: "My Preferences", status: "Available", description: "Review and save your own teaching preferences."},
  {to: "/faculty/schedule", title: "My Schedule", status: "Read only", description: "View your own assignments from the latest GA-generated proposal."},
  {to: "/faculty/adjustments", title: "Adjustment Requests", status: "Requires verified schedule source", description: "Prepare, track and withdraw your own proposals without changing your teaching schedule."},
  {to: "/faculty/profile", title: "My Profile", status: "Read only", description: "View your account, linked faculty identity and available academic metadata."},
];

export default function Dashboard() {
  const {user} = useAuth();
  const binding = user?.faculty;
  return <div className="min-w-0 space-y-6">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5 sm:p-6">
      <p className="text-sm font-semibold text-teal-800">Faculty portal</p>
      <h1 className="mt-1 text-2xl font-bold text-slate-900">Faculty Dashboard</h1>
      <p className="mt-3 break-words text-lg text-teal-950">Welcome, {binding?.name || user?.username}.</p>
      <p className="mt-2 break-all text-sm text-slate-600">Signed in as {user?.username}</p>
      {binding ? <p className="mt-1 text-sm text-slate-600">Linked identity: {binding.display_code}</p>
        : <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">Faculty binding unavailable. Contact an administrator before using faculty-specific features.</p>}
    </header>
    <section aria-label="Faculty quick links" className="grid min-w-0 gap-4 lg:grid-cols-3">
      {links.map(item => <Link key={item.to} to={item.to} className="min-w-0 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-500 focus-visible:outline-2 focus-visible:outline-teal-700">
        <span className="inline-block rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-900">{item.status}</span>
        <h2 className="mt-3 text-lg font-semibold text-slate-900">{item.title}</h2>
        <p className="mt-2 text-sm text-slate-600">{item.description}</p>
      </Link>)}
    </section>
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="font-semibold text-slate-900">Schedule review and adjustments</h2>
      <p className="mt-2 text-sm text-slate-600">My Schedule shows your GA-generated proposal. Adjustment requests require a verified schedule source. Department Chair approvals and official schedule publication are not available yet.</p>
    </section>
  </div>;
}
