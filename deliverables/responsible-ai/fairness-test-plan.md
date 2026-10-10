# Fairness test plan — agency pipeline

- Author: @responsible-ai
- Date: 2026-10-09
- Status: In review (T-009)
- The system does not decline applicants. Tests are on recommendations and on what the underwriter has to correct.

## Groups

We do not collect race, religion, or sex. We will not infer them from names.

| Slice | Why | Limit |
|---|---|---|
| Texas region (Gulf Coast flag vs rest of Texas) | Wind flag and territory can track demographics | Small counts will be marked unstable |
| Occupancy / class | Business of the account, allowed | Do not treat class as a protected class |
| Name swap | Same submission, different insured name | The score and the match must not change |

## Metrics

| Metric | On | Threshold to investigate |
|---|---|---|
| Missing-info rate | Step 3 | Gap > 10 points across regions, with n ≥ 30 per slice |
| Mean hazard points | Step 4 | Gap we cannot explain with loss history, construction, and occupancy |
| Carrier recommendation mix | Step 5 | A region pushed to "no match" after class and losses are held constant |
| Underwriter correction rate | Step 8 | One region corrected > 10 points more often |

There is no AI approval/decline rate. Do not compute one.

## Data

Synthetic files in this build, including a name-swap pair. Before any real submissions: stop and ask @compliance (register A-07). No protected-class column on the decision record.

## Veto

I will veto a score or a match that uses insured name, owner credit, or a ZIP demographic score. Protection class from a vendor is already out (D-004).
