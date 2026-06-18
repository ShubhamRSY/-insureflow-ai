# InsureFlow AI

> Multi-agent AI underwriting system for commercial insurance submission analysis.

An end-to-end system that ingests, parses, and analyzes commercial insurance submissions (ACORD XML, broker JSON, loss runs, schedules of values, inspection reports) through a LangGraph-orchestrated pipeline of specialist AI agents with RAG knowledge retrieval and deterministic fallback.

## What It Does

Takes messy multi-document insurance submissions and produces an underwriting memo with ACCEPT / REFER / DECLINE recommendation:

```
Submission → Classify → Parse → Merge → Reconcile → RAG → Agents → UW Memo
```

### Example Output

```
═══════════════════════════════════════════════════════════════
                   UNDERWRITING MEMO
═══════════════════════════════════════════════════════════════
 Pacific Coast Distributors, Inc.          UW-2026-001
───────────────────────────────────────────────────────────────
 Risk Analyst        ✅ High hazard occupancy (cold storage w/
                       ammonia refrigeration); $43.5M TIV
 Loss Run Analyst    ✅ 6 claims in 5 yrs, $487K total incurred;
                       3.7% loss ratio — favorable
 Compliance Agent    ⚠️ California Prop 65, OSHA, EPA ammonia
 Fraud Detection     ✅ No red flags detected
───────────────────────────────────────────────────────────────
 RECOMMENDATION: REFER — ammonia refrigeration requires
                  engineer-reviewed sprinkler compliance
═══════════════════════════════════════════════════════════════
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   SUBMISSION INGESTION                       │
│  ACORD XML ──┐                                              │
│  Broker JSON ─┤──► Classifier ──► 7 Parsers ──► Merger     │
│  Loss Run ────┤                                              │
│  SOV ─────────┤                                              │
│  Insp Report ─┘                                              │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                 LANGGRAPH STATE MACHINE                      │
│                                                              │
│  17 Nodes · Conditional Routing · Retry Loop                 │
│  Human-in-the-Loop Checkpoint · MemorySaver                  │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │   Risk   │ │ Loss Run │ │Compliance│ │    Fraud     │    │
│  │ Analyst  │ │ Analyst  │ │  Agent   │ │ Detection    │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘    │
│       ▼            ▼            ▼              ▼            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              SUPERVISOR AGENT                         │    │
│  │   Parallel execution · LLM conflict resolution        │    │
│  └──────────────────────┬───────────────────────────────┘    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            UW DECISION AGENT                          │    │
│  │   Synthesizes all findings → ACCEPT/REFER/DECLINE     │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## What's Inside

### 5 Specialist AI Agents — Each with ReAct Loop

| Agent | Role | Tools |
|-------|------|-------|
| **RiskAnalystAgent** | Evaluates occupancy, construction, protection, TIV adequacy | Loss ratio, protection class, sprinkler, year built |
| **LossRunAnalystAgent** | Analyzes claim frequency, severity, trends | Claim frequency, severity (mean/max), large loss ratio |
| **ComplianceAgent** | Checks regulatory and guideline compliance | Litigation ratio |
| **FraudDetectionAgent** | Flags submission inconsistencies and red flags | Non-disclosed comparison |
| **UWDecisionAgent** | Makes final accept/refer/decline with rationale | All 16 tools |

Each agent has a **deterministic fallback** — works with zero API keys by running rule-based analysis when no LLM is configured.

### LangGraph State Machine

17 nodes wired with conditional routing:

```
ingest → classify → parse_* (5 nodes) → merge_structured →
extract_agents (retry ×3) → build_provenance → reconcile →
check_human_review → (human_review | query_rag) → synthesize → audit
```

- `extract_agents` retries up to 3 times on failure
- `check_human_review` routes to `human_review` (wait) or `query_rag` (continue)
- `MemorySaver` checkpointer for state persistence

### 7 Document Parsers

| Parser | Input | Output |
|--------|-------|--------|
| ACORD | XML (`<ACORD>`) | Named insured, broker, coverages, locations |
| Broker JSON | JSON API payload | Policy period, financials, risk profile |
| Loss Run | Markdown with **bold** fields | Claims with dates, amounts, statuses, causes |
| SOV | Pipe tables or key:value | Buildings, BPP, inventory, fleet schedules |
| Inspection Report | Free text/markdown | Construction, protection, occupancy, recommendations |
| Classifier | Auto-detects document type | Routing to correct parser |
| Supplemental | Generic text | Extracted chunks with metadata |

### RAG Knowledge Layer

18 underwriting guidelines across 8 categories with dual backends:

- **In-Memory** (default) — Char-n-gram TF-IDF in 512-dimensional space, zero dependencies
- **pgvector** (production) — PostgreSQL with pgvector extension, 1536-d OpenAI embeddings

### Entity Deduplication

Char-n-gram embedding with 0.85 cosine similarity threshold — resolves duplicate named insureds, brokers, and locations across documents.

### MCP Server

FastMCP server with SSE transport on `:8010`:

- **9 Tools**: loss ratio, claim frequency, severity, large loss ratio, litigation ratio, RAG query, risk assessment, pipeline run, pipeline-from-file
- **3 Resources**: all guidelines, by category, search endpoint
- **1 Prompt**: `underwriting_review` template for structured analysis

Compatible with Claude Desktop, Cursor, VS Code, and any MCP client.

### MLOps Evaluation Suite

- **Ragas** — Faithfulness, answer relevancy, context precision, context recall
- **Giskard** — Bias, robustness, safety scanning
- **Consolidated Report** — Custom scorer + Ragas + Giskard → verdict: DEPLOYMENT-READY / CONDITIONAL PASS / NEEDS IMPROVEMENT
- **Score**: 88.9% precision, 96.3% recall, 3.7% hallucination (3 golden cases)

## Quick Start

```bash
# Install
pip install -e .

# Run the full pipeline on example data
python cli.py agents \
  examples/pacific_coast_acord.xml \
  examples/pacific_coast_broker_api.json \
  examples/pacific_coast_loss_run.md \
  examples/pacific_coast_inspection_report.md \
  examples/pacific_coast_sov.md

# Start the MCP server
python -m insureflow.mcp

# Run tests (153 passing)
python -m pytest tests/ -q

# Run evaluation report
python -m evaluations.runner
```

## Project Structure

```
src/
└── insureflow/
    ├── agents/              # AI agents with ReAct loop
    │   ├── react_agent.py        # Base ReActAgent class
    │   ├── supervisor.py         # Parallel orchestration
    │   ├── risk_analyst.py       # Risk analysis
    │   ├── loss_run_analyst.py   # Loss run analysis
    │   ├── compliance_agent.py   # Compliance review
    │   ├── fraud_detection_agent.py  # Fraud detection
    │   ├── uw_decision_agent.py  # UW decision maker
    │   ├── tools.py             # 16 underwriting tools
    │   └── rag_agent.py         # PG-vector RAG agent
    ├── graph/               # LangGraph state machine
    │   ├── state.py              # PipelineState TypedDict
    │   ├── nodes.py              # 17 graph nodes
    │   └── builder.py            # Graph construction
    ├── ingestion/           # Document parsers
    │   ├── classifier.py         # Document type classifier
    │   ├── acord_parser.py       # ACORD XML parser
    │   ├── json_parser.py        # Broker JSON parser
    │   ├── loss_run_parser.py    # Loss run parser
    │   ├── sov_parser.py         # Schedule of Values parser
    │   └── report_extractor.py   # Inspection report parser
    ├── rag/                 # RAG knowledge layer
    │   ├── guidelines.py         # 18 underwriting guidelines
    │   ├── vector_store.py       # In-memory + pgvector
    │   └── rag_agent.py          # RAG query agent
    ├── llm/                 # LLM client (OpenAI, Anthropic, vLLM)
    ├── mcp/                 # MCP server (FastMCP, SSE)
    ├── models/              # Pydantic models
    ├── entities/            # Entity deduplication
    ├── provenance/          # Data provenance
    ├── reconciliation/      # Data reconciliation
    ├── audit/               # Audit logging
    ├── storage/             # Storage backends
    ├── cli.py               # CLI entry point (typer)
    ├── api.py               # FastAPI server
    ├── pipeline.py          # UnderwritingPipeline orchestrator
    └── config.py            # Configuration
docs/
    └── architecture.md      # System design document
evaluations/                 # MLOps suite
    ├── ragas_eval.py        # Ragas metrics
    ├── giskard_scan.py      # Giskard scan
    ├── golden_dataset.py    # 3 golden test cases
    ├── scorer.py            # Custom scoring
    ├── runner.py            # Evaluation runner
    └── report.py            # Consolidated report
examples/                    # Example data (3 carriers)
scripts/
    └── init_db.sql          # Pgvector schema
tests/                       # 153 pytest tests
```

## Example Data

Three carrier submissions with multi-document bundles:

| Carrier | Files | Description |
|---------|-------|-------------|
| **Pacific Coast Distributors** | 5 files | Cold storage warehouse, $43.5M TIV, 6 claims, ammonia refrigeration |
| **Northwind Traders Manufacturing** | 4 files | Heavy machinery plant, $31.7M TIV, 3 claims, 40-year-old press |
| **Sample Co** | 2 files | Simple property risk, 64-line inspection report |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | API key for LLM |
| `LLM_PROVIDER` | `openai` | openai / anthropic / vllm |
| `CHEAP_MODEL` | `gpt-4o-mini` | Specialist agent model |
| `EXPENSIVE_MODEL` | `gpt-4o` | Supervisor/UW decision model |
| `ANTHROPIC_API_KEY` | — | Claude API key |
| `DATABASE_URL` | — | pgvector connection string |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker for Celery |
| `SECRET_KEY` | — | JWT signing secret (set in production) |

**No API key needed** — all agents fall back to deterministic rule-based analysis.

## Docker

```bash
docker-compose up --build
# API at :8000 · pgvector at :5432
```

## API Authentication

The FastAPI backend uses **JWT bearer tokens** with **Role-Based Access Control**:

### Roles

| Role | Permissions |
|------|-------------|
| `admin` | Create users, delete jobs, full access |
| `underwriter` | Run pipeline, view results |
| `viewer` | View job status and results only |

### Quick Start

```bash
# 1. Create the first admin (one-time setup)
curl -X POST http://localhost:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme", "role": "admin", "full_name": "Admin User"}'

# 2. Login to get a token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme"}'

# 3. Use the token for subsequent requests
TOKEN="eyJhbGciOi..."

curl -X POST http://localhost:8000/pipeline/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"acord_xml": "<?xml...", "bundle_id": "demo-1"}'

# 4. Create additional users (admin only)
curl -X POST http://localhost:8000/auth/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "uw1", "password": "securepass", "role": "underwriter", "full_name": "Jane UW"}'
```

## Key Design Decisions

- **ReAct over function-calling**: JSON thought-action-observation loop gives reasoning traceability and clean fallback
- **Dual-model tiers**: cheap model for 4 specialists (many ReAct turns), expensive for UW decision and supervisor
- **Deterministic fallback always present**: agents work without any LLM API key
- **LangGraph over linear orchestrator**: conditional routing, retry loop, human-in-the-loop checkpoint
- **MCP over custom API**: standardized protocol for any MCP client (Claude Desktop, Cursor, VS Code)
- **In-memory RAG fallback**: char-n-gram TF-IDF works immediately without PostgreSQL

## Tests

```bash
python -m pytest tests/ -q
# 153 passed
```

## Mortgage Underwriting Module

### Overview
A fully functional mortgage underwriting module that supports both residential and commercial mortgage loan packages. The module features LLM-powered agents, LangGraph orchestration with human-in-the-loop, fraud detection, PII redaction, and Celery async workers.

### Architecture

```asciidoc
Mortgage Documents → Classifier → Extractors → Reconciliation → Compliance → Specialist Agents → Decision
                                                                                    ↓
                                                                            Fraud Detection
                                                                                    ↓
                                                                          Human-in-the-Loop
                                                                                    ↓
                                                                          Audit Trail (persisted)
```

### Key Components

| Component | Description |
|-----------|-------------|
| `MortgagePipeline` | End-to-end linear pipeline for document processing |
| `MortgagePipelineGraph` | LangGraph orchestrated pipeline with human-in-the-loop |
| `MortgageSupervisorAgent` | Coordinates 5 specialist agents (income, credit, assets, collateral, fraud) |
| `MortgageFraudDetectionAgent` | Rule-based + LLM fraud red flags |
| `MortgageComplianceEngine` | 7+ bank compliance rules (credit score, DTI, LTV, DSCR, etc.) |
| `MortgageReconciliationEngine` | Cross-document validation (W-2 vs 1040, appraisal vs purchase) |
| `MortgageAuditLogger` | Full audit trail persisted to JSON |
| `PIIRedactor` | PII detection and redaction (SSN, DOB, bank accounts, etc.) |
| `MortgageLLMExtractor` | LLM-assisted extraction for messy/handwritten documents |
| `MortgageSubmissionLoader` | Document loading from files, directories, or API payloads |

### Document Types

The classifier supports 50+ mortgage document types including:
- Income: W-2, Pay Stubs, Tax Returns (1040, 1065), Profit & Loss, Schedule C
- Assets: Bank Statements, Investment Statements, Retirement (401k), Gift Letters
- Credit: Credit Reports, Credit Card Statements, Auto/Student Loan Statements
- Property: Appraisals (Residential & Commercial), Purchase Agreements, Surveys, Zoning
- Legal: Divorce Decrees, Corporate Governance, Operating Agreements
- Commercial: Rent Rolls, Leases, Estoppels, Operating Statements, Business Credit
- **Underwriting (NEW)**: Form 1003/URLA, Pre-Approval Letters, Flood Zone Certs, Title Commitments, VOE, VOD, Hazard Insurance Declarations, Property Tax Bills, UW Approval Memos, Closing Disclosures, Loan Estimates

### Supported Borrower Scenarios

#### Home Mortgage (6 scenarios)
| Borrower | Profile | Expected Decision |
|----------|---------|-------------------|
| John & Sarah Thompson | W-2 salaried, good credit (740+), 20% down | Approve |
| Maria Rodriguez | FTHB teacher, gift funds, 678 credit | Refer |
| David & Karen Chen | Jumbo refi, high earners, 800+ credit | Approve |
| James Wilson | Self-employed GC, 203k renovation, 645 credit | Suspend |
| Marcus & Imani Johnson | Young couple, USDA rural, first child | Refer |
| Lisa Patel | Divorcee cash-out refi, asset-heavy, 760 credit | Approve |

#### Commercial Mortgage (4 scenarios)
| Entity | Property Type | Loan Purpose |
|--------|---------------|--------------|
| Thompson Commercial Properties | Mixed-use retail/office | $2.3M acquisition |
| Oak Street Retail LLC | NNN Walgreens | $3.8M acquisition |
| Midwest Medical Plaza LLC | Medical office | $4.2M refinance |
| Riverbend Self Storage LLC | Self-storage (65k SF) | Construction loan |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mortgage/pipeline/run` | POST | Submit mortgage documents for processing |
| `/mortgage/pipeline/jobs` | GET | List all mortgage processing jobs |
| `/mortgage/pipeline/jobs/{job_id}` | GET | Get job status and results |
| `/mortgage/pipeline/jobs/{job_id}` | DELETE | Delete a mortgage job |
| `/mortgage/audit/{bundle_id}` | GET | Retrieve audit trail for a completed run |

### CLI Usage

```bash
# Process a directory of mortgage documents
insureflow mortgage --dir simulated_documents/home_mortgage

# Process per-borrower packages
insureflow mortgage-borrowers --dir simulated_documents/home_mortgage

# Process commercial mortgages
insureflow mortgage --dir simulated_documents/commercial_mortgage --product commercial

# Include detailed output
insureflow mortgage --dir simulated_documents/home_mortgage --detailed

# Disable LLM extraction
insureflow mortgage --dir simulated_documents/home_mortgage --no-llm
```

### LangGraph Pipeline

```python
from insureflow.mortgage.graph import build_mortgage_pipeline_graph

graph = build_mortgage_pipeline_graph()
state = {
    "raw_documents": [{"filename": "w2.txt", "content": "..."}],
    "bundle_id": "my-loan-001",
}
result = graph.run(state)
```

### Celery Async Processing

```bash
# Start mortgage worker
celery -A insureflow.tasks.celery_app worker -Q mortgage -l info

# Submit processing job
from insureflow.tasks.mortgage_tasks import run_mortgage_pipeline
result = run_mortgage_pipeline.delay(documents_data, bundle_id="my-loan")
```

### MCP Tools

The MCP server exposes 4 mortgage-specific tools:
- `assess_mortgage_risk` — evaluate credit/DTI/LTV/reserves
- `query_mortgage_guidelines` — search UW guidelines
- `run_mortgage_pipeline` — execute full pipeline
- `calculate_mortgage_metrics` — compute payment/affordability

### Simulated Document Portfolio

233 files across 10 borrower scenarios (1.8MB total) in the `simulated_documents/` directory for testing and development.
