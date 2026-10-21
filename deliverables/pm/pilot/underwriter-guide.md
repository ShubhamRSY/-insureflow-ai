# Underwriter guide — assist-only pilot

- Date: 2026-10-21. Synthetic data only until B-190 is merged and @compliance clears real documents.
- This guide is written in OpenCode, not independently reviewed.

## What you are using

The workbench shows saved extraction runs. It never runs extraction, never sends, and never drafts. Your job is to read each proposed value against its cited page and record what you decide.

## On every card

1. Read the yellow banner: **ASSIST-ONLY PILOT — AI proposals only. Nothing is routed, sent or drafted. You decide.**
2. Read **Scope check**. If it says *manual intake*, the file was not read for values; read the whole file by hand and log your decision. Scope is your decision, not the tool's.
3. Treat the carrier match as **Suggestion only — not a decision**.
4. Check every value marked **AI proposal — verify against the source** against its cited text and confidence.
5. Read the standing warning. It gives the measured accuracy of operations and loss runs. Check each of those values against the cited page.

## What you can do

- **Confirm** — tick every value with its cited text, then record the confirmation. This is not an approval and it sends nothing.
- **Edit** — correct a value; give the field, the new value and a reason.
- **Decline** — give a reason.
- **Mark a code wrong** — the score does not change; the mark is logged.
- **Resolve a conflict** — choose a stored side, enter a value and give a reason.
- **Close a subjectivity** — this records a carrier reply, not a send from the tool.

There is no send button, no approve button, no draft button and no producer-request button. If you see one, stop and report it as an incident.

## What is logged

Every view, confirmation, edit, decline, resolution, refusal and mark is written to the pilot logs with the signed-in user (after B-190), the submission, the run hash, the prompt version and the model. Your corrections are the pilot's error measure.

## Stop conditions — call it immediately

Stop the pilot and tell the pilot owner and @model-risk if any of these happens:

- a pilot file is sent, drafted or made sendable;
- a real file is opened before B-190 is merged and checked;
- any change lands in `underwriting_pipeline/` during the pilot;
- a log write fails and the page does not show the failure;
- the correction rate for any field passes the threshold @head-of-underwriting set.
