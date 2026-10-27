# Where we are: AI underwriting assistant (one page)

Author: @pm, 2026-10-19 (T-108, D-113/D-114). Synthetic data only. Not a production approval. The T-027 model-risk veto stands (verdict KEEP, 2026-10-19: the safety checks do not all hold and two fields are far below target).

## What works (on dev files and in the official T-108 hold-out)

- Reads a mixed submission (typed application, schedule, email, loss runs) and fills the main fields, with the source shown.
- Flags values a person must check (for example, a loss-run date read from a scan) instead of hiding them.
- Scope rule (P-055): sends out-of-scope files (scanned applications, several locations, non-English, unidentified applicant) to manual intake with a plain reason. T-108: 11 of 12 caught — **one file leaked (SUB-233)**, 0 in-scope files wrongly sent to manual intake.
- Senior referral (P-052): a senior must confirm the carrier, and the record shows who, when, why and which file version.
- Safety stops: no send before an underwriter decides; no approve or send on manual-intake files; no false "complete" in the hold-out (0).
- Routing (P-061/P-062): **route gate PASS** — 18 of 20 correct, 0 unsafe. The two misses (a file the gold would send direct to Carrier A went to a senior first) are safe.
- Hold-out fields at 20 of 20: named insured, premises, effective date, sales, construction, year built. TIV 19 of 20.
- Quote tracking is in place. Quote replies are simulated for now.

## The 3 open gaps

1. **Scope leak (B-432, High).** One out-of-scope file (SUB-233, two locations written inside the application body) was treated as in scope and reached the underwriter routable and send-enabled. Leakage must be 0. This is the single most important fix (H1).
2. **Operations details (B-433, High).** Operations 9 of 20. Nine files carry the facts but drop or reword one checklist item, with no flag (silent errors). One file (SUB-211) also repeats and truncates. Below the 18/20 floor (H2).
3. **Loss runs (B-433, High).** 5 hit, 9 miss, 6 not credited (below the 18/20 floor). **7 of the 9 "misses" are a scorer rule that compares the answer to the policy-period start date, not the valuation date — the answer is correct.** One miss (SUB-224) is a real error: a date read wrongly from a scan and not flagged.

Also open: **TIV 19 of 20**, sales returned to 20 of 20 (was 19 in T-104), and a small **status/conflict** gap (status 15 of 20, conflict 10 of 20, no false complete). Silent errors overall 17 of 180 (9.4%) — up from 3 of 180 (1.7%) in T-104; 7 of the 17 are the loss-run scorer rule above, 9 are operations wording, 1 is the SUB-224 scan.

## What production still needs

- **T-027 model-risk veto (KEEP):** lifted only after the H1 scope fix and the H2 field fixes pass a new 20 + 12 hold-out, scored once, meeting every gate criterion.
- **Sign-in and audit log for every decision and send (B-190):** required before real data. Today the underwriter is typed in, not logged in.
- **Safe concurrent writes to the decision log (B-191):** required before a pilot. The concurrency test currently errors.
- **Real carrier loss-run formats (R-030):** today a loss run is accepted by its layout, and the layouts are synthetic. Real carrier formats and a source check are needed.

## Next steps

1. User decides whether to approve the fixes for B-432 (scope) and B-433 (operations + loss-run + scan flag, scorer rule). Each prompt/extractor/scorer change needs an approved change P-### first; @ai-engineer-assistant drafts the proposals.
2. @ai-engineer-assistant has written the T-108 root cause (`deliverables/ai-engineer/analysis/T-108-root-cause.md`): 7 of 17 silent errors are a scorer date rule, 9 are gold wording, 1 is a scan read wrong without a flag.
3. Keep the demo on the dev files it uses today (SUB-127 to SUB-184); the hold-out files are never shown.
4. After the demo: collapse "What's new" by default, fix the send-check wording, and show the account-manager check on screen (@software-engineer; B-410, B-412).
5. Head of underwriting reviews how often files go direct to Carrier A: in the dev demo files, every complete file went to a senior first (B-414).
