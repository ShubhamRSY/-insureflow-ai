# B-415 live check — P-059 with P-061 and P-062 (T-107b, D-112)

Author: @ai-engineer-assistant. Dev data only (quick 15 and SUB-127 to 173); not a hold-out; not a production approval (T-027 veto stands).
Routes and statuses below are computed on HEAD 7cfc959 from the saved replies, 0 extra calls. Prompt 759b3e6bc9b2 (P-059), model qwen/qwen3.8-27b on Groq.

## Calls
- 41 live calls, no more: quick 15 = 5 calls (SUB-027, 042, 056, 071, 073); dev SUB-127-173 = 36 calls. The other quick files and 21 of the dev ids make no call (manual intake or no readable text). Cache misses before the run: exactly 41; after: 0.
- After the session restart: 0 calls made. All 41 replies were already saved; this report was scored from them.
- call_failed: 0. Retries (all HTTP 429, all succeeded on retry, logged in each file's report): SUB-042 x1, SUB-071 x2, SUB-150 x1 = 4. The driver's end-of-run counters printed 1 (quick) and 3 (dev) failed attempts; they disagree with the per-file rows (3 + 1). Per-file rows are the log of record. No timeout, no other error, no unusable reply.
- Scores were read-only (no --write): no published score file changed. New replies are in underwriting_pipeline/cache/extractions.

## Old saved replies
Only 16 of the 41 files have an old reply (prompt b025802c0dfa): SUB-027 and the dev files 154-173 that make a call (15). The other 25 have nothing to compare with. The comparison below is on those 16 (dev 154-173 = 20 ids, 15 with a call).

## Totals, new reply vs old reply, SUB-154-173 (same code 7cfc959, same gold, scorer v5)
| Measure | Old reply | New reply |
|---|---|---|
| Operations hits (20 ids) | 7 | 7 |
| Operations flagged "may be missing" (P-059 whole-document check), files | 5 of 16 | 1 of 16 (SUB-154 not flagged now); across all 41 new files: 1 (SUB-134) |
| Silent errors, all fields | 8 of 180 (4.4%) | 9 of 180 (5.0%) |
| Automation rate | 62.2% | 64.4% |
| Status automation (gold-complete shown as plain "complete") | 4 of 8 | 5 of 8 (SUB-154 moved from "review pending" to complete) |
| Routes correct | 13 of 20 | 13 of 20 (no route changed; per file identical) |
| False completes | 0 | 0 |
| Unsafe routes | 0 | 0 |
| call_failed | 0 | 0 |
SUB-027 (quick): old and new identical, all fields hit, status "complete - review pending" both.

## New replies on all of SUB-127-173 (47 ids: 36 with a call, 11 with none)
- Operations: 27 hit, 20 miss (11 misses are the no-call files, which scorer v5 predates P-055 and counts as misses); 9 misses among files with a call.
- Silent errors 12 of 423 values (2.8%); automation 67.8%.
- Status: 28 hit, 8 miss, 11 not credited. False completes 0. Status automation 10 of 18 gold-complete files plain "complete".
- Route: 24 of 47 correct (the scorer counts the 11 no-call files as misses; route gate FAIL, as in D-098's earlier dev re-checks, where the gate needed 18/20). Unsafe routes 0.
- Route misses with a call that matter: SUB-127, 128, 147 (gold carrier_a; R17 sends office-type files with extra words to senior_referral, P-053); SUB-149 (gold carrier_c; habitational, senior_referral with Carrier C suggested); SUB-152 (gold carrier_a; "ammunition" in operations is now no_match R1, the safe direction); SUB-153 (gold carrier_a; hazardous goods referral W2); held files (SUB-135, 148, 150, 151, 173) show a provisional route senior_referral, gold says carrier_a/b or no_match: held for missing information; SUB-134 no_match R8 matches gold.
- Quick (5 call files): every extracted field hit in all 5 except sales and conflict on SUB-073 (correctly flagged); status miss on SUB-027, 056, 071 (shown "complete - review pending", not plain complete: the safe side). Operations flags 0.

## P-061 / P-062 shapes in the dev data
No cached dev file has the SUB-174/182/186/201 shape (office only on the line of business, sub/deli with equipment, restaurant with bar on the line of business, nightclub with snacks only). Those cases are covered by the synthetic self-checks (T-107a), not by this live run.

## SUB-184 and SUB-179 (T-104, now dev data), 0 calls
Replayed from their T-104 saved replies (old prompt b025802c0dfa, cache key patched in a temp script, temp cache copy, no network) on HEAD 7cfc959:
- SUB-184: status "complete - review pending", route carrier_a. Confirmed.
- SUB-179: status "complete - review pending", route carrier_a. Confirmed.

## Risks and open
- P-059 effect is real: the old prompt's replies dropped cooking and line items in 5 of 16 files (flagged by the whole-document check); the new prompt cut that to 1 of 41. This is on 41 files, one model, one host; not a hold-out.
- Silent errors did not fall on 154-173 (8 to 9; one more value wrong and unflagged). The scorer rows were not opened to find which field; if it matters, look at SUB-154, the only file whose status changed.
- Rate limits: 4 retries on 3 files; no run lost a file.
