import {useEffect, useState} from "react";
import type {Account} from "../../services/auth";
import {authRequest} from "../../services/auth";
import {getAllFaculty} from "../../api/faculty";
import type {FacultySummary} from "../../api/faculty";

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([]), [faculty, setFaculty] = useState<FacultySummary[]>([]);
  const [selected, setSelected] = useState(""), [username, setUsername] = useState(""), [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "faculty">("faculty"), [facultyId, setFacultyId] = useState("");
  const [active, setActive] = useState(true), [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  useEffect(() => {
    let cancelled = false;
    Promise.all([authRequest<Account[]>("/users"), getAllFaculty()]).then(([users, rows]) => {
      if (!cancelled) {setAccounts(users); setFaculty(rows);}
    }).catch(reason => {if (!cancelled) setMessage(reason.message);});
    return () => {cancelled = true;};
  }, []);
  function select(id: string) {
    const user = accounts.find(row => row.id === id);
    setSelected(id); setUsername(user?.username ?? ""); setRole(user?.role ?? "faculty");
    setFacultyId(user?.faculty_id ?? ""); setActive(user?.is_active ?? true); setPassword(""); setMessage("");
  }
  return <div className="max-w-3xl space-y-4"><header><h1 className="text-2xl font-bold">Account Administration</h1><p className="mt-1 text-sm text-slate-500">Bind faculty accounts to registered identities. Changing an account revokes its existing sessions.</p></header>
    <form className="space-y-4 rounded-xl border bg-white p-6" onSubmit={async event => {
      event.preventDefault(); setBusy(true); setMessage("");
      const fields = {role, faculty_id: role === "faculty" ? facultyId : null};
      try {
        await authRequest(selected ? `/users/${selected}` : "/users", {method: selected ? "PATCH" : "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify(selected ? {...fields, is_active: active, ...(password ? {password} : {})} : {...fields, username, password})});
        setAccounts(await authRequest<Account[]>("/users")); setPassword(""); setMessage("Account saved. Existing sessions were revoked if the account was updated.");
      } catch (reason) {setMessage(reason instanceof Error ? reason.message : "Account could not be saved.");}
      finally {setBusy(false);}
    }}>
      <fieldset disabled={busy} className="space-y-4">
        <label className="block text-sm">Account<select className="mt-1 w-full rounded border p-2" value={selected} onChange={event => select(event.target.value)}><option value="">Create a new account</option>{accounts.map(user => <option key={user.id} value={user.id}>{user.username} · {user.role}{!user.is_active ? " · Disabled" : ""}</option>)}</select></label>
        <label className="block text-sm">Username or institutional email<input className="mt-1 w-full rounded border p-2" autoComplete="off" required maxLength={254} disabled={!!selected} value={username} onChange={event => setUsername(event.target.value)} /></label>
        <label className="block text-sm">Role<select className="mt-1 w-full rounded border p-2" value={role} onChange={event => setRole(event.target.value as "admin" | "faculty")}><option value="faculty">Faculty</option><option value="admin">Administrator</option></select></label>
        {role === "faculty" && <label className="block text-sm">Faculty binding<select className="mt-1 w-full rounded border p-2" required value={facultyId} onChange={event => setFacultyId(event.target.value)}><option value="">Select a faculty identity</option>{faculty.filter(row => row.instructor_type === "optimization_faculty").map(row => <option key={row.faculty_id} value={row.faculty_id}>{row.display_code} · {row.name}</option>)}</select></label>}
        {selected && <label className="flex gap-2 text-sm"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />Account enabled</label>}
        <label className="block text-sm">{selected ? "New password (leave blank to retain)" : "Initial password"}<input className="mt-1 w-full rounded border p-2" type="password" autoComplete="new-password" minLength={12} maxLength={1024} required={!selected} value={password} onChange={event => setPassword(event.target.value)} /></label>
        <button className="rounded bg-[#0F766E] px-4 py-2 text-white" disabled={busy}>{busy ? "Saving…" : "Save account"}</button>
      </fieldset>{message && <p role="status" className="text-sm">{message}</p>}
    </form>
  </div>;
}
