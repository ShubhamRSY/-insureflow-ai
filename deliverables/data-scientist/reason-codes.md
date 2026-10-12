# Reason codes — point score v1

- Author: @data-scientist
- Date: 2026-10-09
- Status: In review (T-017)
- Code: `underwriting_pipeline/models/points.py`. Run `python underwriting_pipeline/models/points.py`.

The number is a hazard rank. It is not a premium, not a decline, and not a carrier.

| Code | Points | When |
|---|---|---|
| LOSS_HISTORY | 30 | Liability claim, or property claim over $25,000, on a real loss run |
| COOKING | 25 | Restaurant or other cooking |
| FRAME_CONSTRUCTION | 15 | Frame construction |
| HABITATIONAL | 15 | Apartments or other habitational |
| CONTRACTING | 15 | Contracting operations |
| TIV_OVER_1M | 10 | Building TIV over $1,000,000 |

A missing loss run adds no points and does not mean zero claims. Weights are placeholders until losses exist. An underwriter can ignore the total. Nothing in this function binds or declines.
