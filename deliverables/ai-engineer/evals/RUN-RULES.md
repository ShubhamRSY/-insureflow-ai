# Eval run rules — retries (D-094 item 5)

Replaces the T-027 rule "a 429 or network error once; anything else call failed" (that rule was stricter than the code, so the T-027 run needed an outside driver, `T-027/t027_run.py`). From D-094 on, the rule is what the code does, and no driver caps it.

## Retries the pipeline makes (as in the code)

| Where | When | How many | Wait |
|---|---|---|---|
| `llm_extract._post` | HTTP 429 | up to 6 posts in all | the host's Retry-After + 1 s, at most `LLM_MAX_WAIT` (60 s default); 1, 2, 4, 8, 16 s if no Retry-After |
| `llm_extract._post` | timeout or network error | up to 6 posts in all | 1, 2, 4, 8, 16 s |
| `llm_extract.llm_extract` | HTTP 400 | one resend without `response_format` (which can itself retry as above) | none |
| `regression_dev.score_retry` | the file's scoring raised or returned an error | up to 3 attempts of the whole file | 60 s |

Any other HTTP error (401, 500, …) or an unusable reply fails at once. A file that never succeeds is `call_failed`: counted apart, never a miss, never cached (D-021, D-022).

## How each retry is logged

- Token log: one row per failed attempt or retry, with the files, the cache key, the attempt number and the wait (P-012).
- The file's report: `report["retries"]`, one entry per failed attempt or resend of that file's call (kind, attempt, wait, detail, files).
- The score file: each submission row has `retries` (every failed attempt across all `score_retry` attempts) and `attempts`; the Markdown lists "Retries: n (kinds)" per submission.

## What a run must report

The retry count per file and in total, and every `call_failed` file. A retry is not a rule breach; an unlogged retry is.
