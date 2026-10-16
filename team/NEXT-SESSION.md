# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `e70dbd7` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files and `.claude/settings.json` are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.** `intake.py` self-check runs with no argument.
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`.

## Where we stopped (D-094)

- Memo M1–M6, L1–L4 are in the backlog as B-352–B-361.
- The operations gold rule is `deliverables/senior-underwriter/operations-gold-rule.md` (`9cf5aa1`, committed before any code). It applies to new gold only.
- **P-047 is built**, last code commit `b73bd40`:
  - (a) The prompt keeps every rule detail.
  - (b) `prepare.check_operations` compares the answer with the cited line plus any labeled line in the cited file whose label contains a rule-item word. If something is missing, the field is needs review at 0.74 with "operations may be missing: <item>".
  - (c) `workbench._ops` reads the value, the quote and those lines, and drops negated words ("no bar").
- **Reviews of P-047:**
  - @model-risk: APPROVE WITH CHANGES. H1 was closed at `b73bd40` after two look-agains (`deliverables/model-risk/check-P-047.md`).
  - @senior-underwriter: UI APPROVE.
  - Screenshot: `deliverables/software-engineer/screenshots/D-094-P-047-operations-may-be-missing.png`.
- **Scorer v2:** `underwriting_pipeline/ai/eval_holdout_v2.py` (`1ab0a86`).
  - Gold "not in documents" plus an empty answer scores as a hit.
  - Ids and output are set with `HOLDOUT_IDS` and `HOLDOUT_OUT`.
  - `eval_holdout_127.py` is unchanged.
- **Retries:** the code is unchanged. Each failed attempt or retry is in `report["retries"]` and in each score row. The rule is `deliverables/ai-engineer/evals/RUN-RULES.md`, which matches the code, so no outside driver is needed.
- **Dev re-check SUB-127–146** (development data; scorer v2; clean cache re-score at `b73bd40`; files in `deliverables/ai-engineer/evals/P-047-dev/`):
  - Operations 18/20 (was 12). Silent errors 0 (was 7). 0 false completes. Automation 73.3%.
  - Route 14/20. All 6 route misses are holds or no_match. 0 senior_referral and 0 carrier_c, because those files are held for a missing or scanned loss run.
  - With status forced to complete: SUB-141 and SUB-146 go to senior_referral (bar/liquor) and SUB-133 to carrier_c.
  - The live run had 20 calls, 0 failed and 9 logged 429 retries. Those retries are only in `run.log` (B-363).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. B-350: prefixed carrier header with letter words. Needs a P-###.
2. B-364: SUB-134 glass shop routes no_match (gold carrier_c). Also confirm the SUB-139 gold (no_match vs senior_referral, habitational without sprinklers).
3. When to build the next 20-file hold-out under the gold rule and scorer v2. This is the T-027 resolution path.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | H2 is addressed by P-047, but the veto is not lifted. A fresh 20-file hold-out must run: gold first under the operations gold rule, smoke first, .venv, paced, scorer v2, run and scored once on a frozen commit. It needs all 9 fields at 9/10 or better and 0 false completes. Loss runs (62.5%), year built, premises, tiv and construction were below the floor on T-027. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @ai-engineer-assistant: write a P-### for the loss-run field floor, the biggest remaining H1 gap. Scanned runs (B-343/B-357) and missing runs keep files held. Use B-365 (multi-line quotes not found) as a second item.
2. @senior-underwriter + @producer: plan the next 20-file hold-out. Gold comes first and follows the operations gold rule and the M5 convention ("not in documents"). No pipeline run until the user says so.
3. @head-of-underwriting: B-364 (SUB-134 appetite, SUB-139 gold).

## For the AI Engineer

- Pending proposals: none open. P-047 is built and reviewed (H1 closed). B-350 and the loss-run floor each need a P-###.
- Latest scores (dev SUB-127–146, scorer v2): operations 18/20, silent errors 0, 0 false completes, route 14/20, automation 73.3%.
- Top failure to fix next: the loss-run field. It is 5 hit, 3 miss, 12 not credited; scanned and missing runs hold files, so no carrier_c or senior_referral route is reached.
