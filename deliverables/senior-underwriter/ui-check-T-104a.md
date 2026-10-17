# UI check T-104a (D-105, D-065 item 3): Manual intake card
Reviewer: @senior-underwriter. Date: 2026-10-17. Verdict: APPROVE WITH CHANGES (1 High, small fix).
Method: screenshot T-104a-manual-intake.png (SUB-170), code read (manual_intake_html, card lines, What's new), sandbox render of SUB-143, SUB-170, SUB-129 (temp copy, 0 model calls, no real file written).

## What passes (P-055 rev 3 "What it changes")
- Whole file goes to manual intake: status line says manual_intake; route manual_intake; no carrier, provisional or suggested route, no "Carrier match" line.
- No field complete: "Extracted fields: Nothing filled in: a person reads the file."; "Not scored", loss history / cooking / hood "not read (manual intake)".
- No complete / complete-review-pending status; no missing-info draft (0 drafts written in the sandbox for all three).
- Send blocked with plain reason on the card: "No send: this file's status is manual intake (scanned application; multiple locations); it cannot be sent." Edit and approve refused in code; form offers decline only.
- Every matched reason listed as its own bullet (SUB-170: scanned application + multiple locations; SUB-143: application not identified + non-English (Spanish)). Red alert box at the top, easy to see.
- What's new line present (2026-10-17, T-104a, D-105).

## High
H1. Contradictory "none" lines on a manual-intake card. SUB-129 shows "Not read by extraction: application.jpg, loss-runs.pdf" and then "Not read: none" and "Needs human read: none". SUB-170 and SUB-143 show the same two "none" lines. An underwriter or account manager skimming the lower block reads "nothing unread, nothing needs a person", the opposite of the banner. These lines are the file-level read-status block that normally means "all clear". Fix: on manual intake, replace both with "whole file: not read (manual intake)" (same pattern as the existing "Loss history: not read (manual intake)"). Needs a self-check assert that "Not read: none" is absent from a manual-intake card.

## Medium / Low (backlog, one line each)
- M: Card gives no next step or owner ("a person reads this" but who, where does it go); add a one-line "Next: underwriter reads the original documents; producer is told by the account manager".
- M: Account manager has no producer-facing text for a manual-intake file (no draft by design); give a fixed holding note for the AM to approve, not an automated missing-info draft.
- M: Reason "application not identified" is vague for the producer conversation; say what was missing (no ACORD/application found among: email.md).
- M: Decline is the only decision offered on an unread file; confirm with @head-of-underwriting that a decline here is logged as "manual intake decline" and not counted in correction/decline stats.
- L: Jargon in the banner: "scope check scope-v2", "P-055" on the Not scored line; keep for audit, move to a small grey footer.
- L: "Manual intake:" repeats in every bullet under a heading that already says it.
- L: "Address check: —" and "Locations: not stored in the saved run" show on a file that was never read; hide or mark "not read".

## Look-again (2026-10-17)
H1 CLOSED. Sandbox render of SUB-129, SUB-143, SUB-170 and the refreshed screenshot: "Not read", "Needs human read" and "Not read by extraction" now all say "whole file: not read (manual intake)"; no "none" remains. No new High. Verdict now APPROVE.
New Low (backlog): the wording stutters ("Not read: whole file: not read (manual intake)"); "Not read by extraction" no longer names application.jpg / loss-runs.pdf, so the underwriter loses the list of what is in the file (Files line above still names them). Earlier Medium/Low items unchanged.
