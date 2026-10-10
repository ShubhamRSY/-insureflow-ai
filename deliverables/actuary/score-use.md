# What the score is for

- Author: @actuary
- Date: 2026-10-09
- Status: Accepted by @head-of-underwriting (T-023)
- T-011 is cancelled. There is no permissible loss ratio gate and no filed rate to protect.

## The score

A rank of hazard for the underwriter, on this submission, using class, construction, TIV, loss history, and occupancy. Higher means more expected loss cost. It is not a premium and not a probability we can defend until we have labels.

v1 is a point table with reason codes, not a boosted model. We have no loss triangle. @data-scientist agrees in the framing, with one fight recorded there.

## The score must not

- Decline the account.
- Bind.
- Pick the carrier by itself.
- Change a price. We do not have a rate manual.

## Carrier appetite is not the score

Step 5 is a rule table (T-018). A risk can be a poor match for Carrier A and a normal match for Carrier B. Do not train the score on "Carrier A said no." That learns the placeholder rules, then pretends it learned hazard.

## Objection I am leaving in the record

D-004's success metrics do not include loss ratio. I will not block the pipeline. I will block a score that is tuned to "package accepted" or "underwriter clicked approve" and then described as a risk score.

## Fit

When labels exist, the check is whether higher scores have higher loss cost, by class. Until then, the only honest report is the reason codes the underwriter saw and whether they edited them.
