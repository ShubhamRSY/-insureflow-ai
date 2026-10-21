# Next session

Written 2026-10-21 by the orchestrator at wrap-up. Wrap-up commit: `b05a89d` on `ai-team`, pushed to `origin/ai-team` (private). Previous: `f3e066b`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** New hold-outs are scored with **`eval_holdout_v11`** (v10 and earlier frozen). Gold check: `HOLDOUT_IDS=<a-b> .venv/bin/python underwriting_pipeline/ai/eval_holdout_v11.py --check-gold`.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only via `/opt/homebrew/opt/python@3.14/bin/python3.14`.
- @producer cannot write `deliverables/`; it writes the mix to the scratchpad and the orchestrator copies it.

## Frozen code under test (D-119)

| Item | Value |
|---|---|
| Code-under-test commit | `8d605acce37f06f719b5a865a79d783bc3e9c800` (P-069 freeze) |
| Prompt hash (`PROMPT_VERSION`) | `759b3e6bc9b2` |
| Scorer v11 sha256 | `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` |
| Lint sha256 | `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` |
| v10 sha256 (unchanged) | `ffd1afdda55fd761f21deb2f6ede49b9294d7517bed6500ccd9520eba361302b` |

Any byte change to v11 or the lint reopens the @model-risk check.

## Where we stopped

- **P-069 built and frozen (T-116, D-119).** A `business_type` operations slot (22 values from carrier-match.md). Items that fit no slot become `- Operations notes (unscored):`. The rule is in `deliverables/senior-underwriter/operations-gold-rule.md`, including a bar-word line (H1) and a counter-word line for "salad bar" and similar (M6).
  - @model-risk: OBJECTION H1, because dev gold dropped bar_pub on SUB-211/222. The gold and rule were fixed, and the look-again was **APPROVE, no High** (`deliverables/model-risk/check-T-116-P-069.md`). M1–M6 and L1–L2 are not yet in BACKLOG.md.
  - Dev evidence (T-108, cache, 0 model calls): operations went from 12/20 on v10 to **15/20 on v11**, and the other fields are identical. The 5 misses (207, 208, 213, 216, 219) are correct answers that also mention a second class in passing. This is a known limit of the word list and fails closed.
- **T-117 hold-out built and gold frozen, not run.** SUB-238–269: 20 in scope and 12 out of scope, criteria 4/5/4/2.
  - Routes: carrier_a 2, senior_referral 14, no_match 4. W1 held: 238, 239, 252. Office lessors 246/248, delis 247/249, two-operation 250/252.
  - Lint PASS with frozen v11: 0 failures, 3 info, run date 2026-10-21.
  - **Gold manifest sha256 `9ab5960db77f49e02b27518fb13eaff7a0ceb8d6e78c498c430bd2ba350a943d`** (`deliverables/senior-underwriter/T-117-gold-manifest.sha256`). The freeze note is in `deliverables/producer/T-117-mix.md`.
  - Not done: a @model-risk build check of T-117 and a gold-vs-source comparison (both done for T-108, not requested this time).
- All 6 self-checks pass at `b05a89d` (llm_extract, prepare, intake, package, workbench, points).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Run T-117 once** on frozen `8d605ac` with v11 and `--write` (live, paced, smoke first), then score it once. Optionally ask for a @model-risk build check first.
2. @head-of-underwriting to confirm: SUB-248 (a physical-therapist tenant named in the email only, carrier_a kept) and the R17 neutral-word reading on 246/248. If the gold changes, it needs a new freeze note before any run.
3. Dev gold SUB-211: the route says R9/R10, but carrier-match R2 (bar beside restaurant) says senior_referral. Dev data only.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | A fresh hold-out (now T-117) is run and scored once on the frozen commit and passes the gates in its veto message: all fields at the floor, 0 false completes, 0 unsafe routes, route at least 18/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. User decision on running T-117 (and on a @model-risk build check first).
2. If approved: run T-117 once (smoke, then paced live), score with v11 `--write`, and record the scores against the T-027 gates.
3. Add @model-risk M1–M6 and L1–L2 from `check-T-116-P-069.md` to BACKLOG.md, one line each, and get @head-of-underwriting's answer on SUB-248/R17.

## For the AI Engineer

- Pending proposals: none open. P-069 is built and frozen.
- Latest scores (dev T-108, v11, cache): ops 15/20 (v10 12/20), route 18/20, 0 unsafe, 0 false completes. No hold-out has been scored with v11.
- Top failure to fix next: operations misses where a correct answer names a second class in passing ("small office", "therapy"). This is v11's word-list limit and needs a new P-### if it shows up on T-117.
