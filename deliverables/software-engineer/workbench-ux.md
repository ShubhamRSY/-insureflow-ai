# Workbench — first page

- Author: @software-engineer
- Date: 2026-10-09
- The existing page `frontend/src/pages/UWWorkbench.jsx` stays as it is. It talks to the other app and includes bind readiness. This pilot page does not.

## What the page shows

One article per `simulation/inbox/SUB-*` folder: files on disk, files the extractor did not read, extracted fields with source and cited text, conflicts, missing items, point score with reason codes, and a carrier recommendation.

## Decision

Approve, edit, or decline posts to the page only when an underwriter id is present. Edit and decline require a reason. The log records `bound: false` and `sent_to_carrier: false`.

Run the check: `python underwriting_pipeline/app/workbench.py`

Open the page: `python underwriting_pipeline/app/workbench.py --serve` then visit `http://127.0.0.1:8765`

## Carrier package

`underwriting_pipeline/app/package.py` will not write `simulation/to-carrier/` unless the actor is the user. Nothing was sent this round.
