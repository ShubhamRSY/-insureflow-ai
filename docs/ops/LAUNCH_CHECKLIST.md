# Rytera Launch Checklist

Use this checklist before public launch at [ryterainc.com](https://ryterainc.com).

**2026-09-15 status:** Code-side security/UX pass completed — fixed an unauthenticated
cross-tenant IDOR on `/api/resubmit/*` (`src/insureflow/api/main.py`, regression test in
`tests/test_resubmit_idor.py`), corrected a stale `rytera.ai`/`ryterainc.com` domain
mismatch across the marketing site and dashboard footer, added a self-serve
`/dashboard/signup` CTA to the marketing site (previously every CTA dead-ended at the
login-gated `/dashboard`), replaced all 47 native `alert()` popups in the internal
dashboard with a toast component, and added route-based code-splitting (1.34MB bundle →
per-page chunks). Full backend suite (2974 passed), full frontend suite (88 passed), and
a production frontend build all pass. **None of this changes the items below** — every
unchecked item under "Production bind" and most of "Domain & DNS" / "Legal &
compliance" / "Trademark" are business/legal/infra actions outside of what code changes
can complete.

## Production bind (not demo)

Demo / pilot UW can run without these. **Do not** treat cutover as ready until all are true:

- [ ] `OPERATING_MODE=ready` (shadow off)
- [ ] Customer PAS live URL + non-dev key (not `integrations.ryterainc.com`)
- [ ] `ALLOW_SIMULATED_BIND=false` in bank/hardened mode
- [ ] Customer filed rate book imported (`python cli.py cutover-check` → `carrier_book` green)
- [ ] At least one vendor oracle sandbox (CLUE or A-PLUS) with real keys
- [ ] Counsel-signed DPA + privacy; Terraform applied; domain/TLS/SPF; trademark filing in flight

Verify: `PYTHONPATH=src python cli.py cutover-check`

## Domain & DNS

- [ ] Register **ryterainc.com** (and optionally rytera.com, getrytera.com)
- [x] Landing page built at `/` (serves `static/landing/index.html` when browser requests HTML)
- [ ] Point `ryterainc.com` → production host running this API
- [ ] Point `app.ryterainc.com` → production dashboard (`/dashboard`)
- [x] Integration gateway built at `/integrations` (deploy same routes at `integrations.ryterainc.com` in prod)
- [x] TLS path: local Caddy bank profile (`deploy/caddy`) + AWS ALB/ACM (`infra/aws`)
- [ ] Enable production HTTPS (ACM cert ARN in Terraform / Let's Encrypt)
- [ ] Set SPF/DKIM/DMARC for `@ryterainc.com` email

## Bank security posture

- [x] JWT signs/verifies with env `SECRET_KEY` (not hardcoded)
- [x] `BANK_MODE` / `ENVIRONMENT=production` disables open registration + `/auth/reset`
- [x] Encryption key required in bank mode
- [x] Compose bank overlay: no host ports for Postgres/Redis; TLS on `:8443`
- [x] AWS landing zone Terraform (VPC, ECS API + Celery worker, RDS, Redis, Secrets/KMS, WAF, CloudTrail, Cognito)
- [x] CloudWatch JSON logs + LangSmith AI tracing
- [x] Prometheus `/metrics` + Grafana dashboards + OpenObserve shipper (`docs/ops/OBSERVABILITY.md`)
- [x] WORM audit retention module + S3 Object Lock bucket in Terraform
- [x] SSO (`/auth/sso/*`) PKCE + JWKS for Cognito/Okta; set `SSO_REQUIRED=true` at bank cutover to disable password login
- [x] DPA / Privacy / SOC 2 questionnaire templates under `legal/`
- [ ] Apply Terraform to a real AWS account + ACM certificate
- [x] Complete OIDC JWKS validation for production SSO tokens (aud/iss/exp enforced when configured)

## Legal & compliance (carrier launch)

- [x] Privacy policy template (`legal/PRIVACY_POLICY_TEMPLATE.md`)
- [x] Data processing agreement template (`legal/DPA_TEMPLATE.md`)
- [x] SOC 2 / security questionnaire materials (`legal/SOC2_QUESTIONNAIRE.md`)
- [ ] Counsel review + customer countersign
- [x] Model governance docs (registry, override analytics)

## Trademark

- [ ] Search USPTO TESS for "Rytera" conflicts in Class 42 (SaaS) and Class 36 (insurance/financial)
- [ ] File intent-to-use (ITU) or use-based application for **RYTERA** word mark
- [x] ™ notice in product UI (dashboard footer + landing page)
- [x] Trademark notice document: `legal/TRADEMARK_NOTICE.md`
- [ ] Switch to ® after USPTO registration issues
- [ ] Update this file with USPTO serial number when filed

**Notice (current):** Rytera™ · ryterainc.com · Rytera is a trademark of Rytera, Inc. All rights reserved.

## Integration credentials

1. Copy `.env.example` → `.env` (never commit `.env`)
2. **Local dev:** `.env.example` ships with dev gateway key + `http://127.0.0.1:8002/integrations/...` URLs — feeds run **live** against bundled gateway
3. **Production:** replace `INTEGRATION_GATEWAY_API_KEY` and point URLs to `https://integrations.ryterainc.com/...`
4. **Real vendors:** swap gateway URLs for LexisNexis/Verisk/Guidewire endpoints and paste contract API keys

| Variable | Local dev | Production |
|----------|-----------|------------|
| `INTEGRATION_GATEWAY_API_KEY` | `rytera-dev-gateway-key-change-in-production` | Strong secret |
| `CLUE_API_URL` | `http://127.0.0.1:8002/integrations/oracles/clue/v2` | `https://integrations.ryterainc.com/oracles/clue/v2` |
| `*_API_KEY` | Same as gateway key | Vendor or gateway key |

5. Verify: `GET /pipeline/ecosystem/status` — feeds show `mode: live` and `reachable: true`

## Pre-launch smoke test

```bash
cp .env.example .env   # then edit keys
PYTHONPATH=src python cli.py serve --port 8002 --no-reload
curl http://127.0.0.1:8002/health
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/pipeline/ecosystem/status
```

- [x] Run demo submission end-to-end (`python cli.py demo` — 2026-09-03: completed, 96.4% reconciliation match rate, deterministic fallback engaged correctly on invalid LLM key)
- [ ] Confirm Submission Journey shows pipeline stages
- [ ] Confirm enterprise panel reflects integration health

## Legal & compliance (carrier launch)

- [x] Privacy policy template (`legal/PRIVACY_POLICY_TEMPLATE.md`) — publish counsel-approved copy to ryterainc.com
- [x] Data processing agreement template (`legal/DPA_TEMPLATE.md`)
- [x] SOC 2 / security questionnaire materials (`legal/SOC2_QUESTIONNAIRE.md`)
- [x] Model governance docs (registry, override analytics)
- [ ] Counsel review + customer countersign / ToS on site
