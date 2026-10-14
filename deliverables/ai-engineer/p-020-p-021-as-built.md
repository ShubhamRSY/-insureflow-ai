# P-020 and P-021 as built (2026-10-14, D-060, D-061, D-062)

File changed: `underwriting_pipeline/ai/prepare.py` only. Not committed. No model call. No scorer edit, no published score rewritten.

## P-020 input manifest
- `write_drafts()` now saves `input_manifest`: a list of `{name, sha256}` for every file in the submission folder (dotfiles skipped), sorted by name. It is inside the hashed payload, so `saved_hash` covers it.
- Reader for the send gate: `manifest_problem(submission: str, extract_dir: Path | None = None, inbox: Path | None = None) -> str`. Empty string = ok. Otherwise it returns the refusal reason. Defaults: `EXTRACT_DIR` and the new `INBOX_DIR` (`simulation/inbox`).
- Fails closed: no saved run or bad hash (it calls `read_saved_run`), no manifest, unreadable folder, any difference (new file, removed file, changed bytes).
- Self-check (temp folder, real `write_drafts`): unchanged ok; new document refused; removed again ok; changed bytes refused; run without manifest refused; unknown submission refused. `prepare ok`.
- Not done here: `package.py` must call `manifest_problem` (main session).

## P-021 "MM"
- `amount_value()` reads `MM` as million. "$1.2MM" = 1,200,000. Self-checks: "$1.2MM", "$1.2M", "750K", plus the old 220k and $1.2M cases.

## Saved runs without a manifest
All 16 files in `deliverables/data-engineer/extractions/` (SUB-001 to SUB-016). They are old-format files (keys: submission, fields, conflicts only: no hash, no status), so `read_saved_run` already refused them before this change. Re-saving needs `write_drafts()`, which also rewrites drafts and conflict files. It makes no model call only if every submission hits the extraction cache (`underwriting_pipeline/cache/extractions`, 28 entries, keyed on files, prompt, OCR settings and model). I did not check or re-save. A cache miss would need a model host.

## Effect on gates and the quick set
- P-021 only changes a value that used to read as None (unreadable) into a number. In the validation gate this applies to the amount-shaped fields (square feet, TIV, sales) where `amount_value` is called. A "MM" value that was dropped before can now be kept. So it can change outcomes for any file whose text has "MM" amounts.
- In workbench, "$1.2MM" TIV changes from hold ("TIV missing or unreadable") to a number, so it is routed by the caps.
- The quick set of 15 (D-022) should be re-run, because extraction output can change if any dev file has "MM". It needs a model host (cache only if every key is unchanged, which a P-021 code change does not alter, since the cache key does not include prepare.py). Not run here: LLM_* is unset. Pre-check: grep the 15 files for "MM" amounts.

Pre-check result: a grep for digit + "MM" finds no match in any file of SUB-017 to SUB-076, so P-021 cannot change a dev-set result by text. A re-run of the quick set is still owed under D-022 and needs a model host (or a full cache); not run.
