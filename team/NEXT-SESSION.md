# Next session

Written 2026-10-17 by the orchestrator at wrap-up. Wrap-up commit: `26c1dc1` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** The main folder `-insureflow-ai-1` stays on `feat/gcp-infrastructure` with the user's uncommitted work: never touch it. Its `team/NEXT-SESSION.md` is stale; read this one.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>` (about 46 older import-path/type errors are pre-existing).
- Roster now includes @frontend-engineer and @senior-test-engineer (D-106, from the user's PR #9/#10 merges).

## Frozen for T-104 (D-105, D-107)

- **Code: `1cf001f`.** `underwriting_pipeline/` unchanged since (checked at `3678c0f` and `26c1dc1`). No code change until T-104 is run and scored.
- **T-104 files and gold: `3678c0f`.** SUB-174–205: 20 in scope + 12 out (C1 scanned app 4, C2 multi-location 5, C3 non-English 4, C4 not identified 2; two-criteria 3). In-scope gold: complete 7, review pending 2, incomplete 11; carrier_a 2, senior_referral 15, no_match 3. Summary: `deliverables/senior-underwriter/T-104-gold-summary.md`. **The pipeline has not been run on T-104.**

## Where we stopped (D-105 to D-107)

- **P-055 approved (D-105) and built (T-104a):** detector `scope-v2` (`underwriting_pipeline/ai/scope.py`, inventory C-4, Tier 2, deterministic, fail closed). An out-of-scope file is `manual_intake` as a whole file: no model call, no field, no route/provisional/suggested market, no missing-info draft; approve, edit, send and confirm are refused with the reasons; the card lists every reason. As-built: `deliverables/ai-engineer/p-055-as-built.md`.
- Dev out of scope: SUB-129, 140, 142, 143, 144, 145 (also 163, 168, 169, 170, 172). Inbox-wide: language_unsure 0 (code-review fix, was 60).
- **Reviews:** @model-risk BLOCK (H1 location leak, H2 unnamed OCR page) → look-again APPROVE WITH CHANGES, no High (`check-T-104a.md`). @senior-underwriter UI APPROVE WITH CHANGES (H1 "Not read: none") → fixed → APPROVE (`ui-check-T-104a.md`).
- **T-104 built in three rounds (D-107):** the first build had no carrier-format loss run, so no in-scope file could be complete; rebuilt with Carrier A/B/C layouts; SUB-199 replaced by a clear multi-location file; then unintended gaps removed (hood inspection dates, stories, two plain-office Carrier A files).
- Backlog B-398 to B-403. Self-checks at wrap-up: llm_extract, prepare, intake, package, workbench, points all ok.
- Standups missing for this session's turns: @model-risk (T-104a check and look-again) and @producer (its role cannot write team/).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Scorer path for T-104 (B-400):** scorer v5 does not know `manual_intake`; the P-055 detection measures (leakage, recall per criterion, reason accuracy, false manual intake ≤ 2/20) need a scorer change before T-104 is scored. Scorer change = D-017 `approve change P-###` (a new proposal, or say it fits within P-055). Must be built and frozen **before** the T-104 run.
2. **When to run T-104** (smoke first, .venv, paced, run once, score once with `--write`).
3. **P-056 (a)** (still open from D-104): confirm ambiguous dates read month first and flagged.
4. **B-402:** premises named only in the email: in or out of scope under P-055 (for later wording, not this hold-out).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | T-104 run and scored once on frozen code `1cf001f` and gold `3678c0f`, smoke first, .venv, paced, scorer v5 with the P-055 detection path: all 9 fields at 9/10 on the 20 in-scope files, 0 false completes, 0 unsafe, route ≥ 18/20, 0 leaks, 100% detection per criterion, false manual intake ≤ 2/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the worktree and branch (`ai-team`), `git diff 1cf001f -- underwriting_pipeline` empty. User decision on the scorer path (pending 1).
2. If approved: build the v5 P-055 detection path (scorer only, no pipeline code change), self-checks on dev files, @model-risk check (High only), freeze the scorer and record its hash.
3. Run T-104 once and score once as in the T-027 row; @model-risk writes the T-027 memo.

## For the AI Engineer

- Pending: none open as P-###; needed: a scorer proposal for the P-055 detection measures (B-400).
- Latest scores (dev, v4, unchanged this session): SUB-127–146 premises 18, effective_date 19, operations 19, status 17, 0 false completes, 0 unsafe, route 16/20 (old gold). P-055 detector, dev: 11 out-of-scope files detected with every expected reason; boundary files stay in scope. T-103 stays as published.
- Top failure to fix next: no scorer can yet measure the P-055 detection gate, so T-104 cannot be scored (B-400).
