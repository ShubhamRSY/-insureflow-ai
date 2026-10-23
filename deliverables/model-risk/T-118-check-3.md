# T-118 — @model-risk check 3, after P-072 (D-124)

- Reviewer: @model-risk (independent, fresh dispatch). Date: 2026-10-23.
- Scope: T-118 criterion "@model-risk checks the fix on dev with no High before it counts toward H1/H2 closure". High in detail; the rest one line each.
- Read: uncommitted `git diff HEAD` of `prepare.py`, `workbench.py`, `package.py` on `fix-t117`; `proposal-P-072.md`; D-122, D-123, D-124; my `T-118-check.md` and `T-118-recheck.md`; the T-118 screenshots and shot script. I did not read the author's T-118 messages or the task Notes.
- Ran (temp copy of the worktree, D-069; no model call, no hold-out file; nothing written in the worktree except this file and one DISCUSSION entry):
  - `prepare ok`, `workbench ok`, `package ok`; `pytest tests/pipeline` 43 passed.
  - End to end through `process_submission`, model stubbed to the labelled lines (as in the SUB-296 self-check), **HEAD vs new** on all 27 folders under `simulation/inbox-dev/`.
- Synthetic data. **Not a production approval.** An approved P-### is not a production approval, and the T-027 veto stands.

## Verdict: APPROVE (no High). Counts toward H2 closure on dev. Does not close H1.

## What I checked for the earlier High
- The "; no cooking" add is gone from the net diff against HEAD: no `complete_cooking_line`, no `states_cooking`, no `OPS_COOK_EQUIPMENT`; `workbench.EQUIP` is unchanged from HEAD. Operations behaves exactly as HEAD does, so the T-118 H1 false-complete path no longer exists.
- The self-check runs SUB-296 end to end with eight emails, my seven re-check sentences (reworded) among them, and asserts not `complete`, no "no cooking", flag kept. It passes.
- HEAD vs new, 27 dev folders: 24 unchanged. 3 change, all toward holding: SUB-290 adds `square_feet`, SUB-291 adds `suite_count`, SUB-292 adds `sales_or_payroll` and goes from `complete — review pending` to `incomplete`. **No folder moves to `complete`. No crash.**
- Every new path (square feet, sales, counts) only adds an open conflict or empties a value. None can clear a flag or make a file complete. The square-feet refactor (removing the early `return`) only lets the sales and count rules run afterwards. `llm_extract.py` is untouched, so the request stays byte-identical.

## H1 / H2 status (for the T-027 record)
- H2 (planted document conflicts): surfaced on the dev set 3/3 with both sides, and the file is held. This counts toward closure on dev. It is not yet a hold-out result: it needs the next frozen gold and scorer, and the gate still applies.
- H1 (stated "Cooking operations: None" dropped from operations): **not closed by this change.** Under D-124 it moves to the v-next scorer (@senior-test-engineer, @model-risk). The file keeps the review flag, which is safe but means H1 is still a score gap.

## Medium / Low (one line each)
- M1 Sales takes only the first figure per document (missed conflict or false conflict). It fails safe, because a false conflict holds the file.
- M2 Square feet compares schedule rows across buildings (SUB-277/287 class). Those files are hidden by manual intake today.
- M3 `COUNT_RE`'s optional middle word mis-files the noun ("12 unit apartment", "4 HVAC units").
- M4 The SUB-290–295 asserts are still rule-level. Only SUB-296 is asserted end to end, and the dev loss-run format is unpublished.
- M-a The card flag on SUB-296 still reads "operations may be missing: no cooking", and the cooking line reads only the application, while the email states a griddle and a wok. The underwriter is pointed the wrong way (D-065 wording).
- L1 The T-118 screenshots are hand-built cards, not a `process_submission` run (for example, the loss-run date is cited from `application.md`).
- L2 The dev gold for `document_conflicts` still describes itself as not independently reviewed.
- L3 An emptied sales value also appears under "missing" in the producer request next to the conflict line. The producer may get asked for sales twice.
