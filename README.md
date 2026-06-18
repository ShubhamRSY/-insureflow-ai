# InsureFlow AI

> Multi-agent underwriting platform for **commercial insurance** and **bank mortgage** document processing.

InsureFlow AI ingests messy multi-document submissions — ACORD XML, broker PDFs, loss runs, inspection reports, W-2s, credit reports, appraisals — and produces an underwriting memo with a recommendation, premium quote, audit trail, and optional licensed UW sign-off.

Two parallel verticals share the same API, auth, job store, and encryption layer:

| Vertical | Input | Output |
|----------|-------|--------|
| **Insurance** | ACORD, broker JSON/PDF, loss runs, SOV, inspections | ACCEPT / REFER / DECLINE memo + P&C premium quote |
| **Mortgage** | W-2, 1040, credit, bank statements, appraisals | Approve / Refer / Suspend / Deny + rate lock quote |

Both pipelines work **without an LLM API key** — agents fall back to deterministic rule-based analysis.

---

## How It Works

### Insurance (default API path)

```
Broker Package → OCR/Classify → Parse → Provenance → Reconcile
    → Agent Swarm → UW Memo → Rating Quote → Workflow (pending review)
    → Licensed UW Sign-off → Bind → Loss Feedback → Encrypted Audit ZIP
```

### Mortgage

```
Loan Package → OCR/Classify → Extract → Reconcile → Compliance Rules
    → Specialist Agents → Decision Memo → Loan Pricing → Webhook → Audit
```

### Example Insurance Output

```
═══════════════════════════════════════════════════════════════
                   UNDERWRITING MEMO
═══════════════════════════════════════════════════════════════
 Pacific Coast Distributors, Inc.          UW-2026-001
───────────────────────────────────────────────────────────────
 Risk Analyst        ✅ Cold storage w/ ammonia refrigeration; $43.5M TIV
 Loss Run Analyst    ✅ 6 claims in 5 yrs, $487K incurred; 3.7% loss ratio
 Compliance Agent    ⚠️ California Prop 65, OSHA, EPA ammonia rules
 Fraud Detection     ✅ No red flags detected
───────────────────────────────────────────────────────────────
 RECOMMENDATION: REFER — ammonia refrigeration requires
                  engineer-reviewed sprinkler compliance
 Premium Quote:     $48,500 (Commercial Property, 30-day validity)
 Workflow:          PENDING LICENSED UW SIGN-OFF
═══════════════════════════════════════════════════════════════
```

---

## Quick Start

```bash
# Install
pip install -e .

# Optional: OCR for scanned PDFs (requires system Tesseract)
pip install -e ".[ocr]"

# Copy and configure environment
cp .env.example .env

# ── Insurance CLI ──
python cli.py agents \
  examples/pacific_coast_acord.xml \
  examples/pacific_coast_broker_api.json \
  examples/pacific_coast_loss_run.md \
  examples/pacific_coast_inspection_report.md \
  examples/pacific_coast_sov.md

# ── Mortgage CLI ──
python cli.py mortgage --dir simulated_documents/home_mortgage --no-llm
python cli.py mortgage-borrowers --dir simulated_documents/home_mortgage --no-llm

# ── API + Web Dashboard ──
uvicorn insureflow.api:app --reload
# Open http://localhost:8000/dashboard

# ── Docker (API + Redis + Postgres/pgvector + Celery worker) ──
docker compose up --build

# ── Tests ──
python -m pytest tests/ -q
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Gateway                          │
│   JWT Auth · Org-scoped Jobs · Redis Job Store · Dashboard      │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
        ┌───────▼────────┐            ┌───────▼────────┐
        │   INSURANCE    │            │    MORTGAGE    │
        │ InsurancePipeline           │ MortgagePipeline│
        └───────┬────────┘            └───────┬────────┘
                │                             │
    ┌───────────▼───────────────────────────▼───────────┐
    │              INGESTION + OCR                         │
    │  ACORD · JSON · Loss Run · SOV · PDF/Image Upload   │
    └───────────┬─────────────────────────────────────────┘
                │
    ┌───────────▼─────────────────────────────────────────┐
    │  Provenance Engine → Reconciliation Engine           │
    │  (deterministic source-of-truth hierarchy)           │
    └───────────┬─────────────────────────────────────────┘
                │
    ┌───────────▼─────────────────────────────────────────┐
    │  Specialist Agents (parallel, ReAct + fallback)      │
    │  Insurance: Risk · Loss Run · Compliance · Fraud     │
    │  Mortgage:  Income · Credit · Asset · Collateral     │
    └───────────┬─────────────────────────────────────────┘
                │
    ┌───────────▼─────────────────────────────────────────┐
    │  Decision + Rating                                   │
    │  Insurance: UW Memo → P&C Rating → Policy Admin stub │
    │  Mortgage:  Memo → Loan Pricing Engine → Rate Lock   │
    └───────────┬─────────────────────────────────────────┘
                │
    ┌───────────▼─────────────────────────────────────────┐
    │  Production Layer                                    │
    │  Licensed UW Workflow · Bind/Loss Feedback           │
    │  Fernet Encryption · Regulatory Audit ZIP            │
    │  Webhooks (mortgage) · Celery async workers          │
    └─────────────────────────────────────────────────────┘
```

---

## Insurance Module

### What it does

Takes a commercial insurance submission and returns:
- AI underwriting memo (ACCEPT / REFER / DECLINE)
- P&C premium quote via `InsuranceRatingEngine`
- Provenance-backed reconciliation (ACORD vs inspection vs loss run)
- Workflow state: `pending_review → approved/declined → bound`
- Encrypted audit bundle with regulatory ZIP export

### Specialist agents

| Agent | Role |
|-------|------|
| **RiskAnalystAgent** | Occupancy, construction, protection class, TIV |
| **LossRunAnalystAgent** | Claim frequency, severity, loss ratio trends |
| **ComplianceAgent** | Regulatory and guideline compliance |
| **FraudDetectionAgent** | Submission inconsistencies and red flags |
| **UWDecisionAgent** | Final recommendation with rationale |

All agents have a **deterministic fallback** when no LLM key is configured.

### Document parsers

| Parser | Input |
|--------|-------|
| ACORD | XML (`<ACORD>`) |
| Broker JSON | API payload |
| Loss Run | Markdown / PDF (OCR) |
| SOV | Pipe tables or key:value |
| Inspection Report | Free text / markdown |
| Broker PDF | Base64 upload → OCR → classify → extract |
| Classifier | Auto-routes documents to correct parser |

### Production features

| Feature | Module | Description |
|---------|--------|-------------|
| OCR on broker PDFs | `ingestion/insurance/` | Tesseract + pdfminer for scans |
| P&C rating | `rating/engine.py` | Schedule mods, loss ratio adjustments |
| Policy admin adapter | `rating/adapters/stub.py` | Guidewire/Duck Creek-style quote + bind interface |
| Licensed UW sign-off | `workflow/` | `LICENSED_UW` role, license number, override reason |
| Bind/loss feedback | `outcomes/` | Prediction vs actual premium/loss calibration |
| Regulatory audit pack | `audit/package.py` | Encrypted artifacts + ZIP with SHA-256 manifest |

### Insurance API endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/pipeline/run` | POST | underwriter | Submit insurance package (text or base64 PDF) |
| `/pipeline/jobs` | GET | viewer | List org-scoped jobs |
| `/pipeline/jobs/{id}` | GET | viewer | Job status + results |
| `/pipeline/audit/{bundle_id}` | GET | viewer | Full audit trail |
| `/pipeline/audit/{bundle_id}/package` | GET | admin | Regulatory ZIP export |
| `/pipeline/workflow/pending` | GET | viewer | Bundles awaiting UW review |
| `/pipeline/workflow/{bundle_id}/sign-off` | POST | licensed_uw | Approve / decline / refer |
| `/pipeline/workflow/{bundle_id}/bind` | POST | licensed_uw | Bind approved policy |
| `/pipeline/outcomes/loss-experience` | POST | underwriter | Record actual loss data |
| `/pipeline/outcomes/calibration` | GET | viewer | Portfolio loss ratio stats |
| `/pipeline/rating/products` | GET | viewer | Available P&C lines + base rates |

**Submit with PDF upload:**

```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "acord_xml": "...",
    "documents": [{"filename": "broker_slip.pdf", "content": "<base64>", "encoding": "base64"}],
    "use_llm": false
  }'
```

Set `"use_legacy_pipeline": true` to use the original LangGraph-only path.

---

## Mortgage Module

### What it does

Processes residential and commercial mortgage loan packages:
- Classifies 30+ document types (W-2, 1040, credit report, appraisal, rent roll, etc.)
- Cross-document reconciliation (W-2 vs 1040, appraisal vs purchase price)
- Bank compliance rules (CREDIT-001, DTI-001, LTV-001, INCOME-001, etc.)
- Rule-based specialist agents (Income, Credit, Asset, Collateral, Decision)
- Loan product pricing with rate lock quotes
- Per-borrower batch processing from folder structure

### Key components

| Component | Description |
|-----------|-------------|
| `MortgagePipeline` | End-to-end document processing |
| `MortgageSupervisorAgent` | Coordinates 5 specialist agents |
| `MortgageComplianceEngine` | Bank compliance rule engine |
| `LoanPricingEngine` | 7 loan products, LLPA-style adjustments |
| `MortgageAuditLogger` | Encrypted audit bundle persistence |
| `WebhookDispatcher` | HMAC-signed event notifications |
| `MortgageSubmissionLoader` | OCR on PDF/image uploads |

### Borrower scenarios (simulated data)

**Home mortgage** (`simulated_documents/home_mortgage/`):

| Borrower | Profile |
|----------|---------|
| John & Sarah Thompson | W-2, 740+ credit, 20% down |
| Maria Rodriguez | FTHB teacher, gift funds, 678 credit |
| David & Karen Chen | Jumbo refi, 800+ credit |
| James Wilson | Self-employed GC, 203k renovation |
| Marcus & Imani Johnson | USDA rural, first-time buyers |
| Lisa Patel | Divorcee cash-out refi, asset-heavy |

**Commercial mortgage** (`simulated_documents/commercial_mortgage/`):

| Entity | Property |
|--------|----------|
| Thompson Commercial Properties | Mixed-use retail/office |
| Oak Street Retail LLC | NNN Walgreens |
| Midwest Medical Plaza LLC | Medical office |
| Riverbend Self Storage LLC | Self-storage (65k SF) |

### Mortgage API endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/mortgage/pipeline/run` | POST | underwriter | Submit loan package |
| `/mortgage/pipeline/jobs` | GET | viewer | List org-scoped jobs |
| `/mortgage/pipeline/jobs/{id}` | GET | viewer | Job status + results |
| `/mortgage/audit/{bundle_id}` | GET | viewer | Audit trail + memo |
| `/mortgage/products` | GET | viewer | Loan product catalog |
| `/mortgage/webhooks` | POST/GET/DELETE | admin | Event subscriptions |
| `/dashboard` | GET | — | Web UI for job submission |

### Mortgage CLI

```bash
# Single directory
python cli.py mortgage --dir simulated_documents/home_mortgage --no-llm

# Per-borrower batch (discovers packages from folder structure)
python cli.py mortgage-borrowers --dir simulated_documents/home_mortgage --no-llm

# Commercial
python cli.py mortgage --dir simulated_documents/commercial_mortgage --product commercial
```

---

## API Authentication

JWT bearer tokens with role-based access control and org-scoped data isolation.

### Roles

| Role | Permissions |
|------|-------------|
| `viewer` | Read jobs, audit trails, workflow status |
| `underwriter` | Run pipelines, record loss experience |
| `licensed_uw` | Sign off on memos, bind policies |
| `admin` | Create users, delete jobs, export audit packages, manage webhooks |

### Setup

```bash
# 1. Create first admin (one-time)
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme", "role": "admin", "org_id": "my-bank"}'

# 2. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme"}'

# 3. Use token on all requests
export TOKEN="eyJhbGciOi..."
curl http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | OpenAI / compatible API key |
| `LLM_CHEAP_MODEL` | `gpt-4o-mini` | Specialist agent model |
| `LLM_EXPENSIVE_MODEL` | `gpt-4o` | Supervisor / UW decision model |
| `CLAUDE_API_KEY` | — | Anthropic API key (alternative) |
| `SECRET_KEY` | — | JWT signing secret (**change in production**) |
| `DATABASE_URL` | — | PostgreSQL for pgvector RAG |
| `REDIS_URL` | `redis://localhost:6379/0` | Persistent job store |
| `JOB_STORE_BACKEND` | `auto` | `auto` / `redis` / `memory` |
| `ENCRYPTION_KEY` | — | Fernet key for audit bundles at rest |
| `OCR_ENGINE` | `auto` | `auto` / `tesseract` / `pdfminer` |
| `AUDIT_LOG_PATH` | `./audit_logs` | Audit bundle storage path |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery async worker broker |

Generate an encryption key:

```bash
python -c "from insureflow.storage.encryption import EnvelopeEncryption; print(EnvelopeEncryption.generate_key())"
```

**No API key needed** — all agents fall back to deterministic rule-based analysis.

---

## Project Structure

```
src/insureflow/
├── agents/                  # Insurance ReAct agents + mortgage specialists
├── api.py                   # FastAPI server (insurance + mortgage)
├── audit/                   # Audit store, insurance audit logger, regulatory ZIP
├── auth/                    # JWT, roles (viewer → licensed_uw → admin)
├── graph/                   # LangGraph state machine (legacy insurance path)
├── ingestion/
│   ├── insurance/           # Broker PDF OCR, classifier, extractors
│   └── mortgage/            # Mortgage document loader, classifier, extractors
├── insurance/               # InsurancePipeline (production default)
├── mortgage/                # MortgagePipeline, pricing, compliance, webhooks
├── outcomes/                # Bind outcomes, loss experience, feedback loop
├── rating/                  # P&C rating engine + policy admin adapter
├── workflow/                # Licensed UW sign-off state machine
├── storage/                 # Redis job store, Fernet encryption
├── rag/                     # Underwriting guidelines (in-memory + pgvector)
├── provenance/              # Data provenance hierarchy
├── reconciliation/          # Cross-document discrepancy detection
├── tasks/                   # Celery workers (insurance + mortgage)
├── mcp/                     # MCP server for Claude Desktop / Cursor
├── static/dashboard.html    # Web UI
└── cli.py                   # Typer CLI

examples/                    # 3 carrier insurance submissions (Pacific Coast, Northwind, Sample)
simulated_documents/           # 80+ mortgage files across 10 borrower scenarios
tests/                         # pytest suite
evaluations/                   # Ragas + Giskard MLOps evaluation
docs/architecture.md           # Detailed system design
```

---

## Example Data

### Insurance (`examples/`)

| Carrier | Files | Description |
|---------|-------|-------------|
| **Pacific Coast Distributors** | 5 | Cold storage, $43.5M TIV, ammonia refrigeration |
| **Northwind Traders** | 4 | Heavy machinery plant, $31.7M TIV |
| **Sample Co** | 2 | Simple property risk |

### Mortgage (`simulated_documents/`)

80+ `.txt` files across home and commercial mortgage scenarios. Borrower subfolders (`chen_david_karen`, `rodriguez_maria`, etc.) enable per-borrower batch processing.

---

## Other Features

### LangGraph (legacy insurance path)

17-node state machine with conditional routing, 3× extraction retry, and human-in-the-loop checkpoint. Used when `use_legacy_pipeline: true`.

### RAG Knowledge Layer

18 underwriting guidelines across 8 categories:
- **In-memory** (default) — char-n-gram TF-IDF, no dependencies
- **pgvector** (production) — PostgreSQL with OpenAI embeddings

### MCP Server

```bash
python -m insureflow.mcp   # SSE on :8010
```

9 insurance tools + 4 mortgage tools. Compatible with Claude Desktop, Cursor, and VS Code.

### MLOps Evaluation

```bash
pip install -e ".[eval]"
python -m evaluations.runner
```

Ragas (faithfulness, relevancy) + Giskard (bias, robustness) on golden dataset.

---

## Docker

```bash
docker compose up --build
```

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI + dashboard |
| `redis` | 6379 | Job store + Celery broker |
| `db` | 5432 | PostgreSQL + pgvector |
| `mortgage-worker` | — | Celery worker for async mortgage jobs |

---

## Tests

```bash
python -m pytest tests/ -q

# Focused suites
python -m pytest tests/test_mortgage.py tests/test_mortgage_infra.py -v
python -m pytest tests/test_insurance_production.py -v
```

---

## Key Design Decisions

- **Dual verticals, shared infra** — insurance and mortgage share auth, job store, encryption, and API; separate pipelines and agents per domain
- **Deterministic fallback always present** — agents work without any LLM API key
- **Provenance hierarchy** — structured broker data (ACORD) wins over AI-extracted PDF fields; eliminates hallucinations on critical limits
- **Licensed UW gate** — AI recommends; human with license number signs off before bind
- **Encrypted audit at rest** — Fernet envelope encryption on all persisted bundles; regulatory ZIP with checksums for examiners
- **Org-scoped isolation** — jobs, workflows, audit trails, and webhooks scoped per `org_id` in JWT

---

## License

MIT
