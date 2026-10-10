# Model and AI validation standards

- Author: @model-risk
- Date: 2026-10-09
- Status: Draft for review (@compliance)
- Applies to: predictive models, deterministic underwriting rules that change a quote or a decline, and LLM components. A rules engine is a model.

Nothing here is a production approval. No component is approved.

## Risk tiers

| Tier | What it is | Examples in this program | Production use |
|---|---|---|---|
| 1 — Decisioning | Output can change premium, terms, quote issuance, or decline | Auto-quote gates; any future loss model; extraction fields that feed a quote without human edit | Full validation below. @model-risk written approval required. |
| 2 — Material support | Output is shown to the underwriter as a recommendation or a prefill they are expected to rely on | Extraction with citations; triage referral reason; decline **draft** | Full validation, except the benchmark may be an underwriter gold set instead of a challenger model. |
| 3 — Low materiality | Cannot change the file outcome and is not the system of record | Search, formatting, internal summarization that is not stored as the recommendation | Document the limitation. Spot-check. No production approval letter. |

@head-of-underwriting's auto-quote band is **Tier 1**, even though it is deterministic. The decline draft is **Tier 2** only because a human must send it. If that human step is removed, it becomes Tier 1 and is not approved under these standards.

LLM extraction is **Tier 1** if a quoted TIV, construction, loss count, or class code can reach the rater without a human confirming the field. It is Tier 2 if the workbench requires confirmation of every required field in `required-fields.md`.

## Evidence by tier

| Evidence | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Purpose, inputs, outputs, owner, version | Required | Required | Required |
| Conceptual soundness (why this design) | Required | Required | Short note |
| Data lineage and quality checks | Required | Required | — |
| Performance vs a stated baseline | Required | Required on a gold set | — |
| Stability (time split or segment) | Required for statistical models | Required if volume allows | — |
| Limitations and where it fails | Required | Required | Required |
| Explainability: reason a reviewer can check | Required | Required | — |
| Benchmark or challenger | Required for statistical models | Underwriter gold set | — |
| LLM: labeled eval set, hallucination rate, citation accuracy | Required if LLM | Required | Spot-check |
| Prompt / rule / model version control | Required | Required | Version id stored |
| Failure behavior (timeout, low confidence, conflict) | Required: must not quote | Required: must not present a blank as zero | Defined |
| Monitoring metrics and revalidation date | Required | Required | Owner named |
| Fairness review | Required if the output changes who is quoted or declined | Required | — |
| Compliance permitted-use | Required | Required | — |

## Minimum bars (I will not negotiate these away in a pilot)

- Tier 1 and Tier 2: no production use while any **High** finding is open.
- Extraction: every required field either has a source span or is shown as missing. A missing loss run must not be stored as zero losses.
- Auto-quote: each gate maps to a field with a source. "Looks in appetite" is not a gate.
- Held-out evaluation before shadow mode. A demo on five files is not validation.
- Synthetic-only evals are not sufficient for Tier 1. Tier 1 needs historical files or a justified exception I have not granted.
- Revalidation at least annually, and on any prompt, rule, or training-data change.

## Finding scale

| Rating | Meaning |
|---|---|
| High | Can cause a wrong quote, a wrong decline, or an unauditable decision. Blocks production. |
| Medium | Material weakness with a workaround. Blocks scale-up past shadow, not necessarily a desk pilot of Tier 2. |
| Low | Documentation or hygiene. Does not block. |

## What is not approved by writing this document

- Any architecture (T-006 is not written).
- The appetite numbers. I do not own them. I do own whether the implemented rules match the approved matrix.
- Use of a vendor model. Vendor paper is not validation.

## Addendum — D-004 (2026-10-09)

The auto-quote path is withdrawn. There is no Tier 1 quote engine in this product.

| Component | Tier while D-004 holds | Becomes Tier 1 if |
|---|---|---|
| Intake | 3 | — |
| Extraction with citations | 2 | A cited value reaches a carrier package with no underwriter confirm |
| Missing-info request | 2 | The request text declines or binds |
| Hazard points and reason codes | 2 | The score declines, binds, prices, or selects the carrier |
| Carrier A/B/C match | 2 | A match submits without the workbench decision |
| Workbench decision | Not a model | — |

Still not approved for production. T-006 is cancelled; do not build that architecture.

## Inventory

No models in production. Candidates: extraction (Tier 2), completeness request (Tier 2), hazard points (Tier 2, not built), carrier match rules (Tier 2, draft). Auto-quote rules are not a candidate.
