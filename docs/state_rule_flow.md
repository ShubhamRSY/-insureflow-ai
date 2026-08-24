# State-Rule Flow: How the Selected State Acts on a Pipeline Run

**Confirmed:** selecting a state (e.g., Connecticut) in the state selector sets a
state-scoped rule set that is applied automatically at every subsequent stage of
the session's pipeline run. The state is not metadata on the job record only —
it is threaded through the pipeline and consumed by rating, underwriting,
compliance, surplus-lines, and document generation.

## Flow diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ UI StateSelector.jsx → useStateContext                                      │
│   POST /pipeline/run { state_code: "CT", life_product_id, life_coverage_id }│
└──────────────┬──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ api/main.py · SubmissionRequest.state_code                                  │
│   stored on job record AND passed to InsurancePipeline.run(state_code=…)    │
└──────────────┬──────────────────────────────────────────────────────────────┘
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ insurance/pipeline.py · run(state_code)                                     │
│                                                                             │
│  STAGE 1  Document extraction / classification                              │
│           state_code captured; blob-detected state kept only as fallback    │
│                                                                             │
│  STAGE 2  Regulatory pre-check                                              │
│           StateRegulatoryEngine.evaluate(issue_state) → disclosures,        │
│           free-look, rate-filing model, surplus-lines tax                   │
│           issue_state = state_code || detect_state(locations)               │
│                                                                             │
│  STAGE 3  Underwriting (medical / financial / reinsurance)                  │
│           knockout questions + thresholds from the manual; unisex states    │
│           (MT) force unisex mortality inside the rating path                │
│                                                                             │
│  STAGE 4  Rating                                                            │
│           rating.quote(state_override=state_code)                           │
│             ├ state_relativities[issue_state] factor                        │
│             ├ unisex_states override sex factor                             │
│             └ state-of-filing gate (IL pilot exhibit vs issue state)        │
│               → eligible=False when the state has no filed rates            │
│                                                                             │
│  STAGE 5  LOB/Product/Coverage logic path (life/lobs/*)                     │
│           each product module applies ITS OWN per-state rule table          │
│           (free-look days, exam thresholds, disclosures) INSIDE its         │
│         logic and stamps `state_rules_applied` into quote metadata          │
│                                                                             │
│  STAGE 6  Surplus lines classification                                      │
│           classify_surplus_lines(state=state_code …)                        │
│                                                                             │
│  STAGE 7  Summary + report                                                  │
│           summary["issue_state"], summary["state_compliance"]               │
│           memo/report documents render issue-state compliance               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Stage-by-stage contract

| Stage | Consumer | What the state changes |
|---|---|---|
| Selection | `SubmissionRequest.state_code` (`api/main.py`) | Explicit issue state wins over any document-derived state |
| Compliance pre-check | `StateRegulatoryEngine.evaluate` (`regulatory/state_rules.py`) | Rate-filing model, required disclosures, free-look period, surplus-lines tax |
| Underwriting | `underwrite_life`, `evaluate_life_financial`, LOB modules | Unisex states force unisex mortality; per-product exam thresholds are state-adjusted |
| Rating | `rate_life` via `rating.quote(state_override=…)` | `state_relativities` factor; state-of-filing gate flips `eligible` when no filed rates exist for that state |
| LOB logic paths | `life/lobs/<lob>/<product>.py` | Per-product × per-state rule table merged into the decision and stamped as `state_rules_applied` |
| Surplus lines | `classify_surplus_lines(state=…)` | Admitted/non-admitted determination is state-specific |
| Documents | report/quote generators | Issue state surfaced in summary and compliance sections |

## Guarantees

1. **One issue state per run.** `state_code` from the selector overrides document detection everywhere; detection is fallback-only.
2. **State rules are applied inside each logic path**, not bolted on afterward — Term Life + Connecticut executes term-life rules *and* CT rules together in one pass (see `life/lobs/architecture.md`).
3. **Traceability.** Every quote carries `metadata["issue_state"]` and every LOB-path quote carries `metadata["state_rules_applied"]` so an auditor can see exactly which state rules fired.
4. **Fail-closed filing gate.** If the selected state has no filed rates for the product family, the quote is marked ineligible with the reason on the record — it never silently prices on another state's exhibit as if it were filed.

> Note: per-state values shipped in `STATE_RULES` tables (free-look days, exam
> thresholds) are carrier/pilot configuration defaults for this build and must be
> validated against DOI filings before production use in any given state.
