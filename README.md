# InsureFlow AI

Multi-agent AI underwriting system for commercial insurance submission analysis. Automates ingestion, risk analysis, fraud detection, compliance review, and underwriting decision-making through a LangGraph orchestrated pipeline of specialist AI agents with RAG knowledge retrieval.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Submission Pipeline                     │
├──────────────────────────────────────────────────────────┤
│  ACORD XML ─┐                                            │
│  Broker JSON─┤→ Classifier → Parser → Merger → Agents    │
│  Loss Run ───┤                    ↓                      │
│  SOV ────────┤              Reconciliation               │
│  Insp Report─┘                    ↓                      │
│                            LangGraph State Machine        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐│
│  │ Risk     │ │ Loss Run │ │Compliance│ │ Fraud Detect ││
│  │ Analyst  │ │ Analyst  │ │ Agent    │ │ Agent        ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘│
│       ↓            ↓            ↓             ↓          │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Supervisor Agent                    │    │
│  │        (Parallel orchestration + conflict res.)  │    │
│  └──────────────────────────────────────────────────┘    │
│       ↓                                                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │           UW Decision Agent                      │    │
│  └──────────────────────────────────────────────────┘    │
│       ↓                                                  │
│  Underwriting Memo (ACCEPT / REFER / DECLINE)            │
└──────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install
pip install -e .

# Run underwriting pipeline on example data
python cli.py agents examples/pacific_coast_acord.xml \
  examples/pacific_coast_broker_api.json \
  examples/pacific_coast_loss_run.md \
  examples/pacific_coast_inspection_report.md \
  examples/pacific_coast_sov.md

# Start MCP server (SSE on :8010)
python -m insureflow.mcp

# Run tests
python -m pytest tests/ -q
```

## Project Structure

```
insureflow/
├── agents/            # AI agents (ReAct loop, tools, supervisor)
│   ├── react_agent.py       # Base ReActAgent class
│   ├── risk_analyst.py      # Risk analysis specialist
│   ├── loss_run_analyst.py  # Loss run analysis specialist
│   ├── compliance_agent.py  # Compliance review specialist
│   ├── fraud_detection_agent.py  # Fraud detection specialist
│   ├── uw_decision_agent.py # Underwriting decision maker
│   └── supervisor.py        # Parallel orchestration + conflict resolution
├── graph/             # LangGraph state machine
│   ├── state.py             # PipelineState TypedDict
│   ├── nodes.py             # 17 graph nodes
│   └── builder.py           # Graph construction + routing
├── ingestion/         # Document parsers
│   ├── classifier.py        # Document type classifier
│   ├── acord_parser.py      # ACORD XML parser
│   ├── json_parser.py       # Broker API JSON parser
│   ├── loss_run_parser.py   # Loss run markdown parser
│   ├── sov_parser.py        # Schedule of Values parser
│   └── report_extractor.py  # Inspection report extractor
├── rag/               # RAG knowledge layer
│   ├── guidelines.py        # Underwriting guidelines (18 docs)
│   ├── vector_store.py      # In-memory TF-IDF + pgvector backends
│   └── rag_agent.py         # RAG query agent
├── llm/               # LLM client (OpenAI, Anthropic, vLLM)
├── mcp/               # MCP server (9 tools, 3 resources, 1 prompt)
├── models/            # Pydantic data models
├── entities/          # Entity deduplication
├── provenance/        # Data provenance tracking
├── reconciliation/    # Data reconciliation engine
├── audit/             # Audit logging
├── storage/           # Storage backends
├── config.py          # Configuration
└── pipeline.py        # UnderwritingPipeline orchestrator
evaluations/           # MLOps evaluation suite
├── ragas_eval.py      # Ragas faithfulness/relevancy/precision/recall
├── giskard_scan.py    # Giskard bias/robustness/safety scan
├── golden_dataset.py  # 3 golden ACORD test cases
└── report.py          # Consolidated evaluation report
examples/              # Example submission data (3 carriers)
tests/                 # 153 pytest tests
scripts/               # DB init scripts
```

## Key Features

- **5 Specialist AI Agents** — RiskAnalyst, LossRunAnalyst, Compliance, FraudDetection, UWDecision — each with ReAct loop and deterministic fallback (no API key required)
- **LangGraph State Machine** — 17 nodes, conditional routing, retry loop, human-in-the-loop checkpoint
- **RAG Knowledge Layer** — 18 underwriting guidelines, char-n-gram TF-IDF in-memory or pgvector for production
- **Deterministic Fallback** — All agents work without any LLM API key
- **Dual-Model Tiers** — Cheap model for specialists, expensive for underwriting decisions
- **Entity Deduplication** — Char-n-gram embedding with 0.85 cosine threshold
- **MCP Server** — FastMCP with SSE transport, connectable from Claude Desktop, Cursor, VS Code
- **Data Provenance** — Track every extracted field back to source document
- **Evaluation Suite** — Ragas metrics + Giskard bias/robustness scan + consolidated report
- **Containerized** — Docker + docker-compose with pgvector

## Configuration

Set via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | API key for LLM provider |
| `LLM_PROVIDER` | `openai` | Provider: openai, anthropic, vllm |
| `CHEAP_MODEL` | `gpt-4o-mini` | Model for specialist agents |
| `EXPENSIVE_MODEL` | `gpt-4o` | Model for UW decisions |
| `ANTHROPIC_API_KEY` | — | Claude API key (for anthropic provider) |
| `DATABASE_URL` | — | PostgreSQL + pgvector connection string |

## Docker

```bash
docker-compose up --build
```

Starts the API on `:8000` and pgvector on `:5432`.

## Evaluation

```bash
# Run Ragas evaluation (requires OPENAI_API_KEY for LLM judge)
python -m evaluations.ragas_eval

# Run Giskard scan
python -m evaluations.giskard_scan

# Generate consolidated report
python -m evaluations.report
```

## License

MIT
