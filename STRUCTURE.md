# Repository structure

High-level layout for Rytera / InsureFlow AI (`insureflow-ai` package).

```
.
├── src/insureflow/          # Python application package
│   ├── api/                 # FastAPI app (uvicorn insureflow.api:app → api/main.py)
│   ├── agents/              # Specialist UW agents
│   ├── insurance|mortgage|lending/
│   ├── oracles/             # CLUE / A-PLUS / NCCI / CAT clients
│   ├── pilot/               # Shadow pilot + sandbox readiness
│   ├── integration/         # PAS adapters (Guidewire, BriteCore, …)
│   ├── integrations/        # HTTP client + health factory
│   ├── static/              # Built dashboard + marketing landing
│   └── …
├── frontend/                # React/Vite dashboard source
├── tests/                   # Pytest suite
├── evaluations/             # Eval runners (RAGAS, HITL, trends)
├── docs/                    # Product / ops / outreach docs
│   ├── architecture/
│   ├── product/
│   ├── ops/
│   └── outreach/
├── scripts/
│   ├── pilot/               # Oracle verify, scenarios, smoke
│   ├── ops/                 # E2E + health
│   ├── marketing/           # LinkedIn deck builder
│   └── db/                  # SQL init
├── marketing/assets/        # Decks / screenshots
├── examples/insurance/      # Sample ACORD / loss-run packages
├── simulated_documents/     # Mortgage demo packages
├── pilot_packages/          # Partner redacted packages (gitignored contents)
├── legal/                   # DPA, privacy, SOC 2 questionnaire, TM
├── deploy/                  # Docker compose bank, tunnels, Caddy
├── infra/aws/               # Terraform (not yet applied)
├── data/                    # Runtime data (rate_curves.json tracked)
└── ml_data/                 # Training CSV schema / samples
```

## Entry points

| What | How |
|------|-----|
| API + dashboard | `uvicorn insureflow.api:app` or `python cli.py serve` |
| CLI | `python cli.py …` / `insureflow …` |
| Landing | `GET /` → `src/insureflow/static/landing/` |
| Dashboard SPA | `GET /dashboard` → `src/insureflow/static/ui/` |

## Notes

- Runtime caches (`audit_logs/`, `evaluation_*/`, `ml_models/`, `.env`) are gitignored.
- `integration` = PAS adapters; `integrations` = shared HTTP/health — intentional split, not a duplicate package.
- Old `scripts/*.py` names remain as thin shims to the new folders.
