# T-119 build check, look-again (B-457), after the D-128 gold fixes. @model-risk, 2026-10-23

This is the independent look-again on the D-128 gold fixes for hold-out SUB-340–371. It is not a production approval, and the T-027 veto still stands. I did not run the pipeline, any model, or the scorer on submissions. The only thing I re-ran was the lint, with its output sent to the scratchpad. `git status` was the same before and after that run.

## What changed since the earlier check (`T-119-build-check.md`, 23:50)
- All T-119 files are untracked, so I compared modification times against the earlier check. Six files are newer than it:
  - the gold cards SUB-344, SUB-348 and SUB-349;
  - `T-119-gold-summary.md`;
  - `T-119-lint.txt` and `T-119-lint.md`.
- Nothing else is newer: no other gold card, `T-119-routes.md`, `T-119-plan.json`, `lint_holdout.py`, the builder, the mix, or any file under `simulation/inbox/SUB-340…371`. The newest inbox file is from 17:12.
- Hashes: `lint_holdout.py` is `01147a75…ea653`, and `eval_holdout_v11.py` is `7ddcfb50…fcbb`, the same as at the earlier check.

## Resolution conditions (D-128)
1. **SUB-344.** The Conflict line now reads `square footage: 3200 (application) vs 2450 (schedule)`. I recomputed the needles with v11's `money()` and `sides_stored`: they are `['3200', '2450']`, which are exactly the two sides. "Appraisal 2025" and the old-lease remark have moved to a new `- Notes:` line, which v11 does not score.
   - Against the documents: the application PDF text layer says `Square footage: 3,200`, and the schedule row (source `appraisal 2025`) says 2450. **Closed.**
2. **SUB-348.** The Conflict line now reads `cooking: none (application) vs stove top and flat grill (email, hot food all day)`. The application says `Cooking operations: None`. The email says "heat up the soup on the stove top and grill the panini on a flat grill, hot food all day". The line matches the documents and the "1900 sq" needle is gone. **Closed.**
3. **SUB-349.** The Conflict line now reads `cooking: none (application) vs yes (schedule) and griddle (email)`. The application says `Cooking operations: None`, the schedule's cooking column says `Yes`, and the email says "made to order on the griddle". The line matches the documents and the "1700 sq" needle is gone. **Closed.**
4. **Verbatim record.** `T-119-gold-summary.md`, section "D-128 fixes", carries the sentence word for word: "Under v11 these two conflict marks can't be measured; they are reported separately and excluded from the conflict rate. Noted before the run." `team/TASKS.md` T-119 also notes it before the run. **Closed.**
5. **SUB-344 in the no-cooking list.** It is listed, and the list now has 14 files.
   - The documents agree: the application says `Cooking operations: None`, the schedule's cooking column says `No`, and the email does not mention cooking.
   - The card's Operations items carry `no cooking`. **Closed.**
6. **Lint re-run and recorded.** I ran `lint_holdout.py T-119-plan.json --run-date 2026-10-23` myself, with v11 as the default scorer and the LLM_* variables unset. The output matches `T-119-lint.txt` line for line:
   - FAIL on SUB-348 conflict;
   - FAIL on SUB-349 conflict;
   - INFO on SUB-350 being undated, as the plan declares.
   - The run-1 operations FAIL on SUB-348 is gone, and SUB-344 passes. The record in `T-119-lint.md` is current and states its history. **Closed.**

## The other acceptance criteria
- **The gold changes match the documents and the written rules.** I checked this above. Status (incomplete, hold on an open conflict), route (senior_referral; R11 for 344, R9/R10 for 348 and 349), Missing and Operations items are unchanged from the cards I checked earlier, and the routes file is untouched. No other card, the plan and the inbox are all unchanged (see "What changed" above).
- **The lint with v11 has no failure except the two D-128 marks.** Met. The lint exits with code 1 because of those two marks. The run passes only because D-128 excludes them, not because the lint itself passes. This needs a note when the run is reported (M2).

## High
None.

## Medium (backlog, one line each)
- M1 (carried over from the earlier check). Only three conflict marks remain measurable, and two of them are weak. SUB-345's needle is `42 million`, which matches the email's wording rather than the 1240000 side. SUB-346's needles, `8` and `9`, are met by almost any text. In practice the conflict rate rests on SUB-344. Report the per-file results next to the rate.
- M2. v11 will still mark SUB-348/349 as conflict misses in its output. Whoever writes up the results must take them out of the conflict rate by hand, list them separately, and say this was declared before the run (D-128). Do not re-score or edit v11.

## Low (one line each)
- L1. SUB-344 now has a top-level `- Notes:` field that earlier sets do not use. v11 ignores it (SUB-344 lints clean). Keep it unscored.
- L2. "Nothing else changed" rests on file times, because the T-119 files are untracked. Record the gold manifest sha256 at the freeze so the next check has a hash to compare against.
- L1–L4 from the earlier check are unchanged and stay in the backlog.

## Verdict: APPROVE (freeze the gold)
- H1 from the earlier check is closed. The D-128 conditions are met, and the lint re-run reproduces the recorded result.
- Next step: the owner freezes the gold and records the manifest sha256. T-119 is not run until the user says so (D-020).
- This is not a production approval, and the T-027 veto stands.
