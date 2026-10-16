# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `a11ab83` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files and `.claude/settings.json` belong to the user and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- **Score files are written only with `--write`** (D-096 item 4). Re-scores use `HOLDOUT_RESCORE=1`, a temp copy of the cache in `LLM_CACHE_DIR`, and `LLM_PACE_SECONDS=0` (RUN-RULES.md).
- **Standups:** the orchestrator writes the entry for any role that took a turn but cannot write to team/ (D-096 item 5).
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55` for live runs.

## Where we stopped (D-096)

- **P-050 is built** (`512c049`). When TIV is missing, a held file shows the route its class gives: "Provisional route: X (provisional — TIV needed to confirm)". No TIV cap is applied, and sends stay blocked.
  - @model-risk: APPROVE WITH CHANGES, no High finding on P-050.
  - @senior-underwriter UI check: APPROVE WITH CHANGES (B-375).
  - The habitational referral now cites AG:37, AG:62 (it said AG:61, a citation bug).
- **Scorer v3** (`eval_holdout_v3.py`) adds the T-027 route gate: 0 unsafe routes, and at least 18/20 counted over every file in the set. Any file without a route mark makes the gate NOT EVALUABLE; an unsafe route always fails it. v2 stays frozen.
  - @model-risk H1 (dev script crashed) and H2 (loose pass rule) were closed at `86f82fd`.
  - **H3 waits on the user** (pending decision 2).
- **`--write` flag:** `regression_dev.py` and `P-048-dev/run.py` run read-only without it. The frozen scorers are unedited; the driver redirects their output.
- **Dev route gate** (SUB-127–146, v3, cache, 0 calls): **FAIL**.
  - 1 unsafe route: SUB-138 → carrier_a, gold hold.
  - Route 16/20. Misses: SUB-135 (thrift shop has no class word), SUB-138, SUB-143 (clothing store → no_match, gold hold), SUB-144 ("offices" → carrier_a, gold no_match).
  - Loss runs 8/0/12. 0 false completes.
- **P-049** final list from @head-of-underwriting (not built): `deliverables/head-of-underwriting/proposal-P-049.md`.
  - 15 rules: 14 written down, 1 removed (the unsourced Carrier B $2M cap). Rules file: `deliverables/head-of-underwriting/carrier-match.md`.
  - (a) "All restaurants → senior_referral" is justified, not narrowed: AG:39, AG:62 and AG:66 say so, and the code cannot check Carrier B's 3 clean years.
  - (b) Sprinklered apartments → senior_referral is intended (AG:37, AG:62), not a typo for unsprinklered. It reverses D-059 item 6 (sprinklered → carrier_c), so it is the user's call, not a code-bug fix.
  - If approved, carrier_b and carrier_c become suggested markets only; T-103 gold rows 3, 5, 6, 10, 17 and 19 and dev gold SUB-130, 132, 133, 136 and 140 change; the T-103 mix needs re-approval.

## Approved, not built

| Proposal | Task |
|---|---|
| P-049 | principle only (D-096); the rules list awaits "approve change P-049" |
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **"approve change P-049"** on the final list, including the two rulings: all restaurants → senior_referral, and sprinklered apartments → senior_referral (reverses D-059 item 6).
2. **H3:** does a held file's provisional carrier route count as unsafe in the gate? v3 counts it now (conservative). @senior-underwriter then writes the gold rule for TIV-missing files (B-376).
3. When to build T-103. It needs P-049, H3 and B-376 decided first.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | T-103 runs: gold first, smoke first, .venv, paced, scorer v3 with `--write`, run and scored once on a frozen commit. It needs all 9 fields at 9/10 or better, 0 false completes, 0 unsafe routes and route at least 18/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |
| v3 / T-103 gold | @model-risk (OBJECTION) | H3 answered by the user and the TIV-missing gold rule written (B-376). |

## First 3 tasks next session

1. User decisions: P-049 approval, H3.
2. If P-049 is approved: build it (rules file first, then code), re-score SUB-127–146 read-only with v3, get a @model-risk check, then fix @senior-underwriter UI items B-373/B-375.
3. @senior-underwriter: the TIV-missing gold rule (B-376), then T-103 re-approval of the mix by @model-risk. Build T-103 only when the user says so.

## For the AI Engineer

- Pending proposals: P-049 (awaits "approve change P-049"). P-050 is built and checked.
- Latest scores (dev SUB-127–146, v3, cache): route gate FAIL (1 unsafe SUB-138, 16/20); loss runs 8/0/12; operations 19/20; 0 false completes; 0 silent errors.
- Top failure to fix next: the class lists. SUB-138 (fertilizer → carrier_a) is the unsafe route; SUB-135, SUB-143 and SUB-144 are class-word gaps. All of these are P-049 territory.
