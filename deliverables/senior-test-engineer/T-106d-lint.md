# T-106d - test-file lint before a gold freeze

Script: `deliverables/senior-test-engineer/lint_holdout.py` (read-only; no pipeline, no model call; imports only the Scope/gold parsers of frozen `eval_holdout_v6.py`).

Run: `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py PLAN.json [--run-date YYYY-MM-DD]` (default today). Exit 0 = PASS, 1 = any FAIL. One plain line per failure. `HOLDOUT_INBOX` / `HOLDOUT_GOLD` point it at temp copies. `--self-check` runs every case below on in-memory text and a temp set (no real files).

## Checks
1. Loss-run dates, each `loss-run*` file (md/csv/txt; PDF via pdftotext; JPG and image-only PDF via tesseract):
   - Every date on a labelled line (valued / as of / evaluated / run date / report date / `Date:`) and every table-row date must be before the run date.
   - A labelled line with no date the lint can read FAILS; no other date in the file is used instead.
   - Read: `2026-11-30`, `2026/11/30`, `11/30/2026`, `11.30.2026`, `11/30/26`, `November 30, 2026`, `Nov 30, 2026`, `Nov 30, 26`, `30 Nov 2026`, `30-Nov-2026`.
   - A date-like token it cannot read (`2026-13-45`, `Nov 31, 2026`) FAILS. A numeric date whose day-first and month-first readings fall on different sides of the run date (`10/11/2026`) FAILS; if both readings agree it passes.
   - An unreadable scan has its own message ("could not be read here ... read it by eye") and always FAILS.
2. Gold Scope line: `gold_scope()` from v6 on every gold file; invalid or missing gold is a FAIL.
3. Mix vs plan: only plan keys present are compared: `in`, `out`, `per_criterion`, `two_criteria`, `criterion_4`, `routes` (gold "Expected carrier route" counts over in-scope files).
4. Undated loss runs (written in the plan before gold): `"undated_loss_runs": ["SUB-177", ...]`. A typed file with no valued date: declared = INFO, passes; not declared = FAIL. A declared file that does have a valued date = FAIL.

Plan format: JSON, written from the mix .md before gold exists. `T-104-plan.json` is the worked example (it has no `undated_loss_runs`, as written).

## Self-check
`lint_holdout.py --self-check` (2026-10-18, run date 2026-10-17): 24 cases, all ok. They cover every format above before and after the run date, ambiguous and impossible dates, a valued line with no date next to a good date elsewhere, undated declared and undeclared in both directions, the two distinct messages, a clean temp set that passes, and the same set without the declaration that fails.

T-104 (SUB-174-205) with the plan as written: FAIL, 34 lines: 12 loss runs valued after 2026-10-17 (174, 175, 176, 179, 180, 182-187, 194; 174 and 175 are scans read by OCR), 17 typed loss runs with no valued date that the plan does not declare, 5 route-count lines.

Route finding: the plan (producer intent A5/B6/C4/senior 3/no_match 2) differs from gold (A2, B0, C0, senior_referral 15, no_match 3), consistent with the late loss runs pushing files to senior referral. A future plan should state route counts after the loss-run dates are fixed.

## Limits
- A late date on a line that is neither labelled nor a table row (a bare "Nov 30, 2026" in prose) is not checked.
- Tokens are read by pattern: a date-like token it cannot place FAILS, but a date written in words ("the thirtieth of November") is not seen.
- OCR can misread a scan; confirm a scan FAIL by eye. An "as of" in ordinary prose on a loss run FAILS as a labelled line with no date.
- Letter `Date:` lines count as dates.
