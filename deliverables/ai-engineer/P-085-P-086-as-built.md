# P-085 and P-086 — as built (D-169)

- Branch `pilot-final` (worktree `insureflow-pilot-final`), from `pilot-integration` c72726ea. The frozen build on `pilot-integration` is unchanged.
- Approved by @user 2026-11-05: `approve change P-085` and `approve change P-086`, option A each (D-169). Not a production approval.
- Proposals: `proposal-P-085.md`, `proposal-P-086.md` (same folder).

## Files changed

| File | Change |
|---|---|
| `underwriting_pipeline/app/workbench.py` | P-085: `card_status()`, `_open_topics()`, `review_pending_html()` held branch; status line uses `card_status`; the no-send reason reuses `_open_topics`; conflict side shows "(and N more in this file)"; two What's-new lines; self-check asserts and an invariant loop over every status |
| `underwriting_pipeline/models/points.py` | P-085: the "Not scored" reason for an open conflict reads "file held — open conflict, not complete: …" (was "file complete — review pending: …"). It was found on the screenshot. Text only; `POINTS_VERSION` is unchanged (`points-bfcbf9387fd0`) |
| `underwriting_pipeline/ai/prepare.py` | P-086: `cooking_hits()` quotes up to 3 passages per document (`COOKING_QUOTES_MAX`), each at most 360 characters (`COOKING_QUOTE_CHARS`). `spans` lists each passage and `more` counts the rest. `start`/`end` stay on the first passage. The conflict side carries `spans`/`more`. Asserts added |
| `deliverables/software-engineer/P-085-shot.py` | Renders SUB-562 from a temp copy of the T-128 cache, with the model call blocked (D-069) |

## Unchanged

- `PROMPT_VERSION` 392b9ce3c1af; `llm_extract.py`, `scope.py`, `package.py`, `sources.py`.
- Stored statuses, `ready_to_route()`, the send gate, scorer v11, the lint and the gold.

## Checks (2026-11-05)

- Self-checks pass: prepare, workbench, package, points, scope (scope-v8), sources. `tests/pipeline`: 94 passed, including request equality.
- pyright 1.1.390: no new errors (the same 38 as `pilot-integration` on prepare/workbench, all pre-existing; points 0).
- **T-128 replay** (32 files, temp copy of the cache, model call blocked, 0 attempts):
  - 0 status, field, missing, request or scope changes; the conflict set is identical.
  - Only cooking quotes changed. SUB-562's email side now includes "shrimp and fries are fried every day". 560 is unchanged in value, with spans added.
  - SUB-562 `cooking.equipment` start/end are unchanged.
- **Code review** (medium), 10 findings, 9 fixed:
  - Fixed: an uncapped merged quote; start/end spanning uncited lines; "and N more" inside the choosable value; the held text dropping "values to review"; a duplicate open-topic list; a dead fallback; an unused list; the What's-new wording; the missing screenshot.
  - Not changed: the decline log keeps the raw saved status. That is a record of the run, not card wording.
- **Screenshots** (D-065): `deliverables/software-engineer/screenshots/P-085-P-086-SUB-562-held-card.png` and `P-085-P-086-whats-new.png`. On the rendered SUB-562 card, "complete" appears only as "Not complete".

## Known limits

- The value an underwriter can choose for the email side is the joined quotes (verbatim pieces joined with " … "), as before P-086 when it was a single ±120-character window.
- The quote count is per passage, not per line: windows that overlap on one line join, up to 360 characters.
