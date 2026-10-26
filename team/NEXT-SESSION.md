# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `b4c4790` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- **Score files are written only with `--write`.** Re-scores use `HOLDOUT_RESCORE=1`, a temp copy of the cache in `LLM_CACHE_DIR`, and `LLM_PACE_SECONDS=0`.
- Hold-outs are scored with **`eval_holdout_v4`**. v2 and v3 are frozen; their self-checks now fail on the old sprinklered → carrier_c route. This is expected and recorded in RUN-RULES.
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55` for live runs.
- The context7 plugin needs authorization (`/mcp`); until then use the `ctx7` CLI. The pyright CLI is not installed; VS Code diagnostics were empty for the changed files.

## Where we stopped (D-097)

- **P-049 is built** (`96deed8`, `a6cebb3`, `213d884`, `b4c4790`). The rules file is `deliverables/head-of-underwriting/carrier-match.md` (R1–R14, W1, W2); notes show the rule ID.
  - Carrier A is the only direct route.
  - Restaurants and apartments, sprinklered or not, go to senior_referral, with Carrier B or C as the suggested market. **D-059 item 6 is replaced** (AG:37, AG:62).
  - W2 referral words (hazardous goods, lab/medical, cold storage, liquor, vacant) always win over class words.
  - The Carrier B $2M cap is removed.
  - Senior-referral cards say "No send from this screen".
- **Scorer v4** implements H3: "hold" is a status, not a route; unsafe = a carrier route, held or not, where gold says senior_referral or no_match. @model-risk: APPROVE.
- **Dev re-check SUB-127–146** (v4, cache, 0 calls, clean `a6cebb3`; confirmed by @model-risk at `213d884`):

  | Measure | Result |
  |---|---|
  | Route gate | **PASS** |
  | Unsafe routes | 0 |
  | Route accuracy | 18/20 |
  | False completes | 0 |
  | Loss runs, hit / miss / not credited | 8 / 0 / 12 |
  | Operations | 19/20 |

  The 2 misses are SUB-135 (thrift shop) and SUB-143 (clothing store): no_match where gold says carrier_a, which is the safe direction. This is dev data with gold changed alongside the code, so it is not hold-out evidence (B-379).
- **Reviews:**
  - @model-risk: P-049 routing **OBJECTION, H1**. "office building with ground-floor pub", "retail store and cocktail lounge", "office building, no utilities" and "office, unoccupied" still route to carrier_a. It resolves when those never route to carrier_a, rule lines are added to carrier-match.md, each case has a self-check, **and the user approves a new P-###**.
  - @senior-underwriter UI: APPROVE WITH CHANGES. Its High was resolved by the "No send" line.
- Backlog: B-377 (3 clean years) to B-381.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-051 (to approve):** close @model-risk H1 of P-049.
   - Add pub(s) and lounge(s) as words that block carrier_a. With restaurant evidence they still give the R2 referral; with office/retail words they give senior_referral; alone, as now.
   - Add "no utilities" (read before the negation drop) and "unoccupied" to W2e vacant.
   - Rule lines go into carrier-match.md and each H1 case gets a self-check.
2. **Senior-referral send path.** Today a senior_referral file cannot be sent from the workbench: overrides are only allowed on no_match (D-060). Since P-049, that covers every restaurant and apartment file. Should the underwriter be able to confirm the suggested market and send in the workbench? That would change a send gate.
3. W1 prohibited words: the rules file says "overridable by a person", but the code keeps them not overridable (D-057/D-060). Confirm which.
4. When to build T-103. Its gold rows change under P-049 (rows 3, 5, 6, 10, 17, 19 → senior_referral), so the mix needs @senior-underwriter and @model-risk re-approval.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | T-103 runs: gold first, smoke first, .venv, paced, scorer v4 with `--write`, run and scored once on a frozen commit. It needs all 9 fields at 9/10 or better, 0 false completes, 0 unsafe routes and route at least 18/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |
| P-049 routing | @model-risk (OBJECTION H1) | P-051 approved and built, as above. |

## First 3 tasks next session

1. User decisions: P-051, the senior-referral send path, W1 overridable.
2. Build P-051 if approved. Run a read-only v4 dev re-score, then a @model-risk look-again on H1.
3. @senior-underwriter rewrites the T-103 gold plan under P-049; @model-risk re-approves the mix. Build T-103 only when the user says so.

## For the AI Engineer

- Pending proposals: P-051 (close P-049 H1: pub/lounge, no utilities, unoccupied). P-049 is built; scorer v4 is approved.
- Latest scores (dev SUB-127–146, v4, cache): route gate PASS (0 unsafe, 18/20), 0 false completes, loss runs 8/0/12, operations 19/20, 0 silent errors.
- Top failure to fix next: prohibited and vacant words that still reach carrier_a (P-049 H1), then the no-send path for senior referrals.
