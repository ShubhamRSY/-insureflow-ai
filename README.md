# InsureFlow AI

> Enterprise multi-agent underwriting platform for **commercial insurance**, **bank mortgage**, and **consumer/commercial lending** document processing.

InsureFlow AI ingests multi-format submission packages — ACORD XML, broker PDFs, loss runs, W-2s, credit reports, appraisals — and produces an underwriting memo with a recommendation, premium or rate quote, encrypted audit trail, and optional licensed underwriter sign-off.

All three verticals share a unified API, JWT authentication, org-scoped job store, Fernet encryption, and React dashboard. Pipelines operate **with or without an LLM API key** via deterministic agent fallbacks.

---

## Platform Deliverables

InsureFlow AI is a production-ready underwriting operating system with the following capabilities shipped and verified:

### Core Underwriting

| Capability | Insurance | Mortgage | Lending |
|------------|-----------|----------|---------|
| Document ingestion & OCR | ACORD, broker PDF/JSON, loss runs, SOV, inspections | 30+ doc types (W-2, 1040, credit, appraisal, rent roll) | Application data, credit pulls, bank statements |
| Cross-document reconciliation | Provenance hierarchy (ACORD vs inspection vs loss run) | W-2 vs 1040, appraisal vs purchase price, identity checks | Income vs application, debt verification |
| Specialist agents | Risk, Loss Run, Compliance, Fraud, UW Decision (+ Triage, Reinsurance, Portfolio) | Income, Credit, Asset, Collateral, Decision | Credit Risk, Compliance, Pricing |
| Decision output | ACCEPT / REFER / DECLINE + P&C premium quote | Approve / Refer / Suspend / Deny + rate lock | Approve / Counteroffer / Decline + pricing |
| Audit & compliance | Encrypted audit bundle + regulatory ZIP export | Encrypted memo, trail, and pipeline summary | Adverse action notices, Reg B/ECOA/HMDA compliance |

### Production Insurance Workflow

End-to-end bind-ready workflow for carrier-grade operations:

- **Licensed UW sign-off** — `LICENSED_UW` role with license number, notes, and override reason
- **Policy bind** — quote-to-bind via policy-admin adapter stub (Guidewire/Duck Creek-style interface)
- **Loss feedback loop** — record actual loss experience; portfolio calibration by loss ratio
- **Regulatory audit package** — SHA-256 manifest ZIP with encrypted artifacts for examiner review

### Web Dashboard (React)

Modern SPA served at `/dashboard` (React 18, Vite, Tailwind CSS):

| Page | Purpose |
|------|---------|
| **Overview** | Job metrics, quick demos, recent activity |
| **System Health** | Live diagnostics (10 component checks) |
| **Insurance** | Source connector hub, one-click demos, job history |
| **Mortgage** | Loan package submission, job history, rate/DTI display |
| **UW Sign-off** | Licensed review queue with View (job drawer), approve, refer, decline |
| **Renewal Dashboard** | Premium audit tracking, reconciliation status, material adjustments |
| **Authority Matrix** | UW tier overview, binding limits per authority level |
| **Market Admin** | Market phase controls (hard/soft), rate impact cards |
| **Broker Status** | Token-based broker share links, public status pages |
| **Settings** | Session info, RBAC reference (role hierarchy + descriptions), credential reset |

Features: JWT login with first-time setup, self-registration (viewer/underwriter), password visibility toggle, real-time job polling, responsive sidebar navigation.

### Insurance Source Connectors

24 simulated enterprise integrations (all production-ready status in UI):

- Cloud storage (S3, Azure Blob, GCS)
- Document management (SharePoint, Box, Dropbox, Google Drive)
- Broker platforms (Applied Epic, Vertafore, Guidewire BrokerPortal)
- Email ingestion (Exchange, Gmail)
- Legacy systems (Mainframe FTP, AS/400, SFTP)
- Local folder and packaged examples (Pacific Coast, Northwind, Sample)

Category-filtered connector hub with brand logos and pull-to-submit workflow.

### Infrastructure & Operations

- **JWT auth + RBAC** — viewer → underwriter → licensed_uw → admin → cuo; org-scoped data isolation, self-registration for viewer/underwriter
- **Persistent auth store** — file-backed user registry survives server reloads
- **Redis job store** — org-scoped async job tracking for insurance, mortgage, and lending pipelines
- **Celery workers** — async mortgage processing with job-store completion sync
- **System diagnostics** — `cli.py doctor` and `GET /system/diagnostics` (LLM, Redis, Postgres/pgvector, OCR, encryption, examples)
- **Insurance & mortgage webhooks** — HMAC-signed event subscriptions for both verticals
- **Broker status shares** — Token-based public share links for broker-facing status pages
- **Model registry** — Version-controlled model & guideline registry with compliance approval workflow
- **PII redaction** — Automated PII detection (SSN, EIN, DOB, etc.) and document redaction
- **Document analytics** — Analytics engine for document counts, type distribution, field coverage
- **Entity resolution** — Named entity extraction and cross-document entity matching
- **Docker Compose** — Redis, PostgreSQL/pgvector, API, Celery worker

### Quality Assurance

| Suite | Scope | Count |
|-------|-------|-------|
| **Unit tests** (`pytest`) | Parsers, agents, rating, workflow, underwriting, mortgage, lending, oracles, provenance, reconciliation, entities, MCP, document analytics | ~200 (20 test files) |
| **E2E tests** (`scripts/e2e_test.py`) | Full API integration, connectors, production workflow, Celery, Playwright browser | 42 |

E2E coverage includes: auth, diagnostics, all 24 connector pulls, insurance/mortgage demo pipelines, licensed UW sign-off, policy bind, loss experience, regulatory audit package, Celery mortgage path, and browser click-through (login, navigation, password toggle).

```bash
python scripts/e2e_test.py --timeout 360          # Full live-server E2E
python scripts/e2e_test.py --fast --timeout 360   # Skip connector pulls (~6 min)
python cli.py e2e --fast                          # Same via CLI
```

---

## Vertical Overview

| Vertical | Input | Output |
|----------|-------|--------|
| **Insurance** | ACORD, broker JSON/PDF, loss runs, SOV, inspections | ACCEPT / REFER / DECLINE memo + P&C premium quote |
| **Mortgage** | W-2, 1040, credit, bank statements, appraisals | Approve / Refer / Suspend / Deny + rate lock quote |
| **Lending** | Application data, credit pulls, bank statements | Approve / Counteroffer / Decline + risk-based pricing |

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

### Lending

```
Application → Credit Pull → Risk Score → Compliance (Reg B/ECOA/HMDA)
    → Pricing → Decision → Adverse Action Notice → Audit
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

### 1. Install

```bash
pip install -e .

# Optional: OCR for scanned PDFs (requires system Tesseract)
pip install -e ".[ocr]"

# Optional: Playwright for browser E2E tests
pip install playwright && playwright install chromium

# Copy and configure environment
cp .env.example .env
```

### 2. Start infrastructure

```bash
docker compose up -d redis db    # Redis + PostgreSQL/pgvector
```

### 3. Start services

```bash
# API + dashboard (port 8002 — 8000/8001 often in use)
python cli.py serve --port 8002 --no-reload

# Celery worker (required for async mortgage jobs)
python -m celery -A insureflow.tasks.celery_app worker -Q agents,pipeline,mortgage
```

Open **http://localhost:8002/dashboard** — use **First-time Setup** or sign in after `python cli.py auth-reset`.

### 4. CLI examples

```bash
# ── Insurance CLI ──
python cli.py agents \
  examples/pacific_coast_acord.xml \
  examples/pacific_coast_broker_api.json \
  examples/pacific_coast_loss_run.md \
  examples/pacific_coast_inspection_report.md \
  examples/pacific_coast_sov.md

# ── Mortgage CLI ──
python cli.py mortgage --dir simulated_documents/home_mortgage/johnson_marcus_imani --no-llm
python cli.py mortgage-borrowers --dir simulated_documents/home_mortgage --no-llm

# ── Lending CLI ──
python cli.py lending --application examples/lending/application_001.json

# ── System health ──
python cli.py doctor
python cli.py doctor --json

# ── End-to-end test suite ──
python scripts/e2e_test.py --timeout 360
python cli.py e2e --fast

# ── Unit tests ──
python -m pytest tests/ -q
```

### 5. Frontend development (optional)

```bash
cd frontend && npm install && npm run dev    # Vite dev server with API proxy
cd frontend && npm run build                 # Build into src/insureflow/static/ui/
```

### Docker (full stack)

```bash
docker compose up --build
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         FastAPI Gateway                             │
│  JWT Auth · RBAC (viewer→cuo) · Org-scoped Jobs · Dashboard (10pg) │
└──────┬───────────────┬──────────────────┬───────────────┬───────────┘
       │               │                  │               │
 ┌─────▼──────┐  ┌─────▼──────┐   ┌──────▼─────┐  ┌─────▼─────────┐
 │ INSURANCE  │  │ MORTGAGE   │   │  LENDING   │  │   REGISTRY    │
 │ Insurance  │  │ Mortgage   │   │ Lending    │  │ Model Version │
 │ Pipeline   │  │ Pipeline   │   │ Pipeline   │  │ Compliance RW │
 └─────┬──────┘  └─────┬──────┘   └──────┬─────┘  └───────┬───────┘
       │               │                  │                │
       └───────────────┴──────────────────┴────────────────┘
                       │
         ┌─────────────▼─────────────────────────────┐
         │           INGESTION + OCR + REDACTION       │
         │  ACORD · JSON · PDF · W-2 · Credit · App   │
         │  PII Redaction · Entity Resolution          │
         └─────────────┬─────────────────────────────┘
                       │
         ┌─────────────▼─────────────────────────────┐
         │  Provenance Hierarchy → Reconciliation     │
         │  (source-of-truth · cross-doc matching)    │
         └─────────────┬─────────────────────────────┘
                       │
         ┌─────────────▼─────────────────────────────┐
         │  Specialist Agents (ReAct + fallback)      │
         │  Insurance: Risk · Loss Run · Compliance   │
         │            Fraud · Triage · Reinsurance    │
         │            Portfolio Risk · Oracle · RAG   │
         │  Mortgage: Income · Credit · Asset         │
         │            Collateral · Decision           │
         │  Lending:  Credit Risk · Compliance        │
         │            · Pricing                       │
         └─────────────┬─────────────────────────────┘
                       │
         ┌─────────────▼─────────────────────────────┐
         │  Decision + Rating                         │
         │  Insurance: UW Memo → P&C Rating → Bind   │
         │  Mortgage:  Memo → Loan Pricing → Rate Lock│
         │  Lending:   Decision → Pricing → Adverse   │
         │             Action Notice                  │
         └─────────────┬─────────────────────────────┘
                       │
         ┌─────────────▼─────────────────────────────┐
         │     Production Layer                       │
         │  Licensed UW Sign-off · Bind/Loss Feedback │
         │  Premium Audits · Material Adjustments     │
         │  Fernet Encryption · Regulatory Audit ZIP  │
         │  Broker Status Shares · Webhooks (both)    │
         │  Celery Async Workers · Document Analytics │
         └───────────────────────────────────────────┘
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
| **TriageAgent** | Submission scoring & prioritization (hot/warm/cold/no-fit) |
| **ExtractionAgent** | Structured data extraction from documents |
| **VerificationAgent** | Cross-document field verification |
| **SynthesisAgent** | UW memo generation & summary synthesis |
| **RAGAgent** | Guideline-backed Q&A retrieval |
| **ReinsuranceAgent** | Treaty fit analysis (quota share, excess, facultative) |
| **PortfolioRiskAgent** | Portfolio concentration scoring (geo + industry) |
| **OracleAgent** | External data oracle query orchestration |

All agents have a **deterministic fallback** when no LLM key is configured. The agent swarm is coordinated by an **OrchestratorAgent** and **SupervisorAgent** that route tasks, aggregate results, and manage the ReAct loop.

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
| Submission triage & scoring | `agents/triage_agent.py` | Score/prioritize incoming submissions (hot/warm/cold/no-fit) |
| COPE risk analysis | `underwriting/cope.py` | Construction, Occupancy, Protection, Exposure — 4-pillar property framework |
| ISO-style rating | `rating/engine.py` | ISO loss costs × LCM × territory relativities × COPE mods × market cycle |
| Market cycle awareness | `underwriting/market.py` | Hard/soft market adjustments to pricing & appetite thresholds |
| Delegation of authority | `underwriting/authority.py` | Junior/Senior/CUO/MGA tiers with binding limits & co-sign rules |
| Renewal engine | `underwriting/renewal.py` | 60-120 day pre-renewal analysis, loss ratio trends, bundled retention |
| Override analytics | `outcomes/analytics.py` | Structured override capture, pattern detection, knowledge base feedback |
| Reinsurance treaty fit | `portfolio/treaty.py` | Quota share, excess treaties, aggregate utilization, facultative thresholds |
| Portfolio concentration | `portfolio/store.py` | Geographic + industry concentration scoring, double-concentration alerts |
| External data oracles | `oracles/` | CLUE claims history, NCCI workers comp, catastrophe model simulation |
| Appetite filter | `agents/appetite_filter.py` | 9 check methods (NAICS, geography, TIV, loss ratio, premium, years in business, prior cancellation) |
| OCR on broker PDFs | `ingestion/insurance/` | Tesseract + pdfminer for scans |
| Policy admin adapter | `rating/adapters/stub.py` | Guidewire/Duck Creek-style quote + bind interface |
| Licensed UW sign-off | `workflow/` | `LICENSED_UW` role, license number, override reason, override category, UW confidence |
| Bind/loss feedback | `outcomes/` | Prediction vs actual premium/loss calibration |
| Regulatory audit pack | `audit/package.py` | Encrypted artifacts + ZIP with SHA-256 manifest |
| Real-time broker status | `webhooks/` | Token-based public share links, HMAC-signed webhooks |
| PII redaction | `redaction/` | PII detection (SSN, EIN, DOB, etc.) and document redaction |
| Entity resolution | `entities/resolver.py` | Named entity extraction & cross-doc entity matching |
| Model registry | `registry/` | Version-controlled model & guideline registry with approval workflow |
| Document analytics | `analytics/documents.py` | Document count, type distribution, field coverage analysis |
| Premium audits | `outcomes/store.py` | Post-binding premium audit with material adjustment tracking |
| Insurance webhooks | `webhooks/dispatcher.py` | HMAC-signed event subscriptions for insurance events |
| Pipeline v2 | `api.py` | Enhanced pipeline with skip flags (appetite, oracles, portfolio, integration) |
| Lending underwriting | `lending/` | Consumer & commercial credit underwriting (Reg B, ECOA, HMDA) |

### Insurance API endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/pipeline/run` | POST | underwriter | Submit insurance package (text or base64 PDF) |
| `/pipeline/v2/run` | POST | underwriter | Enhanced pipeline with skip flags (appetite, oracles, portfolio, integration) + auto broker share |
| `/pipeline/jobs` | GET | viewer | List org-scoped jobs |
| `/pipeline/jobs/{job_id}` | GET | viewer | Job status + results |
| `/pipeline/jobs/{job_id}/quote` | GET | viewer | Job quote HTML document |
| `/pipeline/jobs/{job_id}` | DELETE | admin | Delete a job |
| `/pipeline/audit/{bundle_id}` | GET | viewer | Full audit trail |
| `/pipeline/audit/{bundle_id}/package` | GET | admin | Regulatory ZIP export |
| `/pipeline/workflow/pending` | GET | viewer | Bundles awaiting UW review |
| `/pipeline/workflow/{bundle_id}` | GET | viewer | Workflow status for a bundle |
| `/pipeline/workflow/{bundle_id}/sign-off` | POST | licensed_uw | Approve / decline / refer (with override category, UW confidence) |
| `/pipeline/workflow/{bundle_id}/bind` | POST | licensed_uw | Bind approved policy |
| `/pipeline/outcomes/loss-experience` | POST | underwriter | Record actual loss data |
| `/pipeline/outcomes/calibration` | GET | viewer | Portfolio loss ratio stats |
| `/pipeline/rating/products` | GET | viewer | Available P&C lines + base rates |
| `/pipeline/queue` | GET | viewer | Prioritized submission queue with triage scores |
| `/pipeline/cope/{bundle_id}` | GET | viewer | COPE risk analysis (C-O-P-E breakdown + schedule mod) |
| `/pipeline/documents/{bundle_id}/missing` | GET | viewer | Missing document checklist |
| `/pipeline/renewal/{bundle_id}` | POST | underwriter | Run renewal analysis |
| `/pipeline/jobs/{bundle_id}/broker-share` | POST | underwriter | Create broker-facing status share link |
| `/underwriting/market` | GET | viewer | Current market phase + rate impacts |
| `/underwriting/market/set` | POST | cuo | Set market phase (hard/soft) |
| `/underwriting/authority` | GET | viewer | All UW authority tiers & binding limits |
| `/analytics/overrides` | GET | viewer | Override analytics with patterns |
| `/analytics/overrides/patterns` | GET | viewer | Detected override patterns |
| `/analytics/documents` | GET | viewer | Document analytics summary |

### Premium Audit endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/pipeline/audits/{bundle_id}/create` | POST | underwriter | Create premium audit for a bound policy |
| `/pipeline/audits/{audit_id}/adjustment` | POST | underwriter | Record material premium adjustment |
| `/pipeline/audits/{audit_id}/complete` | POST | underwriter | Finalize premium audit |
| `/pipeline/audits` | GET | viewer | List all premium audits |
| `/pipeline/audits/material-adjustments` | GET | underwriter | List material adjustments pending review |

### Broker Status & Webhooks

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/broker/status/{token}` | GET | None (public) | Broker-facing status page (token-based) |
| `/webhooks/insurance` | POST | admin | Subscribe to insurance webhook events |
| `/webhooks/insurance` | GET | admin | List insurance webhook subscriptions |
| `/webhooks/{subscription_id}` | DELETE | admin | Delete a webhook subscription |

### Portfolio & Integration

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/portfolio/summary` | GET | viewer | Portfolio concentration summary (geo + industry) |
| `/integration/status` | GET | viewer | System integration health status |

### Demo & Sources

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/api/demo/presets` | GET | None | Available demo presets (Pacific Coast, Johnson, Midwest) |
| `/api/demo/insurance/{preset_id}` | POST | underwriter | Run insurance demo from preset |
| `/api/demo/mortgage/{preset_id}` | POST | underwriter | Run mortgage demo from preset |
| `/api/insurance/sources` | GET | None | List 24 insurance source connectors |
| `/api/insurance/sources/{source_id}/pull` | POST | underwriter | Pull documents from a connector |

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
| `MortgageGraph` | LangGraph mortgage state machine (17 nodes) |
| `MortgageReconciliation` | Cross-document field reconciliation |
| `LLMExtractor` | LLM-based field extraction from documents |
| `DocumentBundler` | Document bundling & loan package assembly |
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

## Lending Module

### What it does

Consumer and commercial lending underwriting for bank and fintech workflows:
- Application intake with consumer credit pulls (simulated)
- Credit risk scoring (FICO tiers, DTI, LTV, payment history)
- Lending compliance rules (Reg B, ECOA, HMDA, UDAAP, Fair Lending)
- Risk-based loan pricing with rate adjustments
- Adverse action notice generation

### Key components

| Component | Description |
|-----------|-------------|
| `LendingPipeline` | End-to-end application-to-decision flow |
| `CreditRiskScorer` | FICO-based credit risk assessment |
| `LendingComplianceEngine` | Reg B, ECOA, HMDA, UDAAP rule engine |
| `LoanPricingEngine` | Risk-based pricing with rate cards |

### Lending API endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/lending/pipeline/run` | POST | underwriter | Submit lending application |
| `/lending/pipeline/result/{application_id}` | GET | viewer | Application status + decision |
| `/lending/products` | GET | viewer | Available loan products & rates |

---

## Model Registry

### What it does

Version-controlled model and guideline registry with compliance review workflow:
- Register model versions with metadata, documentation, and validation status
- Submit entries for compliance review with approval/rejection workflow
- Diff viewer for comparing model versions
- Context management for deployment tracking
- Point-in-time snapshots for audit and reproducibility
- Bootstrap seeding for initial registry setup

### Registry API endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/registry/versions` | GET | viewer | List all registry entries |
| `/registry/versions/{entry_id}` | GET | viewer | Get entry details |
| `/registry/versions` | POST | admin | Create a new registry entry |
| `/registry/versions/{entry_id}/submit` | POST | underwriter | Submit entry for compliance review |
| `/registry/versions/{entry_id}/approve` | POST | admin | Approve a submitted entry |
| `/registry/versions/{entry_id}/reject` | POST | admin | Reject a submitted entry |
| `/registry/diff` | GET | viewer | Compare two registry entries |
| `/registry/context` | GET | viewer | List active deployment contexts |
| `/registry/snapshot` | POST | viewer | Create point-in-time snapshot |
| `/registry/snapshots` | GET | viewer | List available snapshots |
| `/registry/bootstrap` | POST | admin | Seed registry with initial entries |

---

## System Health & Web Dashboard

### CLI doctor

```bash
python cli.py doctor          # Table of component status (ok / degraded / missing)
python cli.py doctor --json   # Machine-readable output
```

Checks ten components: LLM API key, Redis, job store, encryption, OCR, audit path, insurance examples, Postgres/pgvector, and more. Public API: `GET /system/diagnostics`.

### Web dashboard

Open **http://localhost:8002/dashboard** after starting the API.

> Use `insureflow.api:app` via `python cli.py serve`, not `insureflow.llm.main:app`.

| Page | Auth | Purpose |
|------|------|---------|
| **Overview** | Optional | Dashboard metrics, quick demos, job chart |
| **System Health** | No | Live component status with LLM mode indicator |
| **Insurance** | Yes | Connector hub (24 sources), Pacific Coast demo, job table |
| **Mortgage** | Yes | Johnson / Midwest demos, job submission, rate & DTI |
| **UW Sign-off** | Yes | Licensed review queue — View (opens job drawer with full memo), approve, refer, decline |
| **Renewal Dashboard** | Yes | Premium audit history, material adjustment queue |
| **Authority Matrix** | Yes | UW tier cards, binding limits per authority level |
| **Market Admin** | Yes | Market phase selector, rate impact metrics |
| **Broker Status** | Yes | Token-based broker share links, public status pages |
| **Settings** | Optional | Account info, RBAC role reference, sign out, credential reset |

### Auth reset

```bash
python cli.py auth-reset       # Clear all accounts on running server
curl -X POST http://localhost:8002/auth/reset
```

Then use **First-time Setup** in the dashboard login modal (or **Settings → Reset credentials** if signed in).

---

## API Authentication

JWT bearer tokens with role-based access control and org-scoped data isolation.

### Roles

| Role | Level | Permissions |
|------|-------|-------------|
| `viewer` | 1 | Read jobs, audit trails, workflow status |
| `underwriter` | 2 | Run pipelines, record loss experience, create audits |
| `licensed_uw` | 3 | Sign off on memos, bind policies |
| `admin` | 4 | Create users, delete jobs, configure webhooks |
| `cuo` | 5 | Set market cycles, system-wide parameters |

Self-registration (`POST /auth/register`) creates `viewer` or `underwriter` accounts only. Admins use `POST /auth/users` to assign higher roles.

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/status` | GET | No | Check if first-time admin setup is required |
| `/auth/setup` | POST | No (one-time) | Create first admin account |
| `/auth/register` | POST | No | Self-register as viewer or underwriter |
| `/auth/login` | POST | No | Get JWT bearer token |
| `/auth/me` | GET | Bearer | Current user (username, role, org_id) |
| `/auth/roles` | GET | No | List all roles with hierarchy levels and descriptions |
| `/auth/users` | POST | Bearer (admin) | Admin creates user with any role |
| `/auth/reset` | GET/POST | No | Clear all accounts (redirect/JSON) |

### Setup

```bash
# 1. Create first admin (one-time)
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme", "org_id": "my-bank"}'

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
│   ├── appetite_filter.py   # Fast-fail appetite screening (9 checks)
│   ├── base.py              # Base agent class
│   ├── compliance_agent.py  # Regulatory compliance checks
│   ├── extraction_agent.py  # Data extraction agent
│   ├── fraud_detection_agent.py  # Fraud red-flag detection
│   ├── loss_run_analyst.py  # Loss run analysis (frequency/severity)
│   ├── orchestrator.py      # Agent orchestration & routing
│   ├── portfolio_risk_agent.py   # Portfolio concentration analysis
│   ├── prompts.py           # Shared LLM prompt templates
│   ├── rag_agent.py         # RAG-backed Q&A agent
│   ├── react_agent.py       # ReAct agent implementation
│   ├── react_tools.py       # ReAct tool definitions
│   ├── reinsurance_agent.py # Reinsurance treaty fit analysis
│   ├── risk_analyst.py      # Risk analysis (occupancy, construction, TIV)
│   ├── supervisor.py        # Insurance supervisor agent
│   ├── synthesis_agent.py   # Synthesis/memo generation
│   ├── tools.py             # Shared agent tools
│   ├── triage_agent.py      # Submission scoring & prioritization
│   ├── uw_decision_agent.py # UW decision recommendation
│   ├── verification_agent.py # Cross-doc verification
│   └── mortgage/
│       ├── supervisor.py    # Mortgage specialist supervisor
│       └── __init__.py
├── analytics/               # Analytics engine
│   └── documents.py         # Document analytics (exposed at /analytics/documents)
├── api.py                   # FastAPI server (insurance + mortgage + lending + registry)
├── audit/                   # Audit store, insurance audit logger, regulatory ZIP
│   ├── logger.py            # Audit event logging
│   ├── package.py           # Regulatory audit ZIP packaging
│   ├── store.py             # Audit artifact store
│   └── trail.py             # Audit trail models
├── auth/                    # JWT, roles (viewer → licensed_uw → admin)
│   ├── dependencies.py      # FastAPI dependency injection
│   ├── jwt.py               # JWT token creation/validation
│   ├── models.py            # Auth data models
│   └── store.py             # Persistent user store
├── config.py                # Settings singleton (dual-model LLM config)
├── e2e/                     # End-to-end test runner + Playwright browser tests
│   ├── browser.py           # Playwright browser automation
│   └── runner.py            # E2E test orchestration
├── entities/                # Entity resolution
│   └── resolver.py          # Named entity resolution engine
├── exceptions.py            # Custom exception hierarchy
├── graph/                   # LangGraph state machine (legacy insurance path)
│   ├── builder.py           # Graph state machine builder
│   ├── nodes.py             # LangGraph node definitions
│   └── state.py             # Graph state models
├── health/                  # System diagnostics (doctor)
│   └── diagnostics.py       # Component health checks
├── ingestion/
│   ├── acord_parser.py      # ACORD XML parser
│   ├── base.py              # Base parser interface
│   ├── chunker.py           # Document chunking
│   ├── classifier.py        # Document type classifier
│   ├── excel_parser.py      # Excel spreadsheet parser
│   ├── json_parser.py       # JSON/API payload parser
│   ├── loader.py            # Document loader
│   ├── loss_run_parser.py   # Loss run markdown parser
│   ├── ocr.py               # Tesseract + pdfminer OCR
│   ├── report_extractor.py  # Inspection report extraction
│   ├── sov_parser.py        # Schedule of values parser
│   ├── insurance/           # Broker PDF OCR, classifier, extractors
│   └── mortgage/            # Mortgage document loader, classifier, extractors
├── insurance/               # InsurancePipeline (production default)
│   └── pipeline.py
├── integration/             # Core system adapters
│   ├── base_adapter.py      # Abstract adapter interface
│   ├── britecore_adapter.py # BriteCore integration
│   ├── guidewire_adapter.py # Guidewire PolicyCenter integration
│   ├── hubspot_adapter.py   # HubSpot CRM integration
│   ├── isimodotech_adapter.py  # Isimodotech integration
│   ├── policy_admin_service.py # Policy admin service layer
│   └── quicksilver_adapter.py  # Quicksilver MGA integration
├── lending/                 # Consumer & commercial lending underwriting
│   ├── compliance.py        # Lending compliance rules (Reg B, ECOA, HMDA, UDAAP)
│   ├── models.py            # Lending data models
│   ├── pipeline.py          # LendingPipeline (application-to-decision)
│   ├── pricing.py           # Loan pricing engine (risk-based)
│   └── risk.py              # Credit risk scoring & analysis
├── llm/                     # LLM client & configuration
│   ├── client.py            # Multi-provider LLM client (OpenAI, Anthropic)
│   ├── main.py              # Legacy entry point
│   └── prompts.py           # LLM prompt configuration
├── mcp/                     # MCP server for Claude Desktop / Cursor
│   ├── server.py            # MCP protocol server (SSE on :8010)
│   └── __main__.py          # Entry point
├── models/                  # Centralized Pydantic data models
│   ├── agents.py            # Agent output/input models
│   ├── audit.py             # Audit data models
│   ├── mortgage.py          # Mortgage domain models
│   ├── provenance.py        # Provenance data models
│   └── submissions.py       # Submission bundle models
├── mortgage/                # MortgagePipeline, pricing, compliance, webhooks
│   ├── audit.py             # MortgageAuditLogger
│   ├── bundler.py           # Document bundling & packaging
│   ├── compliance.py        # MortgageComplianceEngine
│   ├── graph.py             # LangGraph mortgage state machine
│   ├── llm_extractor.py     # LLM-based field extraction
│   ├── pipeline.py          # MortgagePipeline
│   ├── pricing.py           # LoanPricingEngine
│   ├── reconciliation.py    # Cross-document reconciliation
│   └── webhooks.py          # WebhookDispatcher
├── oracles/                 # External data oracles
│   ├── aplus_client.py      # A-Plus loss history
│   ├── cat_model_client.py  # Catastrophe model simulation
│   ├── clue_client.py       # CLUE claims history
│   ├── ncci_client.py       # NCCI workers comp
│   ├── ncci_codes.py        # NCCI classification codes
│   └── oracle_agent.py      # Oracle query agent
├── outcomes/                # Bind outcomes, loss experience, feedback loop
│   ├── analytics.py         # Override pattern detection & knowledge base
│   ├── feedback.py          # Loss feedback & portfolio calibration
│   ├── models.py            # Outcome data models
│   ├── override.py          # Structured override detail model
│   └── store.py             # Outcome persistence
├── pipeline.py              # Legacy UnderwritingPipeline
├── portfolio/               # Portfolio concentration & reinsurance treaty stores
│   ├── store.py             # Portfolio policy store + concentration analysis
│   └── treaty.py            # Reinsurance treaty model (6 treaty types)
├── provenance/              # Data provenance hierarchy
│   ├── hierarchy.py         # Source-of-truth hierarchy
│   ├── rules.py             # Provenance trust rules
│   └── trust_scorer.py      # Provenance trust scoring
├── rag/                     # Underwriting guidelines (in-memory + pgvector)
│   ├── guidelines.py        # 18 UW guidelines across 8 categories
│   ├── rag_agent.py         # RAG retrieval agent
│   └── vector_store.py      # pgvector/char-n-gram store
├── rating/                  # P&C rating engine
│   ├── engine.py            # ISO-style rating with COPE + market cycle adjustments
│   ├── models.py            # Quote models, rate components
│   ├── quote_document.py    # Quote document generation
│   └── adapters/            # Policy admin adapter (Guidewire/Duck Creek stub)
├── reconciliation/          # Cross-document discrepancy detection
│   ├── discrepancies.py     # Discrepancy type definitions
│   ├── engine.py            # Reconciliation engine
│   └── matcher.py           # Field matching & comparison
├── redaction/               # PII redaction pipeline
│   ├── detector.py          # PII pattern detection
│   ├── pipeline.py          # Redaction pipeline orchestration
│   └── redactor.py          # Document content redaction
├── registry/                # Model versioning & compliance registry
│   ├── models.py            # Registry data models
│   └── service.py           # Version management & approval workflow
├── storage/                 # Redis job store, Fernet encryption
│   ├── base.py              # Storage base interface
│   ├── encryption.py        # Fernet envelope encryption
│   ├── job_store.py         # Org-scoped Redis job store
│   └── memory.py            # In-memory job store fallback
├── tasks/                   # Celery workers (insurance + mortgage)
│   ├── agent_tasks.py       # Agent Celery tasks
│   ├── celery_app.py        # Celery application config
│   ├── mortgage_tasks.py    # Mortgage pipeline Celery tasks
│   └── pipeline_tasks.py    # Insurance pipeline Celery tasks
├── underwriting/            # Core underwriting domain
│   ├── authority.py         # Delegation of authority matrix (Junior/Senior/CUO/MGA)
│   ├── cope.py              # COPE risk analysis (Construction/Occupancy/Protection/Exposure)
│   ├── market.py            # Market cycle awareness (hard/soft market pricing)
│   └── renewal.py           # Pre-renewal engine (60-120 day window, bundling analysis)
├── webhooks/                # HMAC-signed event dispatch + broker status shares
│   └── dispatcher.py        # Webhook event dispatcher
├── workflow/                # Licensed UW sign-off state machine
│   ├── models.py            # Workflow state models
│   ├── service.py           # Workflow orchestration
│   └── store.py             # Workflow persistence
├── static/ui/               # Built React dashboard (Vite output)
└── cli.py                   # Typer CLI

frontend/                    # React dashboard source (Vite + Tailwind)
├── src/
│   ├── App.jsx
│   ├── pages/               # 10 dashboard pages
│   └── components/          # Shared UI components
scripts/
├── e2e_test.py              # E2E test CLI entry point
└── init_db.sql              # PostgreSQL schema initialization

examples/                    # 5 carrier insurance submissions (Pacific Coast, Northwind, Sample, Sunrise, Veririsk)
simulated_documents/           # 80+ mortgage files across 10 borrower scenarios
tests/                         # pytest suite (20 test files)
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
| **Sunrise Artisan** | 2 | Small artisan contractor |
| **Veririsk** | 3 | ISO loss run, inspection report, principal background |
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

### Unit tests (~200)

```bash
python -m pytest tests/ -q

# Focused suites
python -m pytest tests/test_agents.py tests/test_underwriting.py -v
python -m pytest tests/test_mortgage.py tests/test_mortgage_infra.py tests/test_reconciliation.py -v
python -m pytest tests/test_insurance_production.py tests/test_pipeline_graph.py -v
python -m pytest tests/test_lending.py tests/test_oracles.py -v
python -m pytest tests/test_health.py tests/test_mcp_server.py -v
python -m pytest tests/test_provenance.py tests/test_entities.py -v
python -m pytest tests/test_ingestion_parsers.py tests/test_acord_parser.py -v
```

| Test suite | Scope |
|------------|-------|
| `test_agents.py` | Agent orchestration, ReAct tools, extraction |
| `test_underwriting.py` | COPE, market cycle, authority, renewal |
| `test_mortgage.py` | Mortgage pipeline, pricing, compliance |
| `test_mortgage_infra.py` | Mortgage graph, reconciliation, webhooks |
| `test_reconciliation.py` | Cross-document discrepancy detection |
| `test_insurance_production.py` | Full insurance production workflow |
| `test_pipeline_graph.py` | LangGraph state machine |
| `test_lending.py` | Lending pipeline, compliance, risk |
| `test_oracles.py` | CLUE, NCCI, CAT model clients |
| `test_health.py` | System diagnostics |
| `test_mcp_server.py` | MCP protocol tools |
| `test_provenance.py` | Provenance hierarchy & trust scoring |
| `test_entities.py` | Entity resolution |
| `test_ingestion_parsers.py` | JSON, Excel, SOV, loss run parsers |
| `test_acord_parser.py` | ACORD XML parser |
| `test_document_analytics.py` | Document analytics engine |
| `test_pipeline.py` | Pipeline integration tests |
| `test_e2e.py` | End-to-end pipeline scenarios |

### End-to-end tests (42 scenarios)

Full integration suite against the live API — auth, diagnostics, connectors, pipelines, production workflow, Celery, and Playwright browser UI.

```bash
# Prerequisites: API on :8002, Docker Redis/Postgres, Celery worker
python scripts/e2e_test.py --timeout 360           # Full (includes 24 connector pulls)
python scripts/e2e_test.py --fast --timeout 360    # Skip connector pulls
python scripts/e2e_test.py --in-process --fast     # TestClient (no live server)
python scripts/e2e_test.py --no-browser            # Skip Playwright UI tests
python scripts/e2e_test.py --no-celery             # Skip Celery worker test
python cli.py e2e --fast --timeout 360
```

| E2E category | What is verified |
|--------------|------------------|
| Platform | Health, API root, dashboard SPA routes |
| Auth | Setup, login, `/auth/me` |
| Diagnostics | 10/10 system checks (API + in-process doctor) |
| Connectors | All 24 insurance source pulls |
| Insurance pipeline | Pacific Coast demo job, audit, workflow, rating |
| Production workflow | UW sign-off → bind → regulatory ZIP → loss experience → calibration |
| Mortgage | Products, Johnson demo, audit, webhooks |
| Celery | `use_celery=true` mortgage job completion |
| Browser UI | Login, password toggle, all nav pages, refresh |
| Sync pipelines | In-process insurance + mortgage pipeline runs |

---

## Key Design Decisions

- **Dual verticals, shared infra** — Insurance and mortgage share auth, job store, encryption, and API; separate pipelines and agents per domain
- **Deterministic fallback always present** — Agents work without any LLM API key; LLM enhances analysis when configured
- **Provenance hierarchy** — Structured broker data (ACORD) wins over AI-extracted PDF fields; eliminates hallucinations on critical limits
- **Licensed UW gate** — AI recommends; a licensed underwriter with license number signs off before bind
- **Encrypted audit at rest** — Fernet envelope encryption on all persisted bundles; regulatory ZIP with checksums for examiners
- **Org-scoped isolation** — Jobs, workflows, audit trails, and webhooks scoped per `org_id` in JWT
- **Connector abstraction** — Unified pull API for cloud, DMS, broker, and legacy sources with simulated enterprise integrations
- **Test-driven delivery** — ~200 unit tests plus 42-scenario E2E suite covering API, production workflow, Celery, and browser UI

---

## License

MIT
