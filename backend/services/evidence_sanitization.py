"""Test-evidence privacy filter. Never use logs as a credential transport.

Redact whole sensitive assignment/header lines so pytest's abbreviated values,
escaped reprs and malformed/truncated receipts cannot retain prefixes/signatures.
The generic token filter also catches unlabelled encoded receipt fragments.
"""
import re

MARKER = '[REDACTED_SESSION_RECEIPT]'
SENSITIVE = re.compile(r'''(?ix)(?:["'\\]*)(?:review_token|assessment_receipt|session_token|session_id|session_cookie|session|csrf_token|x-csrf-token|csrfToken|access_token|refresh_token|password|authorization|set-cookie|cookie|private_key|client_secret|api_key|provider_response)(?:["'\\]*)\s*[:=]''')
ENCODED = re.compile(r'(?<![A-Za-z0-9_-])(?:eyJ[A-Za-z0-9_=-]{8,}(?:\.{1,3}[A-Za-z0-9_=-]*)*|[A-Za-z0-9_=-]{16,}(?:\.{3})?[A-Za-z0-9_=-]*\.[a-fA-F0-9]{16,})(?![A-Za-z0-9_-])')
URI = re.compile(r'\b[a-z][a-z0-9+.-]*://[^\s/<>"\x27]+:[^\s/<>"\x27]+@[^\s<>"\x27]+', re.I)
PEM = re.compile(r'-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)',re.S)


def sanitize(value: str) -> str:
    value = PEM.sub('[REDACTED_PRIVATE_KEY]', value)
    value = URI.sub('[REDACTED_CONNECTION]', value)
    value = re.sub(r'(?i)\bBearer\s+[^\s\"\x27]+', MARKER, value)
    return '\n'.join(MARKER if SENSITIVE.search(line) else ENCODED.sub(MARKER,line) for line in value.split('\n'))


def sanitize_tree(value):
    if isinstance(value,dict):
        return {key:MARKER if SENSITIVE.search(str(key)+':') else sanitize_tree(child) for key,child in value.items()}
    if isinstance(value,list): return [sanitize_tree(child) for child in value]
    return sanitize(value) if isinstance(value,str) else value
