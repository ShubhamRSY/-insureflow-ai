# P-070 — as built (T-118)

- Built by @ai-engineer-assistant (main session, OpenCode) under **D-122** (the user typed `approve change P-070` on 2026-10-21). Proposal: `deliverables/ai-engineer/proposal-P-070.md`. Cause: `deliverables/ai-engineer/analysis/T-117-H1-H2-cause.md`.
- Branch `fix-t117` (from `ai-team`). Nothing on `main` was touched. **This is not a production approval**; @model-risk checks the result, and the T-027 veto stands until its conditions are met.
- Development data only. No hold-out file was used to develop or to verify this change; no model call was made; no published score was rewritten.

## What was built

All of it is in `underwriting_pipeline/ai/prepare.py` (no prompt, no model, no scorer). The app layer (`underwriting_pipeline/app/workbench.py`, `underwriting_pipeline/app/package.py`) shows the new results in plain words.

1. **The stated cooking line is carried into the operations value** — `complete_cooking_line()`. When the cited document states `Cooking operations: None` (the `OPS_NO_COOK` vocabulary) and the merged value does not carry it, the value ends `; no cooking` and the cooking line is added as a second cited part, so the card shows both lines. The flag then clears because the value carries what the source states, not because a rule was switched off. A document that mentions cooking equipment (fryer, grill, hood, kitchen, oven, …) is left alone.
2. **Square feet: the words the documents use** — `AREA_WORD` ("square footage", beside the words already known) and `AREA_HEADERS` (`sq_ft` beside `sqft`, `sf`, …). `_square_feet()` now finds the second number and the existing rule raises the `square_feet` conflict, each side keeping the whole cited line or the whole schedule row.
3. **Sales: a rating figure stated differently** — `_sales_figures()` / `apply_sales_conflicts()`. The labelled line (`Annual sales | Gross sales | Gross revenue | Revenue | Sales`) and an amount near `sales | revenue | turnover` in free text are read with `amount_value()`. When two documents state different amounts, an open `sales_or_payroll` conflict is raised with both sides and the merged sales value is emptied with the reason *"the documents state different sales figures"*; the file is held. A rounding is not silently accepted (the underwriter resolves it on the card).
4. **An occupancy count: suites and units** — `_count_figures()` / `apply_count_conflicts()`. The count of `suite(s) | unit(s) | apartment(s) | tenant(s)` (number words one to twelve and digits) is read from the operations value and from every other document. Different counts are an open conflict on the topic of the noun (`suite_count`, `unit_count`, `apartment_count`, `tenant_count`). The operations value is **kept** — only the count is in dispute — and the file is held because an open conflict clears `complete`.
5. **The topics read as English** — `prepare.PLAIN`: "square footage", "sales or payroll", "suite count", "unit count", "apartment count", "tenant count". The topic appears in plain words on the card, in the resolve form, in the send refusal and in the producer request.

### Refinements over the proposal (as recorded in the cause write-up)

- The count topic follows the noun that was counted (`suite_count`, `unit_count`, `apartment_count`, `tenant_count`) instead of one `suite_count`, so a unit count is not filed under suites.
- The sales rule reads only documents (not the merged value) for the comparison, so the merged value cannot fight itself.
- The count conflict keeps the operations value; only a *scored* field in dispute is emptied (the sales value).

## Self-checks (development files only)

- New dev set `simulation/inbox-dev/document_conflicts/` (SUB-290–295), built by `deliverables/producer/build_document_conflicts_dev.py`; dev notes and manifest in `deliverables/senior-underwriter/gold-set-document_conflicts/dev/` (the proposal wrote the folder as `deliverables/gold-set-document_conflicts/dev/`; the house convention `deliverables/senior-underwriter/gold-set-<name>/` was used).
  - SUB-290 square footage 2800 (application) vs 3150 (`sq_ft` column) → open conflict, held.
  - SUB-291 two office suites vs three → open conflict, the operations value kept, held.
  - SUB-292 $412,000 vs "about 540k in sales" → open conflict, the sales value emptied with the reason, held.
  - SUB-293 `Cooking operations: None` → the value ends `; no cooking`, both lines cited, no flag.
  - SUB-294 the documents agree → no conflict, the file stays complete.
  - SUB-295 "about 540k" against $540,000 → no conflict (the same amount is not a disagreement).
- `python underwriting_pipeline/ai/prepare.py` → `prepare ok` (the in-place self-check reads the dev set and asserts the three conflicts, the cooking completion, the emptied sales value and the plain request labels).
- `python underwriting_pipeline/app/workbench.py` → `workbench ok`; `python underwriting_pipeline/app/package.py` → `package ok`; `python underwriting_pipeline/models/points.py` → `points ok` (the model file is unchanged).
- `pytest tests/pipeline -q -p no:cacheprovider` → **43 passed**, 19 warnings.
- `python underwriting_pipeline/ai/eval_holdout_v11.py --self-check` → `eval_holdout_v11 self-check ok` (the frozen scorer is unchanged).
- `python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-117-plan.json` → `PASS: 0 failure(s), 3 info, 32 files` (the frozen gold is unchanged).
- `pyright` on the three changed files: 49 diagnostics, the same 8 / 6 / 35 as before the change (no new finding).

## Request equality — zero changed requests

`llm_extract.py` is not touched, so `PROMPT_VERSION` (`759b3e6bc9b2`), the document list and `cache_key` do not move. Checked by computing `llm_extract.key_for(docs)` for the same folder from the pre-change tree and from this tree:

| | prompt version | cache key | files |
|---|---|---|---|
| `ai-team` (pre-change) | `759b3e6bc9b2` | `ab7653c9a5b040138b67778f5ef1a72a5c8071aea9fc445129ccd1e43ca61372` | application.md, email.md, loss-runs.md, schedule.csv |
| `fix-t117` (this change) | `759b3e6bc9b2` | `ab7653c9a5b040138b67778f5ef1a72a5c8071aea9fc445129ccd1e43ca61372` | application.md, email.md, loss-runs.md, schedule.csv |

**Zero changed requests.** The cached replies stay valid, no token was spent, and the request-equality baseline on `pilot-integration` is unchanged (it is not re-baselined).

## D-065 (the workbench)

- The card shows the completed operations value with **both** cited lines (`Operations: …` + `Cooking operations: None`), the three conflict topics in plain words with each side in words (value, file, cited text — not a JSON blob), the emptied sales value with the reason *"the documents state different sales figures"*, the resolve form for each open conflict, and the send refusal *"No send: open conflict on square footage, sales or payroll, suite count: the underwriter must choose or enter the value on the card (logged with this run) before a send."*
- One "What's new" line (2026-10-21, T-118, D-122).
- Screenshots (a temp copy, D-069): `deliverables/software-engineer/screenshots/T-118-document-conflicts.png` and `T-118-no-cooking-cited.png`. The page is rendered by `deliverables/software-engineer/T-118-shot.py` from synthetic cards; the real workbench page, the decision log and the outboxes were not written.
- @senior-underwriter reviews the UI part, High findings only: `deliverables/senior-underwriter/T-118-ui-review.md`.

## Not included

- The scorer: the frozen v11 is not touched and the published T-117 scores are not rewritten (D-020). The M-class readings and the suite-count topic need a v-next scorer, frozen before the next gold.
- The loss-run layout lint (memo H3), the equipment case of H1, and the golden rule "no cooking is not a scored item for non-food classes" (@head-of-underwriting's call).
- A tolerance band for a rounded sales figure: a separate P-### if the pilot shows it is too noisy.

## Expected effect (an expectation, not a score)

- **H1**: the four operations values carry the stated cooking line → the v11 checklist reads `no cooking` → operations would read **16/20** under the frozen v11. The 18/20 floor still needs the v-next scorer for the M-class readings.
- **H2**: the three planted disagreements become open conflicts and the three files are held. The pipeline behaviour (an open conflict, both sides, a hold) is what production use needs; the v11 field vocabulary has no word for a suite count, so a v-next scorer is needed to credit that topic.
- No published score moves.

## P-071 (D-123), 2026-10-23: fix for @model-risk T-118 High H1

Built in the Claude Code session (not OpenCode).
- `prepare.py`: `complete_cooking_line` adds "; no cooking" only when `states_cooking()` is false for **every** document in the folder. `states_cooking` reads `OPS_COOK_EQUIPMENT`, `HAZARD_TERMS` and `COOK_EQUIP`. `COOK_EQUIP` is the workbench equipment list moved to `prepare.py`; `workbench.EQUIP` is now `prepare.COOK_EQUIP` (same tuple). A negated mention also counts, so the worst case is the pre-P-070 flag.
- Dev file SUB-296 (`Cooking operations: None` + email "flat-top griddle and a wok station", published Carrier A no-claims run). Self-check, end to end through `process_submission` (model call stubbed, answers grounded by `llm_extract.accept_field`): SUB-296 is `complete — review pending` with operations flagged; the same file with a neutral email is `complete` with "; no cooking". A mutation check (the P-070 rule put back) makes SUB-296 `complete` with "; no cooking", so the check catches H1.
- Changed behaviour on dev: **SUB-293** (email "There is no kitchen or any cooking on site") no longer gets "; no cooking"; the flag stays. Dev gold and the T-118 screenshot updated to match.
- Unchanged: `llm_extract.py`, `PROMPT_VERSION` 759b3e6bc9b2, no frozen file, no hold-out file.
- Checks: prepare ok, llm gate ok, intake ok, package ok, workbench ok, points ok; frozen v11 self-check ok; frozen lint SELF-CHECK PASS; `pytest tests/pipeline` 43 passed; pyright no new error in the changed lines.
- Seen, not changed (outside P-071): the SUB-296 flag reads "operations may be missing: no cooking", while the email states a griddle and a wok, and the card's cooking-equipment check reads "not stated" because it reads only the application.

## P-072 (D-124), 2026-10-23: the "; no cooking" add removed

Built in the Claude Code session. Supersedes P-070 change 1 and P-071.
- `prepare.py`: `complete_cooking_line`, `states_cooking`, `COOK_EQUIP`, `OPS_COOKING_NONE`, `OPS_NO_COOK_ANSWER`, `OPS_COOK_EQUIPMENT` and the call in `process_submission` are removed. The operations value is never extended; `check_operations` keeps flagging "operations may be missing: no cooking" as before P-070.
- `workbench.py`: `EQUIP` is back in `workbench.py`, unchanged from the branch base (the P-071 move is reverted; no refactor kept). "What's new": the P-070 line no longer claims the cooking add; one P-072 line.
- Self-checks: dev SUB-293 and SUB-296 keep the operations flag with no "no cooking"; SUB-296 end to end through `process_submission` (model stubbed, answers grounded by `llm_extract.accept_field`) with 8 emails (as built, a neutral email, and the six @model-risk re-check sentences): none `complete`, none with "no cooking", flag present in each.
- Dev gold: SUB-293–296 are `complete — review pending` (the operations flag stays).
- Checks: prepare ok, llm gate ok, intake ok, package ok, workbench ok, points ok; frozen v11 self-check ok; frozen lint SELF-CHECK PASS; `pytest tests/pipeline` 43 passed; `PROMPT_VERSION` 759b3e6bc9b2; no frozen file changed; `llm_extract.py` unchanged.
- Screenshots `T-118-document-conflicts.png` and `T-118-no-cooking-cited.png` re-taken with headless Chromium on a temp render (D-069).
- The H1 scoring gap (the scorer cannot read "no cooking" from an answer that leaves it out) goes to the v-next scorer.
