# Testing evidence

Follow [the development documentation standard](../DEVELOPMENT_DOCUMENTATION_STANDARD.md). Keep existing phase reports in place and reference their historical test ledgers instead of duplicating them.

Store sanitized command results, API assertion summaries and an artifact manifest under `<phase>/<unique-run-id>/`. Reusable evidence-only fixtures may live in `<phase>/`; application regression tests remain in `backend/tests/` and `frontend/tests/`.

Do not store credentials, cookies, HAR files, raw authenticated responses, database copies, private faculty records or GA checkpoints here. Record exact commands and environment, passed/failed/skipped/deselected counts, timestamps and limitations. Browser evidence must identify whether it uses real services, isolated storage or mocked responses.

- [Phase 4A evidence and current run links](../thesis-evidence/phase-4a-evidence.md)
