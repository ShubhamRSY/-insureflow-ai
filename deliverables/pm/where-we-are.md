# Where we are: AI underwriting assistant (one page)

Author: @pm, 2026-10-18 (T-105, D-110). Synthetic data only. Not a production approval. The T-027 model-risk veto stands (verdict KEEP, 2026-10-17).

## What works (on dev files and in the test run)

- Reads a mixed submission (typed application, schedule, email, loss runs) and fills the main fields, with the source shown.
- Flags values a person must check (for example, a loss-run date read from a scan) instead of hiding them.
- Scope rule (P-055): sends out-of-scope files (scanned applications, several locations, non-English, unidentified applicant) to manual intake with a plain reason. Hold-out: 12 of 12 caught, 0 leaked, 0 in-scope files wrongly sent.
- Senior referral (P-052): a senior must confirm the carrier, and the record shows who, when, why and which file version.
- Safety stops: no send before an underwriter decides; no approve or send on manual-intake files; no false "complete" in the hold-out (0).
- Hold-out fields at 20 of 20: named insured, premises, effective date, TIV, construction, year built. Sales 19 of 20.
- Quote tracking is in place. Quote replies are simulated for now.

## The 2 open gaps

1. **Operations details (B-406).** Operations score 12 of 20. Three files have wrong operations and no flag (silent errors, 3 of 180 values overall). Missing items include cooking and hood-inspection details.
2. **Routing rules (B-407).** Route accuracy 16 of 20 (target 18). Three files go to "no match" when a carrier or senior route was right. One nightclub file shows a provisional senior referral when it should show no match.

Also open, same test run: **loss runs (B-408).** 9 of 20. In the test set every carrier loss run is dated after the run date, so none is accepted automatically. The scorer also counts "needs review" as a miss.

## What production still needs

- **T-027 model-risk veto (KEEP):** lifted only after the fixes above pass a new hold-out, scored once.
- **Sign-in and audit log for every decision and send (B-190):** required before real data. Today the underwriter is typed in, not logged in.
- **Safe concurrent writes to the decision log (B-191):** required before a pilot. The concurrency test currently errors.
- **Real carrier loss-run formats (R-030):** today a loss run is accepted by its layout, and the layouts are synthetic. Real carrier formats and a source check are needed.

## Next steps

1. User decides whether to approve the fixes for B-406 and B-407 (and the scorer rule for B-408). Each fix needs an approved change P-### first; @ai-engineer-assistant drafts the proposals.
2. Demo rehearsed on a temporary copy (2026-10-18): content accurate; setup steps fixed; on-screen rough edges logged (B-410 to B-413).
3. @senior-underwriter confirms the time-saved assumptions in the demo guide before any number is shown.
4. After the demo: collapse "What's new" by default, fix the send-check wording, and show the account-manager check on screen (@software-engineer; B-410, B-412).
5. Head of underwriting reviews how often files go direct to Carrier A: in the dev demo files, every complete file went to a senior first (B-414).
