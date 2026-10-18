# T-107a / T-107c / T-107d UI check (D-065 item 3, D-112)

Reviewer: @senior-underwriter. Scope: the four screenshots, `workbench.py` (`_match`, `_send_html`, `_send_panel`, `_no_send_reason`, What's new), `package.py` (`agency_problem`, `senior_confirm_problem`), T-107 criteria in `team/TASKS.md`. Read only. High findings in detail, the rest one line.

## Verdict: APPROVE WITH CHANGES (one High)

## What passes
- T-107c refusals are plain and true. SUB-907 before confirm shows "No send: a senior referral needs a senior underwriter to confirm the market first" and the same reason in the Account-manager check line. No "not in appetite" for a senior referral. This matches the criterion.
- After the senior confirm, the green "Market confirmed: carrier_b by UW-001 ... Reason: ..." banner and the green "Account-manager check: passes (... senior-confirmed carrier). The account manager still writes a reason to send." read correctly. It says who confirmed, why, and what is still needed (approve plus typed line).
- T-107d: the latest 5 show, "Show all 48" opens the rest, and the count is correct.

## High findings

### H1. The R1 "prohibited class" note never names the word that fired or the line it came from, and R1 cannot be overridden
- Where: `workbench.py` line 248, `out("no_match", "prohibited class (R1; AG:45-50)")`. The card shows only this fixed text.
- Why it matters: since P-061/P-062 the trigger can come from the Line of business line, not just operations.
  - An office or consulting insured is now R1 because the Line of business says "lounge" or "bar".
  - "restaurant and lounge" with real cooking is R1 too.
  - The word list is broad (bar, bars, pub, lounge, cannabis, student housing, armed guard, and others).
  - The block is never overridable and offers no market confirm.
- What the underwriter sees is "prohibited class" on an insured whose ops read "consulting firm". They cannot tell whether it is a real nightclub, an "employee lounge", a mis-keyed Line of business, or a Spanish word. They cannot check it against the file without hunting through the application.
- A hard stop on a never-overridable rule needs a checkable reason. The AM check line adds nothing better: it says "the file is not in appetite" for this route.
- Required change: put the matched word(s) and the source line in the note, for example `prohibited class (R1; AG:46): "lounge" on the Line of business line`. Show the same text in the AM check line for no_match. This is display only; no routing change.

## Medium (backlog, one line each)
- M1. The P-061 senior-referral note says "class read from the line of business only (P-061; ...)". It is true, but "P-061" means nothing to an underwriter. It does not say which class word was read or what to check ("operations text does not say it; confirm the operation"). Rewrite in words and name the word.
- M2. The R2 note ("possible bar/liquor exposure — confirm liquor sales") does not say whether the bar word came from operations or the Line of business line. The R1 notes for "nightclub/lounge beside restaurant" and "bar beside an office" are the same fixed R1 text, so the underwriter cannot see which of the three situations applies (this feeds H1).
- M3. The green "Account-manager check: passes" line still shows beside the red "Approve first", "Re-review needed" and "Send refused: ... not acknowledged" messages. It is only hidden by `_no_send_reason`. Suppress it, or add "send still blocked until you approve", so "passes" is not read as "ready".
- M4. Nothing says "ready for the account manager" in one place. The signals are spread across a banner, a send form and a check line, and the queue list has no such state. A single status line would help.
- M5. The refused card shows two near-identical red lines, "No send: ..." and "Account-manager check: refused, ...", with the same reason twice. Show it once.
- M6. What's new is `<details open>`: five dense paragraphs (~300 px) sit above the queue, so the work list starts lower on every page load. The "collapsed" screenshot is not collapsed and does not show "Show all". Default it to closed, or show one-line headlines.
- M7. The AM refusal "the file is not in appetite" is generic for no_match (R8 vs R1). Use the card's route note.

## Low
- L1. The refused screenshot is unstyled (plain labels, tiny form). This is acceptable for the pilot workbench.
- L2. The fixture is SUB-907 with "x" placeholders. It is fine for a sandbox, but the demo screenshots should use a realistic file.
