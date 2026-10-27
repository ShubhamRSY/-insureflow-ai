# P-070 — Carry the stated cooking line into operations, and make a disagreement between documents an open conflict and a hold

- Author: @ai-engineer-assistant (cause), orchestrator (main session) (this proposal). **Not approved, not built.** Evidence: `deliverables/ai-engineer/analysis/T-117-H1-H2-cause.md`. Development data only. Not a production approval; @model-risk can still block it, and @model-risk must check the result before any use beyond development.
- Raised because T-117 (@model-risk, `deliverables/model-risk/T-027-memo-T-117.md`) carries two High findings that only the pipeline can close: **H1** the stated cooking line is dropped on 4 of 20 files; **H2** 0 of 3 planted document conflicts surfaced. The memo asks for "an approved P-### extractor change" (H1) and "a fix so that a disagreement between documents on a scored or rating field becomes an open conflict and a hold", built on dev with self-checks shaped like 249, 252 and 257 (H2).

## Problem

**H1.** On SUB-248, 250, 254 and 257 the application says `Cooking operations: None` (`application.md:23`) and the model's operations value leaves it out. The prompt already asks for the line (`llm_extract.py:40`); the model complies on 16 of 20 files and not on these 4. The pipeline then only flags it: `check_operations` (`prepare.py:922-938`) computes the missing item `no cooking` (`ops_missing` + `OPS_NO_COOK`, `prepare.py:905-915`, `prepare.py:849`) and writes a reason, never the value. The value stays incomplete by construction.

**H2.** All 20 saved replies carry `"conflicts": []`. The three planted disagreements were missed for three different reasons:

| File | The disagreement | Why nothing caught it |
|---|---|---|
| SUB-249 | square footage 2,800 (`application.md:18`) vs 3,150 (`schedule.csv`, column `sq_ft`) | the deterministic rule exists (`prepare.py:803-821`) but its readers only know "square feet", `sqft` and `sf` (`prepare.py:695,700,709`); the documents say "Square footage" and `sq_ft`, so the rule never saw the second number |
| SUB-252 | two office suites (`application.md:13`) vs three (`email.md:5`) | nothing compares a **count** across documents; `agrees()` only compares two values of one field (`prepare.py:148-156`) |
| SUB-257 | `Annual sales: $412,000` (`application.md:15`) vs "about 540k in sales" (`email.md:5`) | nothing reads a rating figure out of a second document; the card showed the GL base `$412,000`, status `complete — review pending`, no conflict, no hold |

An open conflict already holds a file (`prepare.py:1145-1151`), and a conflicting scored field is already nulled with both sides stored (`prepare.py:1111-1114`). What is missing is the **detection**.

## Change (all inside `underwriting_pipeline/ai/prepare.py`, no prompt, no model)

1. **The stated cooking line is carried into the operations value.** When the cited source document has a `Cooking operations:` line that states none (`None`, `n/a`, `nil` — the vocabulary `OPS_NO_COOK` already uses) and the merged value does not carry it, the value becomes `<value>; no cooking` and the cooking line is added as a **second cited part** (the same multi-part citation the model already produces: `llm_extract.py:533-542` joins the cited parts into the quote). `check_operations` then finds nothing missing, so the flag clears because the value now carries what the source states, not because a rule was switched off. If the value already carries it, nothing changes. The wording `no cooking` is the reading the operations gold rule and the v11 scorer use for that line, and the gold's own answer for SUB-248 is `Lessor of professional office building, six suites; no cooking`; the cited text shows the source line, so the underwriter sees what was read.
2. **Square feet: the words the documents use.** `_square_feet` (`prepare.py:692-718`) learns `square footage` as a label and `sq_ft` as a table column, beside the words it knows. The existing rule (`prepare.py:803-821`) then raises the `square_feet` conflict. Each side keeps the whole cited line (the labelled line, or the schedule row), not only the number, so the underwriter sees which row.
3. **Sales: a rating figure stated differently.** A new rule reads the sales amount from every document — the labelled `Annual sales|Gross sales|Gross revenue|Revenue|Sales` line, and an amount near the words `sales|revenue|turnover` in free text (`about 540k in sales`, `sales of $412,000`) — using `amount_value` (`prepare.py:102`). When two documents state different amounts, an open `sales_or_payroll` conflict is raised with both sides, and the merged sales value is nulled with `needs_review`, exactly as the pipeline already does for a field in dispute (`prepare.py:1111-1114`). The file is held.
4. **An occupancy count: suites and units.** A new rule reads the count of `suite(s)|unit(s)|apartment(s)|tenant(s)` from the operations value (the application's side) and from the other documents (number words one to twelve and digits). When the counts differ, an open conflict on the topic `suite_count` is raised with both sides. The operations value is **kept** — the description is not in dispute, only the count — and the file is held because an open conflict sets `complete = False`. `suite_count` is not one of the nine fields, so nothing is nulled.
5. **The topics read as English.** A conflict topic appears raw in the producer request (`prepare.py:278-291`) and on the card. The three topics read as "square footage", "sales or payroll" and "suite count".

## Self-checks (development files only, no model call, no hold-out file)

- A new dev set `simulation/inbox-dev/document_conflicts/` (SUB-290–295), built by `deliverables/producer/build_document_conflicts_dev.py`, with dev notes in `deliverables/gold-set-document_conflicts/dev/` and a manifest, in the style of the `commercial_property` dev set. The shapes are taken from the memo's description of 249, 252 and 257; the files are new and are not copies of the hold-out.
  - **SUB-290** (like 249): an application with `Square footage: 2,800` and a schedule whose `sq_ft` column says `3,150` → a `square_feet` conflict with both sides, the file held, the operations value untouched.
  - **SUB-291** (like 252): an application whose operations say "two office suites" and an email that says "three suites" → a `suite_count` conflict, the operations value kept, the file held.
  - **SUB-292** (like 257): an application with `Annual sales: $412,000` and an email with "about 540k in sales" → a `sales_or_payroll` conflict, the sales value nulled, the file held.
  - **SUB-293** (negative): an application with `Cooking operations: None` whose operations answer already says "no cooking" → the value is not touched, no words are added twice.
  - **SUB-294** (negative): an application and an email that agree on square feet, sales and suites → no conflict at all, the file stays complete.
  - **SUB-295** (negative): a free-text rounded sales figure ("about 400k" against `$412,000`) → the rule raises the conflict and holds the file; the underwriter resolves it on the card. A rounding is not silently accepted (see Risk).
- The rules are also self-checked in place, in the `prepare.py` self-check block (`python underwriting_pipeline/ai/prepare.py` → `prepare ok`): the cooking completion, the two square-feet wordings, the two sales readings, the suite count, and the three negative cases.
- `python underwriting_pipeline/ai/eval_holdout_v11.py --self-check` and the frozen lint stay green. `pytest tests/pipeline -q` stays green.

## D-065 (the workbench)

- The card shows the completed operations value with **both** cited lines, and the new conflict topics with their two sides in plain words.
- One "What's new" line (date, task id, decision number).
- A Playwright screenshot under `deliverables/software-engineer/screenshots/`, taken on a temp copy (D-069).
- @senior-underwriter reviews the UI part, High findings only.

## Expected effect (an expectation, not a score)

- **H1**: the four operations values carry the stated cooking line → the v11 checklist reads `no cooking` → operations would read **16/20** under the frozen v11 (the three M-class readings stay misses and SUB-254 keeps its M-class cause). The floor 18/20 still needs the new scorer version for the M-class readings, which is not part of this change.
- **H2**: the three planted disagreements become open conflicts and the three files are held. Under the frozen v11 the conflict mark is credited for SUB-249 and SUB-257; for SUB-252 the frozen scorer's side-needle set needs both counts in the conflict data, which this change stores, but the v11 field vocabulary has no word for a suite count, so a v-next scorer (frozen before the next gold) is needed for that topic. The pipeline behaviour — an open conflict, both sides, a hold — is what production use needs.
- **No request changes.** Nothing in `llm_extract.py` changes, so `PROMPT_VERSION`, the documents and `cache_key` (`llm_extract.py:72-74`) do not move: the model request is byte-identical, the cached replies stay valid, no new token is spent, and the request-equality baseline is unchanged (**zero changed requests**). The request-equality test on `pilot-integration` is run as a check, not re-baselined.
- No effect on any published score. T-117 stays as published and the hold-out is not used to develop or to verify this change.

## Not included

- The scorer. The frozen v11 is not touched and the published T-117 scores are not rewritten (D-020). The M-class readings ("to &lt;customer&gt;" is not a class, a copied side remark is not an extra class, "no … food service" means cooking=none) and the suite-count topic vocabulary are a v-next scorer, frozen before the next gold — @senior-test-engineer with @model-risk.
- The loss-run layout lint (memo H3), which is a build-side rule, not a pipeline change.
- The equipment case of H1 ("Cooking operations: Slicer, grill, hood" missing from the value): a wider rule with more risk; it goes to the backlog.
- The golden rule "no cooking is not a scored item for non-food classes" — that is @head-of-underwriting's call, and it is the alternative to change 1, not an addition to it.

## Risk

- The cooking completion writes words the source does not use ("no cooking" for "Cooking operations: None"). It is a cited, deterministic reading of a stated line, not a guess, and the cited text is on the card; @model-risk judges whether the wording is acceptable.
- A free-text sales figure that is a rounding rather than a different figure will hold the file. The file is not declined and nothing is auto-decided; the underwriter resolves it on the card. If the pilot shows this is too noisy, a tolerance band is a separate P-###.
- A suite count in free text can be a different kind of unit ("two suites" vs "two tenants"); the noun list is fixed (`suite|unit|apartment|tenant`) and a count that appears in only one document is never a conflict.
- The square-feet change is a vocabulary change: it can only add a conflict where two documents state two areas, which is the case the memo calls a production risk.

To approve, the user types: `approve change P-070`.
