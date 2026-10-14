# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `dfc79de` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start. D-065 (definition of done = backend + UI) applies to every builder task.

## Where we stopped

- D-068: P-025 kept and fixed. @model-risk re-check: **APPROVE**, H1 (B-243) and H2 (B-244) closed. T-027 veto stands.
  - B-244: one needs-review list (`package.needs_review_ids`, used by the workbench too); `send_to_carrier` refuses, for every actor, while the latest approve's acknowledgment does not cover every needs-review value. Card: "Send refused: N values need review and are not acknowledged (...)".
  - B-243: `regression_dev.py` split counts conflict like status and adds premises; `--self-check` added.
  - B-247: a resend writes `SUB-###-resend-N.md`; earlier package files are kept; card lists every package sent.
  - B-249 (the user called it B-248): the send form is hidden until an approve is logged; card says "Approve first". B-248 (SUB-009 sent-date mismatch) stays open.
- @senior-underwriter UI check: **APPROVE**, no High. Lows B-253 to B-256. B-252: sandbox `serve()` rewrites the real `workbench.html`.
- Quick set of 15, P-025-fix (`regression-quick-15-2026-10-14-P-025-fix.json`), 0 model calls. No plain hit comes from a low-confidence value.
- Screenshots (sandbox): `deliverables/software-engineer/screenshots/D-068-*.png`.
- Earlier today: P-022, P-023, P-016, P-024, P-025 built; workbench reads saved runs only, plain refusals, send action, draft approve, folded no-run cards, carrier named on the send form, resend needs a reason.
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

1. B-220 (Medium, raised twice by @model-risk): an acknowledgment is matched by field id only, so a re-saved run with a new value in an acknowledged field passes the send gate without a fresh approve.
2. Which remaining D-065 UI gaps to build (override form, decision/acknowledgment history, subjectivity closures, model version, intake upload).
3. The confidence-versus-hit table (B-222), needed to lift T-027; then the new 20-file hold-out (T-091 to T-093).
4. Parked: P-018, P-019/T-099, T-100. OCR price basis: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | The confidence-versus-hit table built, then the new 20-file hold-out (T-091 to T-093), gold first, scored once |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. B-220: tie the acknowledgment to the value and quote, not only the field id (@software-engineer), with UI and screenshot.
2. B-222 confidence-versus-hit table (@ai-engineer-assistant) once @user says so; it is on the T-027 path.
3. B-248, B-250 (sent dates), B-252 (sandbox serve writes the real page); then the remaining reviewers of T-079, T-083, T-085, T-086, T-087.

## For the AI Engineer

- Pending proposals: none. P-025 approved by @model-risk after the fixes.
- Latest eval scores (quick-15, P-025-fix, cached; hit / hit (needs review)): named_insured 13/0, operations 12/1, sales 13/0, construction 13/1, year_built 15/0, premises 12/0, tiv 14/0, loss_runs 8/1, conflict 10/3, status 12/1.
- Top failure to fix next: B-220 (acknowledgment by field id survives a changed value); on scores, SUB-074.
