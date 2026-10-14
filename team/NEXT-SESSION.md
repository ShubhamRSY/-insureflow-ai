# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `005eb40` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- T-085 and T-086 (demo blockers 6 and 7) are built together under D-056 in `underwriting_pipeline/app/package.py` and `workbench.py`, and are IN_REVIEW.
  - `build_package(submission)` reads the hash-checked saved run. It applies the latest logged edit per field, adds each field's citation, names the carrier from `route()`, and labels the file SYNTHETIC. It refuses on an empty field or when no carrier is named, for every actor.
  - `send_to_carrier(submission, actor, out_dir, reason, user_line)`: a user send needs the exact "send to carrier SUB-###" line for that id, logged to `deliverables/software-engineer/sends.jsonl`.
  - An edit row now stores `field_id` and `new_value` (B-139). After an edit, the latest decision is "edit", so the underwriter must approve again before a send.
- @compliance re-checked T-020: **APPROVE** on items (b), (c), (d), no High. The T-020 veto stands on item (e) only (T-087). Medium/Low: B-185 to B-189.
- T-079 has @compliance APPROVE (D-055 build). T-079, T-085, and T-086 still wait on @senior-underwriter and @account-manager (T-079 also @model-risk).
- The stubbed test file is updated by @software-engineer (D-056): 24 pass, 9 known-gap, 1 error, 1 fail. The error (eight threads on the decision log) and the fail (token log) are not from this change.
- Self-checks at wrap-up, no model host: llm_extract, prepare, intake, package, workbench, and points all ok.
- Parked until after the demo: P-019, T-100, and P-018.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-015 score fixes | no build task |
| P-016 citations, confidence, unread content | no build task |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 |

## Pending decisions for the user

1. D-041 to D-044: confirm or reject under D-054.
2. @software-engineer's QUESTION in `team/DISCUSSION.md`: when `route()` gives hold or no_match there is no carrier to name, so the package is refused even for the user. Should the user be able to name a carrier in the send line?
3. B-185 and B-183: the code cannot prove the send line or the underwriter id came from the person named (`[NEEDS LEGAL CONFIRMATION]` before real files).
4. P-018: waits on `approve change P-018` (parked). P-019/T-099 and T-100: parked.
5. OCR price basis in the cost model: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-020 | @compliance | Item (e), T-087; (a) to (d) are met |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. T-087 quote tracking by @software-engineer (T-020 item e, the last item of the veto), then @compliance.
2. The remaining reviewers of T-079, T-085, and T-086 (@senior-underwriter, @account-manager, @model-risk for T-079).
3. T-083 carrier match (blocked on the @responsible-ai T-082 veto), or only after the demo: `architecture.md` stale lines and the reviews of T-094 to T-096.

## For the AI Engineer

- Pending proposals: P-018 (parked); P-019 (parked, needs D-054 confirmation).
- Latest eval scores: no new run. Baseline SUB-077 to 086: 2 of 8 scored fields at the D-013 pilot floor of 9/10.
- Top failure to fix next: no quote status per submission and carrier from the carrier replies (T-087, T-020 item e).
