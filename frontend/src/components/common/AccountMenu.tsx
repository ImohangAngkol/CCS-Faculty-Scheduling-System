import {useState} from "react";
import {useAuth} from "../../context/AuthContext";
import ChairReviewLink from "./ChairReviewLink";
export default function AccountMenu() {
  const {user, logout} = useAuth();
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  return <div className="flex flex-wrap items-center justify-end gap-3 border-b bg-white px-6 py-2 text-sm">
    <ChairReviewLink/>
    <span>{user?.faculty?.display_code ?? user?.username} · {user?.role === "admin" ? "Administrator" : "Faculty"}</span>
    <button type="button" className="rounded border px-3 py-1" disabled={busy} onClick={async () => {
      setBusy(true); setError(""); try {await logout();} catch (reason) {setError(reason instanceof Error ? reason.message : "Logout failed. Retry.");} finally {setBusy(false);}
    }}>{busy ? "Signing out…" : "Sign out"}</button>{error && <p role="alert" className="text-red-700">{error}</p>}
  </div>;
}
