# Rytera Launch Checklist

Use this checklist before public launch at [rytera.ai](https://rytera.ai).

## Domain & DNS

- [ ] Register **rytera.ai** (and optionally rytera.com, getrytera.com)
- [x] Landing page built at `/` (serves `static/landing/index.html` when browser requests HTML)
- [ ] Point `rytera.ai` → production host running this API
- [ ] Point `app.rytera.ai` → production dashboard (`/dashboard`)
- [x] Integration gateway built at `/integrations` (deploy same routes at `integrations.rytera.ai` in prod)
- [ ] Enable HTTPS (Let's Encrypt or cloud provider cert)
- [ ] Set SPF/DKIM/DMARC for `@rytera.ai` email

## Trademark

- [ ] Search USPTO TESS for "Rytera" conflicts in Class 42 (SaaS) and Class 36 (insurance/financial)
- [ ] File intent-to-use (ITU) or use-based application for **RYTERA** word mark
- [x] ™ notice in product UI (dashboard footer + landing page)
- [x] Trademark notice document: `legal/TRADEMARK_NOTICE.md`
- [ ] Switch to ® after USPTO registration issues
- [ ] Update this file with USPTO serial number when filed

**Notice (current):** Rytera™ · rytera.ai · Rytera is a trademark of Rytera, Inc. All rights reserved.

## Integration credentials

1. Copy `.env.example` → `.env` (never commit `.env`)
2. **Local dev:** `.env.example` ships with dev gateway key + `http://127.0.0.1:8002/integrations/...` URLs — feeds run **live** against bundled gateway
3. **Production:** replace `INTEGRATION_GATEWAY_API_KEY` and point URLs to `https://integrations.rytera.ai/...`
4. **Real vendors:** swap gateway URLs for LexisNexis/Verisk/Guidewire endpoints and paste contract API keys

| Variable | Local dev | Production |
|----------|-----------|------------|
| `INTEGRATION_GATEWAY_API_KEY` | `rytera-dev-gateway-key-change-in-production` | Strong secret |
| `CLUE_API_URL` | `http://127.0.0.1:8002/integrations/oracles/clue/v2` | `https://integrations.rytera.ai/oracles/clue/v2` |
| `*_API_KEY` | Same as gateway key | Vendor or gateway key |

5. Verify: `GET /pipeline/ecosystem/status` — feeds show `mode: live` and `reachable: true`

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
