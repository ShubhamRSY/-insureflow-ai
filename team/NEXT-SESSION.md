# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `33e399a` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Run every pipeline command with `.venv/bin/python`.** Score files are written only with `--write`; re-scores use `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`. Hold-outs use `eval_holdout_v4`.
- **Branch warning (D-100).** At 14:31 something outside this session checked the main repo folder out to `feat/gcp-infrastructure` and kept committing there (Terraform, `infra/gcp/`, including two ~119 MB provider binaries that GitHub will refuse). This session's P-054 commits first landed there and were cherry-picked onto ai-team; the rest of the session ran in a separate ai-team worktree (user's choice). **Before work: `git branch --show-current` must say `ai-team`.** The GCP commits are not confirmed (D-045/D-053) and are not on ai-team. The main folder still holds the user's uncommitted `src/`, `tests/`, `docs/rag/`, `scripts/` changes.

## Where we stopped (D-100)

- **P-054 built and approved** (`9320666`, `3557e4a`): neutral list holds only non-occupancy words (shop, store, gift, home, trade and goods words, and "cooking" except the empty "Cooking: none" label, go to senior_referral, Carrier A suggested); W2e vacancy variants block the confirm; a carrier named in the same sentence as a decline word in any note on the file (route note, fields, text documents) is excluded. @model-risk check-P-054 OBJECTION (H1, H2) → fixed → look-again **APPROVE**, no High.
- **Code frozen at `3557e4a`** (D-100 item 2).
- **Dev re-check SUB-127–146** (`8d3e4f0`; v4, cache, 0 calls, clean `3557e4a`): 0 unsafe, 0 false completes, route 16/20, **dev route gate FAIL** on gold that predates R17 (SUB-127/128/129/135 gold carrier_a, now senior_referral; safe direction). senior_referral 18/20, carrier_a 1.
- **T-103 built, gold frozen at `33e399a`**: SUB-154–173 by @producer per the mix and @model-risk's 2026-10-16 addendum (condition 3: file 13 is the JPG applicant note; file 8 light wholesale states non-hazardous; file 11 states a TIV). SUB-154/155/162 operations reworded to R17 words before the freeze (my first dispatch left out that constraint). Gold by @senior-underwriter from documents and written rules only: carrier_a 3 (154, 155, 162), senior_referral 12, no_match 3, hold 2; complete 5, review pending 3, incomplete 12. **Pipeline not run on them.**
- Self-checks at wrap-up: llm_extract, prepare, intake, package, workbench, points all ok.
- Standup missing: @producer (outside party, cannot write team/).
- Backlog B-392, B-393.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Run T-103** on the frozen code `3557e4a` with frozen gold `33e399a`: smoke_readers.py first, .venv, paced, scorer v4 with `--write`, run and scored once (T-027 path). Note: SUB-154/155/162 business names hold trade words (Tax, Candle, Bookkeeping); R17 reads only operations text, so if extraction copies a name into operations they go to senior_referral (safe miss).
2. **@model-risk L2 (check-P-048):** state whether route is part of the T-027 gate before T-103 is scored (v4 gate says yes: 0 unsafe, ≥18/20).
3. **Dev gold** (B-392 M4): have @senior-underwriter update SUB-127–146 gold to R17, or leave the dev gate failing on stale gold.
4. **The GCP branch** and the `5ceeef8` roles (B-388): confirm or reject.
5. Senior-underwriter ambiguities for @head-of-underwriting (T-103-gold-summary.md): SUB-161 negated hazard words, SUB-173 "retail food", SUB-167 hold with no provisional route.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | T-103 runs: gold first (done, `33e399a`), smoke first, .venv, paced, scorer v4 with `--write`, run and scored once on a frozen commit (`3557e4a`); all 9 fields at 9/10 or better, 0 false completes, 0 unsafe routes, route at least 18/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the branch (`ai-team`), then user decisions 1–2.
2. If the user says run: T-103 run and score once (decision 1), @model-risk reads the result against the T-027 gate.
3. Decisions 3–5.

## For the AI Engineer

- Pending: no open P-###. Decisions: run T-103; dev gold update; GCP branch; B-388 roles.
- Latest scores (dev SUB-127–146, v4, cache, `3557e4a`): 0 unsafe, 0 false completes, route 16/20 (gate FAIL on stale gold), loss runs 8/0/12, operations 19/20.
- Top failure to fix next: the dev gold predates R17, so the dev route gate cannot pass; T-103 is the real measure.
