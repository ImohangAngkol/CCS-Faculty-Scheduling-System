import {API_BASE, apiFetch} from "./apiSession.ts";

export type Account = {id: string; username: string; role: "admin" | "faculty"; is_active: boolean;
  faculty_id: string | null; faculty: {faculty_id: string; faculty_code: number; display_code: string; name: string} | null};
export type AuthSession = {user: Account; csrf_token: string; expires_at: string};
export class AuthError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}
export async function authRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await apiFetch(`${API_BASE}/api/auth${path}`, {...options, signal: controller.signal});
    if (response.status === 204) return undefined as T;
    const data = await response.json();
    if (!response.ok) throw new AuthError(typeof data.detail === "string" ? data.detail : "Review the account fields and try again.", response.status);
    return data;
  } catch (error) {
    if (error instanceof AuthError) throw error;
    throw new AuthError("Unable to reach authentication service. Check the backend and identity database, then retry.", 0);
  } finally { clearTimeout(timeout); }
}
export function validateSession(session: AuthSession): AuthSession {
  const user = session?.user;
  if (!user || typeof user.id !== "string" || typeof user.username !== "string" || !user.is_active
      || !["admin", "faculty"].includes(user.role) || typeof session.csrf_token !== "string" || !session.csrf_token
      || !Number.isFinite(Date.parse(session.expires_at))) throw new AuthError("Invalid account response. Ask the administrator to check authentication configuration.", 0);
  if (user.faculty && (user.faculty.faculty_id !== user.faculty_id || !Number.isInteger(user.faculty.faculty_code) || user.faculty.faculty_code < 0))
    throw new AuthError("Faculty binding could not be verified. Ask an administrator to repair the account.", 0);
  return session;
}
export const currentSession = async () => validateSession(await authRequest<AuthSession>("/me"));
export const loginAccount = async (username: string, password: string) => validateSession(await authRequest<AuthSession>("/login", {
  method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({username, password}),
}));
export const logoutAccount = () => authRequest<void>("/logout", {method: "POST"});
export const accountHome = (user: Account) => user.role === "admin" ? "/admin" : "/faculty";
