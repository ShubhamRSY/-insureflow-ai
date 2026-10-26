# P-074 as built (D-132)

Branch `p074` in `/Users/disastershubz/INSURANCE FLOW AI/insureflow-fix-t117`, from pilot-integration 3c50cd5. Not committed. Dev data only. Not a production approval; the T-027 veto stands. No model call: LLM_* unset (the stored-reply runs set a Groq host name, a placeholder non-key and a blocked `_post`, so a cache miss fails and never sends).

## Files changed
- `underwriting_pipeline/ai/llm_extract.py`: `HEDGE`, `UNITS`; `_AMOUNT`/`amount_value` read million, thousand, k, m, mm, b and the hedge words; `_NUM`; `_quote_amounts`, `_quote_numbers`, `is_approximate` (C); `accept_field` flags a hedged number ("approximate figure: <quote>", key `approximate`); conflict loop rewritten for D1-D5 (`_side`, `_open_conflict`, `same_value`; a stated side the gate rejected becomes a conflict side with `unverified: true` and the gate's reason). `SYSTEM` and `request_for` untouched: PROMPT_VERSION is still 759b3e6bc9b2.
- `underwriting_pipeline/ai/prepare.py`: `AMOUNT_TOKEN` uses the shared hedge/unit lists (P-070 sales rule reads "1.2 million"); `fuller` prefers an exact side over an approximate one; `_carry_flag` does not carry an approximate side's flag onto an exact side; the model-conflict loop never merges or `_typed_first`-resolves a conflict that has an unverified side; self-checks added (SUB-297, SUB-298 in `dev_cases`; end-to-end stubbed cases).
- `underwriting_pipeline/app/workbench.py`: `side_note`, shown on the Conflicts list and above the resolve form (plus "- not verified" / "- approximate" in the option text); "What's new" line 2026-10-24, P-074, D-132.
- `deliverables/producer/build_document_conflicts_dev.py`: SUB-297, SUB-298 (dev note in the docstring). Rebuilt: SUB-290-296 byte-identical; new `simulation/inbox-dev/document_conflicts/SUB-297/`, `SUB-298/`, gold `deliverables/senior-underwriter/gold-set-document_conflicts/dev/SUB-297.md`, `SUB-298.md`, manifest updated.
- `deliverables/software-engineer/P-074-shot.py` (renders synthetic SUB-297/SUB-298 cards to a temp folder) and `deliverables/software-engineer/screenshots/P-074.png`.
- Self-check expectation changed: llm_extract self-check (c) SUB-094 ("around 1.25 million" beside $1,050,000) used to expect one flagged figure and no conflict; it now expects the open conflict with the email side approximate. This is the SUB-345 shape and the point of P-074.

## Checks
- prepare ok; llm_extract self-check ("llm gate ok"); workbench ok; package ok; intake ok; points ok. All pass.
- `pytest tests/pipeline`: 86 passed, including `test_request_equality` (0 request changes; PROMPT_VERSION 759b3e6bc9b2).
- pyright gate: 96 errors, baseline 96, new 0.
- ruff F on `underwriting_pipeline/`: 5 findings (unused `datetime` import at llm_extract.py:396, unused `os` in smoke_readers.py, 3 Python 3.11 f-string syntax notes in workbench.py:790). The same 5 are present at HEAD; none new.
- `regression_dev.py --quick` (read-only, no --write, LLM_PACE_SECONDS=0, temp copy of the caches, stored replies only, 0 extraction_failed, all 15 replayed): before and after counts are identical (named_insured 5/10, operations 5/10, sales 4/10/1 flagged, construction 5/10, year_built 5/10, premises 5/10, tiv 5/10, loss_runs 5, conflict 4/8/2/1, status 2). No field hit count dropped. The reported hit/miss mix is the stored-reply mix from older prompt versions, not a regression.
- Replay of all 69 dev files that have a stored reply (SUB-001-126 and the dev sets), before (HEAD) against after: 67 identical, 2 changed (below).
- Hold-out SUB-345/348/349/350 replayed read-only from stored replies (no scoring, nothing written): SUB-345 complete - review pending -> incomplete (open conflict, intended); SUB-348, 349, 350 unchanged.

## Status changes, each intended (toward held or review only)
1. SUB-125 (dev): complete - review pending -> incomplete. The model raised an effective-date conflict (2027-08-01 vs 2027-09-01); the email side was rejected, the old code kept 2027-08-01 flagged and dropped the conflict (D1). Now an open conflict, the date empty, held.
2. SUB-098 (dev): status unchanged (incomplete). The sales conflict side "$1.45M" is now marked approximate (its quote is hedged); no value or status moved.
3. SUB-345 (hold-out, read only): see above.
4. SUB-297 (new): incomplete, open sales conflict, sales empty, not routed, not sendable (before the change: complete - review pending, one flagged figure, no conflict, from the stubbed SUB-345 reply). SUB-298 (new): D2, both sides unverified, plus the `~$1.2m` side read by the P-070 rule; open conflict, held; not "all values rejected".
5. SUB-290-296 (rule-level, `dev_cases` and end-to-end stubs): unchanged; SUB-293/296 still never gain "no cooking"; SUB-295 ("about 540k" with an exact 540000) still merges with no conflict and no review flag.

## Hedge-word count before adding hedge handling
- Stored replies (unique quotes in sales, TIV, year, area): about 6, around 10; nearly, almost, close to, circa, approx, "or so": 0.
- Dev source documents (text files, SUB-001-126 and inbox-dev, including the new SUB-297/298): about 22, around 11, roughly 2, "~" 1; the other extra words 0. million/thousand appear in SUB-003, 094, 297, 298.
- Files whose status changed by the hedge rule: none in the replay. The only flips come from Change A (SUB-125, SUB-345).

## Differs from the proposal
- Counts above differ from the proposal's (43/23/2/1/1): this count reads text documents only and excludes hold-out files; the stored-reply count is on unique quotes.
- The P-070 sales backstop does not set the `approximate` flag on its sides (the proposal only asked it to read the units).
- Replay uses a placeholder non-key plus a blocked `_post` because the cache lookup builds its request and needs a key to be set; no request can be sent.
- Dev files SUB-293-296 have no stored replies, so they were checked at rule level and end to end with a stub, not replayed.
- @senior-underwriter and @model-risk reviews are not run here.

## Fixes after P-074-check (deliverables/model-risk/P-074-check.md: APPROVE WITH CHANGES, no High)
- M1 fixed (`prepare._carry_flag`): only the trailing "approximate figure: ..." note is dropped when the exact side wins; any other review reason on the approximate side (per-location note, scan, date order) is carried as before P-074. Self-check lines in prepare.py (both cases).
- M2 fixed (`llm_extract.CURRENCY`, `_HEDGE_BEFORE`, `_AMOUNT`, `prepare.AMOUNT_TOKEN`): a hedge is seen across US$/USD/C$/CAD and a colon. "about US$1.2 million", "about USD 1.2 million", "about: $1.2m", "Approximately: $1,200,000", "roughly C$1.2 million" are approximate; "Annual sales: US$1.2 million" stays exact; the P-070 sales rule reads "Sales about USD 1.2 million". Self-check lines in prepare.py.
- M3 fixed (`prepare.apply_locations`): a premises conflict with an `unverified` side is kept; others are removed as before (P-005). Self-check line.
- M4 correction: the sentence "Nothing moves toward complete" was wrong. Reading "million" (B) can verify a side that was rejected before, so a field can go from missing to present. Dev files where that happens, from stored replies: none among the 69 replayed dev files (no field went from empty to a value; only SUB-125 changed status, toward held) and none in the 4 read-only hold-out replays besides SUB-345, whose email side now verifies as an approximate conflict side, not a field value. It is approved by D-132 (B).
- Lows not changed, listed: L1 "1.2  million" with two spaces is rejected (fails safe; widening it would loosen); L2 ranges ("between $1.0 and $1.2 million") verify the upper figure as exact; L3 hedges outside the D-132 list (est., in the region of, -ish, more or less); L4 the unverified-side note is in the screenshot (SUB-298 card) but only the SUB-297 approximate note is visible in the top of the page; L5 `_apply_reply` can resolve to an unverified side's value if the producer reply contains it (producer evidence; accepted, logged here).
- Re-run after the fixes: prepare ok, llm gate ok, workbench ok, package ok, intake ok, points ok; pytest tests/pipeline 86 passed (request equality included, PROMPT_VERSION 759b3e6bc9b2); pyright gate 96/96, new 0; ruff F the same 5 findings as HEAD; quick-15 from stored replies identical to before the fixes and to HEAD (no field hit count dropped); 69-file replay identical to the first build (only SUB-125 changed, toward held); hold-out read-only replays SUB-345 incomplete (intended), SUB-348/349/350 unchanged.
- Recheck H1 fixed: `_carry_flag` no longer cuts everything after the approximate note. It rebuilds the note from the side's own quote (as `accept_field` wrote it) and removes only that exact string, so "approximate figure: about $1.2 million; values differ by location: ..." keeps the location note and needs_review True. Self-check line added for that order. L8 fixed: the M3 assert now fails on an empty list (exactly one conflict, with the unverified side, must remain).
- Re-run: 6 self-checks ok, pytest tests/pipeline 86 passed, pyright gate 96/96 new 0, ruff F the same 5 as HEAD, 69-file replay identical to the earlier builds (only SUB-125 changes, toward held).
