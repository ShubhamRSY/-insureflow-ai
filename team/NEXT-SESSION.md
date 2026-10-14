# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `2a3882f` on `ai-team`, pushed to `origin/ai-team` (private). The weekly usage limit was hit earlier (resets 2026-10-17); later reviews still ran. Budget rule 8: demo blockers only. Standing rules: D-065 (backend + UI), D-069 (sandbox only). The frontend/ files are the user's and are never staged.

## Where we stopped

- Cooking rule settled: P-031 (D-074) — no negation word: hazards present; any negation word: "Cooking: needs review", score "Provisional — cooking not scored" until a listed underwriter records present/none (B-278 control, logged with the run hash). @model-risk APPROVE; its T-017 veto lifted.
- P-028 (D-075): each saved run stores its extraction cache key; footer shows it. B-284 self-check ties it to a real cache file. @model-risk APPROVE.
- D-076: cache filled for SUB-017..076 (45 calls, 70,640 tokens, 0 failures; 76 results). B-271 drop-analysis correction recorded. Demo runs SUB-009, SUB-010, SUB-029 re-saved from cache with keys.
- D-077: B-222 table rebuilt on 62 files / 464 values. Name swaps: no change (36 business-swap files, 2 person-swap files; coverage gap recorded, B-288).
- D-078 (amends D-060): carrier class from generic restaurant evidence only (restaurant, food service, kitchen, eatery, café, catering, Spanish translations, or stated cooking equipment); all cuisine words removed. Cuisine swap rerun: 0 findings. Screenshot D-078-B-286-cuisine-no-class.png.
- @responsible-ai on P-015, P-031, B-286: **APPROVE WITH CHANGES; T-017 fairness veto lifted on its side.** **High B-290:** PROHIBITED "bar" lets a cuisine word decide ("bar-b-q restaurant", "sushi/taco/oyster/salad bar restaurant" → non-overridable no_match; "bbq/pho/sushi restaurant" → carrier_b).
- @senior-underwriter UI check D-070..D-078: **APPROVE WITH CHANGES.** **High B-294:** What's new promises a no_match override the card does not have. **High B-295:** an extraction_failed card says "no cooking equipment stated".
- Self-checks at wrap-up (no model host): llm_extract, prepare, intake, package, workbench, points all ok.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/`, `scripts/`, `frontend/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 (the workbench draft approve calls the existing `prepare.approve`) |

## Pending decisions for the user

1. B-290: how "bar" is read near food words (the reviewer's two options: not inside bar-b-q / after a food word, or "bar" with restaurant wording → senior referral/hold). @user or @head-of-underwriting.
2. B-294: build the no_match override control (after-demo B-258) now, or remove the claim from What's new.
3. B-291: add more negation words (ningún, ni, nada, tampoco, w/o, zero, nor) — needs a P-###.
4. B-293: bakery and coffee shop now no_match; confirm or add generic words.
5. Start the new 20-file hold-out (T-091 to T-093), gold first — the last T-027 condition.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | none open (@model-risk lifted after P-031; @responsible-ai lifted on 2026-10-14) | — (not a production approval) |
| T-027 | @model-risk (production) | The new 20-file hold-out (T-091 to T-093), gold first, scored once |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md`; B-290 is in the same class lists |

## First 3 tasks next session

1. B-295 (failed-extraction cooking line, small, points.py) and B-294 (override claim) once @user decides.
2. B-290 once @user decides, then the cuisine swap rerun with "bar-b-q" and "… bar" words.
3. T-091 gold for the new hold-out if @user says so.

## For the AI Engineer

- Pending proposals: none numbered. B-290, B-291, B-294 need your call.
- Latest eval scores (quick-15, D-076, cached; hit / hit (needs review)): named_insured 13/0, operations 12/1, sales 13/0, construction 13/1, year_built 15/0, premises 12/0, tiv 14/0, loss_runs 8/1, conflict 10/3, status 12/1.
- Top failure to fix next: B-290 (a cuisine word can still decide the carrier through "bar").
