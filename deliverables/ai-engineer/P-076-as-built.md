# P-076 as built (D-135, T-027 C1)

Author: @ai-engineer-assistant, 2026-10-27. Branch `p076` in the fix worktree (from pilot-integration 48dedf2). Not committed. Development data only. No model call. Not a production approval; the T-027 veto stands.

## Files changed
- `underwriting_pipeline/ai/prepare.py`: `POLICY_NOTE`, `flag_operations()`, one call in `process_submission` after every rule, merge, conflict, `check_operations`, P-074/P-075 (just before `completeness`). Any operations row with a value gets `needs_review=True` and `policy_review=True`. `reason` is never touched, so every specific reason stays. `_saved_payload` keeps `policy_review` (new runs only). Self-check added (model-carried, specific reason kept, agreeing merge, rule-copied shape, scan shape, empty row untouched). `SYSTEM`, `request_for`, `PROMPT_VERSION` untouched.
- `underwriting_pipeline/app/package.py`: no new mechanism (`needs_review_ids` / `ack_problem` reused). Self-check SUB-376: send refused "1 value needs review and is not acknowledged (operations)"; allowed once acknowledged on the current run hash.
- `underwriting_pipeline/app/workbench.py`: review note = specific reason, then the policy note, joined by "; " (policy note alone when no reason). One What's new line (2026-10-27, P-076, D-135). Self-check for both shapes. Pilot per-value confirm unchanged.
- `deliverables/software-engineer/screenshots/P-076-operations-flag.png` (SUB-301 card, temp copy, stubbed host, temp cache; real workbench.html, team/, jsonl and outboxes untouched; git status shows only the 3 files and the png).

## Test expectations changed (stricter only), all in prepare.py self-check
1. `clean` run (`run_case(on_run, ...)`): status "complete" and `complete` True -> "complete — review pending", `complete` False (still `ready_to_route`, request None).
2. `alone` (one accepted typed carrier run): "complete" -> REVIEW_PENDING.
3. `with_letter` (P-040 no-known-loss letter): "complete" -> REVIEW_PENDING.
No pytest or package/workbench expectation needed changing.

## Checks
- Self-checks: prepare ok, llm_extract (gate) ok, package ok, workbench ok, intake ok, points ok.
- `pytest tests/pipeline -q`: 93 passed (baseline 93). Request equality baseline test passes: 0 of 143 changed (no change to prompt, `request_for`, `llm_extract.py`).
- pyright 1.1.390 on the 3 files: 43 errors, same as HEAD (new 0). ruff F: 3 findings, same as HEAD.
- Self code review: flag runs after the last writer of operations (nothing later sets it); only value-bearing rows flagged; failed/rejected/manual-intake runs have no operations value; status goes complete -> review pending through the existing `review` list, no routing/appetite/gate change. Known limit: a run saved before P-076 has no flag and is unchanged until re-extracted. No fixes needed.
- Not run: quick-15 / full regression (needs model calls; the change is a flag after extraction and cannot change a hit count). Not frozen files: no eval_holdout, lint, gold or simulation/inbox change.

## Fix for @model-risk H1 (runs saved before P-076)
- `package.py`: new `is_review_row(row)` (value and (needs_review or field_id == operations)); `needs_review_ids` uses it, so operations is always on the one shared list, flagged or not. Send gate, approve gate and card all read that list.
- `workbench.py`: the card note and the ack checkbox use `package.is_review_row`; an operations row always gets "NEEDS REVIEW: ... Operations is always checked by the underwriter (T-027 C1, D-135)" (after any specific reason). Pilot per-value confirm unchanged. L1 done: the review-note expression is split into readable lines, no behaviour change.
- New self-checks: package SUB-377 (saved before P-076: operations value, needs_review False, no policy_review, status "complete"): send refused naming operations, then allowed once acknowledged on the run hash. Workbench: such a row shows the ack box and the note.
- Expectations changed (stricter only), because operations is now always listed: package.py `decide()` helper now acknowledges what the saved run lists (`ack=False` for the three refusal tests SUB-321, 376, 377); SUB-195 approve line acknowledges operations. workbench.py: the ack list in the D-039 test is `["year_built", "operations"]`; `act` approves for SUB-901, 904, 906 (x2) and the sandbox check carry `ack: ["operations"]`; SUB-908 acks (x2) add operations; the clean card now has exactly one ack box (operations); "Send refused" text for SUB-905 and "acknowledged 2: named_insured, operations" for SUB-908.
- Medium (not fixed): the status line of a pre-P-076 run still reads "complete" (status is saved text, not recomputed); the card also shows the ack box and note, and the send is refused until acknowledged.
- Re-run: prepare, package, workbench, llm gate, intake, points ok; pytest tests/pipeline 93 passed (includes request baseline, 0 of 143 changed); pyright 43 errors, same as before (new 0). Screenshot not retaken (the flagged SUB-301 card is visibly unchanged).
