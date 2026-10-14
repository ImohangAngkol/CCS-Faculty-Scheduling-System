import {useState} from "react";
import {Navigate, useNavigate} from "react-router-dom";
import {useAuth} from "../context/AuthContext";
import {accountHome} from "../services/auth";
export default function Login() {
  const {user, status, login, error: initError, refresh} = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState(""), [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  if (status === "loading") return <p role="status" className="p-8">Checking your session…</p>;
  if (user && status === "ready") return <Navigate to={accountHome(user)} replace />;
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6"><form className="w-full max-w-md space-y-4 rounded-xl border bg-white p-8 shadow-sm" onSubmit={async event => {
    event.preventDefault(); setBusy(true); setError("");
    try {const account = await login(username.trim(), password); setPassword(""); navigate(accountHome(account), {replace: true});}
    catch (reason) {setError(reason instanceof Error ? reason.message : "Unable to sign in."); setPassword("");}
    finally {setBusy(false);}
  }}>
    <h1 className="text-2xl font-bold text-[#115E59]">CCS Faculty Scheduling</h1><p className="text-sm text-slate-600">Sign in with your administrator or faculty account.</p>
    {(error || initError) && <p role="alert" className="text-sm text-red-700">{error || initError}</p>}
    {status === "error" && <button type="button" className="text-sm underline" onClick={() => void refresh()}>Retry session check</button>}
    <label className="block text-sm">Username or institutional email<input className="mt-1 w-full rounded border p-2" autoComplete="username" required maxLength={254} value={username} onChange={event => setUsername(event.target.value)} /></label>
    <label className="block text-sm">Password<input className="mt-1 w-full rounded border p-2" type="password" autoComplete="current-password" required maxLength={1024} value={password} onChange={event => setPassword(event.target.value)} /></label>
    <button className="w-full rounded bg-[#0F766E] p-2 text-white" disabled={busy || !username.trim() || !password}>{busy ? "Signing in…" : "Sign in"}</button>
    <p className="text-xs text-slate-500">Need an account or a password reset? Contact your department administrator.</p>
  </form></main>;
}
