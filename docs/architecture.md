# InsureFlow AI — System Architecture

## 1. Overview

InsureFlow AI is an enterprise multi-agent underwriting platform serving two verticals — **commercial insurance** and **bank mortgage** — on a shared infrastructure layer. It ingests multi-format submission packages, runs deterministic and LLM-enhanced analysis through specialist agents, produces underwriting decisions with premium/rate quotes, and supports the full bind-to-audit lifecycle with role-based access control.

### Design Tenets

- **Deterministic by default** — every agent has a rule-based fallback; LLM keys are optional
- **Provenance-first** — structured broker data (ACORD) always beats AI-extracted values
- **Licensed UW gate** — AI recommends; a licensed underwriter signs off before bind
- **Org-scoped isolation** — all data is scoped by `org_id` embedded in JWT
- **Encrypted at rest** — Fernet envelope encryption on all persisted audit bundles

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                     │
│   React SPA (Vite/Tailwind) · CLI (Typer) · curl · MCP (Claude/Cursor)  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                        API GATEWAY (FastAPI)                            │
│                                                                         │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐   │
│  │ JWT Auth │  │ RBAC     │  │ Org Scope│  │CORS/CSRF│  │ Rate     │   │
│  │ + Bearer │  │ 5 Roles  │  │ Filter   │  │        │  │ Limiting │   │
│  └─────────┘  └──────────┘  └──────────┘  └────────┘  └──────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    AUTH ENDPOINTS                                 │  │
│  │  /auth/setup · /auth/login · /auth/register · /auth/users        │  │
│  │  /auth/me · /auth/roles · /auth/status · /auth/reset             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌────────────────────┐          ┌────────────────────┐                │
│  │   INSURANCE API    │          │   MORTGAGE API     │                │
│  │                    │          │                    │                │
│  │ /pipeline/run      │          │ /mortgage/pipeline │                │
│  │ /pipeline/jobs     │          │  /run              │                │
│  │ /pipeline/queue    │          │ /mortgage/jobs     │                │
│  │ /pipeline/cope     │          │ /mortgage/audit    │                │
│  │ /pipeline/renewal  │          │ /mortgage/products │                │
│  │ /pipeline/audits   │          │ /mortgage/webhooks │                │
│  │ /underwriting/*    │          │                    │                │
│  │ /analytics/*       │          │                    │                │
│  │ /webhooks/*        │          │                    │                │
│  │ /portfolio/*       │          │                    │                │
│  │ /integration/*     │          │                    │                │
│  └────────────────────┘          └────────────────────┘                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
    ┌──────────▼──────────┐       ┌────────────▼────────────┐
    │  INSURANCE PIPELINE │       │   MORTGAGE PIPELINE     │
    │  (InsurancePipeline)│       │  (MortgagePipeline)     │
    └──────────┬──────────┘       └────────────┬────────────┘
               │                               │
    ┌──────────▼───────────────────────────────▼────────────┐
    │              SHARED INFRASTRUCTURE                     │
    │                                                        │
    │  ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
    │  │ UserStore│  │JobStore │  │Fernet   │  │ Audit   │ │
    │  │ (JSON)   │  │(Redis/  │  │Encrypt  │  │Logger   │ │
    │  │          │  │ Memory) │  │         │  │         │ │
    │  └──────────┘  └─────────┘  └─────────┘  └─────────┘ │
    │                                                        │
    │  ┌──────────┐  ┌─────────┐  ┌─────────┐              │
    │  │ Webhook  │  │ Celery  │  │System   │              │
    │  │Dispatcher│  │ Workers │  │Diag.    │              │
    │  └──────────┘  └─────────┘  └─────────┘              │
    └────────────────────────────────────────────────────────┘
```

---

## 3. Insurance Pipeline

The insurance underwriting pipeline is a multi-stage workflow. Each stage is independently testable and can run with or without an LLM API key.

### 3.1 Pipeline Stages

```
Broker Submission
       │
       ▼
┌──────────────────┐
│ 1. TRIAGE        │  Score 0–100 (NAICS fit, geography, size, coverage,
│  TriageAgent     │  document completeness). Priority: HOT ≥80 / WARM ≥50
└────────┬─────────┘  / COLD ≥25 / NO_FIT
         │
         ▼
┌──────────────────┐
│ 2. APPETITE      │  9 deterministic checks: NAICS, geography, TIV, loss
│  AppetiteFilter  │  ratio, minimum premium, years in business, prior
└────────┬─────────┘  carrier cancellation, occupancy, protection class
         │
         ▼
┌──────────────────┐
│ 3. INGESTION     │  Multi-format document ingestion:
│                  │  • ACORD XML parser          (structured)
│                  │  • Broker JSON parser          (structured)
│                  │  • Loss Run parser (tabular)   (semi-structured)
│                  │  • SOV parser                  (semi-structured)
│                  │  • Inspection Report parser    (unstructured)
│                  │  • Broker PDF → OCR → Classify  (unstructured)
│                  │  • Document classifier (auto-routes by type)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. PROVENANCE    │  Source-of-truth hierarchy:
│  ProvenanceEngine│  1. Signed legal submission
│                  │  2. Broker ACORD XML
│                  │  3. Inspection report
│                  │  4. AI-extracted PDF fields
│                  │  High-trust value wins; discrepancy logged
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. RECONCILE     │  Cross-document discrepancy detection.
│  ReconcileEngine │  Critical mismatches → escalate to human review.
│                  │  Non-critical → pick highest trust source.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. COPE ANALYSIS │  4-pillar property risk framework:
│  COPERatingEngine │  • Construction (5 classes: frame, joisted, non-
│                  │    combustible, masonry, fire resistive)
│                  │  • Occupancy (9 types: office, retail, warehouse,
│                  │    manufacturing, food, lodging, garage, mixed, vacant)
│                  │  • Protection (ISO class 1–10)
│                  │  • Exposure (9 CAT types: weather, quake, flood,
│                  │    wildfire, sprinkler leak, theft, liability,
│                  │    business interruption, cyber)
│                  │  Produces risk grade (preferred/standard/non-standard/
│                  │  declined) + schedule rating modifier (−25% to +50%)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 7. AGENT SWARM   │  Parallel specialist agents (ReAct + fallback):
│                  │  • Risk Analyst      — physical property assessment
│                  │  • Loss Run Analyst  — claim frequency/severity/trends
│                  │  • Compliance Agent  — regulatory & guideline checks
│                  │  • Fraud Detection   — submission inconsistencies
│                  │  Each agent returns independent findings + confidence
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 8. RAG LOOKUP    │  Vector similarity search against underwriting
│  pgvector/InMem  │  guidelines. 18 guidelines across 8 categories.
│                  │  In-memory (char-n-gram TF-IDF) by default;
│                  │  pgvector (PostgreSQL + OpenAI embeddings) in prod.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 9. UW DECISION   │  Aggregates agent findings, RAG guidelines, COPE
│  UWDecisionAgent │  grade, and triage score → final recommendation:
│                  │  ACCEPT / REFER / DECLINE + rationale + confidence
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│10. RATING        │  ISO-style premium calculation:
│  InsuranceRating  │  TIV / 100 × ISO_loss_cost × LCM
│  Engine          │    × territory_relativity
│                  │    × (1 + COPE_mod)
│                  │    × (1 + market_mod)
│                  │    × (1 + deductible_credit)
│                  │    + expense_constant
│                  │  + Market cycle line-specific adjustments
│                  │  + Minimum premium threshold enforcement
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│11. REINSURANCE   │  Evaluate treaty fit:
│  ReinsuranceAgent│  • Quota Share — cede % of risk
│                  │  • Excess of Loss — layer-based attachment
│                  │  • Facultative — per-risk placement thresholds
│                  │  Checks aggregate utilization, flags if treaty
│                  │  capacity exhausted
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│12. PORTFOLIO     │  Concentration scoring:
│  PortfolioRisk   │  • Geographic concentration (state/region)
│  Agent           │  • Industry/NAICS concentration
│                  │  • Double-concentration alerts
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│13. WORKFLOW      │  State machine: pending_review → sign-off → bind
│  WorkflowEngine  │  Authority matrix enforcement:
│                  │  • Junior UW     — $25K max premium
│                  │  • Senior UW     — $250K max premium
│                  │  • CUO           — unlimited
│                  │  • MGA           — delegated authority
│                  │  Co-sign threshold: >$100K requires senior+
│                  │  Licensed UW signs off with license number,
│                  │  override category, UW confidence score
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│14. AUDIT         │  Encrypted audit bundle:
│  AuditLogger     │  • All agent findings (signed)
│                  │  • Provenance discrepancies
│                  │  • Decision rationale
│                  │  • Premium/quote components
│                  │  • UW sign-off record
│                  │  • Fernet envelope encryption at rest
│                  │  • Regulatory ZIP export with SHA-256 manifest
└──────────────────┘
```

### 3.2 Post-Bind & Lifecycle

```
  Bound Policy
       │
       ▼
┌──────────────────┐
│ LOSS FEEDBACK    │  Record actual loss experience:
│ /outcomes/loss-  │  • Actual premium vs predicted
│ experience       │  • Loss ratio tracking
│                  │  • Portfolio calibration (LR-based adjustments)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ RENEWAL ENGINE   │  60–120 day pre-renewal window:
│ RenewalEngine    │  • Loss ratio trend analysis (improving/stable/
│                  │    deteriorating)
│                  │  • Bundled policy retention modeling (91% for multi-line)
│                  │  • Premium change recommendation
│                  │  • Retention risk scoring
│                  │  • Action: non-renew (LR>0.75 + ≥3 claims),
│                  │    modify (LR>0.60 or net change <−5%),
│                  │    refer (expiring within 60 days)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PREMIUM AUDIT    │  Track estimated vs actual premium:
│ PremiumAudit     │  • Create audit → start → adjust → complete / dispute
│ Engine           │  • Material adjustment detection (>15% delta or disputed)
│                  │  • Adjustment line items with types + descriptions
└──────────────────┘
```

### 3.3 Override Analytics

```
┌────────────────────────────────────────────────────┐
│ OVERRIDE ANALYTICS ENGINE                          │
│                                                    │
│  Captures structured override data:                │
│  • UW confidence score (1–10)                      │
│  • Override reason category (11 categories:        │
│    competitor_match, loyalty_retention,            │
│    strategic_account, market_conditions,           │
│    broker_relationship, data_quality_issue,        │
│    exception_policy, reinsurance_credit,           │
│    bundled_discount, regulatory_mandate, other)    │
│  • Premium delta (original vs adjusted)            │
│  • Supporting notes                                │
│                                                    │
│  Pattern detection:                                │
│  • Identifies recurring override patterns          │
│  • Suggests knowledge base rules                   │
│  • Generates analytics summaries                   │
└────────────────────────────────────────────────────┘
```

---

## 4. Mortgage Pipeline

The mortgage pipeline processes residential and commercial loan packages through parallel specialist agents and a compliance rules engine.

### 4.1 Pipeline Stages

```
Loan Package
       │
       ▼
┌──────────────────┐
│ 1. INGESTION     │  Classify 30+ document types:
│  DocClassifier   │  W-2, 1040, paystub, credit report, appraisal,
│                  │  bank statement, rent roll, P&L, lease, etc.
│                  │  OCR for scanned PDFs, text extraction for natives
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. EXTRACT       │  Per-document field extraction:
│  FieldExtractor  │  • W-2 → wages, tax withheld, employer
│                  │  • 1040 → AGI, filing status
│                  │  • Credit → score, liabilities, inquiries
│                  │  • Appraisal → value, condition, comps
│                  │  • Bank statements → balances, deposits
│                  │  • Paystubs → YTD earnings, deductions
│                  │  Works with regex (no-LLM) or LLM extraction
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. RECONCILE     │  Cross-document validation:
│  ReconcileEngine │  • W-2 wages vs 1040 income
│                  │  • Appraisal value vs purchase price
│                  │  • Identity checks (name/SSN across docs)
│                  │  • Employment consistency check
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. COMPLIANCE    │  Automated compliance rule engine:
│  Mortgage        │  • CREDIT-001: minimum credit score
│  ComplianceEngine│  • DTI-001: debt-to-income ratio limits
│                  │  • LTV-001: loan-to-value thresholds
│                  │  • INCOME-001: income stability
│                  │  • RESERVES-001: reserve requirements
│                  │  • 20+ rules across credit, income, collateral, docs
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. AGENT SWARM   │  5 parallel specialist agents:
│  MortgageSuper-  │  • Income Agent   — verify income sources & stability
│  visorAgent       │  • Credit Agent   — evaluate credit profile
│                  │  • Asset Agent    — review assets & reserves
│                  │  • Collateral Agent — property & appraisal analysis
│                  │  • Decision Agent — final recommendation
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. PRICING       │  Loan pricing engine:
│  LoanPricing     │  • 7 loan products (Conv, FHA, VA, USDA, Jumbo,
│  Engine          │    Renovation, Commercial)
│                  │  • LLPA-style risk-based adjustments
│                  │  • Rate lock quotes with points/fees breakdown
│                  │  • DTI/LTV-based pricing grids
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 7. DECISION      │  Final decision: Approve / Refer / Suspend / Deny
│  + AUDIT         │  Encrypted audit bundle + HMAC-signed webhook
└──────────────────┘
```

### 4.2 Batch Processing

Per-borrower batch processing from folder structure:
```
simulated_documents/home_mortgage/
├── thompson_john_sarah/      # W-2, 740+ credit, 20% down
├── rodriguez_maria/          # FTHB teacher, gift funds, 678 credit
├── chen_david_karen/         # Jumbo refi, 800+ credit
├── wilson_james/             # Self-employed GC, 203k renovation
├── johnson_marcus_imani/     # USDA rural, first-time buyers
├── patel_lisa/               # Divorcee cash-out refi, asset-heavy
└── commercial_mortgage/
    ├── thompson_commercial/  # Mixed-use retail/office
    ├── oak_street_retail/    # NNN Walgreens
    ├── midwest_medical_plaza/ # Medical office
    └── riverbend_self_storage/ # Self-storage
```

---

## 5. Auth & RBAC

### 5.1 Authentication

- **Method**: JWT bearer tokens (HS256)
- **Token claims**: `sub` (username), `role`, `org_id`, `exp`
- **Token expiry**: configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480 min)
- **Password hashing**: bcrypt
- **Storage**: file-backed JSON (`~/.insureflow/auth_users.json`), survives server reloads
- **Endpoints**:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/status` | GET | No | Check if first-time admin setup is required |
| `/auth/setup` | POST | No | Create first admin account (one-time) |
| `/auth/register` | POST | No | Self-register as viewer or underwriter |
| `/auth/login` | POST | No | Get JWT token |
| `/auth/me` | GET | Bearer | Current user info |
| `/auth/roles` | GET | No | List all roles with hierarchy + descriptions |
| `/auth/users` | POST | Bearer (admin) | Create user with any role |
| `/auth/reset` | GET/POST | No | Clear all accounts |

### 5.2 Role Hierarchy

Each role inherits permissions from all lower levels. Role enforcement at the API layer via FastAPI `Depends(require_role(min_role))`:

| Role | Level | Permissions |
|------|-------|-------------|
| `viewer` | 1 | Read dashboards, jobs, audit trails, workflow status |
| `underwriter` | 2 | Run pipelines, create audits, pull data sources, record loss experience |
| `licensed_uw` | 3 | Sign off on memos (with license number), bind policies |
| `admin` | 4 | Create/manage users, delete jobs, configure webhooks |
| `cuo` | 5 | Set market cycles, system-wide underwriting parameters |

Self-registration creates `viewer` or `underwriter` accounts. Higher roles are assigned by admins via `POST /auth/users`.

---

## 6. Data Model

### 6.1 Key Domain Models

```
User
├── username: str
├── hashed_password: str (bcrypt)
├── role: Role (viewer → cuo)
├── org_id: str
├── disabled: bool
├── full_name: str
└── created_at: datetime

InsuranceJob (JobStore)
├── job_id: UUID
├── org_id: str
├── status: str (processing/done/failed)
├── pipeline_type: str (legacy/production)
├── created_at: datetime
├── results: InsuranceResults
│   ├── bundle_id: UUID
│   ├── ai_decision: ACCEPT/REFER/DECLINE
│   ├── quote: QuoteResult
│   │   ├── adjusted_premium: float
│   │   ├── base_premium: float
│   │   ├── rating_components: dict
│   │   └── metadata: dict
│   ├── memo: UnderwritingMemo
│   ├── cope_score: COPEScore
│   ├── triage_score: int
│   ├── triage_priority: str
│   ├── reinsurance_analysis: ReinsuranceAnalysis
│   ├── portfolio_risk: PortfolioRisk
│   └── work flow_state: str
└── error: str

PremiumAudit
├── audit_id: UUID
├── bundle_id: UUID
├── estimated_premium: float
├── actual_premium: float
├── adjustments: list[AuditAdjustment]
├── premium_delta_pct: float
├── status: AuditStatus (pending/in_progress/completed/disputed)
├── created_at, started_at, completed_at: datetime
└── notes: str
```

---

## 7. Frontend Architecture

### 7.1 Stack

React 18 + Vite + Tailwind CSS. Served as static files from FastAPI at `/dashboard`.

### 7.2 Pages

| Page | Route | Auth | Description |
|------|-------|------|-------------|
| **Overview** | `/` or `/overview` | Optional | Job metrics, quick demos, recent activity, market phase indicator, queue stats |
| **System Health** | `/system` | No | Live diagnostics (10 component checks) |
| **Insurance** | `/insurance` | Bearer | Source connector hub (24 sources), one-click demos, job history with COPE/Docs actions |
| **Mortgage** | `/mortgage` | Bearer | Loan submission, job history, rate/DTI display |
| **UW Sign-off** | `/workflow` | Bearer (licensed_uw+) | Review queue with approve/refer/decline, override category, UW confidence |
| **Renewal Dashboard** | `/renewals` | Bearer | Premium audit history, material adjustment queue, stat cards |
| **Authority Matrix** | `/authority` | Bearer | UW tier overview cards, binding limits table |
| **Market Admin** | `/market` | Bearer (cuo) | Phase banner, rate impact cards, metrics, phase selector |
| **Settings** | `/settings` | Optional | Account info, RBAC role reference, sign out, credential reset |

### 7.3 Components

- Layout — sidebar navigation with user menu, sign-in button
- LoginModal — first-time setup, sign-in, self-registration (viewer/underwriter)
- Badge — status badges for diagnostics
- PasswordInput — toggleable visibility

---

## 8. External Systems Layer

### 8.1 Insurance Source Connectors (24 simulated)

```
┌────────────────────────────────────────────────────────────┐
│  CONNECTOR HUB                                              │
│                                                             │
│  Cloud Storage: S3, Azure Blob, GCS                         │
│  Document Mgmt:  SharePoint, Box, Dropbox, Google Drive     │
│  Broker Systems: Applied Epic, Vertafore, Guidewire BP      │
│  Email:          Exchange, Gmail                            │
│  Legacy:         Mainframe FTP, AS/400, SFTP                │
│  Local:          Folder + example packages (Pacific Coast,  │
│                  Northwind, Sample Co)                      │
└────────────────────────────────────────────────────────────┘
```

### 8.2 External Data Oracles (simulated stubs)

| Oracle | Data Source | Purpose |
|--------|-------------|---------|
| CLUE | Claims history | Prior losses at location |
| NCCI | Workers comp | Class code experience mods |
| CAT model | Catastrophe | Hurricane/quake/ flood exposure scoring |

### 8.3 Policy Admin Adapter (stub)

Guidewire/Duck Creek-style quote + bind interface:
- `bind_policy()` — finalizes quote, returns policy number
- `issue_policy()` — generates policy documents

### 8.4 Core System Integrations (stubs)

| System | Purpose |
|--------|---------|
| BriteCore | Policy admin & billing sync |
| Guidewire | Claims & underwriting integration |

### 8.5 Broker Status Shares

Token-based public share links for real-time submission tracking:
- `GET /broker/status/{token}` — public status page (no auth required)
- `POST /pipeline/jobs/{id}/broker-share` — create share link (underwriter+)

---

## 9. Infrastructure

### 9.1 Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| API server | FastAPI + Uvicorn | HTTP gateway, all verticals |
| Dashboard | React 18 + Vite | Static SPA served by FastAPI |
| User store | JSON file | Auth persistence (survives reloads) |
| Job store | Redis / in-memory | Async job tracking, org-scoped |
| Celery broker | Redis | Async task queue for mortgage |
| Vector store | PostgreSQL + pgvector / in-memory | RAG knowledge retrieval |
| Encryption | Fernet (symmetric) | Audit bundle encryption at rest |
| Container | Docker + Compose | Redis, Postgres, API, Celery worker |
| CLI | Typer | `insureflow` command (serve, agents, doctor, e2e, auth-reset) |

### 9.2 Ports

| Service | Port | Notes |
|---------|------|-------|
| API + dashboard | 8002 | Default (8000/8001 often in use) |
| Redis | 6379 | Job store + Celery broker |
| PostgreSQL | 5432 | pgvector RAG |
| Celery worker | — | No HTTP port |
| MCP server | 8010 | SSE for Claude Desktop / Cursor |

### 9.3 Docker Stack

```yaml
services:
  api:      FastAPI + dashboard  (port 8000)
  redis:    Job store + broker   (port 6379)
  db:       PostgreSQL + pgvector (port 5432)
  mortgage-worker:  Celery worker (no port)
```

---

## 10. System Diagnostics

Ten component checks via `GET /system/diagnostics` and `python cli.py doctor`:

| # | Component | Category | What it checks |
|---|-----------|----------|----------------|
| 1 | LLM API Key | llm | OpenAI / Claude key presence |
| 2 | LLM Pipeline Mode | llm | Enhanced vs deterministic fallback |
| 3 | Redis | storage | Redis reachability |
| 4 | Job Store | storage | RedisJobStore vs MemoryJobStore |
| 5 | Encryption | security | Fernet key configured |
| 6 | OCR | ingestion | pdfminer, pytesseract, tesseract binary |
| 7 | Audit Storage | storage | Audit log directory writable |
| 8 | Insurance Examples | data | Example submission files present |
| 9 | Mortgage Fixtures | data | Simulated documents present |
| 10 | PostgreSQL/pgvector | rag | DATABASE_URL reachable |

---

## 11. Testing Architecture

### 11.1 Unit Tests (~200)

```
tests/
├── test_pipeline.py         # InsurancePipeline end-to-end (4 tests)
├── test_underwriting.py     # COPE, Authority, Market Cycle, Renewal, Premium Audit, Triage (43 tests)
├── test_mortgage.py         # Mortgage pipeline + extraction
├── test_mortgage_infra.py   # Mortgage infrastructure
├── test_insurance_production.py  # Production workflow
├── test_health.py           # Diagnostics
├── test_agents.py           # Agent tests
└── ...
```

### 11.2 E2E Tests (42 scenarios)

`python scripts/e2e_test.py` covers: health, auth (setup + login), diagnostics (10/10 checks), all 24 connector pulls, insurance demo pipeline, full production workflow (sign-off → bind → ZIP → loss experience → calibration), mortgage demo, Celery async path, Playwright browser UI (login, navigation, password toggle).

---

## 12. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Dual verticals, shared infra** | Insurance and mortgage share auth, job store, encryption, and API; separate pipelines and agents per domain |
| **Deterministic fallback always present** | Agents work without any LLM API key; LLM enhances analysis when configured |
| **Provenance hierarchy** | Structured broker data (ACORD) wins over AI-extracted PDF fields; eliminates hallucinations on critical limits |
| **Licensed UW gate** | AI recommends; a licensed underwriter with license number signs off before bind |
| **Authority tiers with binding limits** | Junior ($25K) → Senior ($250K) → CUO (unlimited) — matches "one door down" approval chain |
| **ISO-style rating** | TIV / 100 × ISO_loss_cost × LCM × territory relativity × mods — mirrors real carrier pricing |
| **COPE four-pillar framework** | Construction, Occupancy, Protection, Exposure — each weighted 25%, matches industry standard |
| **Market cycle awareness** | Hard/soft market phases adjust pricing and appetite thresholds; defaults to soft (current market) |
| **Submission triage first** | Runs before appetite filter to match real-world "sort 100 apps, surface best first" |
| **Encrypted audit at rest** | Fernet envelope encryption on all persisted bundles; regulatory ZIP with checksums for examiners |
| **Org-scoped isolation** | Jobs, workflows, audit trails, and webhooks scoped per `org_id` in JWT |
| **File-backed auth** | JSON file survives `uvicorn --reload`, no database dependency for user management |
| **Self-registration limited** | Users can self-register as viewer/underwriter only; higher roles require admin |
