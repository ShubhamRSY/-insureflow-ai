# Backlog — T-026 review (@model-risk, 2026-10-11)

Medium and Low findings only (D-030). The High finding is in the OBJECTION message in team/DISCUSSION.md. Recomputed in memory from the published JSON and the gold files; no model call, no scorer run, nothing written to a score file.

- Medium: "prepare.py unchanged for the run" cannot be checked from the repo. No commit holds the scored file (sha256 5d51f7c0…, recorded in deliverables/model-risk/holdout-SUB-017-026.md on 2026-10-09). The earliest commit, 2b5d084 (2026-10-10 18:20), already holds a different prepare.py (7ea410e6…). The deliverable itself gives no hash. D-034 covers this from now on.
- Medium: the scorer on disk is not the scorer that wrote the published file. `eval_holdout.py` now writes "Call failed: yes/no" on every row and a `call_failed` mark; the published file has neither. The memo's command no longer reproduces the file, and it still writes to the published path, now with the LLM extractor behind `prepare` (D-025).
- Medium: the stated cause covers only PDF and Excel. SUB-020, SUB-021, and SUB-025 had no ignored file and still scored 0 on all seven value fields (unlabeled prose, Spanish labels). SUB-019's email.md names the insured in prose and it was missed. The deliverable does not say why.
- Medium: status and conflict are reported as one number with no breakdown. Recomputed: gold complete 0/5, gold incomplete 5/5; real conflicts found 0/2 (SUB-022, SUB-024); "no conflict" 8/8.
- Low: gold files SUB-017 to SUB-026 all carry the same mtime, 23:04:15, about one minute after the inbox files and 45 seconds before the score. "Gold first" rests on timestamps only.
- Low: the deliverable does not say which gold lines are scored. Effective date is in the extractor's missing list and is not scored. Cooking, hood, sprinklers, liquor, hours, square feet, and the expected recommendation are in gold and are not scored.
- Low: no date, no total (17 of 100), no code hash in the deliverable. The author line is the retired handle @ai-engineer. The file is a published score and stays as it is (D-025).
- Low: n = 10 with two files per format. No per-format rate is supportable.
- Low: `hit_conflict` hard-codes "15 perez", "51 perez", "3000", and "4500". The scorer was written knowing the two gold conflicts and cannot be reused on another set.
- Low: `hit_number` with gold 0 accepts any non-null value that has no digits, so any text would score as TIV 0 on SUB-026. Not triggered in this run.
