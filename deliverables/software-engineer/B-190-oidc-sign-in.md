# B-190 — OIDC sign-in and authenticated audit for the workbench

Date: 2026-10-21. Branch: `sso-b190` (from `ai-team`). Scope: the pipeline workbench only.
Synthetic data only; no real submission, carrier package or decision is used here.

## What changed

- `underwriting_pipeline/app/auth.py` adds the sign-in boundary:
  - OIDC authorization-code flow with PKCE (S256), `state` and `nonce`.
  - ID token verification from the provider JWKS (RS256/384/512, ES256), with issuer,
    audience, lifetime and nonce checks.
  - A short-lived HMAC-signed session cookie; no server-side session store.
  - A per-render signed form token. A stale, forged or other-user token is refused.
  - Origin/Host check on every POST.
  - A fail-closed configuration: without the OIDC settings the workbench shows
    "Sign-in unavailable" and renders no submission.
- `underwriting_pipeline/app/workbench.py` now requires a session on `GET /` and on every
  POST route. `/login`, `/auth/callback` and `/logout` are the only sign-in routes.
  It overwrites a posted `underwriter_id` with the session user, renders the actor as text
  instead of an id field, and appends an audit row for each view, decision, send and
  refusal. A failed audit write is shown to the user and never swallowed.
- `underwriting_pipeline/app/quotes.py` uses the same per-render form token and session
  actor for subjectivity closures.
- Screenshots: `deliverables/software-engineer/screenshots/B-190-sign-in.png` and
  `B-190-signed-in-queue.png` (sandbox copy; the banner says so).

## Configuration (shell environment only)

| Variable | Meaning |
|---|---|
| `OIDC_ISSUER` | provider issuer; discovery at `<issuer>/.well-known/openid-configuration` |
| `OIDC_CLIENT_ID` | registered client id |
| `OIDC_CLIENT_SECRET` | optional; omitted for a public client |
| `OIDC_REDIRECT_URI` | default `http://127.0.0.1:8765/auth/callback` |
| `OIDC_SCOPES` | default `openid profile email` |
| `OIDC_TOKEN_AUTH` | `client_secret_post` (default) or `client_secret_basic` |
| `SESSION_SECRET` | 32+ random characters; signs session, state and form tokens |
| `AUTH_AUDIT_LOG` | default `deliverables/software-engineer/auth-audit.jsonl` |

An identity is mapped to `underwriters.json` by verified `email`, or by `oidc_sub`
(optionally with `issuer`), or by `issuer` + `subject`. An identity with no matching row
gets no session. The default rows carry no provider mapping, so the pilot operator adds
the mapping for the chosen provider.

## Audit log

One JSON object per line, `0600`, append-only with a cross-process lock and `fsync`:

```json
{"v":1,"user":"user","name":"...","action":"view|decision|send|login|logout",
 "submission":"SUB-002","outcome":"ok|refused","reason":"...",
 "at":"2026-10-21T13:25:33-04:00","run_hash":"..."}
```

The log is gitignored. A failed audit write raises; the page shows the failure.

## Verification

- `../insureflow-ai-team/.venv/bin/python -m pytest tests/pipeline -q` → **62 passed**.
  New tests: `tests/pipeline/test_auth.py` (12) and `tests/pipeline/test_workbench_auth.py` (7).
- `python underwriting_pipeline/app/workbench.py` → `workbench ok` (self-checks, sandbox only).
- `ruff check` on the new files → clean. `pyright` on `auth.py` → clean.
- Tests use a local fake OIDC provider and temporary sandbox paths; 0 model calls; no real
  workbench page, log, outbox or token log is written.

## Not done / open

- The provider choice and the pilot tenant configuration need @compliance sign-off. This
  change makes the boundary config-gated; it does not choose a provider or create one.
- The React app is out of scope (it is a post-demo task).
- No decision, send or carrier package was approved by an AI role for this work.
