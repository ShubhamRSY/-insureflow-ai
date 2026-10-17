# Next session

Written 2026-10-17 by the orchestrator at wrap-up. Wrap-up commit: `630a6a0` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** The main folder `-insureflow-ai-1` stays on `feat/gcp-infrastructure` with the user's uncommitted work: never touch it. Its `team/NEXT-SESSION.md` is stale; read this one.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder. The dev SUB-127–146 replies are in the main folder's `underwriting_pipeline/cache/extractions` (copy them, read-only). `intake.py` self-check runs with no argument.
- pyright is not installed in the worktree (D-097 diagnostics could not run this session).

## Where we stopped (D-104)

- **P-055 revision 3** (`deliverables/pm/proposal-P-055.md`): the user's wording for @model-risk M1–M3. Non-English = common non-English words outnumber common English words, names and addresses not counted, unsure → manual intake. New criterion 4: application not identifiable (including email-only files) → manual intake; email-only files are no longer in scope (amends D-103). A file matching several criteria counts under each for detection, once in totals; the card lists every reason. @model-risk L1 also added (an automated missing-info draft counts as a leak; stricter only). **Not approved, not built.**
- **P-056 (b):** the narrowing (numbers and dates keep the lowest-word drop test; a date scores every quote word) recorded as a clarification within P-056, no new P-###.
- **P-056 M1 fixed** (`630a6a0`): `_RANGE` in `llm_extract.py`; "3/15/2026-3/15/2027", "03/15/2026-03/15/2027", "3/15/26-3/15/27", "3/15/26 – 3/15/27" read two dates; self-checks added. No inbox file has a joined range, so no dev count changed and no re-score was run. No What's new line (P-056's line covers it).
- **@model-risk third look-again:** P-056 M1 CLOSED; scorer v5 H3 CLOSED; no new High. Scorer v5 can now be used for new gold. Backlog: P-056 L5 (all-hyphen "3-15-2026-3-15-2027" and half ranges read no date: goes to review); v5 M2 ("Live music - none at all", "Live music not" still hit).
- Self-checks at wrap-up: llm_extract, prepare, intake, package, workbench, points all ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-055 revision 3:** type `approve change P-055`, or not. Also confirm the @model-risk L1 addition, and whether the 12 out-of-scope hold-out files should include email-only / unidentifiable-application files (the text keeps 4+ per criteria 1–3 and treats criterion 4 as fail-closed).
2. **P-056 (a):** confirm that ambiguous dates are read month first and flagged (replaces P-016 D2; @model-risk L1).
3. Backlog from the D-103 check still open: P-056 M2 (location label not tied to the field's own line); M3 (multi-location files route on loc 1 until P-055 is built).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | A new frozen hold-out (under P-055 if approved: 20 in scope + 12 out of scope, gold first with scope labels and an operations checklist, scorer v5), smoke first, .venv, paced, run and scored once: all 9 fields at 9/10, 0 false completes, 0 unsafe, route ≥18/20, plus the P-055 detection measures. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

Scorer v5 H3 objection: closed (D-104).

## First 3 tasks next session

1. Check the worktree and branch (`ai-team`). User decision on P-055 revision 3.
2. If P-055 is approved: build the detector (Tier 2 inventory entry with a version id, deterministic, fail closed), the workbench "Manual intake" card listing every reason and the blocked send (D-065), with self-checks; @model-risk check, High only.
3. @senior-underwriter plans the next hold-out gold (20 + 12, scope labels, operations checklist, v5) under the D-102/D-103/D-104 rules; build it only when the user says so.

## For the AI Engineer

- Pending: P-055 revision 3 (awaiting `approve change P-055`).
- Latest scores (dev, v4, `fd93be4`, unchanged by D-104): SUB-127–146 premises 18, effective_date 19, operations 19, status 17, 0 false completes, 0 unsafe, route 16/20 (old gold). T-103 stays as published: route 16/20, operations 7/20, T-027 KEEP.
- Top failure to fix next: out-of-scope files (scanned application, multi-location, non-English, no identifiable application) need the P-055 detector before the next hold-out.
