# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `50435a2` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Run every pipeline command with `.venv/bin/python`.** Score files are written only with `--write`; re-scores use `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`. Hold-outs use `eval_holdout_v4`.
- **Branch note.** While this session was paused on the usage limit, something outside this session committed `efdd48d` (src/ checkout fix, on ai-team, pushed), `774d8b1` (feat/dev-testing-environments) and `5ceeef8` (feat/senior-test-and-frontend-roles: new roles @senior-test-engineer, @frontend-engineer, protocol and CLAUDE.md edits). The user chose (a): this session's commits were cherry-picked onto ai-team without `5ceeef8`. **The two new roles are not on ai-team and not confirmed (D-045/D-053).** The feature branches are left as they are.

## Where we stopped (D-098)

- **P-051 built** (`644c58b`): Carrier A only from the AG:29-31 allow-list groups (office, retail incl. clothing and thrift shops, wholesale); a second operation (two groups, an allow-list word beside an OTHER word, a bar word beside another operation) → senior_referral (R16); vacant, unoccupied, "no utilities" → senior_referral (W2e); pubs and lounges are W1 (AG:46), never overridable. Rules file carrier-match.md updated.
- **P-052 built** (`644c58b`, `31e2a16`, `e5326dc`): UW-001 is `"senior": true`. A senior picks a carrier and a reason on a senior_referral card; logged in market_confirms.jsonl, bound to the run hash and the reviewed values (an edit after it voids it). The normal send gate applies (approve on this run, acknowledgments, typed line). Never on held files, W1 words, or vacant/no-utilities files (AG:51, @compliance H1 fix). The account manager cannot send a senior referral.
- **Dev re-check SUB-127–146** (v4, cache, 0 calls, clean `644c58b`, `20f3bdb`): route gate PASS, 0 unsafe, route 20/20, 0 false completes, loss runs 8/0/12, operations 19/20. Code changed after seeing the misses: dev, not hold-out evidence.
- **Reviews:**
  - @model-risk (check-P-051-P-052.md): P-051 **OBJECTION H1**: R14 is not a real allow-list; 27 of 36 untested phrases reach carrier_a ("office and casino", "retail and tattoo parlor", "steel wholesale", "wholesale firearms"). P-052 APPROVE WITH CHANGES.
  - @compliance (check-P-051-P-052.md): OBJECTION H1 on P-052 (confirm offered on AG:51 files). **Fixed in `e5326dc`; look-again not yet run.** P-051 passes 1(a)–(d).
  - @senior-underwriter (ui-check-P-052.md): APPROVE, no High.
- Backlog: B-382 (frozen scorers score saved outputs) to B-387.
- Standups missing for this session's turns: @model-risk, @compliance, @senior-underwriter (D-098).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-051 H1 fix (new P-###)**, pick one: (i) Carrier A only when the text holds nothing but allow-list phrases and a closed list of neutral words, and wholesale only when "light" or listed goods; or (ii) no direct Carrier A route: allow-list files go to senior_referral with Carrier A suggested, and a senior confirms (P-052). Either way the 27 probe phrases become self-checks as senior_referral.
2. **@compliance M1:** may a senior pick carrier_a on a W2 file whose note says "not Carrier A"? ("never Carrier A" in P-051 1a vs "they pick the carrier" in P-052.)
3. **The new roles in `5ceeef8`** (@senior-test-engineer, @frontend-engineer): confirm or reject.
4. When to build T-103 (gold rows change under P-049; needs @senior-underwriter and @model-risk re-approval).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | T-103 runs: gold first, smoke first, .venv, paced, scorer v4 with `--write`, run and scored once on a frozen commit; all 9 fields at 9/10 or better, 0 false completes, 0 unsafe routes, route at least 18/20. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |
| P-051 routing | @model-risk (OBJECTION H1) | The user picks (i) or (ii) as a new P-###, it is built with the 27 phrases as self-checks, and @model-risk looks again. |
| P-052 confirm | @compliance (OBJECTION H1) | Fixed in `e5326dc`; @compliance look-again. |

## First 3 tasks next session

1. User decisions 1–3 above.
2. Build the chosen P-051 H1 fix; read-only v4 dev re-score; @model-risk look-again on P-051 H1 and @compliance look-again on P-052 H1.
3. @senior-underwriter rewrites the T-103 gold plan under P-049/P-051; @model-risk re-approves the mix. Build T-103 only when the user says so.

## For the AI Engineer

- Pending: the P-051 H1 fix (new P-###, option i or ii); @compliance M1 ruling; the `5ceeef8` roles.
- Latest scores (dev SUB-127–146, v4, cache, `644c58b`): gate PASS, 0 unsafe, route 20/20, 0 false completes, loss runs 8/0/12, operations 19/20.
- Top failure to fix next: unlisted occupancies beside an allow-list word still reach Carrier A (P-051 H1).
