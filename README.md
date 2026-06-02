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

**No API key needed** — all agents fall back to deterministic rule-based analysis.

## Docker

```bash
docker-compose up --build
# API at :8000 · pgvector at :5432
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
