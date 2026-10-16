# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `d208259` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Run every pipeline command with `.venv/bin/python`.** Score files are written only with `--write`; re-scores use `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`. Hold-outs use `eval_holdout_v4`.
- **Branches (D-099).** efdd48d accepted (on ai-team). 774d8b1 stays on feat/dev-testing-environments (its .env examples hold placeholders only, checked). 5ceeef8 not accepted: feat/senior-test-and-frontend-roles left as is; the two roles are B-388, to be raised as a P-### later. ai-team has no 5ceeef8 (checked).

## Where we stopped (D-099)

- **P-053 built** (`454b2fc`): Carrier A direct only when every operations word (value, quote, cited lines, before the negation drop) is an allow-list phrase, a listed negation, or a neutral word (R17 in carrier-match.md). Any other word → senior_referral, Carrier A suggested, the card names up to 5 unlisted words. Wholesale never direct. 27 named @model-risk probes + light wholesale are self-checks.
- **@compliance M1 built** (`454b2fc`): a senior cannot confirm a carrier the route note excludes ("not Carrier A"); the card leaves it out and says why; a logged confirm for it does not count.
- **Dev re-check SUB-127–146** (`8c985da`; v4, cache, 0 calls, clean `454b2fc`): route gate PASS, 0 unsafe, route 19/20 (SUB-129 light wholesale → senior_referral, safe miss), 0 false completes; senior_referral 15/20 (was 14), carrier_a 4 (SUB-127/128/135/143).
- **Reviews (all no High):** @compliance look-again P-052 H1 + M1: APPROVE (H1 closed). @model-risk P-053: APPROVE WITH CHANGES (P-051 H1 closed). @senior-underwriter UI: APPROVE.
- Self-checks at wrap-up: llm_extract, prepare, intake, package, workbench, points all ok.
- Backlog B-388 to B-391.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **B-389 M1 (@model-risk, concurred by @senior-underwriter, fix before pilot):** neutral "shop", "store", "gift", "home" let "office and shop", "office and store", "office and gift shop", "home office" go to carrier_a. Fix as a new P-###: count them only beside a retail phrase, or treat them as the retail group.
2. **B-390 M1 (@compliance):** extend W2e with vacancy variants ("vacancy", "vacía", "desocupado", "utilities shut off", "power disconnected", "sin servicios") so the AG:51 confirm block applies: a P-### for @head-of-underwriting.
3. **B-390 M2 [NEEDS USER CONFIRMATION]:** does "the file's notes" in D-099 item 4 mean the route note only (as built), or also producer remarks like "declined by Carrier A"?
4. When to build T-103 (gold rows change under P-049/P-053; needs @senior-underwriter and @model-risk re-approval).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | T-103 runs: gold first, smoke first, .venv, paced, scorer v4 with `--write`, run and scored once on a frozen commit; all 9 fields at 9/10 or better, 0 false completes, 0 unsafe routes, route at least 18/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

P-051 routing (H1) and P-052 confirm (H1) objections are closed.

## First 3 tasks next session

1. User decisions 1–3 above.
2. Build the chosen neutral-word and W2e fixes; read-only v4 dev re-score; @model-risk look-again (High only).
3. @senior-underwriter rewrites the T-103 gold plan under P-049/P-051/P-053; @model-risk re-approves the mix. Build T-103 only when the user says so.

## For the AI Engineer

- Pending: none open as P-###; candidates: neutral-word fix (B-389 M1), W2e vacancy variants (B-390 M1); B-388 roles.
- Latest scores (dev SUB-127–146, v4, cache, `454b2fc`): gate PASS, 0 unsafe, route 19/20, 0 false completes, loss runs 8/0/12, operations 19/20.
- Top failure to fix next: "office and shop" / "home office" still reach Carrier A through the neutral list (B-389 M1).
