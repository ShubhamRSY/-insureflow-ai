# T-128 build check 2 (the one look-again, D-129): hold-out SUB-550–581, before the gold freeze

- Reviewer: @model-risk (independent). Date: 2026-11-05. First check: T-128-build-check.md (REJECT, H1 and H2).
- **Verdict: APPROVE.** H1 and H2 are closed. The rebuild adds no High. The gold may be frozen and the manifest sha256 recorded under D-166 and the conditional GO (D-163).
- This is a build check only. It is not a production approval, and the T-027 veto stands.
- I did not read the author's messages or the T-128 Notes. Nothing ran against the pipeline, the model, the scope detector or a scorer run. The pure functions ran on a temp copy (D-069). `git status` was the same before and after every run.

## What I re-ran
- Freeze hashes: all 11 items match the NEXT-SESSION.md table (llm_extract, scope-v8, prepare, package, sources, workbench, smoke_readers, v11, lint, counter v2, counter notes).
- `lint_holdout.py T-128-plan.json --run-date 2026-11-05`: FAIL on SUB-560/scorer and SUB-562/scorer only, the two declared cooking marks. Nothing else fails.
- `HOLDOUT_IDS=550-581 eval_holdout_v11.py --check-gold` and `--check-ops-gold`: 32/32 ok; 20 in scope, 12 out; criteria 1:2, 2:6, 3:2, 4:2; no file under two criteria.
- `prepare.carrier_run_check`: 30/30 runs accepted. Valued dates are before the run date and the effective dates, and loss dates fall inside their terms (554, 559, 561, 563, 565 checked by eye). Carrier C and Carrier B runs both appear in scope.
- `prepare.cooking_word` (applications as md, pdftotext and tesseract; emails): 15 files have a "None" line and no cooking word anywhere else (550–559, 563, 564, 567–569). 3 state cooking (561, 565, 566). 560 and 562 hit "fries", which is the planted conflict.
- The similarity script (`T-128-similarity.py 550 581`) reproduces 0 of 32 emails at ≥ 0.80 (max 0.641), with no email sentence found in scope.py, prepare.py or inbox-dev.
- My own measure, written separately (difflib on whole email bodies, digits masked, against every earlier email in inbox and inbox-dev, plus a word 5-gram overlap against scope.py+prepare.py, inbox-dev and the T-121 emails):
  - Best match: 0 of 32 at ≥ 0.80 and 0 at ≥ 0.70. Max 0.638 (565/525). Mean 0.538. Mean against the T-121 twin: 0.515. At the first check the mean was 0.73 and 15 of 32 were ≥ 0.80.
  - 5-gram overlap with the frozen code: only 573's mandated "mailing address: same as premises" label.
- B-465 by hand on the rewritten emails: all 8 figure conflicts (554, 555, 556, 557, 558, 559, 561, 566) and both cooking conflicts (560, 562) are in the documents as the gold Conflict lines state. The worded amount (555 "$1.9 million") and the approximate figures (558, 561) are present. 557 is the only hold and is still gold "incomplete". The other in-scope emails add no figure that disagrees with the application on a scored field.
- Scope evidence in the rewritten emails is as the gold states:
  - Near-misses: 567 "two floors", 568 "2nd floor", 569 "two entrances".
  - One-building wording: 550 "under one roof at the address on the application".
  - Highway premises in scope: 550 Hwy 71 W, 552 US-59 N, with no second address in any document.
  - Out-of-scope highway second address: 572 Hwy 36 S, in a sentence that names Carrier B.
  - 573: the second address is below a filled "Mailing address: same as premises" line.
  - Words-only files 574–577 have no second street address.
- Name-stem collisions (first two words of insured and subject vs inbox and inbox-dev): none. The only first-word overlaps are Texas place or trade words used for other classes (Caprock, Pecan, Redbud, Rio, Red, Ferreteria).

## H1, closed
D-166 (@user, 2026-11-05, before the freeze and before the run) records the D-128/D-153 form I asked for:
- The SUB-560/562 cooking marks are reported separately and excluded from the conflict rate.
- Planted-conflict recall is measured on the 8 figure conflicts.

T-128-lint.txt records the two FAIL lines as the declared unmeasurable marks and cites D-166. The lint's two FAILs are exactly those marks and nothing else.

## H2, closed (option a)
- All 32 emails were rewritten. Similarity is now below the T-121 baseline on both measures.
- No hold-out sentence appears in the scope.py or prepare.py self-checks or in inbox-dev.
- The similarity gate is part of the B-515 check (mix file).
- The gold cards quote the new emails (for example 550 "under one roof", 577 "The second shop was sold in March").
- The applications are unchanged. They are structured forms, the same template as every earlier set, which I accept.

## New High
None.

## Medium / Low (backlog, one line each)
- M1 (carried): the restaurant Missing line is still inconsistent (561 lists "closing hour and extinguishing-system inspection date", 565 says "not in documents"). Settle it as ask vs hold before the freeze, or pre-register that neither form is scored. Owner @senior-underwriter.
- M3 (new): the slot design still mirrors T-121 at the class level. Operations lines are identical in 550, 559, 562, 564 and 566, and 567/569 share 5-word spans with tuning cases 527/529 ("two floors of the building", "two entrances, the front door on"). Email text is fresh, so this is not leakage, but the T-027 memo should report the near-miss and false-manual-intake results for 550/567/568/569 with this caveat. Owner @model-risk (T-027 memo).
- L1 (carried): confirm v11 counts a silently picked email value as a conflict miss. Owner @senior-test-engineer.
- L2 (carried): 568 building TIV $58,000 for a 2nd-floor tenant is unexplained. Owner @senior-underwriter.
- L4 (carried): `carrier_run_check` "Copy" negation quirk needs a backlog item and a dev test. Owner @ai-engineer-assistant.
- L6 (new): T-128-routes.md (00:57) predates the rebuild. The rows still match the gold, but call 9 quotes the old 577 wording ("sold our second shop"). Refresh the wording and date. Owner @senior-underwriter.
- L7 (new): 556 "seven on the crew" vs 9 employees on the application. v11 does not score employees and T-121 516 had the same shape, so this is not a planted conflict. Note it so a model flag is not read as a gold error. Owner @senior-test-engineer.
- Closed from the first check: M2 (the direct Carrier A emails 550–553 no longer carry goods or trade words), L3 (B-465 and the faithful-answer probe are recorded in T-128-lint.txt). L5 still pending as expected: record the manifest sha256 at the freeze.
