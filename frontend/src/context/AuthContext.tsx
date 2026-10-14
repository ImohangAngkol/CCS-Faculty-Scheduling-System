import {createContext, useCallback, useContext, useEffect, useState} from "react";
import type {ReactNode} from "react";
import {AuthError, currentSession, loginAccount, logoutAccount} from "../services/auth";
import type {Account, AuthSession} from "../services/auth";
import {setSessionSecurity} from "../services/apiSession";

type AuthState = {user: Account | null; status: "loading" | "ready" | "error"; error: string;
  refresh: () => Promise<void>; login: (username: string, password: string) => Promise<Account>; logout: () => Promise<void>};
const AuthContext = createContext<AuthState | null>(null);
export function AuthProvider({children}: {children: ReactNode}) {
  const [user, setUser] = useState<Account | null>(null);
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const [error, setError] = useState("");
  const accept = useCallback((session: AuthSession) => {
    setSessionSecurity(session.csrf_token); setUser(session.user); setStatus("ready"); setError("");
  }, []);
  const clear = useCallback(() => {setSessionSecurity(null); setUser(null); setStatus("ready");}, []);
  const refresh = useCallback(async () => {
    setStatus("loading"); setError("");
    try { accept(await currentSession()); }
    catch (reason) {
      if (reason instanceof AuthError && reason.status === 401) clear();
      else {setStatus("error"); setError(reason instanceof Error ? reason.message : "Unable to verify account.");}
    }
  }, [accept, clear]);
  useEffect(() => {
    let active = true;
    const expire = () => {clear(); setError("Your session expired or was revoked. Sign in again to continue.");};
    currentSession().then(session => {if (active) accept(session);}).catch(reason => {
      if (!active) return;
      if (reason instanceof AuthError && reason.status === 401) clear();
      else {setStatus("error"); setError(reason.message);}
    });
    window.addEventListener("ccs-session-expired", expire);
    return () => {active = false; window.removeEventListener("ccs-session-expired", expire);};
  }, [accept, clear]);
  const login = async (username: string, password: string) => {const session = await loginAccount(username, password); accept(session); return session.user;};
  const logout = async () => {await logoutAccount(); clear();};
  return <AuthContext.Provider value={{user, status, error, refresh, login, logout}}>{children}</AuthContext.Provider>;
}
// Context hooks share the module's provider by design.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {const value = useContext(AuthContext); if (!value) throw new Error("AuthProvider missing"); return value;}
