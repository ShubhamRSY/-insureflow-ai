# Next session

Written 2026-10-11 by the orchestrator at wrap-up. Decisions D-023 through D-040 were recorded today.

## Where we stopped

- `/wrap-up` finished. The session's work is committed as `ddb95ce` on `ai-team` and pushed to `origin/ai-team`. `main` was not pushed and was not changed.
  - The first run stopped at the secret scan on two made-up keys in the `llm_extract.py` self-checks (lines 722 and 900). On the user's word both were changed to `"TEST_NOT_A_REAL_KEY"`, the self-checks were run again, and the scan came back clean. The real key was never in any staged file or any pushed commit (checked by exact match, not printed).
  - The push sent three commits: `2b5d084`, `47c5324`, `ddb95ce`. All three were scanned first.
- `ddb95ce` is the D-034 commit. A scored run may start from it as long as no pipeline file changes first.
- Not committed, left alone: `src/insureflow/` (13 files), `tests/`, `docs/rag/`, `scripts/`.
- Self-checks at wrap-up, no model host set: `llm gate ok`, `prepare ok`, `intake ok`, `package ok`, `workbench ok`, `points ok`.
- Remote: `origin` is `https://github.com/ShubhamRSY/-insureflow-ai.git`, private.
- No model call was made today. The quick set of 15 has not run since P-002 and P-003b.
- No standup entry today from the roles that only reviewed: @model-risk, @software-engineer, @account-manager, @ml-engineer, @actuary, @responsible-ai, @compliance, @senior-underwriter. Their verdicts are in `team/DISCUSSION.md`.

## Built today, not yet reviewed

| Change | Task | State |
|---|---|---|
| P-008 provider guard (Groq and localhost allowed; exact-host ALLOW_PROVIDER; cache-only runs skip it) | T-065 | IN_REVIEW, no verdict |
| P-012 every 429 and retry in the token log | T-073 | IN_REVIEW, no verdict |
| P-013 atomic cache writes | T-074 | IN_REVIEW, no verdict |
| D-028 follow-ups | T-075 | IN_REVIEW, no verdict |
| P-014 token log and cache key (host, temperature) | T-078 | IN_REVIEW, no verdict |

P-009 needed no code: temperature was already 0.

## Approved, not built

| Proposal | What | Task |
|---|---|---|
| P-006 | EasyOCR fallback | T-062, then T-068 |
| P-010 (G2 D1 S1 C1, hash check) | Send gates, `all_values_rejected` | T-069, T-070, T-071 |
| P-011 (W2 U2 O1) | Published scores read-only, scratch folder | T-072 |
| P-015 (S3 H1 M1 T2 V3 W1 A1 E2) | Score fixes | build tasks not yet created |
| P-016 (N2 H2 D2 R1 Q1 C3 S2 G2 L1 E1 P1 K1, plus the acknowledgment at approve) | Citations, confidence, unread content | build task not yet created |
| P-017 (U1 V2 X1 J1) | Commit hash and literal status in score output | build with T-072 in one pass |

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-059 | @model-risk | P-010 built (T-070, T-071) and looked at again by all three reviewers |
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-020 | @compliance | Its items (a) to (f): P-010, D-033 send rule, D-035 items, package from the reviewed file, self-checks |
| T-026 | @model-risk | The retired extractor is in `deliverables/model-risk/model-inventory.md` (T-089); D-036 covers the rest |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |

## Pending decisions for the user

1. Cache key host: host name only today. Two local servers on different ports with one model name would share a key. Include the port or not.
2. P-014 G1 consequence: token-log rows written since the last commit, and 4 cached results that were never tracked, are now only on this disk. Keep as is, or copy them somewhere.
3. T-065 points left open by the owner: ALLOW_PROVIDER matches the host name only (no port, no full URL) and is case-sensitive; a partly cached run stops at the first file that needs a call.
4. T-075 points left open: a temp file under a minute old is kept for the next run; `retry` and `cache_unreadable` rows are not counted as failures.
5. "Underwriter ids tied to my session" (D-038 item 3): the mechanism is not defined. @software-engineer proposes one before building.
6. `team/DEMO-BLOCKERS.md` holds the full fix order; `team/BACKLOG.md` holds 149 rows for after the demo.

## First 3 tasks next session

1. T-064: the quick set of 15, all fresh calls under the new cache key, as the baseline. Start from `ddb95ce`; if any pipeline file changed, commit first (D-034). Record the commit hash by hand in the memo until P-017 is built.
2. T-069 (@data-engineer: yes or no to the saved-file keys), then T-070 (P-010, `prepare.py` and `eval_holdout.py`), then T-071 (@software-engineer). Demo blocker 1.
3. The owed reviews of what was built today: T-065, T-073, T-074, T-075, T-078, one reviewer per dispatch, and second looks at T-060 and T-063.

Inputs that can run alongside with no code: T-082 (@head-of-underwriting class lists), T-089 and T-090 (@model-risk inventory and memo lines).

## For the AI Engineer

- Pending proposals: none waiting on approval. P-006, P-010, P-011, P-015, P-016, P-017 are approved and not built.
- Latest eval scores: no new run today. Official baseline SUB-077 through SUB-086, 71 hits of 100, "8 of 9 fields scored; loss runs = date only": premises 5 hit, 4 miss, 1 flagged; year built 7/10; status 5/10; loss runs 6 hit, 1 miss, 2 not credited, 1 flagged. The rerun (79 of 100) is "with P-002 and P-003b, not a same-code comparison".
- Top failure to fix next: the send gates. A failed or all-rejected file can still be approved or sent as the user (P-010).
