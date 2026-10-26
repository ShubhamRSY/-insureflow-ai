# P-042 — Address check accepts "City TX" without a comma, and says why it flags

- Author: orchestrator (main session, budget rule 3), from the D-088 development re-check. Not approved, not built.
- Development data only (SUB-107–126). Not a production approval.

## Problem

`prepare.flag_invalid_address` (P-002) finds the city only in the form "City, TX". qwen/qwen3.8-27b writes "Austin TX 78757". On the D-088 re-check, 17 of 17 premises values on SUB-107–126 were marked "address invalid" and needs review, though every ZIP is in `texas_zip_city.tsv`. Since P-041, a value that needs review keeps a file from "complete". So no file can be complete. The four files gold calls complete (107, 110, 116, 120) are "complete — review pending" only because of this flag. On 107, 110 and 120 it is the only flag. The flag also has no reason, so the card says only "flagged" (@senior-underwriter M3, B-328).

## Change

1. The check passes when one of the ZIP's listed cities appears right before "TX" or "Texas", with or without a comma (case-insensitive). Otherwise it flags as today.
2. A flagged row gets the reason "address check: ZIP <zip> is not listed for this city" (or "no Texas city found before the ZIP"), so the card says why.
3. Self-checks: "Austin TX 78757" and "Austin, TX 78757" pass; "Dallas TX 78757" and an unknown ZIP flag with the reason; the SUB-107 suite address passes.

Nothing else changes: no prompt, OCR, model or scorer change.

## Expected effect (development data, from the cached D-088 replies)

On the D-088 re-check, 107, 110 and 120 would be complete (status 19/20 or 20/20, depending on 116's scan flags). Automation would rise by about 17 premises values. Silent error is unchanged, because no value changes; only the flag does.

To approve, the user types: `approve change P-042`.
