# T-118 UI review (senior underwriter, from underwriter's POV)

Scope: workbench.py, package.py (plain-language labels), screenshots rendered via `deliverables/software-engineer/T-118-shot.py` (read as text). Screenshots PNGs may not be readable by tools; used HTML/text from temp render.

## What is visible / understandable (meets acceptance criteria)
- **"What's new"**: T-118/D-122 line present (2026-10-21) and names the P-070 changes clearly ("square footage", "sales or payroll", "suite count"), hold until resolution, producer asked, cooking line carried with "no cooking" and both cited lines.
- **Conflicts panel (SUB-292 card)**: Conflicts are listed with plain topic names (`square footage`, `sales or payroll`, `suite count`). Each side shows value + file + cited text (e.g. "2800 (application.md) — cited: Square footage: 2800", "3150 (schedule.csv) — cited: Main building 3150 2025"). Status is `OPEN: no send until the underwriter chooses or enters the value`. Both resolve forms appear (one per open conflict) with "Resolve <plain topic>", dropdown of stored sides, "or enter" field, underwriter id + reason, "Logged with this run. Resolve each open conflict, then approve." This matches D-065.
- **Sales emptied with plain reason**: On the card, `sales_or_payroll` shows value `—`, confidence `0.0`, source `application.md`, cited text `Annual sales: $412,000`, review note `the documents state different sales figures`. The file is held (`complete — review pending: open conflict: square footage, sales or payroll, suite count`).
- **Operations carries cooking line with both cited lines**: SUB-292 operations value is `Lessor of professional office building with two office suites on the second floor; no cooking` (confidence 0.9). Cited text shows both lines: `Operations: ...\nCooking operations: None`. SUB-293 (no-cooking-cited) shows operations value `Office of an architectural design studio; no cooking` with both lines in cited text and no conflict; `complete` (not review-pending for cooking). The flag is not raised just for stated "none" — it is carried because the value carries the source.
- **Send refusal is plain and specific**: `No send: open conflict on square footage, sales or payroll, suite count: the underwriter must choose or enter the value on the card (logged with this run) before a send.` (package.conflict_problem uses `prepare.PLAIN` so field names are English). Account-manager check also reflects the state.
- **Count is a separate topic**: `suite count` appears as its own conflict with both sides (application says 2, email says "three suites"); operations value remains as the extracted operations text (and has `; no cooking` from SUB-293-style behavior where applicable). The code path stores count conflicts separately and does not empty a non-scored field.
- **Resolve applies correctly (logic check)**: after resolving all three with logged rows on the same run hash, `with_resolutions` marks conflicts resolved and sets `sales_or_payroll.value` to the chosen value; `complete` becomes true and `ready_to_route` is true (once all conflicts resolved).

## High findings
None. The UI meets the acceptance criteria from an underwriter's POV:
- Topics are English on card/resolve/send/refusal.
- Both cited lines/sides are visible for cooking and for each conflict.
- Sales emptied with plain reason; file held until resolved.
- Operations kept for count conflict; file held.
- "What's new" line present; screenshots produced via the temp-copy script (D-065 satisfied in structure).
- Resolve forms show choose/enter, log with run hash, show RESOLVED after resolution.

## Backlog (Medium/Low)
- MEDIUM: The conflict list shows "quoted:" values as the full cited text but in the card HTML the "cited:" column in Extracted fields is separate; for conflicts the UI now shows value+file+cited per side which is good, but when a side comes from a schedule row the citation is the whole row line (as designed). Consider ensuring very long quotes wrap/readably in all themes (works in current style).
- LOW: The "No send" reason says "an open conflict is still on the file" in some code paths (old text) but `package.conflict_problem` now produces the detailed reason; both appear appropriately by context. No action needed now.
- LOW: In the resolved state after all conflicts resolved, the card no longer shows resolve forms (correct). The "open conflict" text is removed from send refusal (correct).

## Blockers
None.
