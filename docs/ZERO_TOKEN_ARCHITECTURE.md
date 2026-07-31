# Zero Token Architecture (ZTA)

> **The best token is the one you never had to generate.**

ZTA is the operating principle of this system: **use AI only when you must —
everything else, solve deterministically.** Every pipeline stage is routed
through a decision layer that asks *"can this be solved with code, rules, or a
trained ML model?"* before it ever considers spending a token.

## Why

LLM calls cost money, add latency, and — critically — add nondeterminism.
Underwriting decisions, pricing, and compliance artifacts should be
reproducible. ZTA keeps the deterministic core deterministic, and spends
tokens only on the tasks that genuinely need them:

| Task | Deterministic path | LLM only when… |
|---|---|---|
| Structured document parsing (ACORD) | Rule-based `ACORDParser` | never |
| Unstructured extraction | Regex/rule `InspectionReportExtractor` | regex coverage < threshold |
| Cross-document reconciliation | `ReconciliationEngine` | conflicts require reasoning |
| Risk scoring | Rule engine + trained ML models (`BaseMLModel`) | never |
| Pricing/rating | `InsuranceRatingEngine` (ISO-style) | never |
| UW decision | `UWDecisionAgent` + deterministic conflict resolution | conflicts can't be resolved by rules |
| Memo generation | Template built from agent findings | LLM available & budget allows |
| Property photo analysis | — | always (no deterministic substitute), or skipped |

## How it works

The `insureflow.zta` package provides:

- **`router.py`** — `ZeroTokenRouter.route(task, context)` classifies a task as
  `deterministic` (zero tokens), `llm`, `escalate_human`, or `skip`.
- **`models.py`** — task enums, `RouteContext` signals, `RouteResult`.
- **`report.py`** — `ZtaReporter` accumulates every routing decision per job and
  process-wide stats (`get_zta_stats()`).
- **`config.py`** — environment-driven settings (see below).

The insurance pipeline (`src/insureflow/insurance/pipeline.py`) wires the
router into vision, extraction, reconciliation, the supervisor memo, scoring,
pricing, and the final decision. Every run emits a `zta_report` in the result:

```json
"zta_report": {
  "policy": "Use AI only when you must. Everything else, solve deterministically.",
  "mode": "zta",
  "config": { "enabled": true, "strict": false, "memo_llm": true },
  "tasks": [
    {"task": "extract_unstructured", "decision": "deterministic",
     "reason": "regex/rule extraction captured 82% of expected fields",
     "tokens_saved_est": 1200, "tokens_used_est": 0}
  ],
  "totals": {"tasks": 8, "deterministic": 6, "llm": 1, "tokens_saved_est": 2400}
}
```

## Configuration (env vars)

| Variable | Default | Meaning |
|---|---|---|
| `ZTA_ENABLED` | `0` | Enable per-doc LLM enhancement when regex coverage is low. When off, the pipeline keeps its legacy all-or-nothing `use_llm` behaviour. |
| `ZTA_STRICT` | `0` | Hard mode — never call the LLM. Tasks that can't be solved deterministically are escalated to a human or skipped. |
| `ZTA_MEMO_LLM` | `0` | Allow LLM memo generation. |
| `ZTA_EXPECTED_FIELDS_RATIO` | `0.6` | Regex coverage ratio that counts as "good enough" for deterministic extraction. |
| `ZTA_MAX_LLM_TASKS_PER_JOB` | `5` | Per-job budget of LLM tasks. Beyond this, everything is escalated or resolved deterministically. |

## API

- `GET /api/zta/status` — process-wide routing stats + effective config.
- `POST /api/zta/route` — ask the router how a single task would be resolved
  (body: `task`, plus optional `text`, `regex_field_count`, `conflict_count`,
  `photo_count`, …).

## Token accounting

Every `RouteResult` carries `tokens_saved_est` (input tokens avoided by not
sending the raw text to an LLM) and `tokens_used_est` (what a decision *would*
cost). The reporter aggregates these per job and process-wide, so you can
answer "how many tokens did we not spend this quarter?" from `GET
/api/zta/status`.
