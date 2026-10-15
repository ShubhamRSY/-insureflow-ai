# Problem framing — hazard rank (step 4)

- Author: @data-scientist
- Date: 2026-10-09
- Status: In review (T-007)
- Reviewers: @actuary, @responsible-ai, @model-risk

## Target

**Hazard rank for the underwriter.** Not premium. Not "which carrier declined."

I wanted the label to be "carrier refused the submission," because that is the outcome this agency actually sees. @actuary is right that this learns appetite, not hazard, and our appetites are placeholders. I am dropping that target.

Planned label, once any real outcomes exist: claim occurrence within 12 months of the inception we placed, on synthetic data until then. **We may never receive carrier loss runs back.** If we do not, we cannot claim the score is validated. v1 does not pretend.

## v1 method

Interpretable points, agreed direction with @actuary:

| Driver | Higher points when |
|---|---|
| Loss history | Not a v1 driver (2026-10-14, P-015): no claim fact is extracted until B-149; the page shows "Loss history: not scored" |
| Construction | Frame vs masonry (direction only; weights not set) |
| Occupancy | Cooking (stated fryer or open flame), habitational, or contracting vs office |
| TIV | Higher band |

Each fired driver is a reason code. No names, no ZIP score, no protection-class vendor. A missing loss run adds no points and does not mean zero claims; the file is incomplete (step 3) and is not scored. Cooking points need a stated fryer or open flame (2026-10-14, P-015), never a class or cuisine word.

No gradient boosting. A GLM only if we later have labels and @model-risk agrees the points are not enough.

## Exclusions

- Incomplete files.
- Non-Texas premises.
- Accounts with no placeholder match are still scored. Match and score stay separate.

## Window

12 months from inception. Not used in v1 math. Stated so we do not switch it later without a new framing.

## Baseline

The underwriter's own decision, stored in step 8, is the baseline for "was the score useful," not for training the points. Training on approvals would be the leakage @actuary called out.
