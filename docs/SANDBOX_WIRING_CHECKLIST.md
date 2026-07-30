# Sandbox wiring checklist (insurance)

Use with `.env.production.example`. Goal: move from **simulated** → **sandbox_ready** → **pilot_live_ready**.

## 0. Baseline (today)

```bash
cp .env.production.example .env   # then fill secrets
# Or for local shadow: ensure REDIS_URL + ENCRYPTION_KEY + non-dev gateway key
PYTHONPATH=src python cli.py pilot prepare   # seed → redact → calibrate → status
PYTHONPATH=src python cli.py sandbox-status
PYTHONPATH=src python cli.py doctor
```

Expected early state: `overall=pilot_shadow_ready` once local infra is set (oracles may still be simulated).

## 1. Infra (required before any pilot)

| Variable | Action |
|----------|--------|
| `SECRET_KEY` | ≥32 char unique secret |
| `ENCRYPTION_KEY` | Fernet key from EnvelopeEncryption.generate_key() |
| `REDIS_URL` | Reachable Redis |
| `INTEGRATION_GATEWAY_API_KEY` | Not the `rytera-dev-…` placeholder |
| `PILOT_SHADOW_MODE` | `true` for shadow UW (recommended until PAS live) |

## 2. Oracle sandboxes

| Vendor | Env | Notes |
|--------|-----|-------|
| LexisNexis CLUE | `CLUE_API_KEY`, `CLUE_API_URL`, `ORACLE_MODE=auto\|live` | Point URL at **vendor sandbox**, not `/integrations/oracles/clue` synthetic gateway |
| Verisk A-PLUS | `APLUS_API_KEY`, `APLUS_API_URL` | Same |
| NCCI | `NCCI_API_KEY`, `NCCI_API_URL` | Optional for WC |
| CAT | `CAT_API_KEY`, `CAT_API_URL` | Optional |

Verify:

```bash
PYTHONPATH=src python cli.py sandbox-status
# CLUE / A-PLUS should show sandbox_ready or ready
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/pilot/sandbox-status
```

## 3. Policy admin (bind)

| System | Env |
|--------|-----|
| Guidewire | `GUIDEWIRE_API_KEY`, `GUIDEWIRE_API_URL`, `GUIDEWIRE_MODE=auto` |
| BriteCore | `BRITECORE_*` |

Until these are live:

- Keep `PILOT_SHADOW_MODE=true`
- `/pipeline/workflow/{id}/bind` returns **403**
- Core PAS submit is skipped on pilot package runs

When ready:

```bash
# unset or false
PILOT_SHADOW_MODE=false
ALLOW_SIMULATED_BIND=false
```

## 4. Redacted packages

```bash
PYTHONPATH=src python cli.py pilot seed          # demo packages
# or drop partner files under pilot_packages/<partner>/<id>/
PYTHONPATH=src python cli.py pilot scan-pii --partner demo --submission coastal_fl_appetite_decline
PYTHONPATH=src python cli.py pilot redact --partner demo --submission coastal_fl_appetite_decline --inplace
# Optional: IMAP broker inbox → packages (auto-redacts blocking PII)
PYTHONPATH=src python cli.py pilot ingest-email --partner email --limit 10
PYTHONPATH=src python cli.py pilot run --all
PYTHONPATH=src python scripts/smoke_pilot_deploy.py
```

## 5. Go / no-go

| overall | Meaning |
|---------|---------|
| `not_ready` | Missing Redis/encryption/gateway or all oracles simulated |
| `pilot_shadow_ready` | Safe to run partner packages; bind off |
| `pilot_live_ready` | Required oracles + Guidewire configured |

Partner outreach template: [`PILOT_PARTNER_BRIEF.md`](./PILOT_PARTNER_BRIEF.md)
