# T-128 build check: hold-out SUB-550–581 (before the gold freeze)

- Reviewer: @model-risk (independent). Date: 2026-11-05.
- **Verdict: REJECT.** Two High findings. The gold must not be frozen and T-128 must not run (D-163 is conditional on a check with no High) until both are closed. One look-again is allowed (D-129).
- What I did: I read all 32 folders (md files, pdftotext of the typed PDFs, tesseract of the SUB-570 scan), the 32 gold cards, T-128-routes.md, T-128-mix.md, T-128-plan.json, T-128-lint.txt, carrier-match.md (R14, R17, W1, W2), required-fields.md and the freeze table in team/NEXT-SESSION.md. I did not read the author's messages or the T-128 Notes.
- What I ran (nothing ran against the pipeline, the model, the scope detector or a scorer run):
  - sha256 of every frozen item: all 11 hashes match the freeze table.
  - `lint_holdout.py T-128-plan.json --run-date 2026-11-05`: **FAIL, 2 failures** (SUB-560, SUB-562).
  - `eval_holdout_v11.py --check-gold` and `--check-ops-gold`: 32/32 ok; 20 in, 12 out; criteria 1:2, 2:6, 3:2, 4:2; no two-criteria files.
  - `prepare.carrier_run_check` and `prepare.cooking_word` on a temp copy (D-069): 30/30 runs accepted with the stated valued dates; 15 None-line files with no cooking word elsewhere; 560 and 562 hit "fry" in the email. These match the mix file.
  - B-465 by hand: all 8 planted figure conflicts and both cooking conflicts appear in the documents exactly as the gold Conflict lines state.
  - Name-stem collision check (first two words vs simulation/inbox and inbox-dev): no hits.
  - Text similarity (difflib on email bodies, digits masked) of every T-128 email against every earlier email in inbox and inbox-dev, with T-121 measured the same way as a baseline.
- The repo was unchanged after every run (git status compared).

## High

### H1: the lint fails, and no unmeasurable-mark note exists before the freeze (owner @senior-test-engineer; the note is @user's decision)
The acceptance criteria require "lint PASS with v11 (unmeasurable marks noted before the freeze)". The lint gives `FAIL SUB-560/scorer` and `FAIL SUB-562/scorer`: "the perfect answer is marked miss on conflict". These are the two cooking-conflict files. v11 cannot score a cooking Conflict line, which is the same problem as T-119 H1 (D-128) and T-121 (D-153). No note exists in T-128-lint.txt, T-128-plan.json, the mix file, the routes file, the gold cards, NEXT-SESSION.md or DECISIONS.md. As built, the set does not meet its own gate, and freezing it now would let the conflict-rate denominator be chosen after the run.
**To resolve:** before the freeze, @user records in DECISIONS.md, in the D-128/D-153 form, that the SUB-560/562 cooking-conflict marks are reported separately and excluded from the conflict rate, and that planted-conflict recall is measured on the 8 figure conflicts (554, 555, 556, 557, 558, 559, 561, 566). Then the lint record notes these two FAILs as the declared unmeasurable marks and cites that decision. No gold or scorer change is needed.

### H2: the set reuses T-121's templates, including the files and literal phrases the frozen scope and Part B code was tuned on (owner @producer, builder; @senior-underwriter, gold)
T-128 was required to be "32 new files, nothing reused" and, for the T-027 lift, a fresh hold-out (T-027-memo-T-121.md). In practice T-128 copies T-121 slot by slot (SUB-n ↔ SUB-n−40), with new names, places and figures but the same sentences. Measured email similarity to the closest earlier file:

| Measure | T-121 vs everything older | T-128 vs everything older |
|---|---|---|
| Mean best-match ratio | 0.58 | 0.73 |
| Emails ≥ 0.80 | **0 of 32** | **15 of 32** (14 of them against their T-121 twin) |

The highest pairs: 559/519 0.95, 568/528 0.94, 565/525 0.91, 563/523 0.89, 550/510 0.87, 561/521 0.87, 553/513 0.86, 569/529 0.85. For example, 550 reads "We rent one office in a small building on Hwy 71 in Bastrop. Desks, computers and files only." and 510 reads "...on Hwy 290 in Brenham. Desks, computers and files only."

This matters most where T-027 has to make its call. SUB-510, 513, 527 and 529 were exactly the T-121 false manual intakes that P-077 Part B, P-079/P-080 and the dev re-check were built and checked against ("SUB-510/513/527/529 shapes stay in scope", NEXT-SESSION). The frozen code holds the T-128 phrases word for word:
- `prepare.py:3216-3224` self-check: "One address, one building." and "Same single building." (comment: "SUB-527/529 shapes"). T-128 uses "One address, one building." in 550 and 567, and "Same single building." in 569.
- `scope.py:590` self-check: "The store has two entrances." T-128 569: "The store has two entrances, ...".

So the gates T-027 depends on (false manual intake, near-misses kept, the "one address, one building" criterion, direct Carrier A on highway premises) would be measured on near-copies of the tuning cases. A pass would show the fix reproduces on its own dev shapes, not that it generalises. That is a leakage problem for a hold-out, whatever the names and IDs are.
**To resolve (either):**
(a) Rewrite the email (and, where it is templated, the application wording) of every T-128 file whose best match is ≥ 0.80, plus 567. Use new sentence structures and new near-miss wording. None of the strings may appear in `scope.py` or `prepare.py` self-checks or in inbox-dev. Add a similarity gate to the B-515 collision check: no email ≥ 0.80 against any earlier email (T-121 met this with 0 of 32). Then rebuild, re-write the gold from the new documents, and re-lint. Only the gold-free parts and the plan stand.
(b) @user accepts in writing, before the freeze, that T-128 is a paired replication of T-121 and not a fresh hold-out. In that case T-128 cannot serve as the fresh hold-out the T-027 memo requires for the lift, and a further fresh set would still be needed.

## Medium / Low (backlog, one line each)
- M1: The Missing line is inconsistent between restaurants. 561 lists "closing hour and extinguishing-system inspection date" as missing, but 565 (no closing hour and no inspection date) says "not in documents". Under the T-108/T-117 reading these are asks, not holds, so pick one form for all restaurant cards before the freeze (inherited from 521/525). Owner @senior-underwriter.
- M2: The direct Carrier A emails carry trade and goods words (550/553 "desks, computers and files", "lease... three people"; 551 "dresses, jeans and accessories"; 552 "work clothes, boots and household goods"). If the pipeline cites the email as operations text, R17 fails closed to senior_referral. Pre-register how that route is counted (rule-reading miss or gold ambiguity) before the run. Owner @senior-test-engineer.
- L1: Six conflict emails say which side is right ("that number is wrong", "the app has the old projection"). That is a fair test, but the scorer must count a silently picked email value as a conflict miss; confirm v11 does. Owner @senior-test-engineer.
- L2: SUB-568 building TIV $58,000 for a 2nd-floor tenant is unexplained (author's call 8). Fine if it is intended as improvements. Owner @senior-underwriter.
- L3: Record the B-465 check and the faithful-answer probe result (the lint's scorer test) in T-128-lint.txt, so the evidence is on file and not only implied. Owner @senior-test-engineer.
- L4: The `carrier_run_check` "Copy" negation quirk (the mix file's finding) belongs in the backlog with a dev test. Owner @ai-engineer-assistant.
- L5: The gold manifest sha256 is still pending in NEXT-SESSION.md, as expected before the freeze.

## Criteria met (verified, not taken from the author)
32 files with 20/12 in and out of scope and ≥ 2 per criterion; criterion 2 = 6 (4 words-only: 574–577; 2 SUB-533-shaped: 572 carrier sentence with a highway address, 573 below a filled mailing line); in-scope highway premises 550 and 552 with one address per document; 3 near-misses plus "one address, one building"; 5 plain figure conflicts, 1 worded, 2 approximate; 557 P-081-resolvable and still incomplete; C6 15/3/2; direct Carrier A 4 (allow-list words only on the operations line, TIV ≤ $186,000, clean A runs); Carrier C 7 and Carrier B 6 in scope; all runs accepted, valued before the run and effective dates, loss dates inside their terms; W1 563/564, lessors 557/558, delis 561/562; freeze hashes intact.

This is a build check only. It is not a production approval, and the T-027 veto stands.
