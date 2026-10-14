# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `8649434` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- D-064: P-023 built (B-214): with LLM_BASE_URL or LLM_MODEL unset, extraction stops with a clear message, zero calls; Ollama only when the URL names localhost.
- D-064: P-016 built as approved in D-039 (N2 H2 D2 R1 Q1 C3 S2 G2 L1 E1 P1 K1). `ai/` by @ai-engineer-assistant; workbench by @software-engineer: rows show "NEEDS REVIEW: reason" and the quote, `unread` rows show file/page/reason; approve is refused unless every needs-review value is acknowledged; the log row gains `acknowledged`. PROMPT_VERSION unchanged (82be09bd42f7). Memo `deliverables/ai-engineer/p-023-p-016-as-built.md`. Page not served in a browser.
- @model-risk on P-016: **APPROVE WITH CHANGES**. **High-1 open (B-215):** when the model reports a conflict whose sides agree, each side's needs_review/reason/quote is dropped and the value is stored unflagged, so it is never acknowledged at approve (reproduced: "280,000" vs "$280k" from a scan). Resolve: keep each side's flag and citation; flag the stored value if any side was flagged; self-check. `ai/` change: @user decides whether it is a P-016 fix or a new P-###. Medium/Low B-216 to B-226.
- Quick set of 15 after P-016, one run: 15 from cache, 0 model calls. Changes against the P-022 run: SUB-038 (scan) loss_runs and status hit→miss; SUB-067 (scan) operations and construction hit→miss, conflict hit→not_credited. SUB-074 unchanged. Cause: the C3/S2 scan gates drop low-OCR scan values.
- Demo guide lists SUB-029 as "development-set file", plus SUB-010. The saved demo runs SUB-009/029/010 were saved before P-016 and lack quote/reason/unread keys; a re-save is cache-only for the extraction.
- Earlier today (D-063): P-022 built, @compliance APPROVE; demo re-save SUB-009 (clean), SUB-029 (missing info), SUB-010 (TIV 0 hold).
- Self-checks at wrap-up (no model host): llm_extract, prepare, intake, package, workbench, points all ok.
- Standup entries this session: @ai-engineer-assistant, @software-engineer, @model-risk.
- Still open: T-079, T-083, T-085, T-086, T-087 remaining reviewers; B-190, B-191, B-194, B-197, B-198 on the backlog; P-019, T-100, P-018 parked.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-015 score fixes | no build task |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 |

## Pending decisions for the user

1. B-215 (P-016 High-1): fix under P-016, or number it P-024 and "approve change P-024".
2. Re-save SUB-009, SUB-029, SUB-010 with the P-016 code (cache only) before the demo.
3. The confidence-versus-hit table (B-222), which @model-risk needs for T-027 (b): a scorer-output change; say whether to build it.
4. P-018 (parked). P-019/T-099 and T-100: parked. OCR price basis: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | High-1 (B-215) closed, the confidence-versus-hit table built, then the new 20-file hold-out (T-091 to T-093), gold first, scored once |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. B-215 fix once @user approves it, with the self-check @model-risk asked for; then @model-risk re-checks High-1.
2. Re-save the 3 demo runs with the P-016 code, and serve the workbench once on SUB-009 to see the needs-review list and the acknowledgment.
3. The remaining reviewers of T-079, T-083, T-085, T-086, T-087; then @pm closes what is approved.

## For the AI Engineer

- Pending proposals: B-215 needs your line (P-016 fix or P-024). Nothing else waiting.
- Latest eval scores (quick-15 after P-016, cached): named_insured 13/15, operations 12, sales 13 (+1 flagged), construction 13, year_built 15, premises 12, tiv 14, loss_runs 8 (5 not credited, 1 miss, 1 flagged), conflict 12 (1 not credited, 2 flagged), status 12.
- Top failure to fix next: B-215 (a flagged scan value can be approved without acknowledgment). On scores: SUB-074 (5 misses, unchanged).
