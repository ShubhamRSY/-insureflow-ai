# T-027 production veto — gate memo on T-103 (SUB-154–173)

- Author: @model-risk (independent). 2026-10-16.
- Read: `deliverables/ai-engineer/evals/SUB-154-173-holdout-v4.{md,json}`, `SUB-154-173-holdout-v4-mismatches.md`, `RUN-RULES.md`, frozen scorer `underwriting_pipeline/ai/eval_holdout_v4.py` (judge rules only), gold `SUB-168.md`, prior memo `T-027-holdout-127-memo.md`, `team/NEXT-SESSION.md`.
- Recomputed: every per-field count from the per-submission `checks` in the score JSON (match the published table exactly); route misses from `gold_route`/`route_used`; freeze diffs with git. No model call, nothing rescored, no code, gold, scorer or score file changed.
- Synthetic data. Not a production approval. The approved P-054 is not a production approval either.

## Verdict: KEEP (T-027 veto not lifted)

Process conditions are met. The accuracy gate fails on 8 of 9 fields and on route (16/20). The safety criteria (0 false completes, 0 unsafe routes) hold.

## Per criterion

| Criterion | Evidence | Met |
|---|---|---|
| Gold first, frozen `33e399a` | `git diff 33e399a..HEAD` on gold set and inbox: empty | Yes |
| Frozen code `3557e4a` | `git diff 3557e4a..HEAD -- underwriting_pipeline/`: empty; JSON `uncommitted: []`, commit 2c6b2d9 recorded | Yes |
| Smoke first, .venv, paced (55 s) | As stated in the dispatch; no run record on file (L1). Model qwen/qwen3.8-27b on Groq per JSON | Yes (stated) |
| Scorer v4, `--write`, run and scored once | One live score file, run 20261016T151351-65695; 0 call failed; 4 retries (429) all logged per file | Yes |
| All 9 fields at 9/10 or better | **1 of 9** (named_insured only) | **No** |
| 0 false completes | 0 | Yes |
| 0 unsafe routes | 0 | Yes |
| Route at least 18/20 | **16/20** | **No** |

## Per field vs the 9/10 floor

Rate = hit / (hit + miss); not credited excluded (same convention as the SUB-127–146 memo).

| Field | Hit | Miss | Not credited | Rate | Floor |
|---|---|---|---|---|---|
| named_insured | 19 | 1 | 0 | 95% | met |
| premises | 16 | 4 | 0 | 80% | no |
| effective_date | 17 | 3 | 0 | 85% | no |
| operations | 7 | 13 | 0 | 35% | no |
| sales | 17 | 3 | 0 | 85% | no |
| tiv | 17 | 3 | 0 | 85% | no |
| construction | 17 | 3 | 0 | 85% | no |
| year_built | 16 | 4 | 0 | 80% | no |
| loss_runs | 5 | 4 | 11 | 56% (5/9) | no |

Trend: SUB-107–126 5 of 9, SUB-127–146 3 of 9, SUB-154–173 1 of 9. Silent errors 6/180 (3.3%), all in operations. Status 15 hit, 4 miss, 1 not credited; status automation 4 of 8 gold-complete.

## High findings

### H1 — Field floor fails on 8 of 9 fields; scanned and email-only inputs are the main cause (owner @ai-engineer-assistant)

- SUB-170 (scanned JPG application, 2 locations): every field null, although OCR text was read (the open construction conflict quotes `application.jpg` "Masonry {loc ape"). The gold TIV conflict (465000 vs 546000) was not found. One file costs a miss on 8 fields plus conflict and route.
- SUB-159, 160, 161 (scanned/rotated/image-only carrier loss runs): valued-through date read 0 of 3; files held "incomplete" instead of the P-048(b) "complete — review pending". Three of the four status misses.
- SUB-168, 169 (email only): effective dates stated in the email (2027-04-01; Spanish 2027-05-01) returned null; SUB-169 premises (Pharr, TX) null; SUB-168 premises lacks "TX".
- SUB-163 (Spanish): operations null, which also drove the route to hold.
- SUB-172 (3 locations): premises and year_built null; the three location addresses opened as a premises conflict where gold has none (see M5).
- Operations 7/20 with 6 silent errors (but see M2 on how much of this is wording).
- Remediation: P-### proposals for (1) fields from scanned applications, (2) date read from scanned carrier loss runs and the P-048(b) status, (3) email-only and Spanish facts (effective date, city/state), (4) multi-location premises. Each change only after `approve change P-###`; develop on dev sets only, never on SUB-154–173.

### H2 — Route 16/20, below 18/20 (owner @ai-engineer-assistant)

- Misses: SUB-163 senior_referral → hold (no provisional route; Spanish operations null); SUB-170 senior_referral → hold (scanned application unread); SUB-169 no_match (R8 laundromat) → provisional senior_referral; SUB-167 gold "hold" → provisional senior_referral scored against "hold".
- All four are in the safe direction (no file to a carrier). No reading reaches 18/20: even crediting SUB-167 (M4) gives 17/20. Carrier A direct route: 3/3 hit (154, 155, 162).
- Remediation: falls out of H1 (163, 170) plus the R8 match on email-only text (169).

## What resolves the veto

A new frozen hold-out (20 files, gold first, scored once, no code change after the gold) on a commit carrying approved fixes for H1 and H2, meeting the whole gate: all 9 fields at 9/10 or better, 0 false completes, 0 unsafe routes, route at least 18/20. Settle M1 and M4 (forward only, by the decision owner) before that gold is written. This score stays as published.

## Medium and Low (for the backlog, one line each)

- M1: v4 scores a null on "missing, not given" as a miss (by design), so the 2 email-only files cap sales/tiv/construction/year_built at 18/20 in any mix; convention for future hold-outs needs a @user decision (never applied to this score). Without it those fields would be 94/94/94/89%; premises, operations and loss_runs fail either way.
- M2: operations is scored as "every gold word present", so "Residential apartments" vs "Apartment building" is a miss and a silent error; the mismatches file cuts pipeline text at 140 chars, so I cannot confirm whether restaurant hood/UL 300 facts were dropped. Print full operations text in the mismatches output.
- M3: SUB-164 (applicant's own note under a carrier header) kept the date 2026-09-30, flagged with the correct reason, and showed "complete — review pending" where gold says incomplete; show evidence that send stays blocked until review clears.
- M4: gold uses route "hold" (SUB-167, 168) while D-097 says hold is a status, not a gold route; v4 scores the provisional route against "hold". Settle before the next gold.
- M5: SUB-172 multi-location addresses were opened as a premises conflict; multi-location should list locations, not conflict.
- L1: no T-103 run record (smoke output, interpreter, LLM_PACE_SECONDS, run id) on file; accepted on dispatch facts plus score JSON.
- L2: the three score files are untracked; commit them unchanged.
- L3: status automation 4/8 gold-complete files.
