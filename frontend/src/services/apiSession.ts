import axios from "axios";

// Keep cookies on the same site: localhost frontend and localhost backend in dev.
export const API_BASE = import.meta.env?.VITE_API_URL ?? "http://localhost:8000";
let csrfToken: string | null = null;
let sessionRevision = 0;
const requestSessions = new WeakMap<object, number>();
export function setSessionSecurity(token: string | null) {
  if (token !== csrfToken) sessionRevision += 1;
  csrfToken = token;
}
function expired(requestRevision: number) {
  // An old request must not clear a newer authenticated account.
  if (requestRevision === sessionRevision && csrfToken && typeof window !== "undefined")
    window.dispatchEvent(new Event("ccs-session-expired"));
}
export async function apiFetch(input: string | URL | Request, options: RequestInit = {}): Promise<Response> {
  const requestRevision = sessionRevision;
  const headers = new Headers(options.headers);
  const method = (options.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrfToken) headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(input, {...options, headers, credentials: "include"});
  if (response.status === 401) expired(requestRevision);
  return response;
}
export const apiClient = axios.create({baseURL: API_BASE, withCredentials: true, timeout: 15000});
apiClient.interceptors.request.use(config => {
  requestSessions.set(config, sessionRevision);
  if (!["get", "head", "options"].includes(config.method ?? "get") && csrfToken) config.headers.set("X-CSRF-Token", csrfToken);
  return config;
});
apiClient.interceptors.response.use(response => {
  requestSessions.delete(response.config);
  return response;
}, (error: unknown) => {
  if (axios.isAxiosError(error) && error.config) {
    const revision = requestSessions.get(error.config);
    if (error.response?.status === 401 && revision !== undefined) expired(revision);
    requestSessions.delete(error.config);
  }
  return Promise.reject(error);
});
