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

## Live runs and re-scores are kept apart (B-363, D-095)

- A re-score from saved replies runs with `HOLDOUT_RESCORE=1` (and a temp copy of the cache in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`). It makes no model call: a file with no saved reply stops the run and nothing is written. It writes `<name>-cache-rescore.json/.md`.
- A live run refuses to start when its score file exists, so it never overwrites a live score or its retry rows. Use a new `HOLDOUT_OUT`.
- D-096 item 4: `regression_dev.py` (every hold-out, quick and full run) and the dev scripts write score files only with `--write`. Without it the run is read-only: the files go to a temp folder and nothing in the repo changes. Frozen scorers are not edited; the driver redirects their output. A frozen scorer must not be run directly (D-025).
- D-096 item 2: hold-outs from T-103 on are scored with `eval_holdout_v3` (route gate: 0 unsafe routes, route accuracy at least 18/20). v2 stays frozen.
- D-097: hold-outs are scored with `eval_holdout_v4` (unsafe = a carrier route, held or not, where gold says senior_referral or no_match; "hold" is a status, not a gold route). v2 and v3 stay frozen. Their route column calls the live `workbench.match`, so their route marks follow the routing code of the commit being scored. Since P-049, their `--self-check` fails on its sprinklered → carrier_c route assert. This is expected, and the frozen files are not edited.

## Test-file lint before a gold freeze (T-106d, D-111)

Before any hold-out gold is frozen, run `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py <plan.json> [--run-date YYYY-MM-DD]` (read-only, no model call). It must exit 0: every loss-run date is before the run date, every gold Scope line parses with the scorer v6 parser, and the in/out, per-criterion and route counts match the written plan. Any FAIL line means fix the files (or the plan) first; do not freeze. Plan format and details: `deliverables/senior-test-engineer/T-106d-lint.md`.

## Scorer v8 and the loss-run gold line (P-064, D-116)

- New hold-outs are scored with `eval_holdout_v8`. v7 stays frozen; published v7 scores stay as published.
- Every in-scope gold card whose loss run has a date carries its own line: `- Loss runs valued as of: <YYYY-MM-DD>`. v8 compares the pipeline's date to that date only, never to the policy-period start or any other date in the `- Loss runs:` line. When gold expects no date (loss runs missing / not in documents, or `Expected loss run` starting "needs review" or "loss run found but no valued-as-of date") the line is left out or written `none`.
- A card that breaks this stops v8 before any call (`--check-gold` shows it), as the Scope line does.

## Test the test before a gold freeze (D-116 item 5)

`lint_holdout.py` also runs the scorer test (`--scorer eval_holdout_v8` is the default): a perfect answer built from each gold card must get no "miss" from the scorer and pass the route and P-055 gates with 0 false completes; deliberately wrong answers (one per field on every in-scope file, a leak on every out-of-scope file, and an unsafe route) must each be caught. Any FAIL blocks the freeze. Gold conventions this enforces (found on T-108 gold, see `deliverables/senior-test-engineer/T-109c-lint-check.md`): write `Conflict: none` with no note after it; start `Expected loss run` with "needs review" when review is expected; no "a.m."/"p.m." or other full stops inside an `Operations items` item ("open until 2 am").
