# Underwriting Decision Policy — ACCEPT / REFER / DECLINE / CONDITIONAL_ACCEPT

## The tiers

| Tier | Trigger | Where |
|---|---|---|
| **DECLINE** (hard) | Claim frequency ≥ `HARD_DECLINE_CLAIM_FREQUENCY_PER_YEAR` (10/yr), **or** a critical moral-hazard finding | [`uw_decision_agent.py`](../src/insureflow/agents/uw_decision_agent.py) `_build_recommendation()`; [`insurance/pipeline.py`](../src/insureflow/insurance/pipeline.py) `~1329` (moral hazard) |
| **REFER** | Any CRITICAL finding, **or** any HIGH finding, **or** aggregate risk score ≥ `REFER_AGGREGATE_SCORE_THRESHOLD` (0.7) | `uw_decision_agent.py` `_build_recommendation()` |
| **CONDITIONAL_ACCEPT** | Only MODERATE findings present (no HIGH/CRITICAL) | same |
| **ACCEPT** | No findings requiring conditions | same |

Aggregate risk score is the mean of per-finding severity weights across every
specialist agent's findings (`SEVERITY_WEIGHTS` — critical=1.0, high=0.75,
moderate=0.5, low=0.2).

All thresholds are named constants at the top of `uw_decision_agent.py` — that
file is the single edit point; nothing here needs a doc update to also change
the code, but change the doc when you change the meaning of a tier.

## Why this is conservative

The bar for a straight-through ACCEPT is deliberately high — a single HIGH
finding routes to a human, and REFER is the default outcome for most real
submissions. This is intentional, not a bug: it mirrors the "underwriter as
judge of people" doctrine already written into
[`moral_hazard_agent.py`](../src/insureflow/agents/moral_hazard_agent.py) —
when in doubt, a licensed underwriter looks at it rather than the system
guessing. DECLINE is narrow on purpose: only claim-frequency and moral-hazard
gates can force it outright. Every other combination of findings, however bad,
routes to REFER — a human always has the last word on declining coverage.

## What's deliberately NOT built yet

- **Auto-bind tier** — a fully clean file still requires no conditions to hit
  ACCEPT, but there's no separate "small enough / clean enough to skip human
  review entirely" fast lane. Adding one is a commercial risk-appetite
  decision, not something to infer from the code.
- **Per-state / per-product threshold overrides** — thresholds are global
  today. The life LOB files already have a `merge_state_rules()` pattern
  (`life/lobs/base.py`) that a future per-state override could reuse.
- **Formal audit/explainability export** — `audit.log(...)` calls already
  exist throughout `insurance/pipeline.py`, but there's no queryable
  "why did this decision fire" report product built on top of them yet.

## Non-determinism note

Specialist agents (fraud, risk analyst, loss-run, compliance) can
optionally consult an LLM for additional findings. See the circuit-breaker in
[`react_agent.py`](../src/insureflow/agents/react_agent.py) — once an LLM
call fails for a given process, every agent using that same provider/key
falls back to the deterministic path for the rest of the process, so a given
server process gives the same decision for the same submission every time.
