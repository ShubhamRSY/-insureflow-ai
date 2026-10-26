# @model-risk check of P-044 (D-090), commit 1c2f02d

Date: 2026-10-15. Reviewer: @model-risk. Synthetic data only. An approved proposal is not a production approval. The T-027 veto stands and no send is authorised.

## Verdict: APPROVE (no High findings). Four Medium/Low items go to the backlog.

Evidence. I ran the self-checks with `.venv/bin/python` and LLM_API_KEY, LLM_BASE_URL and LLM_MODEL unset: prepare ok, workbench ok. My probes called functions in memory and wrote nothing. `git status` was the same before and after, apart from this memo and my team entries.

## Acceptance criteria (D-090 item 1)
- **Recognised carrier format only: met.** `carrier_run_valued` needs an exact A/B/C layout: header, then insured, then period line(s), then the valued line, then either a claims table with at least one row or the carrier's own no-claims line, with nothing after it. `loss_run_kind` gives "loss_run" only through that function. The P-043 sentence-pattern code (AUTHORED, HEADER_ISSUER, ISSUED_BY, OTHER_AUTHOR, `_issued_by_carrier`) is gone.
- **Everything else goes to needs review: met.** These all came back "unclear" with nothing accepted: the B-329 sentence; P-043's "good" headers, which now count as unknown layouts; a markdown `#` before the header; a hyphen in place of the em dash; two runs joined together; a table with no rows; a no-known-losses row; and an HTML comment line after the table. In `gate_loss_run`, the value is kept and flagged with RUN_UNCLEAR, which starts with "not a recognised carrier loss run". P-040's letter rule (drop the value, the field stays missing) still applies.
- **Self-checks: met.** They include the B-329 sentence (unclear), one run in each of the A, B and C layouts (loss_run, valued 2026-09-30), and a claim date from a carrier run that is not the valued date (needs review).
- **Recomputed on the inbox.** Across all 59 `simulation/inbox/SUB-*/*loss*.md` files, no file is in a recognised layout: 0 come back loss_run, and the rest are unclear or letter. This matches the dev check, where loss_runs has 0 automated and 0 silent errors, and false completes are 0 (JSON status_split agrees, and the commit matches with nothing uncommitted). I did not re-run the dev check itself. My figure comes from reclassifying the files directly.
- **Workbench:** the What's new line is present and quotes the reason text.

## High
None.

## Medium / Low (backlog, one line each)
- M1: every line that starts with `_` is skipped, wherever it appears, not only the leading banner. A recognised run followed by "_Typed by the applicant from memory_" is still accepted, and so is one with such a line in the middle. Fix: skip `_` lines only before the header.
- M2: the accept path has only ever been tested on in-memory strings. No inbox document is in an A/B/C layout, and no PDF or OCR text has gone through `carrier_run_valued`. Add one synthetic A/B/C file to the dev set before the next hold-out, or real carrier runs will all show review pending (safe, but 0% automation).
- L1: the valued date is not checked as a date. 2026-13-45 is accepted, and so is a valued date before the policy period ends.
- L2: `gate_loss_run` accepts a value that matches a recognised run in another file, but leaves the citation on the cited file, which may be a letter. Re-point the source to the carrier run.
