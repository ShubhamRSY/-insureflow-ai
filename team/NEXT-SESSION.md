# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `8ada0f9` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start. Standing rules: D-065 (definition of done = backend + UI) and D-069 (sandbox and test runs never write real workbench, log or outbox files; in CLAUDE.md).

## Where we stopped

- D-069: P-026 built (B-220 closed): every approve row stores `run_hash` and `at`; the send gate and the acknowledgment check count only an approve whose hash equals the current saved run, for every actor; otherwise "Re-review needed: file changed since your approval". A stale card cannot approve (hidden `run_hash`). @model-risk: **APPROVE**; T-027 veto stands.
- B-248/B-250: sent date comes from a `Sent-on:` header written at send, not file mtime. Packages sent before this (SUB-009 included) show "not recorded"; no date was guessed. Every send (account manager too) is logged in `sends.jsonl` with date, reason and `run_hash`.
- B-252: `workbench.sandbox(tmp)` and `--serve --sandbox [DIR]` point the page, logs, outboxes and model cache at a copy; self-check asserts real files unchanged.
- Session B UI: per-file History panel (who, why, when, short run hash, mark when not current); subjectivity closures with "carrier's word = evidence only"; Suggested market field; footer with model and prompt version. Screenshots `deliverables/software-engineer/screenshots/D-069-*.png` (sandbox).
- @senior-underwriter UI check: **APPROVE WITH CHANGES**, no High. Medium/Low B-264 to B-267. @model-risk Medium/Low B-260 to B-263.
- After demo (backlog): B-257 account manager checks on the card, B-258 carrier override form, B-259 upload.
- Self-checks at wrap-up (no model host): llm_extract, prepare, intake, package, workbench, points all ok.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-015 score fixes | no build task |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 (the workbench draft approve calls the existing `prepare.approve`) |

## Pending decisions for the user

1. B-260: a byte-identical re-save keeps the same hash, so the old approve still counts. Accept, or add a save id to the hash.
2. The confidence-versus-hit table (B-222), needed to lift T-027; then the new 20-file hold-out (T-091 to T-093).
3. Demo readiness: SUB-009's existing package has no recorded send date; re-send in the demo needs a written resend reason.
4. Parked: P-018, P-019/T-099, T-100. OCR price basis: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | The confidence-versus-hit table built, then the new 20-file hold-out (T-091 to T-093), gold first, scored once |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. B-264 to B-266 (suggested market wording, footer model from the saved run, what changed since approval) (@software-engineer), screenshots.
2. B-222 confidence-versus-hit table (@ai-engineer-assistant) once @user says so.
3. A demo walk-through in the sandbox on SUB-009, SUB-029, SUB-010, SUB-038 (@senior-underwriter), then `deliverables/pm/demo-guide.md` updated to the current workbench.

## For the AI Engineer

- Pending proposals: none. P-026 approved by @model-risk.
- Latest eval scores (quick-15, P-025-fix, cached; hit / hit (needs review)): named_insured 13/0, operations 12/1, sales 13/0, construction 13/1, year_built 15/0, premises 12/0, tiv 14/0, loss_runs 8/1, conflict 10/3, status 12/1. No extraction change this session, so no rerun.
- Top failure to fix next: B-222 (the table @model-risk needs for T-027); on scores, SUB-074.
