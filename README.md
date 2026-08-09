# Rytera

> Enterprise AI underwriting for **commercial insurance**, **bank mortgage**, and **consumer/commercial lending** — from messy submission packages to a bind-ready, audit-ready decision.

**Production:** [ryterainc.com](https://ryterainc.com) · **Module:** `insureflow`

Rytera reads the documents carriers actually receive — ACORD XML, broker PDFs, loss runs, schedules of values, floor plans, financial statements, W-2s, credit reports, appraisals — and turns them into an underwriting memo with a recommendation, a premium or rate quote, an encrypted audit trail, and optional licensed-UW sign-off.

Three verticals, one platform. Pipelines run **with or without an LLM API key** — deterministic first, trained ML next, LLM last (budgeted by a zero-token router).

---

## Why Rytera

- **No black box.** Every field is cited with provenance; every decision lands on a visible, auditable journey from intake to memo.
- **Human-in-the-loop.** AI recommends — a licensed underwriter with license number signs off before bind.
- **Cheap at scale.** The ZTA router resolves most submissions deterministically (zero tokens); LLMs are spent only where rule-based parsing genuinely falls short.
- **Desk-native.** Tooling for **line underwriters** (branch process, coverage assist, producer service) *and* **staff underwriters** (home-office guides, rating plans, UW audits, training).

---

## What it handles

| Vertical | Inputs | Output |
|----------|--------|--------|
| **Insurance** | ACORD XML, broker PDF/JSON, loss runs, SOV, inspections, **floor plans/schematics**, **financial statements** | ACCEPT / REFER / DECLINE memo + P&C premium quote |
| **Mortgage** | W-2, 1040, credit, bank statements, appraisals (30+ doc types) | Approve / Refer / Suspend / Deny + rate lock |
| **Lending** | Applications, credit pulls, bank statements | Approve / Counteroffer / Decline + risk-based pricing |

### Smart document parsers

| Parser | What it pulls out |
|--------|-------------------|
| **ACORD XML** | Named insured, broker, coverages, locations, risk profile, **form numbers (125 / 126 / 130 / 140)** |
| **Financial statements** | Balance sheet, income statement, tax returns → 16 revenue/liquidity/leverage line items |
| **Floor plans & schematics** | Area, stories, fire compartments, exits, stairwells, alarm/sprinkler protection |
| **Loss runs** | Claim frequency, severity, loss-ratio trends |
| **SOV** | Pipe tables or key:value values |
| **Inspection reports** | COPE details from free text |
| **Broker PDFs** | OCR → classify → extract |

### Decision intelligence

- **14 specialist agents** — Risk, Loss Run, Compliance, Fraud, UW Decision, Triage, Verification, Synthesis, RAG, Reinsurance, Portfolio, Oracle, + mortgage specialists — each with a deterministic fallback.
- **External data oracles** — CLUE, NCCI, A-PLUS, CAT sim, **credit bureau, public records, OSHA, rating agency** feeds, health-checked via a live gateway.
- **ISO-style rating** — loss costs × territorial relativities × COPE mods × market cycle.
- **Provenance & reconciliation** — structured broker data outranks AI-extracted PDF fields; cross-document conflicts surface as findings, not guesses.
- **Line + staff UW desks**, delegation-of-authority matrix, renewals, portfolio concentration, reinsurance treaty fit, and an override-analytics feedback loop.

### Governance & ops

- Licensed-UW sign-off → bind → loss-feedback calibration loop
- Encrypted audit bundles at rest (Fernet) + regulatory ZIP with SHA-256 manifest
- JWT auth with RBAC roles (`viewer → underwriter → staff_uw → licensed_uw → admin → cuo`), org-scoped isolation
- Model & guideline **registry** with approval workflow
- Webhooks (HMAC) + token-based broker status shares
- PII redaction, entity resolution, document analytics
- React dashboard at `/dashboard` with a full submission-journey view (COPE, provenance, reconciliation, pricing build-up, human checkpoints, audit trail)

---

## Quick start

```bash
pip install -e .
cp .env.example .env            # configure keys — or skip, deterministic mode works without LLM
```

```bash
# Infrastructure (Redis, Postgres) — or use the in-memory fallback
docker compose up -d redis db

# API + dashboard
uvicorn insureflow.api:app --reload --port 8002

# CLI examples
python cli.py insurance demo --preset pacific_coast
python cli.py system health
python cli.py test
```

> **No LLM key?** Fine. Every agent falls back to deterministic rule-based analysis.

**Submit a package via API:**

```bash
curl -X POST http://localhost:8002/pipeline/run \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"documents": [{"filename": "broker_slip.pdf", "content": "<base64>", "encoding": "base64"}], "use_llm": false}'
```

### Docker (full stack)

```bash
docker compose up --build   # api:8000 · redis · postgres+pgvector · celery worker
```

---

## Architecture

```
Clients (SPA / CLI / MCP / curl)
        │  HTTPS · JWT
        ▼
API Gateway (FastAPI) — auth · RBAC · org scope · rate limits
        │
        ├── Intake & connectors  (24 connectors, Connect & pull hub)
        └── Vertical pipelines   (/pipeline/* insurance · /mortgage/* · /lending/*)
        │
        ▼
Shared intelligence — ZTA router (deterministic → ML → LLM)
        Parsers · Provenance · Reconciliation · Rating · Compliance
        Specialist agents · RAG (pgvector) · ML models · Vision
        │
        ▼
Workflow · Audit · Governance — UW sign-off → bind → loss feedback
        Webhooks · Fernet audit bundles · Model registry
        │
        ▼
Infrastructure — Redis jobs · PostgreSQL+pgvector · Celery · Railway
```

Deep dive: [`docs/architecture/architecture.md`](docs/architecture/architecture.md) · [`docs/ZERO_TOKEN_ARCHITECTURE.md`](docs/ZERO_TOKEN_ARCHITECTURE.md)

---

## Tests

```bash
python -m pytest tests/ -q                                     # unit + integration
python -m pytest tests/ -q --ignore=tests/test_e2e.py          # skip E2E for speed
python scripts/ops/e2e_test.py --fast --timeout 360            # live-server E2E
python -m ruff check . && python -m ruff format --check .      # lint
python -m mypy src/ tests/                                     # types
```

**1,400+ tests** across parsers, agents, rating, workflow, oracles, provenance, reconciliation, integrations, ML, ZTA, security, and SSO — plus a 42-scenario live E2E suite.

---

## More docs

| Topic | Where |
|-------|-------|
| Full API reference (insurance / mortgage / lending) | [`docs/api.md`](docs/api.md) |
| Configuration (`.env`) | [`.env.example`](.env.example) |
| Launch checklist & ops | [`docs/ops/LAUNCH_CHECKLIST.md`](docs/ops/LAUNCH_CHECKLIST.md) |
| Underwriting fundamentals | [`docs/underwriting/underwriting_fundamentals.md`](docs/underwriting/underwriting_fundamentals.md) |
| MLOps evaluations & quality gates | [`evaluations/`](evaluations/) |
| Project layout | [`STRUCTURE.md`](STRUCTURE.md) |

**Example data:** 5 carrier submissions in [`examples/`](examples/) · 80+ mortgage docs across 10 borrowers in [`simulated_documents/`](simulated_documents/)

---

## Key design decisions

- **Deterministic fallback always present** — the platform works with zero API keys.
- **Provenance beats prompting** — structured broker data outranks AI-extracted fields on critical limits.
- **Licensed-UW gate** — AI recommends, a licensed underwriter decides, then bind.
- **Encrypted audit at rest** — Fernet bundles + SHA-256 regulatory ZIPs for examiners.
- **Test-driven delivery** — 1,400+ tests and a full E2E suite keep production honest.
- **Production on Railway** — Redis, PostgreSQL/pgvector, all 10 diagnostics green.

---

## License

MIT
