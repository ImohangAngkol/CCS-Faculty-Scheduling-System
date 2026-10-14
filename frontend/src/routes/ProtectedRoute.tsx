import type {ReactNode} from "react";
import {Navigate, Link} from "react-router-dom";
import {useAuth} from "../context/AuthContext";
import {accountHome} from "../services/auth";
export default function ProtectedRoute({role, children}: {role: "admin" | "faculty"; children: ReactNode}) {
  const {user, status, error, refresh} = useAuth();
  if (status === "loading") return <p role="status" className="p-8">Checking your session…</p>;
  if (status === "error") return <div className="p-8"><p role="alert">{error}</p><button onClick={() => void refresh()} className="mt-3 underline">Retry session check</button></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <div className="p-8"><h1 className="text-xl font-bold">Access unavailable</h1><p>You do not have permission to open this portal.</p><Link className="underline" to={accountHome(user)}>Return to your dashboard</Link></div>;
  return children;
}
