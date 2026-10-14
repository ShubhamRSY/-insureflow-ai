# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `485eed7` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start.

## Where we stopped

- D-063: P-022 approved and built. B-205: `write_drafts()` takes the manifest before extraction reads any file. B-206: `sources.read_folder` skips dotfiles like `folder_manifest`. B-209: `workbench._tiv` holds a TIV with an area unit (sq ft, sq. ft., sqft, sf, square feet/foot). Memo `deliverables/ai-engineer/p-022-as-built.md`.
- @compliance on P-022: **APPROVE**, no High. Low B-211 (metric area units), B-212 (`facts()` TIV digits), B-213 (change-and-revert during extraction). B-214 (Low): with LLM_* unset, extraction falls back to localhost Ollama instead of refusing.
- Demo runs re-saved with today's code and a manifest (Groq, openai/gpt-oss-120b): **SUB-009** clean → carrier_a; **SUB-029** missing info (effective_date, loss_run_valued_through) → hold, draft in `simulation/pending-approval/SUB-029.md`; **SUB-010** TIV 0 → hold "TIV missing or unreadable". `manifest_problem` empty for all three. SUB-001..016 have no missing-info case with today's files; SUB-029 is from the dev set (scorers do not read saved runs). Other saved runs SUB-001..016 are still old-format, no manifest, and refused (B-208 partly closed).
- The cache had no hits for SUB-001..016 under the current key; any further re-save needs model calls.
- Quick set of 15 (D-022), one run: 15 from cache, 0 model calls, 0 failed attempts; identical to quick-15-after-T-070. File `deliverables/ai-engineer/evals/regression-quick-15-2026-10-14-P-022.json`.
- Token log: run 20261014T143300-63126 has 16 failed localhost rows from a dry run (nothing cached).
- Self-checks at wrap-up (no model host): llm_extract, prepare, intake, package, workbench, points all ok.
- No standup entries this session from @ai-engineer-assistant or @compliance.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.
- Still open from before: T-079, T-083, T-085, T-086, T-087 remaining reviewers; B-190, B-191, B-194, B-197, B-198 on the backlog; P-019, T-100, P-018 parked.

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

1. Whether the demo also needs SUB-001..016 re-saved (model calls; cache has no hits).
2. B-214: should extraction refuse when LLM_* is unset instead of falling back to localhost Ollama? Needs a P-number and "approve change P-###".
3. P-018 (parked). P-019/T-099 and T-100: parked.
4. OCR price basis in the cost model: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | P-016 built, then the new 20-file hold-out scored once (T-091 to T-093) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. The remaining reviewers of T-079, T-083, T-085, T-086, T-087; then @pm closes what is approved.
2. Walk the demo once on SUB-009, SUB-029 and SUB-010 in the workbench (send gate, hold notes, missing-info draft).
3. Demo-blocker check: `team/DEMO-BLOCKERS.md` against what is now built.

## For the AI Engineer

- Pending proposals: none awaiting your line. P-022 built. B-214 needs a number if wanted. P-018, P-019 parked.
- Latest eval scores: quick-15 (2026-10-14, cached): named_insured 13/15, operations 13, sales 13 (+1 flagged), construction 14, year_built 15, premises 12, tiv 14, loss_runs 9 (5 not credited, 1 flagged), conflict 13 (2 flagged), status 13.
- Top failure to fix next: SUB-074 (operations, construction, premises, tiv, status all miss) and SUB-067 (named_insured, sales, premises, status).
