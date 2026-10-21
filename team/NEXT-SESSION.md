# Next session

Written 2026-10-21 (second session) by the orchestrator at wrap-up. Wrap-up commit: `50b9205` on `ai-team`, pushed to `origin/ai-team` (private). Previous: `b05a89d`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** New hold-outs are scored with **`eval_holdout_v11`** (v10 and earlier frozen). Gold check: `HOLDOUT_IDS=<a-b> .venv/bin/python underwriting_pipeline/ai/eval_holdout_v11.py --check-gold`.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only via `/opt/homebrew/opt/python@3.14/bin/python3.14`.
- @producer cannot write `deliverables/`; it writes to the scratchpad and the orchestrator copies it.

## Frozen code under test (D-119)

| Item | Value |
|---|---|
| Code-under-test commit | `8d605acce37f06f719b5a865a79d783bc3e9c800` (P-069 freeze) |
| Prompt hash (`PROMPT_VERSION`) | `759b3e6bc9b2` |
| Scorer v11 sha256 | `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` |
| Lint sha256 | `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` |
| **T-117 gold manifest sha256** | **`7e076534432f1276bfe6198643547498b613c4f2b7aceb2ed618314b5e39fd33`** (supersedes `9ab5960d…`) |

Any byte change to v11, the lint or the gold reopens the check. Commits after `8d605ac` touch docs and gold only, so the code under test is unchanged.

## Where we stopped

- **@model-risk T-117 build check** (`deliverables/model-risk/T-117-check.md`): OBJECTION with 2 Highs, both gold.
  - H1: SUB-246 and SUB-248 were carrier_a against R17 (unlisted words such as lessor and suites).
  - H2: SUB-249 had business_type=retail, which the documents do not support.
  - Everything else passed: hashes, the manifest reproduced, lint, check-gold, ops-gold, gold vs builder source (all fields), all 14 valued-as-of lines, Scope lines, and no run artefact.
- **@senior-underwriter gold fix:**
  - SUB-246 and SUB-248 now go to senior_referral with carrier_a suggested (R17). 248 keeps its hold.
  - SUB-249 has `retail` removed.
  - T-117 routes are now **carrier_a 0, senior_referral 16, no_match 4**.
  - Lint PASS (0 failures, 3 info), check-gold 32 ok, ops-gold 20 ok. Re-frozen. The orchestrator re-verified the hashes and the lint.
- **No @model-risk look-again on the fix yet.** The T-116 precedent had one.
- Medium/Low findings in the backlog:
  - B-447: pre-register 3 operations misses.
  - B-448: SUB-252 R1 vs R2 needs a @head-of-underwriting ruling.
  - B-449: no in-scope direct carrier_a route (a run limitation).
  - B-450: Lows.
- Self-checks 6/6 ok at `50b9205`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **@model-risk look-again on the T-117 gold fix** before the run (recommended; quick, gold-only diff `28bba4b..50b9205`).
2. **SUB-252 (B-448):** gold says R1 no_match, frozen code gives R2 senior_referral. @head-of-underwriting rules, or pre-register it. If the gold changes, re-lint and re-freeze.
3. **Run T-117 once** on frozen `8d605ac` with v11 and `--write` (smoke first, then live and paced), then score it once. Pre-register B-447 and B-449 in the run notes first.
4. Carried over: dev gold SUB-211 R2 vs R9/R10 (dev data only). The SUB-248 question is resolved by H1.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | T-117 is run and scored once on the frozen commit and passes the gates in its veto message: all fields at the floor, 0 false completes, 0 unsafe routes, 0 leaks / 100% recall, route at least 18/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |
| T-117 freeze | @model-risk (OBJECTION H1/H2) | The gold fix is in; it closes on a @model-risk look-again with no High. |

## First 3 tasks next session

1. @model-risk look-again on the T-117 gold fix, plus a user/@head-of-underwriting answer on SUB-252 (B-448).
2. Pre-register B-447 and B-449 in the T-117 run notes, then run T-117 once if the user approves (smoke, then paced live) and score it with v11 `--write` against the T-027 gates.
3. Backlog: @model-risk M1–M6 and L1–L2 from `check-T-116-P-069.md`, one line each (still not in BACKLOG.md).

## For the AI Engineer

- Pending proposals: none open.
- Latest scores (dev T-108, v11, cache): ops 15/20, route 18/20, 0 unsafe, 0 false completes. No hold-out has been scored with v11 yet.
- Top failure to fix next: none in code until T-117 runs. On T-117, watch the 3 pre-registered operations misses (B-447) and the SUB-252 route (B-448).
