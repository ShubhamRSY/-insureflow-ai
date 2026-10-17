# @model-risk check — T-104a (D-105, P-055 rev 3), detector `scope-v1`

- Date: 2026-10-17. Reviewer: @model-risk. 0 model calls; probes in temp dirs only.
- **Verdict: BLOCK** (do not freeze the code for T-104 until H1 and H2 are closed). This is not a production approval in any case; C-4 stays "Not approved for production" and the T-027 veto stands. P-055 being approved (D-105) is not a production approval.

## What I re-ran
- `scope.py`, `prepare.py`, `package.py`, `workbench.py`, `points.py` self-checks: all pass ("scope ok scope-v1", "prepare ok", "package ok", "workbench ok", "points ok"). `git status` and file mtimes unchanged afterwards: no real file written.
- pyright on the 5 changed files: 47 errors on HEAD, the same 47 after the change (normalised diff empty); `scope.py` 0 errors, 1 openpyxl stub warning. No new pyright errors.
- Inventory: C-4 entered as Tier 2, version `scope-v1`, not approved. OK.
- Whole-file manual intake: no model call, empty fields, status `manual_intake` in REFUSED_STATUSES, no draft (stale draft and conflict file removed), approve / edit / send / package / confirm refused with reasons, route `manual_intake` with no provisional or suggested market. Screenshot shows every reason and the send refusal. OK.

## High findings

### H1 — Criterion 2 leaks: a multi-location schedule is read as the application when its headers use common words
- `_kind()` turns any csv/xlsx/"schedule" file with 3 or more application labels into the application, and `_addresses()` is then never run on it. A standard SOV header (`Premises Address`, `Construction`, `Year Built`, `Operations`) reaches 3 labels.
- Reproduced on a temp copy of dev SUB-172 with the "(loc n)" lines removed from the application (the P-055 required near-pass form "multi-location only in a schedule file"): original headers → `multiple_locations`; the same schedule with `year_built`→`Year Built` and `cooking`→`Operations` → **in scope, no reason**. The file would then be read, routed and could be sent.
- The application location list is also narrow: `Location #2: ...`, `Locations:\n1. ...\n2. ...`, `Location 2 - ...`, `Second location: ...` all return in scope.
- The self-check asserts the leak as intended behaviour (`application.csv` / `data.csv` with two street addresses must NOT be `multiple_locations`), against P-055 criterion 2 ("a schedule file (csv, xlsx, ...) with two or more address rows").
- **Resolves it:** a file named schedule / sov / locations, or any csv/xlsx not named application/acord, is always checked for address rows regardless of labels; a csv/xlsx application is also checked for 2+ distinct premises address rows; the application location list accepts `Location #n`, `Location n -`, numbered location lists and a second distinct premises address (mailing/prior lines excluded). Replace the asserting self-check with the opposite, and add the SUB-172 schedule-only variant above plus each list form as self-checks. Re-run the in-scope boundary checks (one-row schedule, mailing/prior address) to show they stay in scope.

### H2 — Criterion 1 / fail closed: a readable scanned page that is not named as the application is ignored
- `_codes()` flags a non-application "other" document only when it is unreadable. A readable OCR image or OCR'd PDF with fewer than 3 labels and a neutral name passes silently.
- Probes: `application.md` (typed) + `IMG_0412.jpg` (OCR, "Sprinklers: no / Loss history: none") → in scope; same with `page2.pdf` carrying OCR words → in scope. P-055: "A scanned page anywhere in the application counts"; unknown → manual intake.
- **Resolves it:** any OCR-read document (image suffix, `ocr_words`, `ocr_confidence`) that is not identified by name as an email, loss run, schedule or reply is treated as part of the application (`scanned_application`) or as `unidentified_scan`; both are manual intake. Add both probes as self-checks; show the scanned-loss-run boundary case (SUB-159 kind) stays in scope. Any extra false manual intake counts against the 2/20 ceiling on T-104.

## Backlog (Medium / Low, one line each)
- M: Manual-intake card still prints "Cooking: not scored — no cooking equipment stated in the file" and "Hood and suppression: not stated" for a file that was never read (SUB-170's schedule lists fryers); show "not read (manual intake)" instead.
- M: Criterion 3 counts only Spanish words; a French/Vietnamese/other application with English labels counts as English and stays in scope. Count non-English as "not in the English list" or fail closed when most words are in neither list.
- M: Schedule without an "address" header falls back to a street-suffix regex; "100 Broadway", "12 Calle Sol" are not counted.
- M: Frozen scorers and eval gold do not know status/route `manual_intake`; scorer v5 must have the P-055 measures (leakage, recall per criterion, reason accuracy, false manual intake) before T-104 is scored (author notes this).
- L: A searchable PDF whose text layer was made by a scanner's OCR looks typed; record it as a known limit in C-4.
- L: Language thresholds (MIN_WORDS 5, UNSURE_RATIO 0.5) were tuned on the inbox incl. T-103 files (60 → 0 unsure); fine as T-103 is not gate evidence, but record the tuning in C-4.
- L: openpyxl stub warning in `scope.py` self-check import.

## Look-again — scope-v2 (2026-10-17)

- **Verdict: APPROVE WITH CHANGES.** H1 and H2 are closed, and I found no new High. The code may be frozen for T-104 under D-105 step 3. This is still not a production approval: C-4 `scope-v2` stays "Not approved for production", and the T-027 veto stands.
- Re-run: all 5 self-checks pass ("scope ok scope-v2"). No real file changed (git status the same). pyright: `scope.py` 0 errors; the other 4 files have the same 47 errors as HEAD. Inventory C-4 now names `scope-v2` and the known limits.
- **H1 closed.** Every csv, xlsx, schedule, sov or locations file is counted for address rows. Temp SUB-172 with the schedule only and headers renamed `Year Built`/`Operations` → `multiple_locations`. A labelled `schedule.csv` and `sov.xlsx`, `Location #2:`, a numbered `Locations:` list, `Location 2 -` and `Second location:` → all `multiple_locations`.
- **H2 closed.** `IMG_0412.jpg` and `page2.pdf` with OCR words beside a typed application → `scanned_application`. The scanned loss run (SUB-159 kind) stays in scope.
- In-scope boundary cases stay in scope: a mailing and a prior address, a one-row schedule with a mailing column, one place written twice, a Spanish email, `Other locations: none`, and a loss-run xlsx with a carrier address. Dev SUB-127 to 173 give the same detections as the as-built note.

### Changes (backlog, before or with T-104; none blocks the freeze)
- M (leak, recommended before freeze): an application that names a second premises in a form outside the spec examples stays in scope. Probes: `Location No. 2: 200 Oak Ave`, `Building 2: ...`, `Premises address: 100 Main St, Austin TX and 200 Oak Ave, Austin TX`, and "we also operate a second store at 200 Oak Ave". Cheap fix: count distinct street matches on premises lines, and accept `No.`/`Building n`. Watch it in shadow (M2).
- M (false manual intake): `Additional premises: N/A` → `multiple_locations`. LOC_ORDINAL should skip none/N/A values. It counts against the 2/20 ceiling.
- L: an unreadable neutral image (e.g. `building-photo.jpg`) is `unidentified_scan`. This fails closed and is accepted, but record it in C-4.
- Still open from the first check: the M cooking/hood lines on the manual-intake card, the M languages other than Spanish, the M street regex without an address header, and the M scorer v5 measures for manual_intake.
