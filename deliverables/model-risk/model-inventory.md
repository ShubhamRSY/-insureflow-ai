# Model inventory

- Author: @model-risk
- Date: 2026-10-13
- Source: D-031 item 5 ("Also create deliverables/model-risk/model-inventory.md") and D-036.
- Status: **a record, not an approval.** Every component below is **not approved for production** unless this file says otherwise in its own line. Nothing here is a production approval; nothing here lifts a veto unless the entry says the veto is lifted and names it.

## How to read this inventory

- **Tier** is the risk tier from `deliverables/model-risk/validation-standards.md` as amended for D-004. The standing table there:

  | Component | Tier while D-004 holds | Becomes Tier 1 if |
  |---|---|---|
  | Intake | 3 | — |
  | Extraction with citations | 2 | A cited value reaches a carrier package with no underwriter confirm |
  | Missing-info request | 2 | The request text declines or binds |
  | Hazard points and reason codes | 2 | The score declines, binds, prices, or selects the carrier |
  | Carrier A/B/C match | 2 | A match submits without the workbench decision |
  | Workbench decision | Not a model | — |

- **No production use while any High finding is open** (validation-standards, minimum bars). A veto is lifted only by the role that holds it.
- The label-scanner extractor is retired and no longer a component in use (D-010, D-036).
- **Score quoting.** No score file is edited by this inventory (D-025). Every quoted score carries the wording set for it below. For scores published before the new hold-out the standing line is: **"8 of 9 fields scored; loss runs = date only"** (D-033 item 5). The new 20-file hold-out (T-093) carries its own label, **"9 of 9 extracted fields scored; claims not read; loss runs = date only"** (D-039). A null that matches a missing gold line is never a hit. A failed model call is counted apart and is never a miss (D-021).

---

## C-1 — LLM extractor

- **Owner:** @ai-engineer-assistant (`underwriting_pipeline/ai/llm_extract.py`, `sources.py`, `prepare.py`).
- **Purpose:** read a submission folder (typed PDF, Excel, email body, scanned image, Spanish) and return structured JSON with a citation and a confidence on each field.
- **Tier:** **Tier 2** (extraction with citations). Becomes **Tier 1** if a cited value reaches a carrier package with no underwriter confirm.
- **Version id:** prompt version `82be09bd42f7` (sha256 of the system prompt, first 12 hex) · model `openai/gpt-oss-120b` · temperature `0`. The cache key holds the prompt version, the model name, the host, the temperature, and the file contents (P-014).
- **Status:** **Not approved for production.** Failed-call handling: see the T-059 veto below.
- **Open vetoes:**
  - **T-027 — production veto on extraction (@model-risk), OPEN.** Citation does not prove the value; the scan gate ignores digits; unread content is not flagged; no hold-out score exists for the current prompt and gate. Resolved by P-016 (T-080) (a) no value fallback, value inside the quoted span; (b) gate on the lower of model and OCR confidence, OCR from the cited words; (c) every file and page read or listed as needs human — then the new 20-file hold-out, gold first, committed, scored once (T-091 to T-093). Lifting the veto is @model-risk's call.
  - **T-059 — veto on the failed-call status gate (@model-risk), OPEN.** A failed or empty call must be status `extraction_failed` with the error, must block every send and draft for every actor including the user, and must be counted apart from a miss in every scorer. Criteria 3 and 4 fail today. Resolved by P-010: T-070 (`prepare.py`, `eval_holdout.py`) and T-071 (`package.py`, `workbench.py`), then the T-059 reviewers look again; @model-risk says whether its veto is resolved.
- **What it may not do:**
  - May not feed a rater or a carrier package as a Tier 1 input; it is Tier 2 only while the workbench requires confirmation of every required field (`required-fields.md`).
  - May not invent, guess, or fall back to a value outside the quoted span.
  - May not read a loss run as zero claims; a missing loss run is not zero losses.
  - May not treat a failed or empty call as empty data; it may not send, decline, bind, or set a price.
- **Score files that belong to it** (in `deliverables/ai-engineer/evals/`): `SUB-027-036-holdout.md` (no `.json`); `SUB-037-046-holdout.json/.md`; `SUB-047-056-holdout.json/.md`; `SUB-057-066-holdout.json/.md`; `SUB-067-076-holdout.json/.md`; `SUB-077-086-holdout.json/.md` with `-original` and `-rerun` copies and `SUB-077-086-original-vs-rerun.md`; `SUB-017-036-dev-rerun.json/.md`; `regression-SUB-017-076.json` and `regression-SUB-017-076-before-P002-P003b.json` with `regression-SUB-017-076.md`. The matching per-set memos are `deliverables/model-risk/holdout-SUB-027-036.md` through `holdout-SUB-077-086.md`.
- **Rule for quoting them:** every one carries **"8 of 9 fields scored; loss runs = date only"** (D-033 item 5). The `SUB-077-086` rerun is **not quoted as an improvement**; the `-original` score is the official baseline (D-026). A failed call is counted apart and is not a miss (D-021). The new hold-out (T-093) uses its own D-039 label.

## C-2 — Point score (hazard points and reason codes)

- **Owner:** @data-scientist (`underwriting_pipeline/models/points.py`, `deliverables/data-scientist/reason-codes.md`).
- **Purpose:** rank hazard and produce reason codes for the underwriter. Fixed points, not a fit.
- **Tier:** **Tier 2** (hazard points and reason codes). Becomes **Tier 1** if the score declines, binds, prices, or selects the carrier.
- **Version id:** **none recorded.** `points.py` has no version constant. The decision-log tag `ai_version()` = `<LLM_MODEL>+rules-d015` (`underwriting_pipeline/app/workbench.py:103-105`) is **not** a component version and was found wrong (T-021 High-1). P-015 (T-084), if approved, stores the points version on each decision row.
- **Status:** **Not approved for production.**
- **Open vetoes:**
  - **T-017 — production veto on the point score (@model-risk), OPEN.** Criterion 1 (interpretable, underwriter can override) not met.
  - **T-017 — fairness and contestability veto (@responsible-ai), OPEN.** Same criterion 1.
  - **T-017 — @actuary, REJECT**, criterion 1 not met.
  - Resolved by P-015 (T-084): remove loss-history points and show "Loss history: not scored"; failed/incomplete files show "Not scored" with reason; decision rows save points, codes, and points version; cooking points from stated hazards only; underwriter can mark a code wrong with a logged reason. Then @actuary, @model-risk, and @responsible-ai look again. Each veto is lifted only by its holder.
- **What it may not do:**
  - May not decline, bind, price, or select a carrier; it may not change the file outcome.
  - It is a recommendation the underwriter overrides; it may not be described as validated or as a production model.
- **Score files that belong to it:** **none.** There is no hold-out score for the point score.
- **Rule for quoting it:** no numeric score may be quoted for it. The T-017 review record is the only assessment.

## C-3 — Carrier match (Carrier A/B/C)

- **Owner:** rules @head-of-underwriting (`deliverables/head-of-underwriting/carrier-match.md`); code `route()` @software-engineer (`underwriting_pipeline/app/workbench.py:38-52`) and the in-appetite check in `underwriting_pipeline/app/package.py:48`.
- **Purpose:** recommend a placeholder carrier for a submission.
- **Tier:** **Tier 2** (Carrier A/B/C match). Becomes **Tier 1** if a match submits without the workbench decision.
- **Version id:** **D-041 class lists and caps** (2026-10-13): Carrier A offices/dry retail/light wholesale/low-hazard personal services, ≤ $5,000,000; Carrier B restaurants/food service and light contractors (roofing excluded), ≤ $2,000,000, "3 clean years not checked"; Carrier C broader fallback ≤ $10,000,000; `no_match` classes listed; caps inclusive. The code `route()` does **not** yet match this (T-083).
- **Status:** **Not approved for production.**
- **Open vetoes:** **none open on this component.** @head-of-underwriting's T-082 is IN_REVIEW; that is a review, not a veto.
- **What it may not do:**
  - It is a recommendation only; the underwriter chooses.
  - `no_match` is not a decline to the producer and no class is an automatic decline.
  - May not submit anything without the workbench decision; it may not bind or set a price.
- **Score files that belong to it:** **none.** There is no numeric eval for the match.
- **Rule for quoting it:** no score may be quoted. The only record is the class list in `carrier-match.md` (D-041) and the code in T-083.

---

## R-1 — Label-scanner extractor (RETIRED under D-010)

- **Owner (historical):** @ai-engineer (retired handle).
- **Component:** the pattern/label-matching extractor replaced by the model-based extractor in D-010.
- **Tier:** **retired — not in use.** No tier applies.
- **Status:** **RETIRED under D-010 (2026-10-09).** Closed under D-036 as "scored, component not accepted — retired under D-010". It is never a component in use and is never cited for the current extractor.
- **Score file:** `deliverables/ai-engineer/evals/SUB-017-026-holdout.json/.md` (the hold-out on SUB-017 through SUB-026). The earlier `SUB-007-016-field-accuracy.json/.md` is also from before D-010 and is not the current extractor.
- **Rule for quoting it (D-036, exact):** the SUB-017 through SUB-026 score is quoted **only** as **"0 of 7 value fields; other hits came from empty output"**, and it is **never cited for the current extractor**. No other number from it may be used.
- **Veto on it:** the T-026 production veto (@model-risk) was on the extractor as scored. **It is lifted — see below — because the component is retired, not because it passed validation.**

---

## T-026 veto on the retired extractor — lifted (2026-10-13)

@model-risk **lifts** the T-026 production veto on the label-scanner extractor scored on SUB-017 through SUB-026.

- Why: the component is **retired under D-010** and is not in production. A production veto blocks production use; with the component retired there is no production use to block. The inventory entry above now exists, which is the condition D-036 set for this call.
- What this does **not** do: it does not accept the component, does not approve anything for production, and does not lift the T-027 or T-059 vetoes on the current extractor. The score stays quarantined and is quoted only as "0 of 7 value fields; other hits came from empty output", never for the current extractor (D-036).
- No published score file was edited or recounted (D-025).

## Inventory summary

| Id | Component | Owner | Tier | Version id | Open vetoes | In production |
|---|---|---|---|---|---|---|
| C-1 | LLM extractor | @ai-engineer-assistant | 2 | `82be09bd42f7` + `openai/gpt-oss-120b` | T-027, T-059 | No |
| C-2 | Point score | @data-scientist | 2 | none recorded | T-017 (@model-risk, @responsible-ai, @actuary) | No |
| C-3 | Carrier match | @head-of-underwriting / @software-engineer | 2 | D-041 | none | No |
| R-1 | Label-scanner extractor | — | retired | — | T-026 **lifted** | No (retired) |

**No component is approved for production.** This inventory approves nothing.
