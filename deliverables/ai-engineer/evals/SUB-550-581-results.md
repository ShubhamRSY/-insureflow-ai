# T-128 hold-out results: SUB-550 to SUB-581 (run once, scored once, 2026-11-05)

Run `20261105T012147-15550`, code `1ddae83c` (HEAD `fffdcca5`), PROMPT_VERSION `392b9ce3c1af`, scope-v8 (P-084), scorer v11, counter `count_ops_gate_v2.py` (D-141) with the M1 rule (D-158), gold manifest `307e6fec…e0ff`. qwen/qwen3.8-27b on Groq, paced 55 s, fresh empty cache. Nothing fixed (D-020, D-163). Synthetic; not a production approval.

## Gates

| Gate | Target | Result | Pass |
|---|---|---|---|
| Leakage (out-of-scope file shown as in scope) | 0 | 0 of 12 | yes |
| Detection recall, overall | 100% | 12/12 | yes |
| — criterion 1 / 2 / 3 / 4 | 100% | 2/2, 6/6, 2/2, 2/2 | yes |
| — words-only multi-location 574, 575, 576, 577 | 100% | 4/4 (multiple_locations) | yes |
| — SUB-533-shaped 572 (highway second address, carrier sentence), 573 (below the mailing line) | 100% | 2/2 (multiple_locations) | yes |
| Reason accuracy | — | 12/12 cards list every gold criterion | — |
| Near-misses kept in scope (567 two floors, 568 2nd floor, 569 two entrances; 550, 567 one-address wording) | all | 3/3 (+ 550 in scope) | yes |
| Highway premises kept in scope (550 Hwy 71 W, 552 US-59 N) | 2/2 | 2/2 | yes |
| Wrong (false) manual intake | ≤ 2 | **0 of 20** | yes |
| False completes | 0 | 0 | yes |
| Unsafe routes | 0 | 0 | yes |
| Route accuracy | ≥ 18/20 | 19/20 (557 shown "hold", gold senior_referral) | yes |
| Direct Carrier A (550, 551, 552, 553) | — | 4/4 carrier_a | — |
| Fields (≥ 18/20 each) | ≥ 18 | named insured, premises, effective date, construction, loss runs 20/20; operations 19 (557 empty, in an open conflict); TIV 19 + 1 flagged (559); sales 17 + 3 flagged (555, 556, 561, all planted); year built 19 (561, see note) | yes |
| C2 v2 operations silent errors (M1: over files that reached a status) | 0 | 0 of 20 (no file in manual intake) | yes |
| C3 understated hazards | 0 | 0 (cooking conflicts 560, 562 raised; cooking stated 561, 565, 566 hit) | yes |
| C4 operations present ≥ 18/20, hits ≥ 15/20 | 18 / 15 | present 19, hits 19 | yes |
| Planted-conflict recall, 8 figure conflicts (D-166) | 100% | 8/8 (554, 555, 556, 557, 558, 559, 561, 566 held as open conflicts, both sides stored) | yes |
| Cooking-conflict marks 560, 562 (reported apart, D-166) | — | both raised as open cooking conflicts; v11 marks miss (unmeasurable). 560 cites the fryer sentence; 562 cites the subject and name lines, not the frying sentence | — |
| Silent error rate (D-084) | — | 0.006 (1 of 180: 561 year built, see note) | — |
| Automation rate | — | 0.861 (155 of 180); T-121 0.689 | — |
| Status automation | — | 0 of 10 gold-complete files shown plain "complete" (all "complete — review pending", the safe side) | — |

**Every T-121 gate passes on T-128.**

## Notes (reported, nothing fixed)
1. **SUB-561 year built — a gold wording artefact, not a model error.** The pipeline showed `1939`, the documents and gold say `1939`. The gold Conflict line reads "sales: 498000 (application) vs 530000 (email, 'about $530,000'; the email says the application shows the year before)". v11 treats a field as part of the conflict when its topic word is in the gold Conflict line (`year` → year_built) and then marks the shown value a miss. The word came in with the email rewrite (T-128 build check H2). As scored: year built 19/20 and one silent error; on the values: 20/20 and 0 silent. The published score stays as scored (D-020). The lint's perfect-answer test did not catch it (B-465 gap).
2. **SUB-557** (the P-081-resolvable file): the model put the operations text itself into the 9 vs 10 suite conflict, so operations is empty (a miss, in an open conflict, not silent) and the route shows "hold" instead of senior_referral (a miss, the safe side). Status incomplete, as gold.
3. **"complete — review pending" with an open conflict**: 554 (sq ft), 558 (sq ft) and 562 (cooking) read "complete — review pending" while their planted conflicts are open; the other conflict files read "incomplete". Not a false complete (v11 status hit, report `complete` false), but the card wording differs from the gold status. For the memo.
4. Retries: SUB-550 one 429, SUB-559 one 429, SUB-558 one timeout; 0 failed calls. 20 model calls (out-of-scope files make none), 0 from cache, 38,449 tokens (1,922 per call), $0 (Groq free tier, D-011).
5. The run paused for several hours between SUB-556 and SUB-570 (the computer slept); pacing and cache were unaffected.
