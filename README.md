# Rytera

> Enterprise multi-agent underwriting platform for **commercial insurance**, **bank mortgage**, and **consumer/commercial lending**.

**Live:** [app.ryterainc.com](https://app.ryterainc.com) · **Package:** `insureflow-ai`

---

## What It Does

Ingests multi-format submission packages (ACORD XML, broker PDFs, loss runs, W-2s, credit reports, appraisals) and produces underwriting memos with recommendations, premium/rate quotes, encrypted audit trails, and optional licensed underwriter sign-off.

All three verticals share a unified API, JWT auth, org-scoped job store, Fernet encryption, and React dashboard. Pipelines work **with or without an LLM API key** via deterministic agent fallbacks.

| Vertical | Input | Output |
|----------|-------|--------|
| **Insurance** | ACORD, broker JSON/PDF, loss runs, SOV, inspections | ACCEPT / REFER / DECLINE + P&C premium quote |
| **Mortgage** | W-2, 1040, credit, bank statements, appraisals | Approve / Refer / Suspend / Deny + rate lock |
| **Lending** | Application data, credit pulls, bank statements | Approve / Counteroffer / Decline + risk-based pricing |

---

## Quick Start

### Local Development

```bash
# Install
pip install -e ".[ocr]"
cp .env.example .env

# Start infrastructure
docker compose up -d redis db

# Start API + dashboard
python cli.py serve --port 8002

# Open http://localhost:8002/dashboard
```

### Docker (Full Stack)

```bash
docker compose up --build
```

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI + dashboard |
| `redis` | 6379 | Job store + Celery broker |
| `db` | 5432 | PostgreSQL + pgvector |
| `mortgage-worker` | — | Celery worker for async mortgage jobs |

### CLI Examples

```bash
# Insurance
python cli.py agents examples/pacific_coast_acord.xml examples/pacific_coast_broker_api.json

# Mortgage
python cli.py mortgage --dir simulated_documents/home_mortgage --no-llm

# Lending
python cli.py lending --application examples/lending/application_001.json

# System health
python cli.py doctor
```

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  FastAPI Gateway                      │
│  JWT Auth · RBAC · Org-scoped Jobs · Dashboard (10p) │
└──────┬───────────────┬──────────────┬────────────────┘
       │               │              │
 ┌─────▼──────┐  ┌─────▼──────┐  ┌───▼──────┐
 │ INSURANCE  │  │  MORTGAGE  │  │ LENDING  │
 │ Pipeline   │  │  Pipeline  │  │ Pipeline │
 └─────┬──────┘  └─────┬──────┘  └───┬──────┘
       └───────────────┴──────────────┘
                       │
         ┌─────────────▼─────────────────┐
         │  Specialist Agents (12+ agents)│
         │  Risk · Loss Run · Compliance  │
         │  Fraud · Triage · RAG · Oracle │
         │  Income · Credit · Asset       │
         └─────────────┬─────────────────┘
                       │
         ┌─────────────▼─────────────────┐
         │  Decision + Rating + Workflow  │
         │  UW Memo → Rating → Bind      │
         │  Audit ZIP · Webhooks         │
         └───────────────────────────────┘
```

---

## Project Structure

```
src/insureflow/
├── api.py              # FastAPI server
├── config.py           # Settings (dual-model LLM)
├── cli.py              # Typer CLI
├── agents/             # Insurance + mortgage specialist agents
│   ├── orchestrator.py
│   ├── risk_analyst.py
│   ├── loss_run_analyst.py
│   ├── compliance_agent.py
│   ├── fraud_detection_agent.py
│   ├── triage_agent.py
│   ├── uw_decision_agent.py
│   ├── rag_agent.py
│   └── mortgage/       # Mortgage supervisor
├── insurance/          # InsurancePipeline
├── mortgage/           # MortgagePipeline, pricing, compliance, webhooks
├── lending/            # Consumer/commercial lending
├── rating/             # P&C rating engine + policy admin adapters
├── oracles/            # CLUE, NCCI, A-PLUS, CAT model
├── rag/                # RAG + knowledge graph + vector store
├── underwriting/       # COPE, authority, market, renewal
├── portfolio/          # Concentration + reinsurance treaty
├── provenance/         # Source-of-truth hierarchy
├── reconciliation/     # Cross-document discrepancy detection
├── redaction/          # PII detection + redaction
├── registry/           # Model versioning + compliance workflow
├── outcomes/           # Loss experience + override analytics
├── analytics/          # Document + agent performance analytics
├── entities/           # Named entity resolution
├── audit/              # Audit store + regulatory ZIP
├── auth/               # JWT, RBAC, persistent user store
├── workflow/           # Licensed UW sign-off state machine
├── webhooks/           # HMAC-signed event dispatch
├── integration/        # Guidewire, BriteCore, HubSpot adapters
├── storage/            # Redis job store + Fernet encryption
├── tasks/              # Celery workers
├── health/             # System diagnostics
├── e2e/                # E2E test runner + Playwright
├── llm/                # Multi-provider LLM client
├── mcp/                # MCP server for Claude Desktop/Cursor
└── static/ui/          # Built React dashboard

frontend/               # React 18 + Vite + Tailwind
deploy/                 # Docker, Caddy, Cloudflare tunnel configs
infra/aws/              # Terraform (VPC, ECS, RDS, Redis, WAF)
evaluations/            # Ragas + Giskard MLOps eval
tests/                  # pytest suite (395+ tests)
examples/               # 5 insurance submission packages
simulated_documents/    # 80+ mortgage files across 10 scenarios
```

---

## Testing

```bash
# Unit + integration (395+ tests)
python -m pytest tests/ -q

# E2E (live API required)
python scripts/e2e_test.py --fast --timeout 360

# Focused suites
python -m pytest tests/test_agents.py tests/test_mortgage.py -v
```

---

## Configuration

Copy `.env.example` to `.env`. No API key required — agents fall back to deterministic analysis.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | OpenAI key (optional) |
| `LLM_CHEAP_MODEL` | `gpt-4o-mini` | Specialist agent model |
| `LLM_EXPENSIVE_MODEL` | `gpt-4o` | Final decision model |
| `SECRET_KEY` | — | JWT signing (**change in prod**) |
| `REDIS_URL` | `redis://localhost:6379/0` | Job store |
| `ENCRYPTION_KEY` | — | Fernet key for audit bundles |

---

## Authentication

JWT with RBAC: `viewer` → `underwriter` → `licensed_uw` → `admin` → `cuo`

```bash
# First-time setup
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme", "org_id": "bank"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme"}'
```

---

## Deployment

### Cloudflare Tunnel (free, branded URL)

```bash
brew install cloudflared
cloudflared tunnel login
cloudflared tunnel create rytera
cloudflared tunnel route dns rytera app.ryterainc.com
cloudflared tunnel run --url http://localhost:8000 rytera
# → https://app.ryterainc.com
```

### AWS (production)

```bash
cd infra/aws && terraform init && terraform apply
```

Provisions: VPC, ALB + TLS, ECS Fargate, RDS Postgres, ElastiCache Redis, WAF, CloudTrail, Secrets Manager.

---

## License

MIT
