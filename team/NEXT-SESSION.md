# Next session

Written 2026-10-21 (third session) by the orchestrator at wrap-up. Wrap-up commit: `dea2eb5` on `ai-team`, pushed to `origin/ai-team` (private). Previous: `50b9205`. The T-117 run commit `05c3110` was made outside this conversation; the user asked for its results to be read here.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** New hold-outs are scored with **`eval_holdout_v11`** (v10 and earlier frozen). Gold check: `HOLDOUT_IDS=<a-b> .venv/bin/python underwriting_pipeline/ai/eval_holdout_v11.py --check-gold`.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only via `/opt/homebrew/opt/python@3.14/bin/python3.14`.
- @producer cannot write `deliverables/`; it writes to the scratchpad and the orchestrator copies it.

## Freeze 2026-10-23 (D-127), for the T-119 hold-out — read this first

Recorded by the orchestrator in the Claude Code session, 2026-10-23. Supersedes the older freeze below for T-119.
- Worktree and branch: `/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration`, `pilot-integration` (pushed; never `main`).
- Code under test: `pilot-integration` commit `b6a35b7d94de4afa36d7457b21d28d6f4c8b4358` (pipeline code identical to the merge `d7949d2`: T-118 P-070 conflicts with the cooking add removed by P-072).
- `PROMPT_VERSION` `759b3e6bc9b2` (`llm_extract.py` unchanged since T-117; request equality 143/143 identical at `d7949d2`).
- Scorer: **v11** (`underwriting_pipeline/ai/eval_holdout_v11.py`) sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`, self-check ok. v12 dropped (D-127; parked in `deliverables/backlog/P-073-v12/`).
- Lint: `deliverables/senior-test-engineer/lint_holdout.py` sha256 `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653`, SELF-CHECK PASS.
- Under v11 an answer that omits the cooking slot where gold says no cooking is a miss; T-119 results list these separately (D-127).
- Next: build T-119 (SUB-340–371) per `team/TASKS.md`, gold first, lint PASS with v11, @model-risk build check, freeze gold, record the manifest. Do not run it.

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

- **T-117 was run once and scored once** (`05c3110`): frozen `8d605ac`, scorer v11 `--write`, gold `7e076534…`, run id `20261021T112723-44537`, 20 calls, 0 failed, fresh cache.

  | Gate | Result |
  |---|---|
  | named_insured, premises, effective_date, sales, tiv, construction, year_built | 20/20 each |
  | operations | **13/20 FAIL** |
  | loss_runs | **16/20 FAIL** |
  | False completes / unsafe routes / leaks | 0 / 0 / 0 |
  | Route accuracy | 19/20 (miss SUB-252, B-448) |
  | Recall / false manual intake | 12/12 / 0/20 |

- **@model-risk T-027 memo** (`deliverables/model-risk/T-027-memo-T-117.md`): **KEEP**, veto not lifted. Run integrity verified.
  - H1 (B-451): the "Cooking operations: None" line is dropped on 4 files. Real misses. Crediting the 3 scorer-reading cases still gives only 16/20.
  - H2 (B-452): 0 of 3 planted conflicts raised (SUB-257 sales $412k vs ~$540k, no hold). Planted-conflict recall 100% joins the gate from the next hold-out.
  - H3 (B-453): the 4 loss-run misses are a build/gold error (Carrier C format). The model read every date.
  - Medium/Low: B-454 to B-459, including the skipped look-again on the gold fix (B-457).
- Per the user, nothing was fixed. Self-checks 6/6 ok at `dea2eb5`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. Whether to raise proposals for H1 (B-451, keep the cooking line in operations) and H2 (B-452, raise planted conflicts). Each needs `approve change P-###`. The alternative for H1 is a @head-of-underwriting scoring ruling before the next gold.
2. H3 (B-453): a lint rule that runs every built carrier loss run through `carrier_run_check`, plus a v-next scorer for the 3 scorer-reading operations cases. Both must be frozen and hashed before any new gold.
3. B-458: a SUB-252 R1 vs R2 ruling by @head-of-underwriting.
4. When to build the next 20+12 hold-out: at least 2 direct carrier routes (B-459), a look-again on every gold fix, and the planted-conflict gate.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production), KEEP 2026-10-21 | H1/H2 fixed on dev under an approved P-### with a @model-risk check (no High); the H3 lint rule and a v-next scorer frozen and hashed; a fresh 20+12 hold-out (look-again on every gold fix) run and scored once, meeting every gate plus planted-conflict recall 100%. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. User decisions on H1/H2 proposals and the H3 lint/scorer work. @ai-engineer-assistant drafts P-### for H1 and H2 if asked.
2. Addenda (no score rewrite) to the T-117 run record and mismatches for B-454 and B-456. @head-of-underwriting rules on B-458.
3. Backlog: @model-risk M1–M6 and L1–L2 from `check-T-116-P-069.md`, one line each (still not in BACKLOG.md).

## For the AI Engineer

- Pending proposals: none open; H1 (B-451) and H2 (B-452) need new P-### to proceed.
- Latest scores (T-117 hold-out, v11, scored once): 7 fields 20/20, operations 13/20, loss_runs 16/20, 0 false completes, 0 unsafe, route 19/20, 0 leaks, recall 12/12.
- Top failure to fix next: the operations answer drops "Cooking operations: None" (B-451), then conflicts never raised (B-452).
