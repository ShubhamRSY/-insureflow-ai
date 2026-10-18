# Next session

Written 2026-10-18 by the orchestrator at wrap-up. Wrap-up commit: `8eff864` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1` (user's uncommitted work); its `team/NEXT-SESSION.md` is stale. The code-review plugin reviews the main folder's diff, not the worktree: review the worktree diff by hand or point the plugin at it.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder. `regression_dev.py` with no argument makes live calls (B-405).
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>` (23 old errors in llm_extract/prepare, none in changed lines).

## Where we stopped (D-111)

- **P-059 built** (T-106a): the prompt keeps items from the Cooking operations, Hood and Line of business lines (prompt `759b3e6bc9b2`, was `b025802c0dfa`). The whole-document check (`prepare.py` `ops_line_missing`, `OPS_EXTRA`) flags gas, "no cooking", the cooking clauses and the hood dates missing from the answer. It now flags all 3 T-104 silent errors (SUB-180 gas, SUB-201 snack warmer, SUB-204 no cooking).
  - Why the old check missed them: it compared word-list items only, and "no gas", appliance words and "None" under cooking were not on the list. Details: `deliverables/ai-engineer/p-059-p-060-as-built.md`.
  - **No live run yet.** All in-scope dev cached replies are on the old prompt (B-415: quick 15 = 5 calls; dev SUB-127–173 = 36 calls). If the model ignores the new sentence, 33/38 cooking-line dev files would drop to "complete — review pending".
- **P-060 built** (T-106c): `eval_holdout_v7.py` (sha256 `efe532a0006e21e6…`) = v6 + the loss-run mark. v6 is frozen and unchanged (`4bf1cd63…`).
- **Routes check** (T-106b, report only): `deliverables/head-of-underwriting/T-104-route-check.md`. SUB-182 and SUB-186 are code wrong; SUB-174's rule is unclear (the line-of-business question); SUB-201 is gold wrong as written (the W1/W1b tables conflict, and "small kitchen" is an R9 word). Drafted, not built: **P-061**, **P-062**.
- **Lint** (T-106d): `deliverables/senior-test-engineer/lint_holdout.py PLAN.json --run-date YYYY-MM-DD` (`--self-check`: 24 cases). It checks that loss-run valued dates are before the run date, that the Scope lines parse, the plan mix, and `undated_loss_runs`. It is the gold-freeze gate (RUN-RULES). Example plan: `T-104-plan.json`. T-104 fails it, as expected.
- **@model-risk** (`deliverables/model-risk/check-P-059-P-060-T-106d.md`): P-059 APPROVE WITH CHANGES, no High, code may be re-frozen. v7 APPROVE. Lint BLOCK (H1 dates, H2 undated) → both closed in look-again 2.
- Reviews not run: @senior-underwriter UI review (the only UI change is a What's new line). The T-106a screenshot is not taken (B-423).
- Missing standups for today: @ai-engineer-assistant, @head-of-underwriting, @senior-test-engineer, @model-risk (told not to edit team/ while running in parallel).
- Backlog: B-415 to B-424.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-061** (drafted by @head-of-underwriting): class words are read from the Line of business and Cooking operations lines (SUB-174, 182, 186). Re-check after P-059's live run first; P-059 may already fix 182 and 186. It also needs @head-of-underwriting's ruling on whether the line of business counts as class text.
2. **P-062** (drafted): nightclub/lounge is always R1 (no_match, never referable, even while held), and snack-only food is not restaurant evidence (SUB-201; closes the W1-vs-W1b conflict). @model-risk H2 asked for this.
3. **Live check of P-059** (B-415): allow 5 + 36 calls (qwen, paced 55 s)?
4. Re-freeze once 1–3 are settled; then a new 20 + 12 hold-out, gold first, lint passing.
5. Still open: P-056 (a) month-first dates (D-104); B-402 email-only locations wording; detector gaps B-398/B-404.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | H1 (P-059 built, live check owed) and H2 (P-061/P-062 approved and built) checked on dev files; re-freeze; a new 20 + 12 hold-out, gold first, lint passing (loss runs valued before the run date, at least 2 held W1 files, at least 2 office-lessor / deli files); run and scored once with v7, meeting all 15 criteria. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the worktree and branch. The user decides on the live P-059 check (B-415) and on P-061/P-062.
2. If allowed: the live quick 15 + dev SUB-127–173 on the P-059 prompt (report the operations flag rate and status automation), then re-check SUB-182/186 routes; build the approved P-061/P-062 with dev self-checks; @model-risk check, High only.
3. Re-freeze. @senior-underwriter + @producer write the next hold-out plan as JSON (routes under current rules, `undated_loss_runs` declared, B-424). The lint must pass before the gold freeze.

## For the AI Engineer

- Pending: P-061 (class words from LOB / cooking lines), P-062 (nightclub always R1); P-059 and P-060 are built.
- Latest scores (T-104, v6, `6e7cfa2`, as published): P-055 gate PASS; 0 false completes, 0 unsafe; route 16/20; operations 12/20, loss runs 9/20; T-027 KEEP. No new score: P-059 has no live run.
- Top failure to fix next: confirm P-059 live (operations), then the W1 nightclub provisional route (P-062).
