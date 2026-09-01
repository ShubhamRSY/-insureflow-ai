# Rytera — System Architecture

> **Version:** 0.3.x · **Module:** `insureflow` · **Docs:** [`docs/ZERO_TOKEN_ARCHITECTURE.md`](../ZERO_TOKEN_ARCHITECTURE.md)

Rytera is an enterprise multi-agent underwriting operating system for **commercial
insurance**, **bank mortgage**, and **consumer/commercial lending**. It ingests
multi-format submission packages, routes every stage of analysis through a
decision layer that prefers deterministic code before ever spending a token,
produces decision memos with premium/rate quotes, and supports the full
sign-off → bind → audit → renewal lifecycle under role-based access control.

Three verticals share one platform: a unified **Connect & pull** intake hub,
a common ingestion/provenance/reconciliation core, specialist agent swarms,
deterministic rating and ML scoring, encrypted audit trails, an enterprise
integration gateway, and an ML model/guideline registry.

---

## 1. Design Tenets

| Tenet | Description |
|-------|-------------|
| **Zero Token Architecture (ZTA)** | Use AI only when you must — every stage asks "can code, rules, or a trained model solve this deterministically?" before spending a token. See [§ 7](#7-zero-token-architecture-zta). |
| **Deterministic by default** | Every agent has a rule-based fallback; LLM keys are optional. |
| **Provenance-first** | Structured broker data (ACORD) always beats AI-extracted values; a provenance hierarchy resolves conflicts by source trust. |
| **Licensed UW gate** | AI recommends; a licensed underwriter signs off before bind. |
| **Org-scoped isolation** | Jobs, workflows, audit trails, webhooks, and bundles are scoped by `org_id` embedded in the JWT. |
| **Encrypted at rest** | Fernet envelope encryption on every persisted audit bundle; regulatory ZIP exports carry a SHA-256 manifest. |
| **Governed models** | Every model/guideline change is versioned, reviewed, and approved through the registry before promotion. |
| **Single intake, three verticals** | One **Files / Connect & pull / Sample data** widget and one draft-bundle pipeline power all pages. |

---

## 2. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                      │
│  Vanilla-JS SPA (/dashboard) · Landing page (/) · CLI (Typer) · curl · MCP │
└──────────────────────────────────┬─────────────────────────────────────────┘
                                   │ HTTPS (JWT Bearer)
┌──────────────────────────────────▼─────────────────────────────────────────┐
│                           API GATEWAY (FastAPI)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ JWT Auth │ │ RBAC (5) │ │ Org Scope│ │CORS/CSRF │ │ Gateway Key Auth │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│                                                                            │
│  Auth · Dashboard · Broker shares · System health · Security posture       │
│                                                                            │
│  ┌────────────────────────┐   ┌────────────────────────┐                  │
│  │  INTAKE & CONNECTIONS  │   │  VERTICAL PIPELINES     │                  │
│  │  /api/insurance/sources│   │  /pipeline/*   (Ins)    │                  │
│  │  /api/connections/*    │   │  /mortgage/*   (Mtg)    │                  │
│  │  /pipeline/bundles*    │   │  /lending/*    (Lnd)    │                  │
│  │  draft-bundle assembly │   │  /api/demo/*            │                  │
│  └────────────────────────┘   └───────────┬────────────┘                  │
│                                           │                               │
│  ┌────────────────────────────────────────▼────────────────────────────┐   │
│  │  SHARED INTELLIGENCE LAYER (ZTA router first, then deterministic,  │   │
│  │  then ML, then LLM)                                                │   │
│  │  Parser · Provenance · Reconciliation · Rating · Risk · Rules      │   │
│  │  Specialist Agents · RAG · ML models · Vision                       │   │
│  └────────────────────────────────────────┬────────────────────────────┘   │
│                                           │                               │
│  ┌────────────────────────────────────────▼────────────────────────────┐   │
│  │  WORKFLOW · AUDIT · GOVERNANCE                                       │   │
│  │  Sign-off → Bind · Loss feedback · Renewal · Premium audit          │   │
│  │  Audit logger (Fernet) · Broker shares · Webhooks                    │   │
│  └────────────────────────────────────────┬────────────────────────────┘   │
│                                           │                               │
│  ┌────────────────────────────────────────▼────────────────────────────┐   │
│  │  INFRASTRUCTURE & EXTERNAL SYSTEMS                                   │   │
│  │  Redis (jobs) · PostgreSQL+pgvector (RAG) · Celery · Registry store │   │
│  │  Integration gateway → Oracles · Policy admin · CRM · Enterprise ops │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Layered view

| Layer | Responsibility |
|-------|----------------|
| **Client layer** | SPA dashboard, marketing landing page, CLI, MCP server (SSE), curl. |
| **API gateway** | Auth, RBAC, org scoping, rate limiting, CORS/CSRF, gateway key auth, static file serving. |
| **Intake & connections** | 24 vertical-aware source connectors, email picker, draft-bundle accumulation, file/OCR upload. |
| **Vertical pipelines** | Insurance / Mortgage / Lending orchestration (sync + Celery async). |
| **Shared intelligence** | ZTA routing → deterministic parsers/engines → trained ML → LLM agents/RAG. |
| **Workflow & audit** | UW sign-off, bind, loss feedback, renewals, premium audits, encrypted audit bundles, webhooks, broker shares. |
| **Infrastructure** | Redis job store, PostgreSQL/pgvector, Celery workers, registry file store, Docker/Compose, Railway. |
| **External systems** | Integration gateway adapters for oracles (CLUE/NCCI/A-PLUS/CAT/ISO), policy admin, CRM, enterprise ops. |

---

## 3. End-to-End Request Flow

The platform runs three primary flows — all share the intake, ZTA routing, and
audit stages.

### 3.1 Unified intake (all verticals)

```
User opens /dashboard → Files / Connect & pull / Sample data
  │
  ├─ Files:        upload documents (upload → OCR → classify → draft bundle)
  ├─ Connect & pull: pick connector (24, vertical-aware) → authenticate
  │                  (simulated) → pull documents → accumulate into draft bundle
  └─ Sample data:   load a packaged example submission (Pacific Coast,
                    Northwind, Sample Co, or per-vertical fixtures)
           │
           ▼
     draft bundle (org-scoped)
           │  POST /pipeline/bundles → GET /pipeline/bundles/{id}
           │  POST /pipeline/bundles/{id}/run?vertical=insurance|mortgage|lending
           ▼
     pipeline engine (sync or Celery async) → zta_report + results
           ▼
     audit bundle (Fernet-encrypted) + optional UW sign-off / bind
```

### 3.2 Insurance flow

```
Broker package → Triage → Appetite filter → Ingest/OCR/Classify
  → Provenance → Reconcile → COPE analysis → Agent swarm (Risk, Loss Run,
    Compliance, Fraud, UW Decision) → RAG guidelines → UW decision
  → Rating quote → Reinsurance → Portfolio risk → Workflow (pending review)
  → Licensed UW sign-off → Bind → Loss feedback → Renewal → Encrypted audit ZIP
```

### 3.3 Mortgage flow

```
Loan package → Ingest/OCR/Classify (30+ doc types) → Extract
  → Reconcile (W-2 vs 1040, appraisal vs price, identity) → Compliance rules
  → Agent swarm (Income, Credit, Asset, Collateral, Decision) → Pricing
  → Decision (Approve/Refer/Suspend/Deny) → HMAC webhook → audit
```

### 3.4 Lending flow

```
Application → Credit pull → Income/debt verification → Risk score (ML + rules)
  → Compliance (Reg B / ECOA / HMDA) → Credit-risk & pricing agents
  → Decision (Approve/Counteroffer/Decline) → Adverse-action notice → audit
```

### 3.5 Async path

Long-running pipelines run under **Celery** with Redis as broker and result
backend. The job store tracks progress (`pending → running → done/failed`);
the SPA polls `GET /pipeline/jobs/{id}` and streams progress
(`GET /pipeline/jobs/{id}/stream`).

---

## 4. Intake & Source Connectivity

### 4.1 Connector hub

24 simulated enterprise integrations behind vertical-aware endpoints
(`?vertical=insurance|mortgage|lending`):

| Category | Connectors |
|----------|------------|
| Cloud storage | S3, Azure Blob, GCS |
| Document management | SharePoint, Box, Dropbox, Google Drive |
| Broker platforms | Applied Epic, Vertafore, Guidewire BrokerPortal |
| Email | Exchange, Gmail (with inbox filter) |
| Legacy | Mainframe FTP, AS/400, SFTP |
| Local | Folder + packaged example packages |

The **Connect & pull** component renders the connector grid with brand logos,
a category filter, an email picker, and pull-to-accumulate into a draft bundle.
It is embedded in the shared **Files / Connect & pull / Sample data** widget
used by the Insurance, Mortgage, and Lending pages (`RunSelector` + `ConnectAndPull`).

### 4.2 Draft bundles

| Endpoint | Purpose |
|----------|---------|
| `GET/POST /pipeline/bundles` | List / create org-scoped draft bundles |
| `GET /pipeline/bundles/{id}` | Bundle state + accumulated documents |
| `GET/POST /pipeline/bundles/{id}/documents` | List / attach documents |
| `POST /pipeline/bundles/{id}/run` | Execute a bundle against any vertical |
| `GET /pipeline/documents/{id}/missing` | Missing-document checklist |
| `POST /pipeline/documents/{id}/request` | Request missing documents |
| `POST /api/insurance/sources/{id}/pull` | Pull a single connector |

---

## 5. Ingestion, Provenance & Reconciliation Core

### 5.1 Document ingestion

| Parser | Format | Type |
|--------|--------|------|
| `ACORDParser` | ACORD XML | Structured |
| Broker JSON parser | JSON submission | Structured |
| Loss Run parser | Tabular loss runs | Semi-structured |
| SOV parser | Schedules of values | Semi-structured |
| Inspection Report extractor | Unstructured | Regex/rule + optional LLM |
| PDF pipeline | Scanned/native PDFs | OCR (pdfminer + Tesseract) → classify |
| Document classifier | Auto-routes documents by type | Model + rules |

Mortgage ingestion classifies 30+ document types (W-2, 1040, paystub, credit
report, appraisal, bank statement, rent roll, P&L, lease, …). Lending ingests
application data, credit pulls, and bank statements.

### 5.2 PII redaction & entity resolution

- **Redaction** (`redaction/`): automated PII detection (SSN, EIN, DOB, account
  numbers) and document redaction before LLM exposure.
- **Entity resolution** (`entities/`): named-entity extraction and cross-document
  entity matching (identity checks across W-2/1040/credit).

### 5.3 Provenance hierarchy

Source-of-truth order: **1.** signed legal submission · **2.** broker ACORD XML
· **3.** inspection report · **4.** AI-extracted PDF fields. The highest-trust
value wins; discrepancies are logged for reconciliation.

### 5.4 Reconciliation

Cross-document validation with per-vertical rules:

| Vertical | Reconciliation checks |
|----------|------------------------|
| Insurance | ACORD vs inspection vs loss run vs SOV |
| Mortgage | W-2 vs 1040 income, appraisal vs purchase price, identity, employment |
| Lending | Income vs application, debt verification |

Critical mismatches escalate to human review; non-critical resolve to the
highest-trust source.

---

## 6. Vertical Pipelines

### 6.1 Insurance (`insurance/`)

> **Deep dive (commercial lines):** [`commercial_underwriting_pipeline.html`](./commercial_underwriting_pipeline.html) — full layered system design (input → API gateway → AI orchestrator → RAG/memory/LLM → tool-calling/Agent Gateway → validation → response & action → audit log), the decision-scoring formula, data handling/retention specifics, and the fail-closed reliability model. Open it directly in a browser.

| Stage | Engine | Notes |
|-------|--------|-------|
| 1. Triage | `TriageAgent` | 0–100 score (NAICS fit, geography, size, coverage, doc completeness); HOT/WARM/COLD/NO_FIT |
| 2. Appetite | `AppetiteFilter` | 9 deterministic checks (NAICS, geography, TIV, loss ratio, min premium, years in business, cancellation, occupancy, protection class) |
| 3. COPE | `COPERatingEngine` | Construction (5 classes), Occupancy (9 types), Protection (ISO 1–10), Exposure (9 CAT types) → risk grade + −25%…+50% modifier |
| 4. Agents | Risk, Loss Run, Compliance, Fraud, UW Decision | ReAct with rule fallback; independent findings + confidence |
| 5. RAG | pgvector/in-memory | 18 underwriting guidelines across 8 categories |
| 6. Decision | `UWDecisionAgent` | ACCEPT / REFER / DECLINE + rationale + confidence |
| 7. Rating | `InsuranceRatingEngine` | ISO-style premium (see § 6.4) |
| 8. Reinsurance | `ReinsuranceAgent` | Quota share, excess of loss, facultative; capacity flags |
| 9. Portfolio | `PortfolioRiskAgent` | Geographic / industry concentration scoring |
| 10. Workflow | `WorkflowEngine` | Authority matrix sign-off, bind state machine |
| 11. Lifecycle | Renewal, Premium Audit, Loss feedback | § 6.5 |

### 6.2 Mortgage (`mortgage/`, `agents/mortgage/`)

Stages: ingest/classify → extract → reconcile → compliance rules (CREDIT-001,
DTI-001, LTV-001, INCOME-001, RESERVES-001, 20+ rules) → agent swarm (Income,
Credit, Asset, Collateral, Decision) → pricing (7 products, LLPA-style
adjustments, rate lock) → decision (Approve / Refer / Suspend / Deny) → HMAC
webhook → encrypted audit.

### 6.3 Lending (`lending/`)

Stages: application → credit pull → risk scoring (`LendingDefaultRiskModel` +
rules) → compliance (Reg B / ECOA / HMDA, adverse-action notices) → agents
(Credit Risk, Compliance, Pricing) → decision (Approve / Counteroffer / Decline)
→ risk-based pricing (`LoanPricing` + `PricingAgent`) → audit.

### 6.4 Rating engines

- **Insurance** — ISO-style: `TIV/100 × ISO_loss_cost × LCM × territory_relativity
  × (1+COPE_mod) × (1+market_mod) × (1+deductible_credit) + expense_constant`,
  market-cycle adjustments, minimum premium enforcement.
- **Mortgage** — `LoanPricingEngine`: 7 products, LLPA-style grids, rate-lock
  quotes with points/fees.
- **Personal lines** — `rating/personal/`: homeowners (protection-class-driven),
  auto, life rating with filing manuals.

### 6.5 Post-bind lifecycle

| Component | Purpose |
|-----------|---------|
| Loss feedback | Record actual loss experience; portfolio calibration by loss ratio |
| Renewal engine | 60–120 day window, loss-ratio trend, retention risk, non-renew/modify/refer |
| Premium audit | Estimated vs actual tracking, material adjustment detection (>15%), disputed flows |
| Override analytics | UW confidence, 11 override categories, premium delta, pattern detection |

---

## 7. Zero Token Architecture (ZTA)

> **"The best token is the one you never had to generate."**

ZTA is the operating principle of the platform: **use AI only when you must —
everything else, solve deterministically.** See
[`docs/ZERO_TOKEN_ARCHITECTURE.md`](../ZERO_TOKEN_ARCHITECTURE.md) for the full
specification.

### 7.1 Router

`insureflow.zta.ZeroTokenRouter.route(task, context)` classifies every pipeline
task as:

| Decision | Meaning |
|----------|---------|
| `deterministic` | Solved with code/rules/ML — **zero tokens** |
| `llm` | Reasoning genuinely required; budget not exhausted |
| `escalate_human` | No deterministic solution and LLM budget exhausted / strict mode |
| `skip` | Not applicable |

### 7.2 Wired stages

| Task | Deterministic path | LLM only when… |
|------|--------------------|----------------|
| Structured parsing (ACORD) | Rule-based `ACORDParser` | never |
| Unstructured extraction | Regex/rule extractor | regex coverage < threshold |
| Reconciliation | `ReconciliationEngine` | conflicts require reasoning |
| Risk scoring | Rule engine + trained ML | never |
| Pricing / rating | `InsuranceRatingEngine` | never |
| UW decision | Deterministic conflict resolution | conflicts can't be resolved by rules |
| Memo generation | Template from findings | available & budget allows |
| Property photo analysis | — | always (or skipped) |

### 7.3 Configuration & accounting

- Env: `ZTA_ENABLED`, `ZTA_STRICT`, `ZTA_MEMO_LLM`, `ZTA_EXPECTED_FIELDS_RATIO`,
  `ZTA_MAX_LLM_TASKS_PER_JOB`.
- Every `RouteResult` carries `tokens_saved_est` and `tokens_used_est`; the
  reporter aggregates per job and process-wide.
- API: `GET /api/zta/status`, `POST /api/zta/route`.
- Every pipeline result embeds a `zta_report` (policy, mode, config, per-task
  decisions, totals).

---

## 8. Deterministic Core, ML & LLM Layers

### 8.1 Layered inference (resolution order)

1. **Deterministic code** — parsers, rules, rating engines (zero tokens).
2. **Trained ML models** — gradient-boosted predictors on engineered features
   (zero tokens, deterministic).
3. **LLM agents / RAG** — only when ZTA permits and budget allows.

### 8.2 Trained ML models (`ml/`)

| Model | Purpose |
|-------|---------|
| `LossPredictionModel` | Expected loss / loss ratio |
| `FraudDetectionModel` | Submission fraud score |
| `PremiumOptimizerModel` | Premium recommendation |
| `PortfolioRiskModel` | Portfolio concentration risk |
| `BehavioralScoringModel` | Broker/borrower behavior |
| `ChurnPredictionModel` | Retention / churn |
| `MortgageDefaultRiskModel` | Mortgage default probability |
| `LendingDefaultRiskModel` | Lending default probability |
| `VisionModel` (`ml/vision/`) | Property/photo analysis |

Lifecycle: `draft → training → ready → champion / challenger → retired`.
Training via `POST /ml/train`; prediction via `/ml/predict/*`; explainability
via `/ml/explain/{model_type}`; training-data export via `/ml/export-training`.

### 8.3 Agent swarm & LLM

- Specialist agents run **ReAct** with a **rule-based fallback** so the pipeline
  works with no API key.
- `agents/` (insurance + mortgage), `graph/` (LangGraph-style pipeline builder),
  `knowledge/` (heuristic learner, pattern/edge-case detection, tacit store),
  `rag/` (retrieval policy, rerank fallback).

---

## 9. Workflow, Audit & Governance

### 9.1 Authority matrix & sign-off

| Role | Binding limit |
|------|---------------|
| Junior UW | $25K max premium |
| Senior UW | $250K max premium |
| CUO | Unlimited |
| MGA | Delegated authority |

Co-sign threshold: > $100K requires senior+. Licensed UW signs off with license
number, override category, and confidence score. State machine:
`pending_review → sign-off → bind`.

### 9.2 Audit

- Every run writes an **encrypted audit bundle** (Fernet envelope): agent
  findings, provenance discrepancies, decision rationale, quote components,
  sign-off record.
- **Regulatory ZIP export** with SHA-256 manifest and package listing
  (`/pipeline/audit/{id}/package`).
- Deep-dive view: `GET /pipeline/{bundle_id}/deep-dive`.

### 9.3 Broker status shares

Token-based public share links: `POST /pipeline/jobs/{id}/broker-share` →
`GET /broker/status/{token}` (no auth) with document response via
`/broker/status/{token}/respond`.

### 9.4 Webhooks

HMAC-signed event subscriptions for insurance (`/webhooks/insurance`) and
mortgage (`/mortgage/webhooks`).

---

## 10. Model & Guideline Registry

`insureflow.registry.RegistryService` provides version-controlled, review-gated
governance over model components and guidelines:

- **Entries** are typed, versioned, checksummed artifacts with `draft →
  in_review → approved / rejected → active / superseded` lifecycle.
- **Diffing** between any two versions (`/registry/diff`).
- **Snapshots** of the full registry at release points (`/registry/snapshots`).
- **Review workflow**: `submit_for_review` → `approve`/`reject` with comments.
- **API**: `/registry/versions`, `/registry/bootstrap`, `/registry/snapshot`,
  `/registry/diff`, `/registry/context`.
- Benchmark output (`evaluations/benchmark.py`) embeds `model_metadata` and
  `registry_inventory` so every run records exactly which artifacts were used.

---

## 11. Auth, RBAC & Security

### 11.1 Authentication

- JWT bearer (HS256); claims `sub`, `role`, `org_id`, `exp`; expiry via
  `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480 min); bcrypt password hashing.
- **User store** (`auth/store.py`): Redis-backed (`rytera:auth:users`) with JSON
  file fallback — survives container redeploys.
- SSO support (`/auth/sso/*`), first-time setup (`/auth/setup`), reset
  (`/auth/reset`).

### 11.2 RBAC

Roles (hierarchical, enforced via `Depends(require_role(min_role))`):
`viewer` → `underwriter` → `licensed_uw` → `admin` → `cuo`. Self-registration
creates only viewer/underwriter; higher roles require admin assignment.

### 11.3 Security posture

- `security/`: secrets loader (env/gateway-key), posture reporting
  (`GET /security/status`).
- `auth/store.py` Redis-backed persistence with file fallback.
- Fernet envelope encryption at rest; HMAC-signed webhooks; org-scoped data.

---

## 12. Data Model (core entities)

```
User            role (viewer→cuo) · org_id · bcrypt hash · disabled · created_at
InsuranceJob    job_id · org_id · status · pipeline_type · results
                └ results: bundle_id · ai_decision · quote (adjusted/base/
                  components) · memo · cope_score · triage · reinsurance ·
                  portfolio_risk · workflow_state
MortgageJob     job_id · org_id · status · borrower · decision · rate lock ·
                compliance results
LendingJob      application_id · org_id · status · decision · pricing · adverse
PremiumAudit    audit_id · bundle_id · estimated vs actual premium · adjustments ·
                status (pending/in_progress/completed/disputed) · timestamps
DraftBundle     bundle_id · org_id · vertical · documents[] · status
RegistryEntry   entry_id · component_type · version_label · checksum · status ·
                reviewer · comments · superseded_by
```

---

## 13. API Surface (route map)

| Group | Routes |
|-------|--------|
| Auth | `/auth/*` (setup, login, register, me, roles, users, reset, sso/*) |
| Pipeline | `/pipeline/run`, `/pipeline/v2/run`, `/pipeline/jobs*`, `/pipeline/queue`, `/pipeline/bundles*`, `/pipeline/checkpoints/*`, `/pipeline/audit/*`, `/pipeline/audits*`, `/pipeline/workflow/*`, `/pipeline/outcomes/*`, `/pipeline/renewal/*`, `/pipeline/cope/*`, `/pipeline/ecosystem/*`, `/pipeline/vision/*`, `/pipeline/rating/products`, `/pipeline/documents/*` |
| Insurance sources | `/api/insurance/sources`, `/api/insurance/sources/{id}/pull`, `/api/insurance/sources/email-inbox/filter` |
| Connections | `/api/connections/{id}`, `/api/connections/{id}/pull` |
| Mortgage | `/mortgage/pipeline/run`, `/mortgage/pipeline/jobs*`, `/mortgage/products`, `/mortgage/audit/*`, `/mortgage/webhooks*` |
| Lending | `/lending/pipeline/run`, `/lending/pipeline/result/{id}`, `/lending/products` |
| Demo | `/api/demo/presets`, `/api/demo/{vertical}/{preset}` |
| ML | `/ml/status`, `/ml/train*`, `/ml/predict/*`, `/ml/score/*`, `/ml/explain/*`, `/ml/export-training`, `/ml/models` |
| Registry | `/registry/*` (versions, bootstrap, snapshot, diff, context) |
| Evaluations | `/evaluations/*` (quality-gates, drift, golden inventory, hitl, trends, cadence) |
| Integrations | `/integration/status`, gateway `/integrations/*` |
| Enterprise ops | `/pipeline/ecosystem/*`, `/api/checkpoints/*` |
| Underwriting | `/underwriting/authority`, `/underwriting/market` |
| Analytics | `/analytics/*` (overrides, agent-performance, documents) |
| Portfolio | `/portfolio/summary` |
| ZTA | `/api/zta/status`, `/api/zta/route` |
| Pilot | `/pilot/*` (packages, redact, calibration, sandbox, seed, email intake) |
| Observability | `/ops/snapshot`, `/metrics`, `/observability/log-explorers` |
| System | `/health`, `/system/diagnostics`, `/security/status`, `/api/dashboard/overview` |
| Broker | `/broker/status/{token}`, `/broker/status/{token}/respond` |
| Releases | `/releases/checklist`, `/releases/experiments*` |

---

## 14. Frontend Architecture

### 14.1 Stack

Vanilla-JS SPA served as static files by FastAPI at `/dashboard` (Vite build,
modular CSS). Marketing landing page at `/`. No backend framework — a thin API
client wraps the FastAPI endpoints.

### 14.2 Pages

| Page | Route | Purpose |
|------|-------|---------|
| Overview | `/` | Metrics, quick demos, recent activity, market phase, queue stats |
| System Health | `/system` | 10-component live diagnostics |
| Insurance / Mortgage / Lending | `/insurance` `/mortgage` `/lending` | Shared **Files / Connect & pull / Sample data** intake, job queue, pipeline visualization, results |
| Queue | `/queue` | Job queue management |
| Workflow | `/workflow` | Licensed UW review queue — approve/refer/decline, override category, confidence |
| Renewal Dashboard | `/renewals` | Premium audits, material-adjustment queue |
| Authority Matrix | `/authority` | UW tiers + binding limits |
| Market Admin | `/market` | Phase banner, rate-impact cards, phase selector |
| Portfolio | `/portfolio` | Concentration buckets, exposure |
| Evaluations | `/evaluations` | Quality gates, HITL reviews, drift, trends |
| Registry | `/registry` | Model/guideline version review |
| Webhooks | `/webhooks` | Subscription management |
| Integrations | `/integrations` | Gateway health/status |
| Pilot | `/pilot` | Partner sandbox, calibration, redaction |
| Override Analytics | `/override-analytics` | Override patterns |
| Broker Status | `/broker/status/{token}` | Public broker share |
| Settings | `/settings` | Account, roles reference, sign out, credential reset |

### 14.3 Key components

`RunSelector` (Files / Connect & pull / Sample data), `ConnectAndPull` (connector
grid + email picker + draft-bundle accumulation), `InsuranceSourceHub`,
`JobDrawer`/`SubmissionJourney` (9-stage pipeline panel, COPE, provenance,
reconciliation, compliance), `StageStrip`, `AuditTrailViewer`, `LoginModal`,
`Layout`.

---

## 15. Integration Gateway & External Systems

### 15.1 Gateway (`gateway/`)

Bundled HTTP adapter layer (same routes can be deployed at
`integrations.rytera.ai` in production), protected by gateway API keys:

| Category | Systems |
|----------|---------|
| Oracles | CLUE, NCCI, A-PLUS, CAT, ISO loss costs |
| Policy admin | Guidewire PolicyCenter, BriteCore |
| CRM | HubSpot (local gateway mock in dev) |
| Enterprise ops | Loss control, claims, broker portal, actuarial |

Modes: `auto` / `live` / `simulated` with health-checked connectivity
(`/integration/status`, `/pipeline/ecosystem/status`).

### 15.2 Enterprise ecosystem (`enterprise/`)

`EnterpriseEcosystemService`: oracle feed status, loss-control dispatch, claims
summary, actuarial filing status, CRM summary, broker document requests, human
checkpoint resolution (`/pipeline/checkpoints/*/resolve`), actuarial feedback
loop.

### 15.3 Pilot & sandbox (`pilot/`)

Partner-facing sandbox: `PackageLoader`, `AutoRedact` + `PiiGate`, `EmailIntake`,
`Calibration` (shadow-mode pilot with `PILOT_SHADOW_MODE`), `SandboxReadiness`.
Endpoints under `/pilot/*` (packages, redact, calibration, sandbox-status, seed).

---

## 16. Observability & Security

| Area | Mechanism |
|------|-----------|
| Health | `/health` (status + version) |
| Diagnostics | `/system/diagnostics` — LLM, Redis, job store, encryption, OCR, audit storage, examples, mortgage fixtures, pgvector, observability |
| Telemetry | `observability/` — Prometheus `/metrics`, Grafana dashboards, OpenObserve shipper, CloudWatch, `ops/snapshot`, log explorers |
| Security posture | `/security/status`, secrets loader, gateway key auth |
| Encryption | Fernet envelope encryption; SHA-256 manifest on regulatory ZIPs |

---

## 17. Infrastructure & Deployment

### 17.1 Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| API server | FastAPI + Uvicorn | HTTP gateway, all verticals, static SPA |
| Dashboard | Vanilla JS + Vite | SPA served by FastAPI at `/dashboard` |
| Job store | Redis (persistent) / in-memory | Async job tracking, org-scoped |
| Celery | Redis broker + result backend | Async insurance/mortgage pipelines |
| Vector store | PostgreSQL + pgvector / in-memory | RAG knowledge retrieval |
| User store | Redis-backed + JSON fallback | Auth persistence |
| Registry store | Versioned files | Model/guideline governance |
| Encryption | Fernet | Audit bundle encryption at rest |
| Container | Docker + Compose | Redis, Postgres, API, Celery worker, Prometheus, Grafana, OpenObserve |
| Deploy | Railway | Production at ryterainc.com |
| CLI | Typer | `serve`, `agents`, `doctor`, `e2e`, `auth-reset` |
| MCP | FastMCP over SSE | Claude Desktop / Cursor integration |

### 17.2 Ports

| Service | Port |
|---------|------|
| API + dashboard | 8002 (default) |
| Redis | 6379 |
| PostgreSQL | 5432 |
| MCP server | 8010 (SSE) |
| Prometheus | 9090 |
| Grafana | 3000 |
| OpenObserve | 5080 |
| Celery worker | — |

### 17.3 Runtime modes

- **Local**: `docker compose up` or pip-installed CLI (`insureflow serve`).
- **Production (Railway)**: Redis, PostgreSQL, Fernet key; async via Celery.
- **Modes**: deterministic-only (no LLM key) → enhanced (LLM via ZTA budget).

---

## 18. Testing & Quality

| Suite | Scope |
|-------|-------|
| **Unit + integration** (`pytest tests/`) | Parsers, agents, rating, workflow, underwriting, mortgage, lending, oracles, provenance, reconciliation, gateway, registry, ML, ZTA, security, draft bundles, production integrations — **~1,000 tests** |
| **E2E** (`scripts/ops/e2e_test.py`, `cli.py e2e`) | Health, auth, diagnostics, 24 connector pulls, insurance demo, production workflow (sign-off → bind → ZIP → loss experience → calibration), mortgage demo, Celery async, Playwright UI |
| **Benchmarks / evals** (`evaluations/`) | Golden inventory, quality gates, drift detection, HITL review, registry inventory in output |

CI gates (`.github/workflows/ci.yml`): `ruff check .` · `ruff format --check .`
· `mypy src/ tests/` · `pytest` · frontend build · Docker build.

---

## 19. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Zero-token routing first** | Deterministic core stays reproducible and cheap; tokens spent only where reasoning is genuinely required |
| **Three verticals, shared core** | One intake, auth, job store, encryption, audit; separate pipelines/agents per domain |
| **Deterministic fallback always present** | Agents work with no API key; LLM enhances when configured |
| **Provenance hierarchy** | Structured broker data beats AI-extracted fields; eliminates hallucinations on critical limits |
| **Licensed UW gate** | AI recommends; a licensed underwriter signs off before bind |
| **Authority tiers** | Junior ($25K) → Senior ($250K) → CUO (unlimited), matching approval chains |
| **ISO-style rating** | Mirrors real carrier pricing; auditable components |
| **COPE four-pillar framework** | Construction / Occupancy / Protection / Exposure, industry standard |
| **Market cycle awareness** | Hard/soft phases adjust pricing and appetite; defaults to soft |
| **Triage before appetite** | Match real-world "sort 100 apps, surface best first" |
| **Encrypted audit at rest** | Fernet envelope + SHA-256 manifest ZIP for examiners |
| **Registry-gated model changes** | Every model/guideline promotion is versioned, diffed, and approved |
| **Redis-backed auth** | Survives container redeploys; JSON fallback when Redis is absent |
| **Single intake widget** | One Files / Connect & pull / Sample data UX across every vertical |
| **Celery-first async dispatch** | Heavy pipeline swarms run on worker processes, never an API event loop; falls back to in-process when the broker is down |
| **Locked atomic file stores** | Cross-process `flock` + temp-file rename so multi-worker file fallbacks never corrupt or drop records |

---

## 20. Scaling & Operations

### 20.1 Multi-worker web

The API runs multiple uvicorn workers (`WEB_CONCURRENCY`, default CPU count capped
at 4) so one event loop is never a single point of failure. `entrypoint.sh`
picks up `PORT`/`WEB_CONCURRENCY`; `railway.json` pins the same entrypoint and a
`/health` healthcheck with ON_FAILURE restart.

### 20.2 Async dispatch

Pipeline runs default to Celery when a broker (`REDIS_URL` / `CELERY_BROKER_URL`)
is configured and reachable, so the 13-agent swarm never blocks the API. When the
broker is down the request degrades gracefully to in-process background tasks.

- `INSURANCE_USE_CELERY=1|0` — force the mode (compose already sets `=1`).
- `INSURANCE_IN_PROCESS=1` — force in-process (local debugging, tiny deploys).
- Dispatch logic: `src/insureflow/tasks/dispatch.py`; celery tasks under
  `src/insureflow/tasks/` on the `agents`, `pipeline`, and `mortgage` queues.

The Celery worker is a separate service (compose `worker`,
`celery -A insureflow.tasks.celery_app worker -Q agents,pipeline,mortgage`) —
scale it independently of the API.

### 20.3 Durable stores under concurrency

- **Job store** — Redis (`JOB_STORE_BACKEND=redis`), falling back to a locked
  file store; production refuses in-memory stores.
- **User store** — Redis-first, JSON fallback; both paths now write under a
  cross-process `flock` with atomic temp-file rename
  (`src/insureflow/storage/lock.py`).
- **Registry / audit / metrics** — JSON/JSONL writes go through the same atomic
  primitives; the concurrency tests assert **zero** dropped records.

### 20.4 Metrics across replicas

Business metrics (fill rate, override rate, cycle time) default to JSONL. Set
`METRICS_BACKEND=redis` (compose/Railway already do) so every worker aggregates
the shared append log in Redis and each `get_*` read refreshes from it — no
per-worker partial dashboards.

### 20.5 Load testing

`python scripts/ops/load_test.py --base http://localhost:8000 --requests 500 --concurrency 20`
reports p50/p95/p99 latency, throughput, and error rate against `/health`,
`/`, and `/auth/status`. Run it after scaling changes; exit code is non-zero
when the error rate exceeds the budget.

### 20.6 Redis

Redis is the shared state for the broker and job store. In production use a
managed, persistent Redis (Railway Redis, ElastiCache, Upstash) — not the
ephemeral in-memory default — so job status survives restarts.

---

## 21. Related Documentation

- [`docs/architecture/commercial_underwriting_pipeline.html`](./commercial_underwriting_pipeline.html) — commercial-lines system design deep dive (layered architecture, decision logic, data handling, reliability)
- [`docs/ZERO_TOKEN_ARCHITECTURE.md`](../ZERO_TOKEN_ARCHITECTURE.md) — ZTA specification
- [`docs/README.md`](../README.md) — platform guide (README)
- [`docs/ops/LAUNCH_CHECKLIST.md`](../ops/LAUNCH_CHECKLIST.md) — production launch checklist
- [`docs/product/PRODUCT_GUIDE.md`](../product/PRODUCT_GUIDE.md) — product guide
- [`docs/ML_TRAINING_DATA.md`](../ML_TRAINING_DATA.md) — ML training data
