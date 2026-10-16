# @model-risk check — D-092 (P-045, B-343, T-102 mix)

- Date: 2026-10-15. Reviewer: @model-risk. Deliverable: commit 0a56520.
- Evidence read: D-092; `git show 0a56520` (prepare.py `CARRIER_NEGATION`, `carrier_run_check`, `carrier_run_valued`, `gate_loss_run`; workbench.py What's new; gold SUB-150/151; dev-SUB-147-152-D-092-cached.md/.json; BACKLOG B-345); simulation/inbox/SUB-150, SUB-151 loss-runs.md; T-102; check-D-091.md.
- Re-run (D-069): full repo copied to a scratch directory. `prepare.py` and `workbench.py` self-checks with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL unset: "prepare ok", "workbench ok". `dev_p044_147.py` (DEV_TAG=mr-recheck) on the copy with a copy of cache-D-091, placeholder key, outbound network denied (sandbox-exec): 0 model calls, 6 of 6 from cache, table identical line for line to the committed report: plain complete SUB-147, SUB-149; **0 false completes**; SUB-150/151 missing with the 1c reason, incomplete.
- In-memory probes on the copy (results below). Repo git status unchanged except this file, DISCUSSION.md and STANDUP.md.

## Item 1 — P-045 and B-343: CHANGES REQUIRED (1 High open)

| Criterion | Result |
|---|---|
| (a) "_" lines not skipped; carrier-negating line sends to review with reason | Met when a value is extracted. A leading "_" line breaks the layout; "_not from Carrier B_", "Not issued by", "COPY", "Sample", "Copia" give `negated` and the review reason quotes the line. See M1 for the no-value case. |
| (b) valued date real and not in the future | Met. 2026-13-45, 2025-02-29, 2031-01-01 give `bad_date` with reason; today's date is accepted. |
| (c) carrier layout, no readable valued date: incomplete with the stated text | **Not met in general (H1).** Met only when the model returns no date (as in the cached dev run). |
| Dev gold SUB-150/151 corrected with note | Met. The notes match the documents (150 opens with a Carrier A header then prose; 151 Carrier B layout without a valuation line). |
| Self-checks for each | Present and pass. The (c) self-check covers only the value-is-None case. |
| SUB-147–152 from cache: 0 false completes | Met, reproduced. |
| B-343 scans, image-only, xlsx never auto-accepted, reason text | Met: jpg-in-scans, image-only PDF in scans and xlsx each give "loss run from scan/spreadsheet: check it (<file>)"; a typed PDF in the layout is still accepted. |
| xlsx reader logged as backlog | Met (B-345). |

### H1 (High) — an undated carrier run with an extracted date becomes "complete — review pending", not incomplete
- Where: `gate_loss_run`, final branch. When the cited source is `no_date`, the code sets `needs_review` and the 1c reason but **keeps the value**.
- Probe: SUB-151 layout without the valuation line; model value "2026-01-01" cited to loss-runs.md → `{'value': '2026-01-01', 'needs_review': True, 'reason': 'loss run found but no valued-as-of date; ...'}`. A flagged field with a value gives status REVIEW_PENDING, and `ready_to_route` is True for review pending without a conflict (prepare self-check, P-041). So the file can be approved and routed with a loss-run date that the document does not contain, and the card shows a date next to "no valued-as-of date".
- Why it matters: (c) says "status stays incomplete". The dev run passed only because the cached qwen replies returned no date for 150/151. SUB-151 has policy terms ending 2026-05-01 and 2027-05-01, which a model can plausibly return. The T-102 copied-header letter with a valued date (M3) will reach exactly this branch in the hold-out unless the letter is classified as a letter.
- Remediation: when the value's source (or the only loss-run document) is `no_date`, set `value=None` as the no-known-loss letter path does, keep the 1c reason, and add a self-check with a value present that asserts value None and status incomplete. This is extraction code: it needs a P-### and the user's `approve change P-###`. Closed when that self-check passes and the cached SUB-147–152 re-run is unchanged.

### Medium / Low (backlog, one line each)
- M1: a negated carrier run (e.g. a "COPY" line) when the model returns no value leaves the field missing with **no reason** on the card; (a) asks for the reason.
- M2: any csv/xlsx that merely contains the date string (e.g. an SOV) overrides the specific reason with "loss run from scan/spreadsheet: check it (sov.csv)", naming the wrong file (probe: negated typed run plus sov.csv).
- L1: "copy" inside a claims row ("copy machine fire") negates a genuine carrier run; safe direction (review).
- L2: negation is checked only inside the carrier document; "the attached loss run is a sample" in the email is ignored, and "duplicate", "draft", "copies", "not a carrier document" are not matched.
- L3: a valued date before the first policy period start is still accepted (rest of D-091 M7; not in the user's (b)).
- L4: the dev report header records commit 7a5eb4c (the parent), not the code that produced the table.

## Item 2 — T-102 mix: CONFIRMED

- M3 (copied-header letter contains a valued-as-of date), M4 (one typed carrier run uses the no-claims line), M5 (gold follows the documents; the 5 typed carrier files have no other planned gap), L2 (xlsx carrier run always goes to review; none planned) are in the acceptance criteria. Gold expects review for the 2 JPG scans and the 1 image-only PDF. The no-banner rule is added. Counts add up: 8 carrier (3 typed PDF, 2 md, 2 JPG, 1 image-only PDF), 6 non-carrier, 6 none.
- No SUB-127–146 file exists in simulation/inbox or the gold set (checked).
- M-T102 (Medium): the gold reason for the copied-header letter and for the "carrier layout with the valued-as-of line missing" file should follow D-092 1c (incomplete, "loss run found but no valued-as-of date"); say so in T-102 so the gold writer and the scorer agree.
- L5: "all of them carry a typed carrier-format loss run" still contradicts M5 (a clean scanned-run file can be gold-complete); read it as "at least 5 of them".
- Building the files may proceed (D-092 item 4). Do not run the pipeline on SUB-127–146 until H1 is closed.

## Decision
- Item 1: not approved; H1 open. Item 2: mix confirmed.
- This is a development check. It is not a production approval; the T-027 veto stands. An approved P-045 is not a production approval.
