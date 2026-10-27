# T-120 build check: SUB-450 to SUB-481, before the gold freeze
- Reviewer: @model-risk (independent). Date: 2026-10-27. Worktree `insureflow-integration`, branch pilot-integration, commit 1aea7e4.
- Scope: gold vs builder source (B-465), scope (criteria 1–4), v11 operations/cooking slots, valued-as-of dates, routes vs carrier-match.md (R1–R17, W1/W2, D-125), C6 counts, freeze of the C2/C4 counter. High findings in detail; Medium/Low one line each (D-129).
- Not run, not scored. No pipeline, no model. Only pure functions were called: the frozen v11 slot/class reader (`_slots`, `answer_classes`, `ops_items_hit`) and `prepare.cooking_word`, on text written from the documents. The builder was re-run in a scratch copy only.

## Verdict: BLOCK (gold freeze), 1 High. One look-again (D-129).
This verdict is on the build and gold only. It is not a production approval; the T-027 veto stands.

## What I recomputed (passes)
- **Rebuild:** the builder, run in a scratch directory, gives byte-identical output to `simulation/inbox/SUB-450..481` (all 32 folders, PDFs and JPGs included).
- **Freeze:** sha256 of v11 `7ddcfb50…`, lint `01147a75…` and `count_ops_gate.py` `f942010d…` match the "Freeze 2026-10-27" lines in `team/NEXT-SESSION.md`. The counter was committed in 62b1d23, before the build (e07bb6f, fix 9f059e1) and before the gold (1aea7e4). There is no change under `underwriting_pipeline/` or `src/` from fa604b9 to 1aea7e4. D-134 (C1–C7) is in DECISIONS.md before the gold.
- **Lint re-run:** I got the same result as `T-120-lint.txt`. It fails only on SUB-461 and SUB-463 (cooking conflict marks with no figure, the D-128 kind), plus the SUB-468 undated info line.
- **Gold vs builder source:** I checked these on all 20 in-scope cards against the builder values: insured, premises and ZIP, effective date, sales, TIV, construction, year built, valued-as-of date, and claim count, paid and open amounts. Status, conflict and route also match. 0 mismatches.
  - All 9 conflict lines name a field that really differs in the builder source (B-465): 454 sq ft, 455 sales, 458 suites, 459 sq ft, 460 TIV, 461 cooking, 462 sales, 463 cooking (the schedule says Yes), 469 sq ft. No planted conflict is missing from the gold, and I found no conflict in the source that the gold leaves out.
- **Scope:** 20 in scope. Every in-scope application is English and typed (the PDF text layers are 725–861 characters), with one premises each. Out of scope: criterion 1 = 470, 471, 472 (471's PDF has no text layer), 2 = 473, 474, 475, 3 = 476, 477, 478, 4 = 479, 480, 481. That is three files per criterion, none combined, and it matches the plan JSON.
- **Valued-as-of:** I confirmed 27 carrier runs, valued 2026-05-26 to 2026-09-09. Every one is before its effective date and before 2026-10-27, and each gold date equals the date in the file. Carrier C terms use "D - D" and the claim numbers use C-#####. No "None reported" rows. SUB-456 has no run; SUB-468 has an owner letter (declared undated).
- **Routes vs written rules:**
  - carrier_a: 450, 451, 452, 453. Every operations word is an R14 phrase or a non-occupancy word; TIV is $185k or less; each has a clean Carrier A run.
  - R17 wholesale or extra words (senior_referral): 455, 458, 459, 461, 469. R11 contractor: 454, 456, 460. R9/R10 restaurant: 462, 463, 467, 468.
  - 464 is R2 under D-125 (pub plus kitchen plus offices). 465 and 466 are R1 (W1). 457 is R8.
  - Holds are R5 or loss-run holds. All 20 routes agree with the rules as written. The judgment calls are declared.
- **C6 (recomputed with `prepare.cooking_word` over every md, csv and PDF text in scope):**
  - None-line files with no cooking word anywhere else: 14 (450–460, 465, 466, 469). The gate needs at least 12.
  - Cooking stated: 4 (462, 464, 467, 468). The gate needs at least 3.
  - Planted cooking conflicts: 2 (461, 463). The gate needs at least 2.

## High
### H1: four operations gold marks a document-faithful answer cannot hit under frozen v11. They would be counted as C4 misses and as C2 "silent errors".
v11 scores operations on the answer's words. The business_type set must match exactly, and the slot words are read whole-word. The lint's "perfect answer" is built from the gold items, not from the documents' own words, so it cannot see this. I fed v11 answers that copy the application wording and got these results:

| SUB | Gold line | Builder line | What v11 reads from the faithful answer | Result |
|---|---|---|---|---|
| 469 | `SUB-469.md` l.13 `business_type=wholesale; business_type=other_class` | build l.418 "Wholesale auto parts, tire mounting…" | `answer_classes` adds other_class only when no other class was found, so {wholesale, other_class} can never be produced | **miss whatever the answer says** |
| 468 | `SUB-468.md` l.13 `oven` | build l.400 "Convection ovens, panini press, espresso machine" | the `oven` trigger does not match "ovens", so no cooking slot is read (operations-gold-rule says oven(s); the frozen scorer reads "oven" only) | miss on the documents' own word |
| 464 | `SUB-464.md` l.13 `{bar_pub, office}` | build l.334 "Pub with full bar **and kitchen**…" | "kitchen" is a restaurant synonym, so the answer reads {bar_pub, office, restaurant}. T-119 SUB-352 missed in exactly this way | miss unless the answer drops "kitchen" |
| 454 | `SUB-454.md` l.13 `{contractor}` | build l.169 "Electrical contracting, …, **office and shop**" | "contracting" is not a synonym and "office" is, so the answer reads {office} or {contractor, office}; the gold notes say there is no office class | miss unless the answer rewrites the line |

- **Effect:** up to 4 of the 5 misses that C4 allows (hits at least 15/20) are scorer artifacts.
  - None of the four has an open operations or cooking conflict. So `count_ops_gate.py` counts each miss without an item-naming reason as silent, against a C2 target of 0.
  - The C2 and C4 verdict could therefore turn on the scorer's vocabulary rather than on the pipeline. This is the same class of defect as D-128, but it is not declared.
- **What would resolve it:** before the gold manifest is recorded, do one of these for each of the four.
  - (a) Declare the mark v11-unmeasurable in `T-120-plan.json` and in the T-120 TASKS note, for @user to confirm, as was done for SUB-461/463. Report it separately and exclude it from the C2 count and the C4 denominator (C4 then out of 16 or more, with the floor restated before the run).
  - (b) Fix it at source so a faithful answer can hit: rebuild the document or correct the gold item, then re-lint. Frozen v11 is not edited.
  - Either way, add the faithful-answer probe (application wording into `ops_items_hit`) to the look-again.

## Medium (backlog, one line each)
- M1: SUB-455 (build l.178–188) reuses the exact T-119 SUB-345 failure pair, $1,240,000 vs "$1.42 million". The same pair is also the P-074 self-test literal (`llm_extract.py` 1129–1143). It is the only "words for the amount" case, so the fix is measured on its own test case. Rebuild with fresh figures before the freeze, or report it as non-independent.
- M2: in SUB-469 the email's 3,600 is the warehouse alone. The dispute is real (the insured calls 4,100 wrong), but the second side is not a total. Report planted-conflict recall on the 6 clean conflicts as well as the 7.
- M3: the loss runs for SUB-464 and SUB-465 list a loss dated before the only term shown (2025-10-19 against a term from 2025-12-03; 2025-09-22 against a term from 2025-12-12). Fix the dates or the term so each run is internally consistent.
- M4: the operations lines of the direct-A files 450, 452 and 453 were rewritten into allow-list words only (9f059e1), while the names and emails still say bookkeeping, hardware and insurance agency. A carrier_a hit tests copying of the words, not reading of the occupancy. Say so in the write-up.

## Low
- L1: `T-120-routes.md` l.44 quotes the email from before the rebuild for 453 ("five agents and a receptionist"). The file now says "five people and a front desk".
- L2: the gold summary says no lint was read, but the gold for 462 and 468 was edited after the first lint run (`T-120-lint.md`, History). State this in the summary.
- L3: the D-128 exclusion of SUB-461/463 is still marked "For @user to confirm", and the gold manifest sha256 is not yet recorded. Both are needed before the freeze.
- L4: in SUB-457, "railings for commercial jobs" may include installation (R11), and the contractor class (a C3 hazard) could be understated. It is declared ambiguous; keep it in the write-up.
