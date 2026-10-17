# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `fd93be4` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** The main folder `-insureflow-ai-1` stays on `feat/gcp-infrastructure` with the user's uncommitted work: never touch it. Check `git branch --show-current` says `ai-team` before work.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder. **The ai-team worktree's cache holds only the T-103 replies.** The dev SUB-127–146 replies are in the main folder's `underwriting_pipeline/cache/extractions` (copy them, read-only). SUB-147–153 have no reply under the current prompt anywhere. This session's 7 live calls went to a temp cache only and are gone.

## Where we stopped (D-103)

- **P-056 built** (`fd93be4`; as-built `deliverables/ai-engineer/p-056-as-built.md`): (a) 2-digit years; an ambiguous day/month is read month first and flagged "date read month first (US order)"; (b) scan floor uses the average of the cited words for text fields, while numbers and dates keep their lowest digit group (@model-risk H1 closed); (c) " ... " quote joins; (d) trailing-period reword; (e) "(loc N)" values from one application become locations, not a conflict (loc 1 required); (f) the operations check reads the whole cited document. What's new line, screenshot `D-103-P-056-values-differ-by-location.png`.
- **Dev before/after** (v4, same replies; `evals/P-056-dev/`): SUB-127–146 premises 17→18, effective_date 18→19, conflict 16→17, status 18→17 (SUB-134 now flagged for "light manufacturing"), automation 4→3 of 6, 0 false completes, 0 unsafe, route 16/20 (old dev gold, B-392 M4). SUB-147–153: no change.
- **Scorer v5** (`eval_holdout_v5.py`; v4 frozen) plus the checklist section of `operations-gold-rule.md`: a "- Operations items:" line; an item is a hit when its words appear together, in order, in one clause, with no negation before or after. @model-risk H2 closed. **H3 ("Live music - no") fix is built with 7 probes, but the @model-risk look-again on H3 has not run. Score no gold with v5 until H3 closes.**
- **P-055 revision 2** (`deliverables/pm/proposal-P-055.md`): the user's scope answers, the ceiling of 2 in 20, the 20 + 12 hold-out, and H1/H2 applied. @model-risk: **APPROVE WITH CHANGES** (M1–M3 below). Not approved, not built.
- B-397: the stronger-model test is deferred.
- Wrap-up checklist (`.claude/commands/wrap-up.md` item 2): the orchestrator writes labelled standups for a role that took a turn and wrote none.
- Self-checks at wrap-up: llm_extract, prepare, intake, package, workbench, points all ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-055:** settle @model-risk M1–M3 in the text first. M1: a measurable rule for "substantial non-English" (the text says "mostly"). M2: what the detector does when it cannot tell which document is the application. M3: whether a file that matches two criteria counts under both. Also confirm: **email-only files stay in scope** (they were not in your D-103 list; draft 1 had them out). Then `approve change P-055` or not.
2. **P-056 (b) scope:** is the narrowing (numbers and dates are not averaged; dates score every quote word) inside your approval, or does it need its own P-###? @model-risk closed H1 but leaves this to you.
3. **P-056 (a):** confirm that ambiguous dates are read month first and flagged. This replaces P-016 D2, which refused them; the 2-digit fix alone would not have read "3/1/27".
4. Backlog from the check (`deliverables/model-risk/check-P-055-P-056-v5.md`): P-056 M1 policy-period ranges like "3/15/2026-3/15/2027" no longer parse (regression, no current file has one); M2 the location label is not tied to the field's own line; M3 multi-location applications no longer stop on a premises conflict until P-055 is built.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | Approved P-### fixes (P-056 now built), then a new frozen hold-out (under P-055 if approved: 20 in scope + 12 out of scope, gold first with scope labels and an operations checklist, scorer v5 once H3 closes), smoke first, .venv, paced, run and scored once: all 9 fields at 9/10, 0 false completes, 0 unsafe, route ≥18/20, plus the P-055 detection measures. |
| Scorer v5 | @model-risk (OBJECTION H3) | Look-again on the built H3 fix (clause rest only no/none/n/0 = miss; 7 probes in the self-check). |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the worktree and branch (`ai-team`). @model-risk look-again on v5 H3 only.
2. User decisions 1–3. If P-055 is approved: build the detector (Tier 2 inventory entry, fail closed), the workbench "Manual intake" card and the blocked send (D-065), with self-checks.
3. @senior-underwriter plans the next hold-out gold (20 + 12, scope labels, operations checklist) under the D-102/D-103 rules; build it only when the user says so.

## For the AI Engineer

- Pending: P-055 (revision 2, @model-risk APPROVE WITH CHANGES, M1–M3); P-056 (b) scope ruling; v5 H3 look-again.
- Latest scores (dev, v4, `fd93be4`): SUB-127–146 premises 18, effective_date 19, operations 19, status 17, 0 false completes, 0 unsafe, route 16/20 (old gold). T-103 stays as published: route 16/20, operations 7/20, T-027 KEEP.
- Top failure to fix next: out-of-scope files (scanned application, multi-location, non-English) need the P-055 detector before the next hold-out.
