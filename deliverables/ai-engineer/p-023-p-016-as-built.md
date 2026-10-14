# P-023 and P-016 (`ai/` part) as built

Date 2026-10-14. Author @ai-engineer-assistant. Approval: D-064 (P-023, P-016 build) and D-039 (P-016 options N2 H2 D2 R1 Q1 C3 S2 G2 L1 E1 P1 K1). No commit. No model call. No scorer run, no score file written. `app/` untouched.

## P-023 (B-214), `llm_extract.py`
- `DEFAULT_BASE` and `DEFAULT_MODEL` are gone. `provider_guard` (both modes) raises SystemExit with `UNSET` if `LLM_BASE_URL` or `LLM_MODEL` is unset: before any cache read or write, before any HTTP attempt. SystemExit, so `prepare.py` does not turn it into `extraction_failed` or "no data"; the run stops. `endpoint_settings` raises RuntimeError for the same case (prepare's metadata call catches it).
- Ollama runs only when `LLM_BASE_URL` names localhost (host name check, not a substring). The P-008 host guard is unchanged.
- Callers: grep of `underwriting_pipeline/` found `DEFAULT_*` only in `llm_extract.py` (self-check). Self-check now sets localhost explicitly. `sources`, `prepare`, `package`, `workbench`, `intake`, `quotes` self-checks pass with LLM_* unset.
- Self-check: five unset combinations x `provider_guard`, `provider_guard(calling=False)`, `llm_extract` -> refused with the message; zero HTTP attempts, empty cache folder, no USAGE, no failure counts.

## P-016
- (a) N2 H2 D2: `accept_field` has no value fallback (`reason: "quote not found in <file>"`); new `value_in_span`. Numbers: whole numbers in the quote, `amount_value` reads $1.2M/220k (moved to `llm_extract`, `prepare.amount_value` is the same function); a number joined by `-` or `/` to digits is not whole unless inside a date. Dates: must parse; ISO or named-month or numeric formats; day/month ambiguous = not stored. Names, addresses: value inside quote, case and spaces ignored. Operations, construction not in the quote: kept, `needs_review True`, `reason "value is not in the cited text (translated or reworded)"`.
- R1: flag only. Status logic unchanged.
- Q1: row key `quote` (exact text from `start` to `end`); `_saved_payload` saves `quote`, `reason` per field and top-level `unread`.
- (b) C3 S2 G2: `sources._ocr_score` returns every word with its score; `read_folder` doc gets `ocr_words` (not in the cache key). On a scan, `confidence = min(model, lowest cited word that holds the value)`; a cited word not in the list is 0; row keeps `model_confidence` and `ocr_cited_confidence`. A scan without a word list takes the page score as before. S2: number and date from a scan that passes stay `needs_review True`, `reason "number or date read from a scan"`. G2: `prepare._set_cited` applies the cited-word score to document rules on a scan (and flags the loss-run date); below 0.75 the rule stores nothing.
- (c) L1 E1: `read_folder` lists unsupported types (`file type .x is not read`) and unopenable files (`could not be opened`) with `unread`, no raise; those docs never reach the model or the key. `_pdf_text` is per page (typed = 40+ chars and not >50% image; else OCR; else listed with page number and reason; "OCR for PDF pages is not available" here, no `pdftoppm`). `llm_extract` packs whole files in order under 120,000 characters; a file that does not fit is not sent, listed in the result key `not_sent`. `prepare` report gets `unread` = rows `{file, page (None = whole file), reason}`; `needs_human` stays a list of names and also includes every unread file.
- P1: SYSTEM untouched; `PROMPT_VERSION` = `82be09bd42f7`. K1: `OCR_SETTINGS` untouched.

## Cache coverage (no model call)
LLM_BASE_URL=https://api.groq.com/openai/v1, LLM_MODEL=openai/gpt-oss-120b, LLM_API_KEY unset, copy of `underwriting_pipeline/cache` in the scratchpad. Keys of the 15 QUICK submissions, computed from `read_folder` and `cache_key`: 15 of 15 exist in the copy, and all 15 keys are identical to the keys computed with HEAD `sources.py` and `llm_extract.py`. The real cache was not written.

## What `app/` must read (@software-engineer)
Per field row in the report and in the saved file: `needs_review` (flag), `reason` (why flagged, or why there is no value), `quote` (exact cited text). Needs-review acknowledgment at approve: list every row with `needs_review == True` and a non-empty `value`, with its `reason` and `quote`. Rows with no value show `reason` as the missing cause. Also `unread` (rows `file`, `page`, `reason`) on the report and the saved file.

## Not built
- `regression_dev.py` confidence-versus-hit table (spec's step-2 reporting, not in the build scope given).
- Quick-15 rerun and the field-by-field comparison with SUB-074 and SUB-067: not run in this turn (needs the Groq host; cached results would now also re-pass the new gates). Expect fewer scan values and more flagged rows.
- Per-page PDF OCR and image-coverage test are untested end to end here (no `pdftoppm`); typed and blank-page cases are self-checked.
- Repeated words on a scan take the lowest score (no word positions).
