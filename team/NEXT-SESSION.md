# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `dc88ad0` on `ai-team`. **Not pushed**: `git push -u origin ai-team` was denied by the session's permission check; the user pushes or allows it. Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- T-079 rebuilt by @software-engineer to D-053 in `underwriting_pipeline/app/package.py`: the send reads `decisions.jsonl` itself, after the P-010 status gate and before the actor check; sendable only if the latest logged decision is approve; an approve after a decline needs a non-empty reason; sends never write the log. Status IN_REVIEW, all 5 boxes ticked by the owner.
- @compliance review: **APPROVE WITH CHANGES**. High: `send_to_carrier(..., log_path=DECISIONS_LOG)` lets the caller choose which log decides (breaks criterion 2). Fix: remove the parameter, read `DECISIONS_LOG` directly; the self-check swaps `package.DECISIONS_LOG` in try/finally. T-020 item (a) is met only once this lands. Medium/Low: B-179 (any id counts as an underwriter, incl. an AI-role id), B-180.
- Known gap, by the owner: `workbench.record_decision` still logs an approve after a decline without a reason (the send refuses it).
- @senior-underwriter, @account-manager, @model-risk have not reviewed T-079 (the user limited this session to @compliance).
- Missing standup: @compliance took a turn and has no 2026-10-14 entry in `team/STANDUP.md`.
- Self-checks at wrap-up, no model host: llm_extract, prepare, intake, package, workbench, points all ok.
- Parked by the user until after the demo: P-019, T-100. P-018 parked (not a demo blocker).
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
| D-053 send rule | T-079: built, one High open |

## Pending decisions for the user

1. D-041 to D-044: confirm or reject under D-054 (listed to the user on 2026-10-14; no answer yet).
2. T-079 questions in `team/DISCUSSION.md`: how "last" is ordered (built as final line; log has date, no time) and which ids count as an underwriter (built as any id; B-179).
3. P-018 (error enum): waits on `approve change P-018`. Parked.
4. P-019/T-099, T-100: parked until after the demo.
5. OCR price basis in the cost model ($10.00 vs $1.50 per 1,000 pages).
6. Who updates the stubbed test file to the T-071 signatures.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-020 | @compliance | Items (a), (c), (d), (e), (f); (b) met; (a) met once the T-079 High is fixed |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @software-engineer fixes the T-079 High (remove `log_path`), then @compliance re-checks; then the other T-079 reviewers.
2. The next demo blockers: T-085, T-086, T-087 (T-020 items d, c, e).
3. Only after the demo: stale lines in `architecture.md`, reviews of T-094/T-095/T-096.

## For the AI Engineer

- Pending proposals: P-018 (parked), P-019 (parked, needs D-054 confirmation).
- Latest eval scores: no new run. Baseline SUB-077 to 086: 2 of 8 scored fields at the D-013 pilot floor of 9/10.
- Top failure to fix next: the T-079 send gate takes a caller-chosen log path (@compliance High).
