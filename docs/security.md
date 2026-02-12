# Security

## API Keys & Secrets

- **LLM / external APIs:** Never commit API keys. Use environment variables; document required vars in `.env.example` (no real values).
- **API auth:** Use env vars for API keys or JWT signing secrets; same for webhook signing secrets if added later.

## RBAC (Placeholder)

- Web dashboard and API support a placeholder RBAC model: e.g. roles `viewer`, `operator`, `admin`.
- **Viewer:** List and view runs, metrics, replay.  
- **Operator:** Create runs, cancel, trigger eval.  
- **Admin:** Delete runs, export data, manage users (placeholder).  
- Implementation: middleware that checks API key or JWT claim; default for local dev is "no auth" or single default key.

## Audit Logs

- Log sensitive actions: run deletion, bulk export, config changes. Store in structured logs with timestamp, actor, action, resource id.
- Dashboard and API can expose "audit" view later (placeholder).

## Data

- Run data (configs, replays, metrics) may contain sensitive scenario or robot data. Restrict access per RBAC; do not log full configs in plaintext in public logs.
- PII: avoid storing PII in run metadata; if needed, document and restrict.

## Dependencies

- Keep dependencies updated; run `pip audit` / `npm audit` in CI. Document in `contributing.md`.
