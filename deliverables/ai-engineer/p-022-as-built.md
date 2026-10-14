# P-022 as built (ai/ part: B-205, B-206)

Approved: D-063. B-209 (area-unit TIV hold) is in app/workbench.py, done by the main session.

- B-205: `write_drafts()` in `underwriting_pipeline/ai/prepare.py` now calls `folder_manifest(folder)` before `process_submission(folder)` and saves that earlier manifest. A file added during extraction is not in it, so `manifest_problem()` refuses the send.
- B-206: `read_folder()` in `underwriting_pipeline/ai/sources.py` skips names starting with ".", the same rule as `folder_manifest`.
- Self-checks: prepare.py (stub extractor writes a late file, then fails; send refused); sources.py (a dotfile is neither read nor in the manifest).
- No other behavior change. No model calls. Scorers and published scores untouched.
- B-208 stands: older saved runs have no manifest until re-saved.
