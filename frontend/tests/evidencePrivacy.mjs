// Sanitize browser scenario errors before any evidence write. No raw captures of
// network headers, response bodies, cookies or private stdin configuration.
const marker='[REDACTED_SESSION_RECEIPT]';
const sensitive=/(?:review_token|assessment_receipt|session_token|session_id|session_cookie|session|csrf_token|x-csrf-token|csrfToken|access_token|refresh_token|password|authorization|set-cookie|cookie|private_key|client_secret|api_key|provider_response)["'\\]*\s*[:=]/i;
export function sanitizeText(value) {
 return value.replace(/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)/g,'[REDACTED_PRIVATE_KEY]')
  .replace(/\b[a-z][a-z0-9+.-]*:\/\/[^\s/<>"']+:[^\s/<>"']+@[^\s<>"']+/gi,'[REDACTED_CONNECTION]')
  .replace(/\bBearer\s+[^\s\"']+/gi,marker)
  .split('\n').map(line=>sensitive.test(line)?marker:line.replace(/eyJ[A-Za-z0-9_=-]{8,}(?:\.{1,3}[A-Za-z0-9_=-]*)*|[A-Za-z0-9_=-]{16,}(?:\.{3})?[A-Za-z0-9_=-]*\.[a-fA-F0-9]{16,}/g,marker)).join('\n');
}
export function sanitizeTree(value) {
 if(typeof value==='string')return sanitizeText(value);
 if(Array.isArray(value))return value.map(sanitizeTree);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([key,child])=>[key,sensitive.test(key+':')?marker:sanitizeTree(child)]));
 return value;
}
