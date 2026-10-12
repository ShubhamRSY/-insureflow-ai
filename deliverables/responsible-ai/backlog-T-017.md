# Backlog — T-017 review, Medium and Low findings

- Author: @responsible-ai
- Date: 2026-10-11
- Triage rule D-030. High findings are in the REVIEW message in team/DISCUSSION.md, not here.
- Evidence: scratch test on 80 gold files and hand-written wording pairs, no model calls. Synthetic data.

| Rating | Finding |
|---|---|
| Medium | FRAME_CONSTRUCTION fires only on the exact value "frame". "wood frame", "Frame (ISO 1)", and "frame construction" score 0. |
| Medium | TIV is parsed by keeping digits only. "$1.2M" becomes 12 (no TIV_OVER_1M), "1500000.00" becomes 150,000,000, and "1,250,000 building / 300,000 contents" becomes one number. |
| Medium | CONTRACTING fires on the substring "painting", so "art gallery selling paintings" gets 15 points. |
| Medium | HABITATIONAL misses "condominium association", "rooming house", and "duplex rental" (0 points) while "6 unit apartments" gets 15. |
| Medium | Insured name is not an input to `facts()`, but operations is free text. If extraction copies a trade name into operations (for example "Guenther Tacos y Mas"), the name changes the score. The T-067 name-swap test should include a name that contains a trigger word. |
| Medium | The feature definitions live in `facts()` in `underwriting_pipeline/app/workbench.py`, outside `underwriting_pipeline/models/`. reason-codes.md does not say where each fact comes from, so the "When" column cannot be checked from the deliverable alone. |
| Medium | The points.py self-check only passes hand-built dicts to `score()`. No check runs a report through `facts()` and asserts each of the six codes can fire. |
| Low | Weights are stated placeholders with no evidence. The "mean hazard points" gap test in fairness-test-plan.md cannot explain a gap with loss history while LOSS_HISTORY is dead. |
| Low | Spanish-source gold files: n=11, mean 8.6 points, others n=69, mean 7.0. Explained by class mix (three restaurants). n is too small to call stable. No action; recheck at n >= 30. |
| Low | Reason codes are shown as raw tokens (COOKING) with no plain-language sentence. |
