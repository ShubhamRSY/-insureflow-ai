# P-025: low-confidence scan values, drop or store as needs-review

Status: PROPOSAL. Not approved. Not implemented.
Author: @ai-engineer-assistant. 2026-10-14. Asked for in D-066 block 1 item 2. Evidence: `deliverables/ai-engineer/p-016-drop-analysis.md`.

## The question
Today (P-016), a scan value whose confidence is under 0.75 is thrown away. The file then shows the field as missing. The other choice is to keep the value, mark it needs-review, and make the underwriter acknowledge it at approve.

## Options
A. Keep as is. Drop everything under 0.75. No change.
B. Store as needs-review above a floor of 0.50, drop below it. The value, quote and reason ("confidence 0.58 is under 0.75") are shown, flagged, and listed at approve.
C. Store everything as needs-review, no floor (the old behaviour, but flagged).
D. Like B, but only for fields that have a quote found in the document and only on scans. Typed documents stay as now.

## Trade-offs in simple words
- A is safest on wrong numbers. It costs correct values: on the quick 15 it lost 2 right values and 2 half-right ones, and the file then asks the producer for items it already has.
- B gets back the right values at 0.58 to 0.66. It also brings back one wrong number (SUB-074 TIV 220000 at 0.67, gold 280000). It still blocks the 0.00 junk ("#5000", "2RO2F-O1-O1").
- C brings back the junk too. Not recommended.
- D is B with a narrower rule. In the quick set it gives the same result as B.

## Expected quick-set impact (from the recomputation, not run)
- A: as now. 15 files: 5 checks stay lost (SUB-038 loss_runs and status, SUB-067 operations, construction, conflict).
- B or D: expect those 5 checks back to hit (the five dropped values sit between 0.58 and 0.66). SUB-074 tiv stays a miss, with a wrong value stored but flagged. SUB-067 stays a status miss. Net about +5 hits against now, equal to the P-022 level.
- C: same 5 back, plus 2 junk values stored on SUB-067. No score gain over B.
- The 15 files are small. One scan page decides each result. Treat these as direction, not proof.

## Acknowledgment at approve (D-039)
Every stored low-confidence value joins the needs-review list. The underwriter must acknowledge each one before approve, and the log names it. Under B, SUB-038 goes from 3 listed values to 5, SUB-067 from 3 to 5 or 6. The list gets longer, and a long list invites click-through. The wrong TIV above would be on that list with its quote, which is the point of the list.

## Send gate
The send gate (`package.py`) does not read needs_review. It reads status, hash, manifest and decision. So a flagged stored value counts as filled: SUB-038 would go back to "complete", and the package could be sent after an acknowledged approve. With option A the same file stays "incomplete" and the producer is asked for a loss run it already sent. Under B the human acknowledgment is the only check on those values. If you want a stronger stop, add as a follow-up (not in this proposal) a send rule that refuses a file whose needs-review values were not acknowledged in the saved decision.

## Recommendation
B, floor 0.50. It restores the right values, keeps the junk out, and puts every uncertain number in front of the underwriter with its quote. It does not touch the prompt, the scorers or any hold-out. After approval I would run the quick 15 only. T-027 stays a production veto either way, and this is not a production approval.

## What changes if approved
`accept_field` in `underwriting_pipeline/ai/llm_extract.py` (low-confidence branch returns the value, flagged, instead of None) and the confidence floor constant. A workbench check is not needed (the reason and quote display already exists from P-016), but D-065 asks me to confirm the card shows the reason text.

Reply with "approve change P-025" and the letter (A, B, C or D). Without it, nothing changes.
