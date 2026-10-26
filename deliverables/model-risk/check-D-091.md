# @model-risk check — D-091 (P-044 accept-path dev check, SUB-127–146 mix, R-030)

- Date: 2026-10-15. Reviewer: @model-risk. Synthetic data only. Development check, not a hold-out and not a production approval. T-027 veto stands.
- Evidence read: D-091; simulation/inbox/SUB-147…152; gold SUB-147…152 (commit 77ee2e4, before extraction); dev_p044_147.py; dev-SUB-147-152-D-091.md/.json; prepare.py `carrier_run_valued`, `loss_run_kind`, `gate_loss_run`; simulation/carrier-loss-run-formats.md; T-102; R-030.
- Re-run: dev_p044_147.py on a temp copy, cache-D-091 copied, LLM_API_KEY placeholder, network blocked (sandbox-exec), .venv python. 6 of 6 from cache, 0 model calls. Table reproduced line for line: plain complete SUB-147, SUB-149; 0 false completes; loss run 5/6, status 3/6.
- Recomputed offline (no model): OCR of SUB-148 scan; `carrier_run_valued` on 9 probe texts (below).

## Item 1 — P-044 accept-path dev check: APPROVE (dev check; criteria met). No High.

Each criterion is met: 6 files with the cases asked for, gold committed before extraction, qwen paced at 55 s, every file reported with its loss-run result, reason and status, and 0 false completes. Reproduced from cache.

What the evidence shows:
- Accept path proven on typed PDF (147) and typed text (149) only.
- SUB-148 (scan) cannot pass by design. OCR text: `Carrier RB Loss History Report`, `Valuation date; 2026-09-39`, so the exact layout fails and the date is wrong. The model returned null, which is correct: it did not invent 2026-09-30. Standing rule S2 also flags every loss-run date read from a scan. The gold expecting "accepted, complete" conflicts with S2 and with T-102's own note.
- Reject path: the P-044 gate only actually ran on SUB-152. On 150 and 151 the model returned null because neither file has a valued date, so the gate was never reached. The 150 "copied header" letter has no date at all, so it does not test the R-030 case.

Medium / Low (backlog, one line each):
- M1: "Loss run as gold 5/6" counts 150/151 ("missing", no reason) as matching gold ("needs review — not a recognised carrier loss run"). Report them as "missing, gate not reached", not as a match.
- M2: The report does not say that scan acceptance is unreachable by design (S2 plus the exact-layout match on OCR text). SUB-148's 3/6 status miss needs that line.
- L1: The gold has two status lines (Status vs Expected pipeline status) for 150–152. false_complete uses the first, which is correct. State this in the report.

## Item 2 — SUB-127–146 mix (T-102): APPROVE WITH CHANGES. No High.

Counts check out: 8 carrier-format + 6 non-carrier + 6 none = 20. Carrier formats: 3 PDF + 2 md + 2 JPG + 1 image-only PDF = 8. Excluding xlsx is justified. No SUB-127–146 submission or gold exists; eval_holdout_127.py predates them (964c159, 201232d).

Changes to make in T-102 before any file is created:
- M3: The "applicant letter that copies a carrier header" must contain a valued-as-of date line, so the P-044 gate is actually exercised. Dev 150 had no date and never reached the gate.
- M4: At least one typed carrier-format run must use the carrier's own no-claims line. End to end, this branch has only been tried on the failed scan (148).
- M5: Gold reflects the documents, not the pipeline. A scanned carrier run in an otherwise clean file is gold-complete, and it is scored as safe but not automated. Reword "all of them carry a typed carrier-format loss run" as a constraint on how the files are built, and say the 5 typed carrier files have no other planned gap (conflict, over-cap, duplicate). Otherwise the automation denominator can drop below 5.
- L2: Record in the plan that an xlsx carrier loss run always goes to review. This is a known limit, not tested.

## Item 3 — R-030: APPROVE (criterion met). No High.

R-030 covers all three parts of the user's criterion: the layouts are synthetic, a copied header or layout can pass, and production needs each real carrier's format plus a source check. It also says this is a pilot limit, not a production control. P-044 auto-accept cannot be approved for production while R-030 is open.

Probe results (`carrier_run_valued`, offline):

| Probe | Result |
|---|---|
| Letter under a copied A header plus a valued line | None (review) |
| Exact layout typed by the applicant | 2026-09-30 accepted (R-030 as logged) |
| Exact layout + a plain signature line | None (review) |
| Exact layout + `_Typed by the owner from memory, not from Carrier A_` | 2026-09-30 accepted |
| `_Prepared by the applicant_` before the header | 2026-09-30 accepted |
| Valued date 2026-13-45 | 2026-13-45 accepted |
| Valued date 2031-01-01 (future) | 2031-01-01 accepted |

- M6: Every line starting with `_` is skipped wherever it appears, so a document that says in italics that it is not from the carrier is accepted as plain. Add this to R-030 and fix it when a P-### is approved. The skip should apply only to the synthetic banner text.
- M7: The valued date is not checked as a real calendar date, not after today, and not before the last period start. Backlog it under R-030.

Decision: no veto raised. These items are not production approvals.
