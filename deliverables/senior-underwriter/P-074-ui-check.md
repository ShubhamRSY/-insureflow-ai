# P-074 UI check (D-065 item 3)

Reviewer: @senior-underwriter. Read the diff of `underwriting_pipeline/app/workbench.py`, the screenshot `deliverables/software-engineer/screenshots/P-074.png`, SUB-297 gold, proposal section "D-065", D-132. Nothing was run. FICTIONAL data, dev case only.

## Criteria

| Criterion | Result |
|---|---|
| Unverified/approximate side shows its reason in plain words on the Conflicts list | Met for approximate (screenshot: "Approximate figure: 'Last year we did about $1.35 million'. It does not confirm an exact amount." in red beside the email side). Unverified: code only (`side_note`), not shown in any screenshot. |
| Same in the resolve form | Met. A red line per flagged side sits above "Resolve sales or payroll"; dropdown options carry " - not verified" / " - approximate". Dropdown contents are not visible in the screenshot (closed select). |
| Held file shows existing refusal | Met. "OPEN: no send until the underwriter chooses or enters the value" plus "Not scored - file incomplete: missing sales or payroll; open conflict on sales or payroll". |
| One What's new line with date, P-074, decision | Met: "2026-10-24 P-074 D-132", top of the list. D-132 exists in D-decisions (P-074 approved). |
| Screenshot of affected card | Present, SUB-297. Page is cropped at the form: the submit button is cut off. |

## Underwriter's view

- It matches the gold: sales 1180000 (application) vs 1350000 approximate (email), file held, nothing sent. The underwriter sees at a glance that the email figure is a hedge and the application figure is the exact one. That is the right information in the right place.
- Showing the value as "1350000" while the hedge lives only in the cited text and the red note is acceptable; the note is directly beside it.
- Escaping is applied (`html.escape`) to value, source, quote and reason. Good.

## High findings

None.

## Medium / Low (one line each)

- Medium: the note says what is wrong but not what to do (e.g. "ask the producer for the exact figure, or enter the one you accept"). Add a short action phrase for the approximate case.
- Medium: an approximate side is still selectable in the dropdown; only the " - approximate" suffix warns. Acceptable because the underwriter decides, but confirm the logged resolution keeps the "approximate" flag so the audit trail shows an approximate figure was chosen.
- Medium: the unverified wording was never screenshotted. Ask for one dev file with an unverified side (quoted text not on the page) so the reason text, which comes from the model/code, is seen as a person would read it.
- Low: the same sentence appears twice in a row (list and form), which reads as duplication on a short card; harmless.
- Low: screenshot cuts off the form buttons; retake full height.
- Low: "(about, around, roughly, ~)" in What's new is jargon-light but fine; no change needed.

## Verdict

APPROVE (no High findings). Medium items go to the backlog.

- High: none.
- Medium: add an action phrase to the approximate note; confirm the resolution log keeps the approximate flag; screenshot an unverified side.
- Low: duplicated sentence; cropped form in the screenshot.
