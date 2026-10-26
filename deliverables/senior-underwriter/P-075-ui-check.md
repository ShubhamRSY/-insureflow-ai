# P-075 UI check (D-065 item 3) - @senior-underwriter

Scope: underwriter's view, High findings in detail, Medium/Low one line each. Read the screenshot (SUB-299 only), the workbench.py/prepare.py diff, the as-built note, and dev gold SUB-299/300/301. Nothing was run.

## Criteria
- Conflict shows both sides with source and quote, plain language: MET for SUB-299 as drawn (bold value, source file, cited quote). "cooking operations" is plain.
- Held file shows existing refusal: MET ("OPEN: no send until the underwriter chooses or enters the value", resolve form present, "Not complete until checked").
- Operations row shows copied line as its own cited part with a rule note: CODE ONLY. Note text and merge note are in the diff; the screenshot is SUB-299 (a held file), where nothing is copied. No picture of SUB-301 (or 294/295) exists, so this was not seen.
- Card cooking line does not mislead: PARTLY (see H1).
- What's new line with date, P-075, D-133: MET.
- Screenshot: present, but covers only one of the two states.

## High
H1. The conflict on SUB-299 shows the wrong "other side". Gold: application "None" vs the email naming a stove top, flat grill and hot food. The card shows application "None" vs application "Sprinklers: Yes, hood only". An underwriter reads that as a sprinkler line and may dismiss it; the email, the real evidence, is not on the card. Directly below, the card says "Hood and suppression: not stated" while quoting "hood only" as cooking evidence, which contradicts itself. Fix: show every document side that tripped the conflict (at least the email sentence), or the strongest one, and make the Cooking paragraph not quote a sprinkler line as the cooking statement. Same check needed on SUB-300 (schedule cooking column Yes, email griddle): confirm both appear.
H2. No screenshot of the copied-line state (SUB-301). The acceptance asks the Operations row to show the copied line as its own cited part with the rule note. Add a P-075 screenshot of SUB-301 (temp copy, D-069) before this is called done.

## Medium / Low (one line each)
- M: Operations review note on SUB-299 reads "operations may be missing: no cooking" - "no cooking" there can read as a finding; word it "cooking not stated in operations".
- M: Conflict bullet label "cooking operations:" is fine, but the source and quote are repeated twice per side; trim.
- L: The false holds listed in the as-built note (19 files, e.g. "electric ranges only", "bar snacks only") will show the same red line; expect underwriter noise, not a defect.
- L: "Not scored... open conflict on cooking operations" and the red "Complete - review pending... Not complete until checked" lines say the same thing; keep one.

## Verdict
APPROVE WITH CHANGES.
High: H1 conflict/card shows a sprinkler line, not the email's cooking sentence, and contradicts "Hood and suppression: not stated". H2 no screenshot of the copied-line Operations row (SUB-301).
