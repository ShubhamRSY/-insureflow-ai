# P-059 (operations) and P-060 (scorer v7) as built — T-106a, T-106c, D-111

Author: @ai-engineer-assistant, 2026-10-18. Not a production approval; T-027 veto stands. No model call was made.

## P-059 what changed
- `llm_extract.py` SYSTEM prompt: one added sentence. The model must also read the "Cooking operations", "Hood & extinguishing system" and "Line of business" lines and keep their items (equipment, "no gas", "None" = no cooking, hood dates, "no liquor"), quoting those lines as extra parts (the multi-part quote of P-048 d already exists). Prompt version `b025802c0dfa` -> `759b3e6bc9b2` (model-inventory.md updated).
- `prepare.py` whole-document check:
  - `OPS_EXTRA`: two new word-list items, "gas" (no gas, gas-fired, gas fryers/range/oven/kiln/roaster, LPG, propane) and "no cooking" (`Cooking operations: None / n/a`).
  - `ops_line_missing()`: for each Cooking-operations clause (split on , ; .) every 4+ letter word (first 5 letters, numbers left out) must be in the answer; the Hood line's inspection date must be in the answer; Line-of-business only its "no ..." clauses. Hood-system clauses inside the cooking line are not read clause by clause.
  - `check_operations` now uses both (`ops_missing_all`). A hit sets needs_review, caps confidence below 0.75, and names the items in the reason ("operations may be missing: ..."). Never a silent value.
- Existing prepare self-check: three expected reason lists were extended (new items), nothing else loosened. `prepare.py` self-check passes.
- `workbench.py`: one "What's new" line (2026-10-18, T-106a, D-111). No other UI change: the flag text already shows the reason.

## Why the old check missed SUB-180, 201, 204
Code and published mismatch file only (the three documents were not opened). The check (P-056 f) reads the whole cited document, but only for items in `OPS_ITEMS`, a fixed word list. Each of the three dropped items was not in that list:
- SUB-180 "no gas": no "gas" item. The answer was a clean copy of the Operations line, so nothing flagged.
- SUB-201 "snack warmer": appliance words (warmer, kiln, oven except fryers/grill) are not items. The answer already had "kitchen" and "bar", so the existing items were satisfied.
- SUB-204 "no cooking": the source says "Cooking operations: None", and the "cooking" item only matches the literal "no cooking" or cooking words, so "None" was not read as a stated absence.
Second cause: the extractor copied only the "Operations:" line, so the answer looked complete to a word-list check. Fix: model asked to keep the sibling lines (prompt), and the check now compares the labeled lines clause by clause.

## P-059 self-checks (dev only)
- `underwriting_pipeline/ai/p059_dev_check.py` on the 38 dev applications (SUB-001-173) with a cooking or hood line, with answers built from the file itself: answer B (every stated line carried) is flagged in 0 of 38 (no false flags); answer A (Operations line only, the old failure) gains a new flagged item in 33 of 38, against 11 flagged by the old word list. 22 of the 33 gain only "no cooking" (None under cooking); the other 11 gain cooking equipment, gas and service dates.
- Synthetic cases modelled on the three misses are asserted in the prepare self-check (flagged when dropped, clean when carried).
- pyright 1.1.390: prepare.py + llm_extract.py 21 errors before and after (no new); eval_holdout_v7.py 1 error (`workbench` import), the same one v6 has; p059_dev_check.py clean.

## Cost to watch (not measured)
Operations answers that omit "no cooking" or the cooking-line items now go to "complete - review pending". With the old prompt, 33 of 38 dev files with such lines would flag; the new prompt should cut that, but only a live run shows how much. Status automation may fall if the model does not follow the new sentence.

## Calls needed (none made)
The worktree cache holds no saved replies for in-scope dev files, and the prompt hash is in the cache key, so every in-scope dev file needs a new call anyway. P-059 relevant dev files are SUB-127-173: 36 not manual-intake, 35 with a cooking line = 36 calls. Quick set (15 files, SUB-027-076): 5 calls (027, 042, 056, 071, 073); none of these has a cooking line, so it checks regressions only. Full 017-076: 20 calls. A dev v6-vs-v7 re-score was therefore not possible without calls; the old-prompt replies would not match the new prompt anyway.

## P-060 scorer v7 (T-106c)
`eval_holdout_v7.py` = v6 plus `loss_run_mark()`, nothing else:
- Gold "Expected loss run" starts "needs review" or "loss run found but no valued-as-of date": pipeline field needs_review -> hit; not flagged -> miss.
- Gold expects a date and the pipeline gives null + needs review -> not_credited (was miss). Null with no flag stays a miss.
- Everything else (missing gold, date match, wrong date) as v6, including a gold line that starts "missing".
- Self-check (`--self-check`, synthetic lines, no gold file, no model) passes and includes the v6 self-check. Dev gold carries the "Expected loss run" line (6 + 6 "needs review", 13 date-accepted, others), so the rule needs no T-104 file. v6 sha256 still starts 4bf1cd63; v2-v6 unchanged; no score file written.
- No dev v6-vs-v7 re-score: the dev gold before D-108 has no Scope lines (v6/v7 stop on them) and in-scope dev replies are not cached here.

## Open
- Screenshot T-106a not taken: the Playwright tool may only write under the main worktree, which this task must not touch. The What's new line is checked by rendering the page on a temp copy (line present).
- Live dev run of 36 calls (SUB-127-173) is needed to see the effect of the prompt sentence.
- @senior-underwriter UI check (High only) and @model-risk check owed.
