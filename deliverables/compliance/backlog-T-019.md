# Backlog — T-019 review, Medium and Low findings

- Author: @compliance
- Date: 2026-10-11
- Per D-030. High findings are in the REVIEW message in `team/DISCUSSION.md`, not here.

- Medium: `ai_version()` writes a hardcoded `+rules-d015` and the model name from the shell at decision time, not the version that produced the extraction on screen. The audit record's version is wrong after D-015 (A-03).
- Medium: "Not read by extraction" lists every file that is not `.md` or `.csv`. The extractor reads PDF, xlsx, and images. 49 of 86 inbox submissions get a false "not read" line.
- Medium: "edit" stores a reason only. No field or corrected value is stored, so a later package carries the uncorrected value (A-02).
- Medium: the page is rendered once when the server starts. After a POST the counts stay at their old values, and nothing shows that a submission already has a decision. Approve and decline for the same file are both logged with no rule for which one stands.
- Medium: an `extraction_failed` file shows "Score: 0 · none" and "hold", and still offers approve. A zero reads as low hazard when nothing was read (D-021).
- Medium: the log row does not record what the underwriter saw: no input hash, no score, no carrier match, and a date with no time (A-03, C-09).
- Medium: `route()` and `facts()` match substrings. "barber shop" and "bargain retail store" come back `no_match`; "office, no kitchen on site" comes back `carrier_b` with reason code COOKING. A wrong reason code is shown to the person deciding.
- Medium: `facts()` never sets `liability_claim` or `property_claim_over_25k`, so LOSS_HISTORY cannot appear on the page and the score understates a file with losses.
- Low: the action select defaults to approve, and approve needs no reason.
- Low: the decline reason is free text with no reason list and no warning against a prohibited basis (A-06).
- Low: `decisions.jsonl` sits in `deliverables/` with no append-only protection and no retention rule. Acceptable for synthetic data only (C-09).
- Low: `workbench-ux.md` says `package.py` writes `to-carrier` only for the user. Since D-017 the account manager can also send.
- Low: the server has no login. Acceptable on 127.0.0.1 with synthetic data; must be closed before any real file (A-07).
- Low: the conflict list shows both values but not whether the conflict is resolved. `all_values_rejected` (D-024) is not shown yet; that is T-071.
