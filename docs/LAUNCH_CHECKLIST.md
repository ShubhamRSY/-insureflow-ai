# Rytera Launch Checklist

Use this checklist before public launch at [rytera.ai](https://rytera.ai).

## Domain & DNS

- [ ] Register **rytera.ai** (and optionally rytera.com, getrytera.com)
- [ ] Point `rytera.ai` → marketing site / landing page
- [ ] Point `app.rytera.ai` → production dashboard (or path on main domain)
- [ ] Point `integrations.rytera.ai` → integration gateway (orchestrates vendor APIs)
- [ ] Enable HTTPS (Let's Encrypt or cloud provider cert)
- [ ] Set SPF/DKIM/DMARC for `@rytera.ai` email

## Trademark

- [ ] Search USPTO TESS for "Rytera" conflicts in Class 42 (SaaS) and Class 36 (insurance/financial)
- [ ] File intent-to-use (ITU) or use-based application for **RYTERA** word mark
- [ ] Add ™ notice in product UI (done in dashboard footer)
- [ ] Switch to ® after USPTO registration issues
- [ ] Update `docs/LAUNCH_CHECKLIST.md` status when filed

**Notice (current):** Rytera™ · rytera.ai · Rytera is a trademark of Rytera, Inc. All rights reserved.

## Integration credentials

1. Copy `.env.example` → `.env` (never commit `.env`)
2. Set `ORACLE_MODE=auto` (default) — live when keys + health check pass, else simulated
3. Paste vendor API keys into `.env`:

| Variable | Source |
|----------|--------|
| `CLUE_API_KEY` | LexisNexis CLUE contract |
| `VERISK_API_KEY` / `NCCI_API_KEY` / `APLUS_API_KEY` / `CAT_API_KEY` | Verisk carrier agreement |
| `GUIDEWIRE_*` | Guidewire PolicyCenter REST credentials |
| `BRITECORE_API_KEY` | BriteCore API key |
| `HUBSPOT_API_KEY` | HubSpot private app token |
| `LOSS_CONTROL_*` / `CLAIMS_*` / `BROKER_PORTAL_*` / `ACTUARIAL_*` | Carrier ops systems or gateway |

4. Default URLs point at `https://integrations.rytera.ai/...` — deploy your gateway there or override per-service URLs in `.env`
5. Verify: `GET /pipeline/ecosystem/status` — feeds show `reachable: true` when live

## Pre-launch smoke test

```bash
cp .env.example .env   # then edit keys
PYTHONPATH=src python cli.py serve --port 8002 --no-reload
curl http://127.0.0.1:8002/health
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8002/pipeline/ecosystem/status
```

- [ ] Run demo submission end-to-end
- [ ] Confirm Submission Journey shows pipeline stages
- [ ] Confirm enterprise panel reflects integration health

## Legal & compliance (carrier launch)

- [ ] Privacy policy and terms of service on rytera.ai
- [ ] Data processing agreement (DPA) for carrier customers
- [ ] SOC 2 / security questionnaire materials
- [ ] Model governance docs (registry, override analytics)
