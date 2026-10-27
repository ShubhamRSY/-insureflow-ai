# T-027 production veto — gate memo on T-104 (SUB-174–205), D-109

- Author: @model-risk (independent). 2026-10-17.
- Read: `deliverables/ai-engineer/evals/SUB-174-205-run-record.md`, `SUB-174-205-holdout-v6.{md,json}`, `SUB-174-205-holdout-v6-mismatches.md`; gold `SUB-174/177/179/182.md`; `team/DECISIONS.md` D-105–D-109.
- Recomputed: every per-field, status, route and P-055 count from the per-submission `checks` and `scope_rows` in the score JSON (all match the published tables). Freeze checks run by me (below). No model call, nothing rescored, no code, scorer, gold or score file changed.
- Synthetic data. Not a production approval. Approved P-055/P-057/P-058 are not production approvals.

## Verdict: KEEP (T-027 veto not lifted)

Run integrity and every safety criterion hold: 0 leaks, 12/12 detection, 0 false manual intake, 0 false completes, 0 unsafe routes. The accuracy gate fails on two fields (operations, loss runs) and on route accuracy (16/20). Lifting with conditions is not justified: the failures are in what the underwriter is shown, not in a guard that a condition could add.

## Integrity (checked by @model-risk)

| Check | Result |
|---|---|
| `git diff 6e7cfa2 -- underwriting_pipeline` | empty (JSON `uncommitted: []`, last pipeline commit 6e7cfa2) |
| `git diff 3678c0f -- simulation/inbox deliverables/senior-underwriter/gold-set` | empty |
| Scorer v6 sha256 | 4bf1cd63a632ad38834909f6822c92619a7b597fe5994a24be1a5914c9d54e5b, matches |
| Run once, scored once, fresh cache | one run id 20261017T200158-46947; `from_cache` 0; 20 calls (12 out-of-scope stopped before any call) |
| Retries / failed calls | 5 retries, all 429, all logged; call_failed 0 |
| Smoke first, .venv, paced 55 s | as stated in the run record (not independently re-observed) |

## Gate table (20 in-scope files; rate = hit / (hit + miss), not credited excluded, as in prior memos)

| Criterion | Target | Result | Met |
|---|---|---|---|
| named_insured | ≥ 9/10 | 20/20 | Yes |
| premises | ≥ 9/10 | 20/20 | Yes |
| effective_date | ≥ 9/10 | 20/20 | Yes |
| operations | ≥ 9/10 | 12/20 (0.60) | **No** |
| sales | ≥ 9/10 | 19/20 | Yes |
| tiv | ≥ 9/10 | 20/20 | Yes |
| construction | ≥ 9/10 | 20/20 | Yes |
| year_built | ≥ 9/10 | 20/20 | Yes |
| loss_runs | ≥ 9/10 | 9/17 (0.53); 3 not credited | **No** |
| False completes | 0 | 0 | Yes |
| Unsafe routes | 0 | 0 | Yes |
| Route accuracy | ≥ 18/20 | 16/20 | **No** |
| Leakage (out of scope) | 0 | 0 of 12 | Yes |
| Detection per criterion | 100% | C1 4/4, C2 5/5, C3 4/4, C4 2/2 | Yes |
| False manual intake | ≤ 2/20 | 0/20 | Yes |

3 of 15 criteria fail.

## High findings

**H1 — Operations 12/20 with 3 silent errors (owner @ai-engineer-assistant).** The extracted operations value copies the application's "Operations:" line and drops items stated in the sibling lines ("Cooking operations:", "Hood & extinguishing system last inspected:", "Line of business:"). SUB-180 ("no gas"), SUB-201 ("snack warmer"), SUB-204 ("no cooking") are wrong and not flagged: operations silent error rate 0.15, the whole run's 3 silent errors. Hood inspection dates and "no liquor" are dropped on SUB-175/182/186/203; those items drive the restaurant/bar rules (R2, R9, R10). This is the same root cause seen on T-103. Remediation: a P-### that builds operations from all operations-bearing lines, checked on dev only, then a new hold-out.

**H2 — Route 16/20; class matching misses known classes, and a W1 class gets a senior_referral path (owner @ai-engineer-assistant, rules @senior-underwriter).** SUB-174 (executive suites, office lessor AG:29) and SUB-182 (sub shop, restaurant evidence R9/R10) go to no_match with "readable class on no carrier list (R8)"; SUB-186 (restaurant with bar) gets the same provisional R8 no_match. SUB-201 (nightclub, full liquor bar; R1, W1) gets a provisional senior_referral "confirm liquor sales" instead of no_match: a prohibited class is presented as a referable risk while held. None is a carrier route, so not unsafe by the gate's definition, but W1 must never read as referable in any state. Remediation: P-### for (a) class matching on line of business plus operations for office lessor and restaurant evidence, (b) the R1/W1 prohibited check evaluated before any provisional route on held files; dev self-checks including a held W1 file.

**H3 — Loss runs 9/17, 0 of 20 accepted automatically (owner @ai-engineer-assistant for the measure, @producer/@senior-underwriter for data).** Two causes, both must be fixed before the next hold-out can test this field: (a) all seven typed carrier runs (SUB-179, 182–187) are valued 2026-11-17 to 2027-07-18, after the run date 2026-10-17, so the pipeline's "not a real past date" check correctly fires and gold "accepted" cannot be met; the test data, not the model, is wrong on this point, and it also forces status automation to 0/9; (b) on 8 files gold expects "needs review — not a recognised carrier loss run" and the pipeline returns null + needs review, which scorer v6 marks miss. Even counting all 8 as correct, loss runs would be 17/20, still below the floor. Remediation: next hold-out loss runs valued before the run date; a scorer change (P-###, user approval) defining how "needs review, no date" is judged, built before gold.

## Medium / Low (backlog, one line each)

- M1 SUB-186: restaurant ask-list requests "liquor sales" although the application says "beer and wine only" — a needless producer request would be drafted.
- M2 Status automation 0/9 gold-complete files; driven by H3(a) and operations flags ("may be missing: liquor/units") on files that state it.
- M3 Conflict mark 15/20; 5 misses classed "gold convention" in the mismatches file — @senior-underwriter to confirm convention vs defect.
- M4 Scorer clause rule splits "until 2 a.m." at the periods (SUB-201); ops checklist also treats "seating 24" ≠ "24 seats". Fix only in a new scorer version.
- L1 Smoke and pacing are stated by the orchestrator, not evidenced by a log line in the run record.
- L2 Groq OTPM 1000 vs request 1400 caused 5 retries; max_tokens should fit the free-tier limit.
- L3 Out-of-scope reason accuracy is reported 12/12 but is not a gate criterion; keep it reported.

## What would resolve the veto next

1. Approved P-### fixes for H1 and H2 (and the H3(b) scorer definition), built and checked on dev files only; @model-risk check, no High.
2. Code and scorer re-frozen and hashed; a new 20 + 12 hold-out with gold written first, loss runs valued before the run date, at least two held W1 files and at least two office-lessor / deli-style class files.
3. Run once and scored once under the same rules as D-109, meeting all 15 criteria above. The P-055 scope gate must still pass.
4. Production approval would additionally need the monitoring plan for silent errors on operations; this memo does not grant it.
