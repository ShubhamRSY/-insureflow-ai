# Current submission-to-bind workflow — small commercial package

- Author: @senior-underwriter
- Date: 2026-10-09
- Status: Draft for review (@ai-engineer, @data-engineer)
- Basis: current desk practice for BOP / package property + GL. Times are typical file times, not a time study. Label them as estimates.

## Path

| Step | What happens | Typical time | Pain |
|---|---|---|---|
| 1. Land | Email or portal drop: ACORD, loss runs, SOV, sometimes a brochure. Clearance against the BOR. | 10 min | Duplicate submissions; BOR fights; attachments named `scan.pdf`. |
| 2. Completeness | Check ACORD 125/126/140, 5-year loss runs, SOV if >1 location or a building schedule. | 20 min | First submission often has 3-year runs, or runs that are not currently valued. We should not quote those. Today people sometimes do. |
| 3. Class and appetite | Map operations to class, check prohibited list, territory, size. | 15 min | Operations on the 125 disagree with the website and the photos. Class code is a judgment, not a lookup. |
| 4. Loss review | Match loss runs to the insured, value them, split property vs liability, note open claims. | 30 min | Runs for the wrong entity; ground-up vs valued; a "no known losses" letter instead of carrier runs. |
| 5. COPE / exposure | Construction, occupancy, protection, exposure; GL class, payroll or sales; additional insureds. | 45 min | SOV address ≠ ACORD premises. Year built blank. Sprinkler "yes" on a building that is a converted house. |
| 6. Referral judgment | Management, unusual ops, contractual risk, prior carrier non-renewal reasons. | 15 min | This is the step people try to skip. It is where habitational and contractors go wrong. |
| 7. Rate | Filed rate in the rating system. Schedule credit/debit is a separate authority. | 20 min | Re-key from the ACORD. Rating fails when protection class or construction is blank. |
| 8. Quote, refer, or decline | Letter or rater output. Decline states the guideline. | 15 min | Decline reasons written in free text. Sometimes the reason is "pricing," which is not a decline. |
| 9. Bind subjectivities | Signed app, inspection if triggered, loss runs updated if quote is stale (>30 days). | 25 min | Quote was issued on incomplete runs; bind is where we discover it. |

End-to-end for a clean office BOP: about **2–3 hours** of touch time over 1–5 days of calendar time, mostly waiting on the broker.

A habitational or contractor file is **half a day** of touch time and should not be on the same path as an office.

## Where the time actually goes

- Re-keying ACORD into the rater.
- Chasing currently valued 5-year loss runs.
- Reconciling one address across ACORD, SOV, and loss runs.
- Rewriting a decline reason so it matches a guideline.

## What must not be automated away

- Class of business when the narrative and the code disagree.
- "No known loss" letters used as a substitute for carrier loss runs.
- Habitational cooking, contractor height, and any request to ignore an inspection recommendation.
- Schedule credits. Those are senior authority today and should stay there.

## Handoff to extraction and data

Documents we actually see, in order of usefulness:

1. Carrier loss runs (PDF), currently valued.
2. ACORD 125, 126, 140.
3. SOV spreadsheet (locations, TIV, construction, year built, sprinklers).
4. Photos or inspection.
5. Supplemental apps (contractor, habitational, restaurant). Rarely complete.

@ai-engineer: extraction that does not flag a conflict between documents will create confident bad quotes. @data-engineer: the canonical model needs a "conflict" state, not only a value.
