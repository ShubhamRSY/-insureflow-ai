# SUB-077 through SUB-086 — original score against the rerun

- Author: @ai-engineer-assistant
- Date: 2026-10-11. Corrected 2026-10-11 after @model-risk's review of T-060 and the user's ruling, D-026.
- Task: T-060 (D-021, D-026)
- Reads the two score files and the token log only. No model call. No published score file was rewritten.
- Synthetic. Not a production approval.

## Result

1. The original score is the official baseline. It stays the published score. No row in the original file has an error, so D-021 does not replace it.
2. The rerun is labeled: **with P-002 and P-003b, not a same-code comparison.** P-002 (address flag) and P-003b (Tesseract score on scans) went into the code after the original run and before the rerun. D-021 item 2 asked for "no extraction change". That was not met. The user accepted the rerun as-is in D-026, for this rerun only.
3. The rerun is not an improved score and must not be quoted as one. The two runs differ in code as well as in the model's answers, so the difference between them measures neither.
4. Ten marks changed: 9 up and 1 down, net +8 hits (71 to 79 of 100). An earlier version of this memo said nine. That was wrong.

## What the saved files back, and what they do not

Backed by `SUB-077-086-holdout-rerun.json`: 10 files, every row has `error: null`, the call-failed count is 0 for every field, and every row has `attempts: 1`. `attempts` is the scorer-level count in `regression_dev.py`: the file was scored once and was not sent back for another try.

Not recorded: how many HTTP attempts each call took, and the count of 429s, timeouts, and other failed attempts inside a call. An earlier version of this memo said "10 on the first attempt. Rate limit 429: 0. Timeout: 0. Other: 0." No saved file holds those numbers, and I withdraw them. At the time of the rerun the code kept failed attempts in memory and printed them; it did not save them, and that printed output was not kept.

What the token log does show (`underwriting_pipeline/cache/token_log.jsonl`, rows 1 to 10): the calls for files 2 to 7 came 2 to 19 seconds after the one before. The calls for files 8, 9, and 10 came 152, 420, and 474 seconds after the one before. The pacing code waits at most about one minute, so pacing alone does not explain those three gaps. A wait on a 429 would. The log cannot say which, so the honest answer for the rerun is "not recorded", not "0".

From now on this is saved. D-026 item 4 (P-012) writes every 429, every other failed attempt, and every retry to the token log.

## Counts per field

Original: hit / miss / not credited / flagged. Rerun: hit / miss / not credited / flagged / call failed. The original file was written before the call-failed column existed; none of its rows has an error.

| Field | Original | Rerun (with P-002 and P-003b) | Hits |
|---|---|---|---|
| named_insured | 9 / 1 / 0 / 0 | 9 / 1 / 0 / 0 / 0 | 0 |
| premises | 5 / 4 / 0 / 1 | 5 / 4 / 0 / 1 / 0 | 0 |
| operations | 8 / 2 / 0 / 0 | 8 / 2 / 0 / 0 / 0 | 0 |
| sales | 8 / 1 / 0 / 1 | 9 / 0 / 0 / 1 / 0 | +1 |
| tiv | 8 / 2 / 0 / 0 | 10 / 0 / 0 / 0 / 0 | +2 |
| construction | 9 / 1 / 0 / 0 | 10 / 0 / 0 / 0 / 0 | +1 |
| year_built | 7 / 3 / 0 / 0 | 8 / 2 / 0 / 0 / 0 | +1 |
| loss_runs | 6 / 1 / 2 / 1 | 7 / 0 / 2 / 1 / 0 | +1 |
| conflict | 6 / 1 / 0 / 3 | 7 / 0 / 0 / 3 / 0 | +1 |
| status | 5 / 5 / 0 / 0 | 6 / 4 / 0 / 0 / 0 | +1 |

operations is 8 and 8, with one mark up (SUB-081) and one down (SUB-084).

## What changed, by file

Seven files have the same marks on every field: SUB-077, 078, 079, 082, 083, 085, 086.

- SUB-081 (blank ACORD plus attachment), 7 up: operations, sales, construction, year built, TIV, loss runs, and status went from miss to hit.
- SUB-080 (multiple locations), 2 up: TIV and conflict went from miss to hit. Named insured and operations are still misses.
- SUB-084 (handwritten Spanish scan), 1 down: operations went from hit to miss.

## What this does and does not show

1. No file has a failed call in either score file, and ten marks still differ. Because the code also changed between the runs, this is not a measure of how much the same code varies from run to run. T-066 (three runs of the quick set at temperature 0) measures that.
2. Why the three files changed is not known. SUB-080 and SUB-081 are not scans, so P-003b does not act on them. SUB-084 is a scan, so its drop could be P-003b or the model. An earlier version said the SUB-081 rerun call "copied the attachment" and the original did not. The original model reply was not saved, so that is a guess and I withdraw it.
3. The four premises misses and four of the status misses are the same four scans in both files (SUB-077, 078, 084, 085).

## Open

- Whether the SUB-084 operations drop is a P-003b effect. It needs the saved result scored with the scan gate off. The code has no such switch. Under D-026 the user did not ask for it.
- The quick set of 15 (T-064, T-066) has not run. The token log holds 13 calls: these 10 and SUB-027, 029, 038.
