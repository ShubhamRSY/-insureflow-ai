# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `ff4767c` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start. D-065 (definition of done = backend + UI) applies to every builder task.

## Where we stopped

- D-067: P-025 option D built (@ai-engineer-assistant): on scans only, a value at 0.50 to below 0.75 is stored needs_review with reason "Low-confidence scan read — check against the page"; below 0.50 dropped; typed unchanged; prompt unchanged. `regression_dev.py` reports "hit (needs review)" apart. Memo `deliverables/ai-engineer/p-025-as-built.md`.
- Quick set of 15 after P-025 (`regression-quick-15-2026-10-14-P-025.json`), 0 model calls: plain hits unchanged except conflict 12→13; "hit (needs review)": operations 1, construction 1, loss_runs 1, status 1 (SUB-038 loss_runs/status, SUB-067 operations/construction).
- @model-risk on P-025: **REJECT**, re-check once closed. **H1 (B-243):** SUB-067's conflict became a plain hit only because of a low-confidence value (break of "never as plain hits"); `CHECK_FIELD` leaves out premises→premises_address. Fix: treat conflict like status in the split, add premises, rerun quick set into a new file. **H2 (B-244):** a 0.50–0.74 scan value counts toward complete and `agency_problem` never reads needs_review, so it can reach a carrier package unacknowledged (SUB-038 became complete). Fix: refuse the send while any low-confidence scan row is unacknowledged; self-check. Medium/Low B-245, B-246.
- Workbench (@software-engineer): B-231 saved-run cards first, no-run cards folded in one closed "No saved run (N)"; B-232 send form names the carrier, "No send: <reason>" on hold/incomplete/refused cards; B-233 second send refused unless a written resend reason, logged in `sends.jsonl` (check in `package.send_to_carrier`). Screenshots (sandbox): `deliverables/software-engineer/screenshots/D-067-*.png`.
- @senior-underwriter UI check: **APPROVE**, no High. Medium/Low B-247 to B-251.
- Earlier today: P-024 (B-215 closed), P-016, P-022, P-023 built; demo runs SUB-009, SUB-010, SUB-029 re-saved from cache.
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

1. P-025 REJECT: fix H1 (B-243, `ai/regression_dev.py`) and H2 (B-244, `app/package.py`) as @model-risk wrote, or roll P-025 back. H1 touches the score report under `ai/`.
2. Which remaining D-065 UI gaps to build next (override form, send/decision/acknowledgment history, subjectivity closures, model version, intake upload).
3. The confidence-versus-hit table (B-222), needed to lift T-027.
4. Parked: P-018, P-019/T-099, T-100. OCR price basis: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | The confidence-versus-hit table built, then the new 20-file hold-out (T-091 to T-093), gold first, scored once |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |
| P-025 | @model-risk (REJECT) | H1 (B-243) and H2 (B-244) closed, then re-check |

## First 3 tasks next session

1. B-244 send gate for unacknowledged low-confidence scan values (@software-engineer), with UI reason and screenshot (D-065).
2. B-243 score split fix (@ai-engineer-assistant) once @user says so; quick set into a new file; @model-risk re-check of P-025.
3. B-247 to B-250 (resend overwrite, sent date) before any demo resend; then the remaining reviewers of T-079, T-083, T-085, T-086, T-087.

## For the AI Engineer

- Pending proposals: none new. P-025 is built but REJECTED by @model-risk (H1 score split, H2 send gate).
- Latest eval scores (quick-15 after P-025, cached): named_insured 13/15, operations 12 (+1 needs review), sales 13, construction 13 (+1), year_built 15, premises 12, tiv 14, loss_runs 8 (+1), conflict 13, status 12 (+1).
- Top failure to fix next: B-244 (a low-confidence scan value can reach a carrier package unacknowledged).
