# D-089 re-check: silent errors split (development data, SUB-107–126)

Computed by the orchestrator from the D-089 run's cached replies (temp copy, placeholder key, no model call). The frozen eval_holdout_107.py compares premises with commas kept. Since P-042, premises values are no longer flagged, so each comma-only difference ("Austin TX" vs gold "Austin, TX") counts as a shown, wrong, unflagged value.

| | Silent errors | Rate (of 180) |
|---|---|---|
| Frozen 107 rule (as reported) | 18 (premises 16, operations 2) | 10.0% |
| Premises compared without commas (the eval_holdout_127 rule, D-088 item 3) | 3 | 1.7% |

The 3 real silent errors:
- SUB-124 premises: "1401 Legacy Gardens Dr, Plano TX 75024 (Plano); Frisco location see schedule". Gold is "1401 Legacy Gardens Dr, Plano, TX 75024"; the extra note after the ZIP is kept in the value.
- SUB-114 operations.
- SUB-124 operations.

The 15 others match the gold exactly once commas are set aside. The published scores and the frozen scorer are not changed.
