# UI check T-109a (D-116, D-065) - @senior-underwriter, 2026-10-19

Looked at: screenshot T-109a-scope-send-refused.png (sandbox SUB-233, stubbed), the What's new entry, and the two refusal texts in workbench.py. Read only; nothing run. High findings only.

## Verdict: APPROVE WITH CHANGES (1 High)

What works: the file cannot be sent and the card says so twice, in red, in the right places (producer draft and carrier send), with the reason "multiple locations". The What's new line is plain and dated. Both buttons are gone, so nothing can be sent by mistake.

## H1 - The card does not say what to do next, and the top of the card says the opposite
- Seen: the route line reads "none yet (provisional - file on hold: missing information) - No send until the hold clears". An underwriter reads that as "get the missing fields and it will clear". It will not: the file is out of scope and stays that way. The red refusal sits at the bottom, below the producer draft.
- Seen: "a person reads this file" does not say who, or whether the underwriter should handle it outside the tool. The producer draft (missing-info list) is still shown above a "No send to producer" line, so it is unclear whether to ask the producer for the missing fields.
- Resolves: (a) when the scope check fails at send time, the route line shows the same words as the refusal (for example "Out of pilot scope: multiple locations - not for this tool; handle manually"), not "until the hold clears"; (b) the refusal ends with the next step in plain words (for example "Read the full file and handle it outside the pilot; do not request missing items through this page"); (c) the refusal sits next to the route line at the top of the card, or is repeated there. Wording only; no gate change.

## Not High (backlog, one line each)
- M: "scope-v4" in the refusal is a code name an underwriter cannot act on; show it small or only in the history.
- M: the "Account-manager check: refused, the file is not complete" line gives a second reason beside the scope reason; state which one decides.
