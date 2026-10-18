# P-055 as built (T-104a, D-105)

Detector `underwriting_pipeline/ai/scope.py`, version `scope-v3` (P-058, see `p-057-p-058-as-built.md`). No model call. Not a production approval.

## Rules as built
- Application = a document named application / solicitud / acord, or an unnamed one with 3 or more application labels. Emails, loss runs, schedules and replies are never the application.
- 1 Scanned application: image, PDF with any OCR page, or a PDF page "scan not readable". Scanned loss runs do not count.
- 2 Multiple locations: 2 or more distinct addresses in a schedule ("100 Main St", "100 Main Street", "Ste 2" are one place, via llm_extract.same_address; "Bldg B" rows stay separate, as SUB-145) (csv, xlsx, or a file named schedule; "address" column, mailing/prior columns ignored), or "(loc 2)" / "Location 2:" in the application.
- 3 Non-English: common Spanish words outnumber common English words in the application; field labels count in their own language (Named insured, Premises, Effective date... English; Asegurado, Fecha efectiva... Spanish); the value of name and address lines is left out, and the insured's name is left out wherever it recurs (same scope under a Spanish name). Unsure (fewer than 5 such words, or Spanish above half of English but not more) is manual intake, reason "document language not clear". With no application, the email and other documents are checked as well (stricter only).
- 4 Application not identified (includes email-only files).
- Fail closed also: "application text layer not known" (unreadable PDF), "a scanned document could not be identified" (unreadable unnamed image), "detector error" (any exception).
- Every matched reason is returned; the card lists all.

## Where wired
- `prepare.process_submission`: detector runs first; out of scope returns `_manual_intake` (status `manual_intake`, empty fields, no model call, request None). Status is in `STATUSES` and `REFUSED_STATUSES`, so write_drafts writes no draft (and removes a stale one), `approve`, `package.send_to_carrier`, `agency_problem`, `confirm_problem`, and `workbench.record_decision` refuse; `build_package` refuses too. Refusals use `prepare.status_refusal` ("manual intake (scanned application; multiple locations)"). The saved run carries `scope` (version, in_scope, reasons) under the hash.
- `workbench._match`: route `manual_intake`, no provisional, no suggested market, not a hold. Card: Manual intake block listing every reason; no draft, approve, carrier match or Missing section; What's new line (2026-10-17, T-104a, D-105). Screenshot `deliverables/software-engineer/screenshots/T-104a-manual-intake.png` (temp sandbox copy).
- extraction_failed: an out-of-scope file makes no model call, so it cannot fail; an in-scope file that fails stays extraction_failed.

## After code review (coordinator findings 1-7)
- Language: inbox-wide `language_unsure` 60 -> 0 (all 173 files); non_english 17, not_identified 30, scanned 29, multiple_locations 13 unchanged; in scope 53 -> 95. No file is still language_unsure.
- A csv/xlsx named application/acord, or holding 3+ application labels, is the application, not a schedule.
- write_drafts removes a stale conflict file for a manual-intake file. Card: no edit option, record_decision refuses edits, the field table is replaced by "Nothing filled in: a person reads the file." Decline stays. match() docstring lists manual_intake; package._route/_overridable handle it (not overridable); no route-keyed counters exist.
- prepare self-check: the real detector runs on all 57 stub-fixture calls; 33 stay in scope (no stub), 24 (no application file or terse) are let through by the stub.
- Backlog (no code): frozen scorers (v4 etc.) and eval_gold do not know route/status manual_intake; the P-055 detection measures need a scorer path before T-104 is run.

## scope-v2 (after @model-risk BLOCK, H1/H2)
- H1: every csv/xlsx/schedule/sov/locations file is counted for address rows even when it also holds application labels or is the application; mailing/prior lines are not counted. The application list forms are widened: "(loc n)", "Location n:", "Location #n:", "Location n -", a numbered or bulleted list under a Locations/Premises heading, "Second/Additional location:", and two distinct premises address lines.
- H2: any OCR-read document not identified by name as email, loss run, schedule or reply is a scanned page of the application (scanned_application; unreadable ones unidentified_scan). A scanned loss run (SUB-159 kind) stays in scope.
- Card: Loss history / Cooking / Hood lines read "not read (manual intake)".
- Inbox-wide vs scope-v1 fixes: scanned_application 29 -> 31 (SUB-074, 084: readable unnamed scan.jpg); all other counts unchanged (not_identified 30, non_english 17, multiple_locations 13, in scope 95). SUB-127-173 out of scope: 129, 140, 142, 143, 144, 145, 163, 168, 169, 170, 172 (unchanged).
- Known limits (backlog): a searchable PDF whose text layer came from a scanner's OCR looks typed; language thresholds (MIN_WORDS 5, UNSURE_RATIO 0.5) were tuned on the inbox incl. T-103 files; only Spanish is counted as non-English.

## Dev detection, SUB-127 to 153
SUB-129 scanned application (jpg). SUB-140 multiple locations. SUB-142 not identified (email-only). SUB-143 not identified + non-English (email-only, Spanish). SUB-144 scanned + multiple locations. SUB-145 multiple locations. Others stay in scope. Also SUB-163, 169 non-English; SUB-170 scanned + multiple; SUB-172 multiple locations.

## Known limits
- Terse stub fixtures under 5 common words are still "language not clear" (fail closed); no file in the inbox is.
- Spanish is the only named language; any other language is "not clear" (manual intake).
- Application identified by file name or labels only; an unusual name with few labels is "not identified" (safe).
- A frozen scorer or regression run on an out-of-scope dev file now gets status manual_intake (SUB-129, 140, 142-145). Published scores are not rewritten.
- Not run: regression_dev --quick (needs saved replies; 0 calls this task), T-104 files.
