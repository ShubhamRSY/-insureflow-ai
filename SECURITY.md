# Security

Rytera source and underwriting IP are **proprietary**. The GitHub repository
must stay **private** (Settings → General → Danger zone → Change visibility).
A public clone cannot be obfuscated enough to protect the product idea —
visibility is the control.

## What this repo must never contain

- Live API keys, JWT `SECRET_KEY`, Fernet `ENCRYPTION_KEY`, PAS/oracle tokens
- Customer submissions, MIB/MVR/Rx payloads, or audit bundles
- `.env` (use `.env.example` only)

If a secret was ever committed, **rotate it** — deleting the file is not enough.

## Production posture

Set `ENVIRONMENT=production` or `BANK_MODE=true`. Startup refuses default
secrets, open registration, and simulated binds. Anonymous `/system/diagnostics`,
`/security/status`, and `/metrics` are closed (set `METRICS_BEARER` to scrape).

## Report a vulnerability

Email security concerns to the repo owners. Do not open a public issue with
exploit details or customer data.
