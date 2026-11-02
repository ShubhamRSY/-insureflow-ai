# T-117 H1 and H2 — cause write-up

- Author: @ai-engineer-assistant. Branch `fix-t117` (from `ai-team` 53a7252). Written before any change, on the code under test `8d605ac`.
- Read-only analysis of the published T-117 run (SUB-238–269, run `20261021T112723-44537`, prompt `759b3e6bc9b2`). No model call, no score file touched, no hold-out file touched, no workbench page touched.

## How this was checked

| What | Where |
|---|---|
| The model's own saved replies | `underwriting_pipeline/cache/T-117-live/extractions/*.json` (20 files, one run), mapped to submissions by the order in `deliverables/ai-engineer/evals/SUB-238-269-run-record.md` |
| The published marks | `deliverables/ai-engineer/evals/SUB-238-269-holdout-v11.json` (`checks.conflict`, `checks.operations`, `checks.status`, `system_status`) |
| The documents | `simulation/inbox/SUB-2xx/` (read only) |
| The code | `underwriting_pipeline/ai/{llm_extract,prepare,eval_gold,eval_holdout_v11}.py` |

## H1 — the stated cooking line is dropped by the model, and the pipeline only flags it

### What the model returned

All four files say the same thing in the application (`Cooking operations: None`, `application.md:23`) and the model's saved reply leaves it out:

| File | Model's operations value | Model's quote | Application line 23 |
|---|---|---|---|
| SUB-248 | `Lessor of professional office building, six suites` | `Operations: Lessor of professional office building, six suites` | `Cooking operations: None` |
| SUB-250 | `Tax preparation office (second floor); cell phone repair and retail accessories (ground floor)` | `Operations: Tax preparation office (second floor); …` | `Cooking operations: None` |
| SUB-254 | `Wholesale electrical supplies to contractors, counter pickup` | `Operations: Wholesale electrical supplies to contractors, counter pickup` | `Cooking operations: None` |
| SUB-257 | `Thrift retail, used clothing and household goods, donations in the back` | `Thrift store in Brownsville, clothing and household goods, donations in the back.` | `Cooking operations: None` |

The quote is the "Operations:" line only, so the cooking line was never read. On SUB-251 and SUB-255 the same model and the same prompt kept `no cooking` (`Cooking operations: Cheese boards only, no cooking`, `Cooking operations: None, shop heaters only`), so this is inconsistent behaviour, not a wording rule.

### Two causes, in order

**Cause 1 — the model.** The prompt already asks for exactly this: `llm_extract.py:40` — *"Also read the application's 'Cooking operations', 'Hood & extinguishing system' and 'Line of business' lines, not only the 'Operations' line: keep every item they state (equipment such as a snack warmer or kilns, 'no gas', 'None' as no cooking, hood inspection dates, 'no liquor'), and quote those lines as extra parts."* The model did not comply on 4 of 20 files. The instruction is not missing; the compliance is not reliable.

**Cause 2 — the pipeline never completes the value.** `check_operations` (`prepare.py:922-938`) knows exactly what is missing: `ops_missing` (`prepare.py:905-915`) with the rule `OPS_NO_COOK` (`prepare.py:849`, source `cooking(?: operations)?\s*:\s*(?:none|n/?a|nil)`, answer `no (?:commercial )?cooking|no kitchen|not cook\w*|no food|none`) returns the item `no cooking` for all four files. What it then does is only set a reason, `needs_review=True` and a lower confidence (`prepare.py:934-938`). **Nothing ever writes the stated line into the value.** So the operations value is incomplete by construction, the flag is the only repair, and the field stays un-automated.

Published effect: `checks.operations = miss` on 248, 250, 254, 257; the metric `operations.automated = false` on the same four; the flag is on the card (`operations may be missing: no cooking`).

### What a fix must do

Complete the value from the **cited** source (the model's own source document, its "Cooking operations" line), keep the citation (the cooking line as a second cited part, so the card shows where the added words come from), and let the existing flag clear because the value now carries what the source states. No model call, no prompt change.

## H2 — no conflict was raised, because the model reported none and the deterministic rules do not cover these three shapes

Every one of the 20 saved replies carries `"conflicts": []`. The published marks: `checks.conflict = miss` on SUB-249, SUB-252 and SUB-257. On SUB-257 the pipeline's own status was **`complete — review pending`** with the GL base shown as `412000`, no conflict and no hold — the memo's worst case.

### SUB-249 — square footage 2,800 vs 3,150: the rule exists, its vocabulary is short

- The documents: `application.md:18` `Square footage: 2,800`; `schedule.csv:1` header `…,sq_ft,…` with the row value `3150`; `email.md:5` *"Schedule has the square footage from the appraisal, the application I think is the old number."* The email names the disagreement and the model still reported no conflict.
- The rule that should have caught it exists: `apply_document_rules` (`prepare.py:803-821`) raises a `square_feet` conflict when `_square_feet` (`prepare.py:692-718`) finds two distinct areas.
- `_square_feet` reads an area in three ways only: a number **before** `square feet|sq. ft.|sqft|sf` (`prepare.py:695`); a line **labelled** `Square feet:|Sq. ft.:|Sqft:|Sf:` (`prepare.py:700`); a table column whose header cell is exactly `sqft` or `sf` (`prepare.py:709`).
- Neither side matches: the application says **"Square footage"**, and the rule knows "square feet"; the schedule's column is **`sq_ft`**, and the rule knows `sqft`/`sf`. The rule never sees 3,150.
- I ran the rule on the real documents: `_square_feet(texts)` returns `[]` for SUB-249, SUB-257 and SUB-248.

So the one deterministic conflict rule in the pipeline never saw the second number. The gap is the words the documents use.

### SUB-252 — two office suites vs three: nothing compares a count across documents

- The documents: `application.md:13` `Operations: Pub with full bar on ground floor; two office suites on second floor`; `email.md:5` *"Top floor is two office suites, the owner's business and an accountant. Email says three suites, the application says two, the third is a storage room that I think counts."*
- The pipeline has no rule that compares a **count** across documents. `agrees()` (`prepare.py:148-156`) compares two values of the same field; `extract()` (`prepare.py:180-213`) reads labelled lines only; nothing reads a count out of free-text email.
- The model took the application's side and reported no conflict.

### SUB-257 — sales $412,000 vs "about 540k": nothing reads a rating figure out of another document

- The documents: `application.md:15` `Annual sales: $412,000`; `email.md:5` *"Last year was about 540k in sales, the application says 412k because the accountant used the tax form number."*
- `_square_feet` covers square feet only. There is no rule that reads an amount near `sales|revenue|turnover` from a second document, so 540,000 is never compared with 412,000.
- The model took the application's number and reported no conflict → the card shows the GL base `$412,000`, status `complete — review pending`, no conflict, no hold.
- The published marks hide it: `checks.sales = hit` (the scorer compares the value with the gold's `412000`) and the silent-error counter never sees a conflict that was never raised.

### Why the misses are invisible in the score

- `checks.conflict` is `miss` for the three files: the scorer asks whether the gold's conflict sides are stored in the open conflicts (`sides_stored`, `eval_holdout_v11.py:755-765`, used at `eval_holdout_v11.py:924-930`). No conflict, no sides, `miss`.
- A conflicting **scored** field must be nulled with both sides stored (`prepare.py:1111-1114`); that is what the scorer's topic rule expects (`eval_holdout_v11.py:947-954`: sides stored **and** the value null → `flagged`; sides stored and the value kept → `miss`). So for SUB-257 the sales value has to go null for the conflict to count.
- A conflict on a topic that is **not** one of the nine fields (square feet, a suite count) must not blank a value; the file is held anyway because an open conflict sets `complete = False` (`prepare.py:1145-1151`).
- The scorer's own field vocabulary is narrow: `expected_conflict_fields` (`eval_gold.py:74-85`) knows `premises_address`, `sales_or_payroll`, `square_feet` and nothing else. A suite-count conflict cannot be credited by the frozen v11; that is a scorer-version question, not a pipeline question.

### What a fix must do

Raise an **open** conflict (both sides, each with its value, its file and its cited text) and hold the file when two documents state a **rating or scored figure** differently: square feet, sales, TIV, year built, construction, and an occupancy count (suites/units). Null the scored field when the field itself is in dispute; keep the value when only the count is. Never resolve one by itself.

## What the fix must not do

- No prompt change, no model change, no new token. A change in `prepare.py` leaves `PROMPT_VERSION` and the documents untouched, so `cache_key` (`llm_extract.py:72-74`) does not move: **the model request stays byte-identical** and the cached replies stay valid.
- No change to the frozen scorer v11, no change to the published score files, no change to the hold-out gold or to the hold-out files, no change to the published T-117 numbers.
- No conflict that is auto-resolved: every side stays `resolution: unresolved`, `resolved_value: null`; the underwriter resolves it on the card.
- No value that is not in a document: every side is a cited string from a named file, and the added cooking words are the cited line's own wording.

## What the change is expected to do (an expectation, not a score)

- **H1**: the four operations values carry the stated cooking line → the v11 checklist reads `no cooking` → operations would read **16/20** under the frozen v11 (the three M-class readings stay misses; SUB-254 also keeps its M-class cause). The floor 18/20 still needs the new scorer version for the M-class readings — that is not part of this change.
- **H2**: SUB-249 → a `square_feet` conflict; SUB-257 → a `sales_or_payroll` conflict with the sales value nulled; SUB-252 → a suite-count conflict on its own topic with the operations value kept. All three files are held (`status: incomplete`).
- Under the frozen v11 the SUB-249 and SUB-257 conflict marks would be credited (`flagged`) and the SUB-252 mark could still be missed (the scorer's side-needle set for "office suites: 2 vs 3" needs both counts in the conflict data, which the fix can store; a v-next scorer is still needed for the topic vocabulary). Either way the pipeline behaviour — an open conflict and a hold — is what a production use needs.
- No effect on any published score: T-117 stays as published, and the hold-out is not used to develop or to verify this fix.

## Next step

`deliverables/ai-engineer/proposal-P-070.md` — the change itself, with the dev self-checks and the self-check shapes. It needs the user's `approve change P-070` before any code under `underwriting_pipeline/ai/` is touched (D-017).
