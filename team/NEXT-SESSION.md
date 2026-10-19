# Next session

Written 2026-10-19 by the orchestrator at wrap-up. Wrap-up commit: `cd3d905` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale. The code-review plugin reviews the main folder's diff: review the worktree with a reviewer agent on `git -C <worktree> diff <from> <to>` (done this way in D-112).
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder. `regression_dev.py` with no argument makes live calls (B-405).
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>` (about 40 old errors in workbench/prepare; the self-check reuses the name `card`, which gives false positives).
- A subagent hit the session limit mid-task on 2026-10-18; it resumed from its saved state with SendMessage, and no call was repeated.

## Where we stopped (D-112)

- **P-061 and P-062 built** (T-107a; `eb2bd84`, `940f40b`, `4682413`, `7cfc959`):
  - Class, bar and prohibited words are read from operations plus the "Line of business:" line, through one `class_text()` shared by `_match` and `confirm_problem`.
  - Cooking equipment on operations or the "Cooking operations:" line is R9 evidence. Negated equipment does not count: "no deep fryer", "Fryer: none", "Oven not used".
  - A class read only from the Line of business never reaches carrier_a.
  - Nightclub and lounge are always R1. Snacks only is not restaurant evidence.
- **W1 and W1b are one table** in carrier-match.md. The stricter rule wins and every row is cited:
  - A bar word beside a non-food operation is now R1 no_match (was R16 senior_referral).
  - Bar, tavern and pub with real restaurant evidence stay R2, as P-062 names that case.
  - The R1 note names the word and its line.
- **T-107c:** a P-052 senior-confirmed carrier passes the account-manager check. R2, held and W1 files never pass, and the card shows the real refusal reason. **T-107d:** What's new shows the latest 5 plus "Show all".
- **Reviews:**
  - Code review (High) fixed: negated equipment turned R1 into R2.
  - Security review fixed: quadratic regex backtracking.
  - @senior-underwriter UI: APPROVE WITH CHANGES; its High was fixed.
  - @model-risk: OBJECTION H1 (a bar word on the Line of business allowed a market confirm), then **APPROVE** on look-again at `4682413`.
- **B-415 live check** (T-107b, `deliverables/ai-engineer/b-415-live-check.md`): 41 calls, 0 failed, 4 retries. Routes on `7cfc959`. 0 unsafe, 0 false completes.

  | SUB-154–173 | Old reply | New reply |
  |---|---|---|
  | Operations hits | 7 | 7 |
  | Routes correct | 13/20 | 13/20 |
  | Silent errors | 8/180 | 9/180 |
  | Status automation | 4/8 | 5/8 |
  | Operations flags | 5/16 files | 1/41 files |

  Dev SUB-127–173 route is 24/47 against dev gold written before P-049, with the 11 no-call files counted as misses. This is not a gate result (B-427).
- **Demo** (T-107e/f/g):
  - Opening best case: SUB-184 → Carrier A → account-manager check passes → sent. Backup: SUB-179.
  - Time saved is labelled an unmeasured estimate: about 10–25 min per in-scope file, about 5–15 over a mix.
  - run-demo.sh replays on the new replies, 0 live calls, all steps pass, and the screenshots are retaken.
  - Second rehearsal: READY WITH FIXES. Its High (an old refusal text in step A2) and the Mediums are fixed in the guide.
- Backlog: B-425 to B-428.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Re-freeze** the code at `cd3d905`, or a later commit if B-428 or B-425 are fixed first for the demo.
2. **Next hold-out** (20 + 12): @senior-underwriter and @producer write the plan JSON under the current rules (P-061/P-062, merged table). The lint must pass before the gold freeze. When to build it?
3. Still open: P-056 (a) month-first dates (D-104); B-402 email-only locations; detector gaps B-398/B-404; B-416/B-417 (ops check polarity and labels, each needs a P-###).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | H1 operations and H2 routes are now built and checked on dev (P-059 live, P-061/P-062 APPROVE). Remaining: re-freeze; a new 20 + 12 hold-out, gold first, lint passing (loss runs valued before the run date, at least 2 held W1 files, at least 2 office-lessor / deli files); run and scored once with v7, meeting all 15 criteria. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the worktree and branch. The user decides: re-freeze, and whether to fix B-428 ("Not read by extraction" beside values read from that file) before the demo.
2. Give the manager demo from `deliverables/pm/demo-guide.md` using `run-demo.sh` (0 live calls).
3. @senior-underwriter + @producer write the next hold-out plan JSON under P-061/P-062; lint before the gold freeze; @model-risk approves the mix.

## For the AI Engineer

- Pending proposals: none open. P-059 to P-062 are built and approved by @model-risk (P-061/P-062 on look-again).
- Latest scores (B-415, dev, saved replies, routes on 7cfc959): 0 unsafe, 0 false completes, 0 call failed; SUB-154–173 operations 7 (unchanged), silent errors 9/180, operations flags 1/41. T-104 hold-out scores stay as published (route 16/20, operations 12/20).
- Top failure to fix next: route accuracy is unproven on real-shaped files under P-061/P-062 (synthetic checks only, B-427). Build the next hold-out.
