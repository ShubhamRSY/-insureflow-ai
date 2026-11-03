# T-121 hold-out results: SUB-510 to SUB-541 (run once, scored once, 2026-11-03)

Run `20261103T151602-99173`, code `8baa00a` (HEAD b92a5b8), PROMPT_VERSION `392b9ce3c1af`, scope-v5, scorer v11, counter `count_ops_gate_v2.py` (D-141), gold manifest `8ba4a9f3…a7f`. qwen/qwen3.8-27b on Groq, paced 55 s. Nothing fixed (D-154). Synthetic; not a production approval.

## Gates

| Gate | Target | Result | Pass |
|---|---|---|---|
| Leakage (out-of-scope file shown as in scope) | 0 | 0 of 12 | yes |
| Detection recall, overall | 100% | 12/12 | yes |
| — criterion 1 / 2 / 3 / 4 | 100% | 2/2, 6/6, 2/2, 2/2 | yes |
| — words-only multi-location SUB-534, 535, 536, 537 (P-077) | 100% | 4/4 (reason multiple_locations) | yes |
| Near-misses kept in scope (527 two floors, 528 2nd floor, 529 two entrances) | 3/3 | 1/3 (528 kept; 527, 529 manual intake by Part B, not Part A) | no |
| Wrong (false) manual intake | ≤ 2 | 4 of 20 (510, 513, 527, 529) | **no** |
| False completes | 0 | 0 | yes |
| Unsafe routes | 0 | 0 | yes |
| Route accuracy | ≥ 18/20 | 16/20 (the 4 manual-intake files) | **no** |
| Direct Carrier A (510, 511, 512, 513) | — | 2/4 (511, 512 carrier_a; 510, 513 manual intake) | — |
| Fields vs floor (≥ 18/20 each) | ≥ 18 | named insured, premises, effective date, operations, construction, year built 16/20; sales 14 + 2 flagged; TIV 15 + 1 flagged; loss runs 16 + 4 not credited | **no** (every miss is one of the 4 manual-intake files) |
| C2 v2 operations silent errors | 0 | 4 counted (510, 513, 527, 529: empty because manual intake; no value shown) | **no** (as counted) |
| C3 understated hazards | 0 | 0 (cooking conflicts 520, 522 raised; cooking stated 521, 525, 526 hit) | yes |
| C4 operations present ≥ 18/20, hits ≥ 15/20 | 18 / 15 | present 16, hits 16 | **no** (present) |
| Planted-conflict recall, 6 figure conflicts (D-153) | 100% | 6/6 (514, 515, 517, 518, 519, 521 held as open conflicts) | yes |
| Cooking-conflict marks 520, 522 (reported apart, D-153) | — | both raised as "cooking: the documents disagree" (v11 marks miss, no figure) | — |
| Silent error rate (D-084) | — | 0.0 (0 of 180) | — |
| Automation rate | — | 0.689 (124 of 180); T-120 0.861 | — |

## Cost and calls
- 21 model calls logged, 0 from cache, 40,132 tokens (1,911 per call); Groq free tier (D-011), $0.
- Retries (RUN-RULES): SUB-517 one HTTP 503 "over capacity" (whole-file retry, attempt 2 ok); SUB-518 one 429. 0 failed calls.

## The one failure: P-077 Part B fails closed on 4 in-scope files
Every gate failure above comes from the same 4 files. Each went to manual intake with "number of locations not clear" (Part B, `prepare._location_problem`); Part A (scope-v5 rules) fired on none of them:
- SUB-510: the model's count was 1 with the quote "Premises address: 1906 Hwy 290 W Ste 104, Brenham TX 77833"; the check says the quote "shows no premises address" (a highway address is not read as a street address).
- SUB-513: count 1, quote "We lease one office suite on Marble Falls Ave" (email; no house number).
- SUB-527: count 1, quote "One address, one building." (email; near-miss file).
- SUB-529: count 1, quote "Same single building." (email; near-miss file).
All 4 fail in the safe direction (a person reads the whole file). On the 16 files that reached a status, every field is a hit or correctly flagged.
