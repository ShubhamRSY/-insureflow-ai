# T-121 build check (before the gold freeze): @model-risk

- Date: 2026-11-03. Worktree `insureflow-integration`, branch `pilot-integration`. Build commit `8642042`, HEAD `d0e3c513`. The only change after the build is the T-105 demo replies and `drive.py`; no T-121 file is touched.
- Scope of the check: gold vs builder source, scope (including the P-077 near-misses), slots, valued-as-of dates, and routes vs the written rules. Reviewed independently: I did not read the author's messages or the T-121 Notes, except one targeted grep to confirm the D-128 note exists.
- Nothing was run against the hold-out. No pipeline, no model, no score, no scope detector. I used only pure functions and the frozen lint.
- **Verdict: APPROVE.** No High findings, so the gold may be frozen once the manifest sha256 is recorded.
- This is not a production approval. The T-027 veto stands.

## What I recomputed (evidence)

| Check | Result |
|---|---|
| Freeze hashes (llm_extract, scope.py, prepare.py, scorer v11, lint, C2 counter v2) vs NEXT-SESSION 2026-11-03 | All 6 match |
| Rebuild in a scratch copy (D-069), compare byte by byte with the committed SUB-510..541 (including PDFs and JPG) | Identical, all 32 folders. Repo untouched |
| Lint v11 re-run, run date 2026-11-03 | 2 FAIL: SUB-520 and SUB-522 cooking-conflict marks only. Noted in TASKS before the freeze (D-128). Nothing else |
| `prepare.carrier_run_check` on all 29 loss runs | 29 accepted. Valuation dates run from 2026-07-21 to 2026-10-13. All are before the run date and the effective date, and every loss date is inside its term. No "None reported" rows |
| `prepare.cooking_word`, md, csv and the pdftotext of the typed PDFs, own cooking line skipped | 15 files with a None line and no other cooking word (510–519, 523, 524, 527–529). Cooking is stated in 521, 525 and 526. Cooking conflicts are planted in 520 (email "fry") and 522 (email fryer). C6 met |
| Gold vs builder: insured, premises, effective date, sales, TIV, construction, year built, valued-as-of, claims, 20 in-scope files | All match the builder arguments and the PDF text layers |
| Planted measurable conflicts | 6, all scorable under v11: 514 sq ft, 515 sales (worded), 517 suites, 518 sq ft (approximate), 519 TIV, 521 sales (approximate). Both sides are plain figures in two documents, and each gold Conflict line names the field. None is on the premises address (D-149) |
| Scope | 20 in / 12 out. Criterion counts 1:2, 2:6 (534–537 words only, no second street address in any document, loss runs included), 3:2, 4:2. Near-misses: 527 "two floors", 528 "2nd floor, suite 210", 529 "two entrances". Every document gives a single address, and the gold keeps them in scope. 516 has a mailing PO Box (role-labelled), in scope. 537 is a closed second store, out of scope (D-146) |
| Routes vs carrier-match.md | 510–513 route carrier_a on R14 + R17: allow-list words only, TIV ≤ 174,000, clean typed Carrier A run. 523 and 524 are R1 (W1). Contractors go to R11 and restaurants or delis to R9/R10. Wholesale, lessor, gift, tax, law and shoe words go to R17 senior_referral, suggested Carrier A. The plan route counts (4 / 14 / 2) match the gold |
| Loss-run mix (in scope) | Carrier C 7, Carrier B 5, Carrier A 7, missing 1 (516) |
| Collisions: 41 names and addresses vs every other text file in simulation/inbox and inbox-dev | 1 partial hit (M1) |

## High findings

None.

## Medium / Low (backlog, one line each)

- **M1:** SUB-524 "Velvet Room Nightclub LLC" shares its name with published hold-out SUB-201 "Velvet Room Lounge LLC" (also a nightclub; scored in the SUB-174-205 v6 eval). The mix's "0 collisions" claim is therefore wrong. The address, documents and wording all differ. **Fix:** rename the SUB-524 insured and rebuild before the freeze (update gold SUB-524), or record the overlap in the mix.
- **L1:** C6 cooking conflicts (520, 522) are both unmeasurable under v11. Report them apart from the conflict rate as D-128 requires. C6 is met only on build, not on measurement.
- **L2:** SUB-525 cites R10 in the gold but "R9, R10" in T-121-routes.md. The route is the same; align the reference text.
- **L3:** For SUB-519, the email side of the conflict is an "appraised" value set against "Building TIV". It is acceptable as a planted figure, but an appraisal is not always an insurable value. The underwriter wording should say so.
- **L4:** 510, 512 and 513 have business words in the insured name, and the 510 email says "desks, computers and files". A pipeline that cites these as operations text would fail closed to senior_referral. That is the safe direction (routes judgment call 1).
