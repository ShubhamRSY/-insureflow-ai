# Assist-only pilot — C1–C8 build and decision map

- Date: 2026-10-21. Branch: `pilot-conditions` (from `ai-team` `fd12f9c`).
- Basis: `deliverables/model-risk/T-027-assist-mode-pilot.md` (the authoritative C1–C8 text) and `deliverables/pm/pilot-readiness.md`.
- Not a production approval. The T-027 veto stands. Synthetic data only in this branch and in every screenshot.
- Written in OpenCode, not independently reviewed. Code review by @model-risk is still required.

## Three buckets

**(a) Code built on `pilot-conditions`**

| # | Built | Where |
|---|---|---|
| C1 | `PILOT_MODE=assist-only` makes `build_package` and `send_to_carrier` refuse with "assist-only pilot: send disabled". `approve` is refused; the workbench offers `confirm`, which records every value and never makes the file sendable. Self-check: no approve row exists after a confirmation. | `app/pilot.py`, `app/package.py`, `app/workbench.py` |
| C2 | `write_drafts` refuses, deletes a stale pending draft, and writes no missing-info request; `prepare.approve` refuses producer requests. | `ai/prepare.py` |
| C3 | The header says "ASSIST-ONLY PILOT — AI proposals only. Nothing is routed, sent or drafted. You decide." Every card has a scope verdict, and route text reads "Suggestion only — not a decision". | `app/workbench.py` |
| C5 | Correction rows (field, suggested, final, reason, actor, run hash) and event rows (action, refusal, time) are written under `flock` + `fsync`, 0600. The pilot monitor shows corrections per field, overrides, refusals, time per file and `extraction_failed` counted apart. The GET display log writes one row per file with run hash, prompt version and model. | `app/pilot.py`, `app/workbench.py` |
| C6 | Every value carries "AI proposal — verify against the source" with citation and confidence; needs-review values are never pre-ticked; a standing warning names both the last approved numbers (operations 9/20, loss runs 5/20, T-108) and the latest frozen, unapproved numbers (13/20, 16/20, T-117 KEEP). | `app/workbench.py`, `app/pilot.py` |
| B-191 item 2 | A `flock` or `fsync` failure now raises; `act` shows "… refused: <reason>" with the write error. No silent success path remains. | `app/workbench.py` |

**(b) Documented here (process, no code)**

- `underwriter-guide.md` — what the pilot user sees and must do.
- `incident-rollback.md` — stop events, who is told, how the tool is taken back to normal.
- `data-handling.md` — environment-only model host, synthetic-first rule, log contents and retention.
- `freeze-note.md` — the C7 values to record at pilot start and the `git diff` check.
- `self-check-C1-C6.md` — the exact commands and results run on this branch.

**(c) Company decisions still open (not made here)**

- `c-open-questions.md` — exact question, owner, and what it blocks.

## Status against C1–C8

| # | Status on this branch | What is still needed |
|---|---|---|
| C1 | Built; test proves refusal and no approve row | Independent code check (@model-risk) and the pilot-start self-check record |
| C2 | Built; test proves refusal and empty outbox | Same |
| C3 | Built; test proves label and always-on scope | @senior-underwriter UI check, High only (C3/C6 require it) |
| C4 | Code built on `sso-b190` (`e9edeba`), **not on this branch** | Review and merge `sso-b190`; @model-risk check; then C4 is met |
| C5 | Built, except the display-log actor is `unauthenticated` on this branch | Merge B-190 so views carry the signed-in user; @model-risk reviews the export at pilot end |
| C6 | Mechanism built | @model-risk must approve the warning source and any replacement numbers (see c-open-questions); @senior-underwriter UI check |
| C7 | Freeze note written; freeze has not started | Record the final branch SHA/prompt/model at pilot start; no `underwriting_pipeline/` change during the pilot |
| C8 | Not met | @pm registers the task; @head-of-underwriting sets the per-field threshold; @user decides go/no-go |

## Hard blockers

- **B-190**: built and pushed on `sso-b190`, not reviewed or merged. No real data before it is merged and checked.
- **B-191**: item 1 (cross-process lock), item 3 (thread/process tests) and item 4 (independent check) are done; item 2 (failed write is never silent) is now built and tested on this branch. Independent re-check is still required per D-057.
