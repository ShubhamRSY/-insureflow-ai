# Proposal P-016 — Exact citations, the confidence gate on scans, and unread content (T-027 (a), (b), (c))

- Author: @ai-engineer-assistant
- Date: 2026-10-11
- For: @user (the AI Engineer)
- Task: T-080. Line 3 of `team/DEMO-BLOCKERS.md`. Decisions: D-033 item 4, D-037.
- Status: PROPOSAL. Not approved. Not implemented.
- No code, prompt, OCR setting, cache file, scorer, or score file was changed to write this. No model call was made. No scorer was run.
- Synthetic data only. Not a production approval. Lifting the T-027 veto is @model-risk's call.
- Published scores are not recounted.

One proposal for (a), (b), and (c) together, as D-037 says: "Draft (a)–(c) as one proposal for my approval." Where a point is your choice, the options are lettered and none is picked.

## What the reviewers say resolves it

@model-risk, OBJECTION, Re: T-027, 2026-10-11:

> Resolves the veto: (a) no value fallback; the value must be inside the quoted span for names, numbers, dates, addresses; translated fields stay needs_review; (b) gate on the lower of model and OCR score, OCR score taken from the cited words including digits, plus a confidence-versus-hit table; (c) every file and page is either read or listed as needs human, with the reason; (d) then a new 20-file hold-out, gold first, commit hash and call log saved, scored once.

@senior-underwriter, REVIEW, Re: T-027, 2026-10-11:

> High-1: ... Resolve: no quote match, no value.
> High-2: ... Resolve: decide needs-human per page and name the page.
> High-3: ... Resolve: scan numbers and dates are marked needs review; a date must parse.

D-037, your words: "(b) amends P-003b: gate on the lower of model and OCR confidence, OCR confidence from the cited words including digits. (c): every file and page is read or listed as needs human with the reason."

(d), the new hold-out, is not in this proposal. It is T-091, T-092, and T-093.

## What the code does today

- `llm_extract.accept_field`, line 228: `span = find_quote(text, quote) or find_quote(text, str(value))`. When the model's quote is not in the file, any place the value's characters appear becomes the citation. Nothing checks that the value is in the quote.
- `accept_field`, lines 210 to 212: on a scan the model's confidence is replaced by the page score. `sources._ocr_score` builds that score from words of four or more letters only (line 101). Digits are not in it.
- `sources.read_folder`, line 201: a file type it does not know is skipped with `continue` and is listed nowhere.
- `sources._pdf_text`, lines 141 to 143: a PDF with 40 typed characters in total is never OCR'd. Lines 150 to 158: a scanned PDF gets one text and one mean score, and the per-page "needs human" answer is thrown away. Line 159: any OCR error is swallowed with no reason.
- `llm_extract.llm_extract`, line 376: `packed[:120000]` cuts the text and says nothing.

## The change

### (a) Exact citations only

In `accept_field` (`underwriting_pipeline/ai/llm_extract.py`), and one new small function beside it, `value_in_span(field_id, value, span_text)`:

1. The value fallback is removed. The quote must be found in the named file. "No quote match, no value." The row keeps `value: None`, `needs_review: True`, and a new key `reason: "quote not found in <file>"`.
2. The value must be inside the quoted text, by field:
   - `named_insured`, `premises_address`: the value's characters are in the quote, ignoring case and runs of spaces.
   - `sales_or_payroll`, `tiv_building`, `year_built`: the value must equal one whole number in the quote. A whole number is a run of digits with digits on neither side, commas removed. "10" is not inside "2010000". "1990" is not inside "210-555-1990" as a year (see N below for the phone case). "2021" is not inside "Year built: 1948".
   - `effective_date`, `loss_run_valued_through`: "a date must parse". The value must be a real calendar date (`datetime.date.fromisoformat`), and the same date must be in the quote.
   - `operations`, `construction`: if the value's words are in the quote, it is accepted as today. If they are not (a translation such as "mamposteria" to "masonry", or a rewording), the value is kept and "stays needs_review", with `reason: "value is not in the cited text (translated or reworded)"`.
3. A value that fails rule 2 for a name, number, date, or address is not stored: `value: None`, `needs_review: True`, `reason: "value not inside the cited text"`.
4. The conflict sides go through the same function, because `llm_extract` already calls `accept_field` for each side.

Your choices on (a):

- N, numbers written another way in the file ("$1.2M", "220k").
  - N1: digits only. A value the file writes as "1.2M" is not stored and needs a person.
  - N2: also accept when the existing `prepare.amount_value` reads the same number from the quote. The helper moves to a place both files can import; its rules do not change.
- H, a number that sits inside a phone number or a policy number written with dashes ("210-555-1990").
  - H1: whole-number rule only. "1990" cited to "210-555-1990" would pass rule 2, because the dashes end the number. It then depends on the model's quote, not on the fallback, which is gone.
  - H2: a number joined to other digits by "-" or "/" is not a whole number, except inside a date. "1990" in "210-555-1990" fails.
- D, a date the file writes another way ("November 1, 2026", "01/11/2026").
  - D1: only a date written in the file exactly as the value (YYYY-MM-DD). Anything else is not stored.
  - D2: also accept a date in the quote that parses to the same day from a short fixed list of formats. Day-first and month-first cannot be told apart for some dates, so those stay not stored.
- R, what "stays needs_review" does to the file's status. Today `needs_review` blocks nothing: `prepare.completeness` looks only at whether a value is present, and nothing under `app/` reads the flag.
  - R1: flag only. The value counts as present. The row carries the flag and the reason. Showing it, and whether a send waits on it, is under `underwriting_pipeline/app/` and is @software-engineer's; it needs a task from @pm.
  - R2: a kept value that needs review does not count as confirmed: the file is `incomplete`, with a new report key `needs_review_fields`, and the producer request does not ask for those fields.
- Q, the quote on the stored row (T-081 needs the cited text).
  - Q1: each accepted row also keeps `quote`, the exact text between `start` and `end` in the text `sources.read_folder` returned. `start` and `end` stay. The key in the saved extraction file is @data-engineer's to add (as in T-069).
  - Q2: no new key. The workbench calls `sources.read_folder` again and slices with `start` and `end`.

### (b) The gate on scans — this amends P-003b (D-020 item 1)

P-003b says: on a scanned page the gate uses the Tesseract page score in place of the model's score. P-016 replaces that sentence with D-037's: the gate uses the lower of the model's confidence and the OCR confidence, and the OCR confidence comes from the cited words, digits included. A typed PDF, an Excel file, and an email keep the model's confidence and the 0.75 line, as in P-003b.

- `sources._ocr_score`: also returns every word with its own Tesseract score, with no letters-only filter and no four-letter minimum. The page score it returns today is not changed, and `_read_scan` still uses it to decide whether a page can be read at all.
- `sources.read_folder`: a scanned file's doc gets `ocr_words` (word, score). `ocr_confidence` stays.
- `accept_field`: when the source is a scan, `ocr = score of the cited words`; `confidence = min(model_confidence, ocr)`. The row keeps `model_confidence` and gains `ocr_cited_confidence`. A cited word that is not in the word list counts as 0.
- The 0.75 line is not changed.
- The confidence-versus-hit table @model-risk asks for: `regression_dev.py` puts each field's final, model, and cited-word confidence on its rows and prints one table of confidence band against hit and miss. No hit or miss rule changes. A first table from the saved replies is below.

Your choices on (b):

- C, which number "from the cited words" is. Measured on the saved scans below.
  - C1: the lowest score among all words of the quote, labels included.
  - C2: the mean score of all words of the quote.
  - C3: the lowest score among the words of the quote that hold the value.
- S, @senior-underwriter's line: "scan numbers and dates are marked needs review".
  - S1: the gate as D-037 words it, and nothing more.
  - S2: also, every number and date that comes from a scan and passes the gate is kept with `needs_review: True` and `reason: "number or date read from a scan"`. What that does to the status follows R.
- G, the document rules in `prepare.apply_document_rules` (`carrier_run_date`, "joisted masonry", "cook <food>"). They cite their own match, so (a) holds for them. They store confidence 0.95 from any text, scan text included, so (b) does not reach them.
  - G1: leave them as they are.
  - G2: on a scan source they take the cited-word score like any other value.

### (c) Every file and page is read or listed as needs human, with the reason

`sources.py` and `prepare.py`. The four cases in @model-risk's H3:

1. Unsupported file type. `read_folder` no longer skips it. It returns a doc with no text, `needs_human: True`, and `reason: "file type .docx is not read"`.
2. An unreadable page inside a multi-page PDF. `_pdf_text` reads page by page. Each page is typed, read by OCR, or not read. A page that is not read is listed with its number and the reason ("page 3: scan not readable, OCR score 22"). A readable page no longer hides it, and the unreadable page's score no longer pulls the readable page down, because (b) scores the cited words.
3. Scanned pages in a PDF that has 40 typed characters. The 40-character test is applied to each page, not to the whole file. A page under 40 typed characters, or a page mostly covered by an image, goes to OCR.
4. Text past 120,000 characters. Nothing is cut silently. Files are packed whole, in order. A file that does not fit is not sent and is listed: "not sent: text past 120,000 characters".

Also, when OCR for PDF pages cannot run (on this machine `pdftoppm` is not installed), each such page is listed with the reason "OCR for PDF pages is not available" in place of today's silent `except`.

`prepare.process_submission`: `report["needs_human"]` stays a list of file names, so `package.py` line 39 and the workbench keep working with no edit. A new key `report["unread"]` holds one row per file or page: `{"file", "page", "reason"}`. A premises dropped by P-001 keeps adding its file name as today.

Your choices on (c):

- L, text past 120,000 characters.
  - L1: as above. The file that does not fit is listed for a person; the rest is read.
  - L2: split into more than one model call. More tokens, and the merge of two replies is new logic. Not drafted here.
- E, a file that cannot be opened (damaged or locked PDF, a text file that is not UTF-8). Today it raises out of `read_folder` and the whole submission fails. It is in (c)'s words and not among H3's four cases; it is @model-risk's Medium in `deliverables/model-risk/backlog-T-027.md`.
  - E1: include it. The file is listed with `reason: "could not be opened"` and the other files are read.
  - E2: leave it in the backlog.

## Files and functions that change

| File | Function | Part |
|---|---|---|
| `underwriting_pipeline/ai/llm_extract.py` | `accept_field`; new `value_in_span`; `llm_extract` (the 120,000 cut; pass word scores); the self-check | (a), (b), (c) |
| `underwriting_pipeline/ai/sources.py` | `_ocr_score`, `_read_scan`, `_pdf_text`, `read_folder`; the self-check | (b), (c) |
| `underwriting_pipeline/ai/prepare.py` | `process_submission` (`unread`; R2 and G2 only if chosen); `amount_value` moves under N2 | (a), (c) |
| `underwriting_pipeline/ai/regression_dev.py` | the row dict in `quick` and `main`; one table | (b) |

Not mine: the workbench and `package.py` (`underwriting_pipeline/app/`, @software-engineer), and the saved extraction file's keys (@data-engineer).

## The reviewers' cases, as self-checks

Each becomes one assert in the `llm_extract.py` self-check, with no model call:

| Case | From | Expected after P-016 |
|---|---|---|
| year built 1990, quote not in the file, "210-555-1990" in the file | @senior-underwriter High-1 | not stored: quote not found |
| TIV 850000, "Policy no. 8500001" in the file | @senior-underwriter High-1 | not stored |
| Masonry, "Prior carrier: Masonry Mutual" in the file, quote not in the file | @senior-underwriter High-1 | not stored |
| value "2021" citing "Year built: 1948" | @model-risk H1 | not stored: value not inside the cited text |
| "10" with an invented quote, "2010000" in the file | @model-risk H1 | not stored |
| effective dates "2O2H-01-O1", "RO2F-O1-01", "A2F-O1-O1" | both | not stored: the date does not parse |
| SUB-084 construction at model confidence 0.6 on a scan | @model-risk H2 | not stored: the lower score is 0.6 |
| SUB-078 year built 1991, gold 1981 | both | depends on C: see below |
| SUB-077 year built 1942, gold 1948 | both | kept under C1, C2, and C3; marked needs review only under S2 |
| a folder with one unsupported file | @model-risk H3 | listed in `unread` with the reason |
| a two-page PDF, one readable page and one blank | both | page 2 listed; page 1's values kept |
| a PDF with a typed cover page and a scanned page | both | the scanned page goes to OCR or is listed |
| text past 120,000 characters | @model-risk H3 | the file that does not fit is listed |

SUB-077 year built 1942 is the one reviewer case the gate in D-037's words does not catch at the 0.75 line: Tesseract scored the word "1942" at 0.85 and the lowest word of that quote at 0.79. I say so plainly because both reviewers named it.

## What happens to values that pass today — estimate from the 13 saved replies

This is an estimate. I re-applied today's gate and a scratch copy of the proposed rules to the 13 saved replies (SUB-027, 029, 038, and 077 through 086). No model call. Nothing in the repo was written. It is not a score: the "right" and "wrong" marks compare the model's raw value with the gold line before the later rules in `prepare.py` run, and effective date has no gold line.

All 13:

- 115 values in the replies. Today's gate keeps 115 and drops 0. That matches @model-risk's count.
- The value fallback fired on 0 of the 115. Removing it changes nothing on these replies. It closes the hole the reviewers showed with made-up fields.
- 8 typed files, 71 values: all 71 are inside their quote and all have model confidence 0.75 or more. (a) and (b) change nothing on the typed files.
- 5 scans, 44 values (SUB-038, 077, 078, 084, 085). 6 fail (a):
  - three effective dates that do not parse: "2O2H-01-O1" (SUB-077), "RO2F-O1-01" (SUB-078), "A2F-O1-O1" (SUB-085);
  - SUB-085 TIV "O" (a letter, cited to "Building Tiv: O");
  - SUB-084 operations "taqueria restaurant" cited to "Operaciones: taqueria", and SUB-084 construction "masonry" cited to "Construcetow: mancposteria". These two are translated: kept as needs review by (a), then dropped by (b) (model 0.6 for construction; cited words 0.44 to 0.66 for operations).

The 44 scan values under (a) and (b) together. 40 have a gold line; today 31 of those are right and 9 are wrong.

| | Kept | Kept and right | Kept and wrong | Dropped and right | Dropped and wrong | Dropped, no gold |
|---|---|---|---|---|---|---|
| Today | 44 | 31 | 9 | 0 | 0 | 0 |
| C1, lowest word of the quote | 24 | 21 | 2 | 10 | 7 | 3 |
| C2, mean of the quote | 38 | 30 | 7 | 1 | 2 | 3 |
| C3, lowest word that holds the value | 30 | 27 | 2 | 4 | 7 | 3 |

One kept value in each row is SUB-038's effective date, which parses and has no gold line.

- The 2 wrong values kept under C1 and C3: SUB-038 premises (the scan reads "san Antonio") and SUB-077 year built 1942.
- Under C2, five more wrong values stay: four premises with a misread or missing ZIP (P-001 already drops those four later in `prepare.py`) and SUB-078 year built 1991 (cited words mean 0.82).
- SUB-078 year built 1991 is dropped under C1 (0.63) and C3 (0.63), and kept under C2.
- Right values that stop passing under C3: loss-run dates on SUB-038 (0.58) and SUB-077 (0.39), SUB-078 named insured (0.66), SUB-084 construction (model 0.6). Under C1 six more: SUB-038 year built, SUB-077 TIV, SUB-078 TIV, SUB-084 and SUB-085 named insured, SUB-084 loss-run date.

First confidence-versus-hit table, the 40 scan values with a gold line, right : wrong:

| Band | Model confidence | Page score (today's gate) | C1 | C2 |
|---|---|---|---|---|
| under 0.50 | 0 : 0 | 0 : 0 | 1 : 5 | 0 : 0 |
| 0.50 to 0.74 | 1 : 0 | 0 : 0 | 9 : 2 | 1 : 2 |
| 0.75 to 0.89 | 0 : 0 | 24 : 8 | 5 : 2 | 13 : 6 |
| 0.90 and over | 30 : 9 | 7 : 1 | 16 : 0 | 17 : 1 |

The model's own confidence does not separate right from wrong on scans. The lowest cited word does: 16 of 16 right at 0.90 and over, 1 of 6 right under 0.50.

## Expected score impact

- Typed PDF, Excel, email, Spanish text: no change expected. On the 8 saved typed files nothing moves.
- The quick set of 15 has four scans: SUB-038, 053, 067, 074. Only SUB-038 has a saved reply. On it: C1 loses year built and the loss-run date (both right today); C3 loses the loss-run date; C2 loses nothing. For SUB-053, 067, and 074 I have no saved reply and give no number. By the share on the five saved scans, C1 would drop about one right scan value in three, C3 about one in eight, C2 about one in thirty.
- A dropped value makes the file incomplete, so `status` can drop on the same row where gold says complete.
- Wrong values stored as confirmed on scans go down: from 9 to 2 (C1, C3) or to 7 (C2) on the five saved scans.
- Under R2 or S2, more scan files show `incomplete`, and `status` hits drop where gold says complete.
- (c) changes no score on SUB-017 through SUB-086: every file there is `.md`, `.pdf`, `.xlsx`, `.png`, or `.jpg`, and all 20 development PDFs are one typed page each. It matters on the new hold-out if @producer builds mixed PDFs.
- Hits are expected to go down on scans, not up. What goes up is how many stored scan values are true.

Every field whose hit count drops on the quick set will be reported against the T-064 baseline.

## Prompt version, cache key, and how many files are called again

- As drafted, the prompt text `SYSTEM` is not changed, so `PROMPT_VERSION` stays `82be09bd42f7`.
- The key is made from the prompt version, the model, and for each file its name, hash, OCR settings line, needs-human flag, and text. The new doc keys (`ocr_words`, the page list, `reason`) are not put in the key.
- The 13 saved replies stop being reachable when P-014 is built (T-078: host and temperature go into the key), before P-016 and whatever P-016 does. T-064 then calls the quick 15 fresh and saves them. The numbers below are counted from those T-064 results.
- The gate, (a), and (b) run after the saved reply is read. They need no new call.
- (c) changes a key only where it changes a file's text or adds a file. On SUB-017 through SUB-086 it does neither.

Your choices:

- P, the prompt.
  - P1: no prompt change. Quick 15 after P-016: 0 new calls. Full 60: 0 new calls for files already saved.
  - P2: one added line telling the model that the quote must hold the value as the file writes it. It may win back values that (a) drops. It changes `PROMPT_VERSION`, so every file is a new key: 15 calls for the quick set, 60 for the full set. It is a prompt change and is covered by this proposal only if you pick P2.
- K, the `OCR_SETTINGS` line in `sources.py`. Its comment says to change it whenever the OCR steps change. The image steps do not change; the way a PDF's pages are read does.
  - K1: leave the line. A key changes only when a file's text really changes.
  - K2: update the line. Every folder with a PDF or an image is a new key: 8 of the quick 15 (SUB-027, 038, 042, 053, 056, 067, 071, 074), and 32 of the full 60.

The new 20-file hold-out is 20 fresh calls under every option.

## Trade-off

- Fewer values are stored from scans, some of them right. A person reads more. That is the price of not storing a misread number as confirmed.
- C1 is the strictest and loses the most right values. C2 loses almost none and keeps most of the wrong ones. C3 sits between, and reads "the cited words" as the words that hold the value.
- None of C1, C2, C3 catches SUB-077's 1942. Only S2 marks it, by marking every scan number and date.
- One more list on the report (`unread`), and one more key on each row (`reason`, and `quote` under Q1).
- Per-page PDF reading is slower on a scanned PDF and still needs `pdftoppm`, which this machine does not have. Without it the pages are listed for a person, not read.
- "Mostly covered by an image" is a simple test. A page with a typed header over a small scanned table can still pass as typed.

## Risk to the loss-run no-guess rule

- The rule gets stricter, not looser. A loss-run date must now parse, must be inside its quote, and on a scan must pass the cited-word score. The "no known loss" guard on line 232 stays.
- No path is added that writes a date the file does not show.
- The cost: on the saved scans, right loss-run dates are dropped under C1 (SUB-038, 077, 084) and C3 (SUB-038, 077). The file then shows loss runs as missing and the draft request asks the producer for runs that were sent. Nothing is guessed, and nothing is sent without a person. Loss-run hits on scans can drop.
- Under G1 the `carrier_run_date` rule still stores a date from scan text at 0.95 without the cited-word score. Under G2 it does not.

## What is NOT changed

- The 0.75 line. The prompt (unless P2). The model, the host, temperature 0. The image OCR steps and the cut-offs for an unreadable page (mean 40, four words).
- P-001 (no five-digit ZIP, no premises), P-002 (address flag), P-005, the conflict rules, the document rules (unless G2).
- Every scorer and every hit, miss, not-credited, flagged, and call-failed rule. No published score is rewritten or recounted.
- The cache files and the token log. P-010, P-011, and P-014 as approved.
- `package.py`, `workbench.py`, and anything else under `underwriting_pipeline/app/`. Nothing under `src/insureflow`.
- No auto-decline and no auto-bind. No send is authorized. A failed call is still `extraction_failed`.
- The other Medium and Low findings in `deliverables/model-risk/backlog-T-027.md`.

## After approval

1. Build, with the self-checks in the table above. No model call in any self-check.
2. `python underwriting_pipeline/ai/regression_dev.py --quick`, written to a scratch path, compared with the T-064 baseline. Every field whose hit count drops is reported.
3. The code is committed before that run (D-034, D-038 item 6: the orchestrator commits).
4. @model-risk and @senior-underwriter look at T-027 again. The new hold-out (T-091 to T-093) starts only after this is frozen and committed.

## Your choices on P-016

| Letter | Point | Options |
|---|---|---|
| N | numbers written as "1.2M" | N1, N2 |
| H | a number inside a dashed phone or policy number | H1, H2 |
| D | dates in another format | D1, D2 |
| R | what needs review does to the status | R1, R2 |
| Q | the quote on the stored row | Q1, Q2 |
| C | the OCR score of the cited words | C1, C2, C3 |
| S | every scan number and date marked needs review | S1, S2 |
| G | document rules on scan text | G1, G2 |
| L | text past 120,000 characters | L1, L2 |
| E | a file that cannot be opened | E1, E2 |
| P | the prompt | P1, P2 |
| K | the `OCR_SETTINGS` line | K1, K2 |

P-016 is not implemented until the user replies "approve change P-016".
