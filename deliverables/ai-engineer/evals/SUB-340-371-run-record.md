# T-119 run record (2026-10-24), official hold-out SUB-340 to SUB-371 (D-130)

- Worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration`, branch `pilot-integration`, HEAD `58cc170` (working tree clean before the run). Python: `/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1/.venv/bin/python` (this worktree has no `.venv`).
- Frozen values, verified just before the run:
  - `git diff b6a35b7..HEAD -- underwriting_pipeline/` empty (0 lines). The score file records "last pipeline commit d7949d268f59ceb60593e840a5eef181c6d226c5".
  - `PROMPT_VERSION` `759b3e6bc9b2`.
  - scorer `underwriting_pipeline/ai/eval_holdout_v11.py` sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` (match).
  - lint `deliverables/senior-test-engineer/lint_holdout.py` sha256 `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` (match). The lint was not run (not part of this task).
  - T-119 gold manifest sha256 `2feba3b2b007ab197c22a40427b105242585ee0783bed7c5e5a575408fd55fcc` (match); `shasum -c` on all 33 lines: OK.
- Scorer pre-checks (HOLDOUT_IDS=340-371): `eval_holdout_v11 --self-check` ok; `--check-gold` 32 ok, 0 fail (20 in scope, 12 out; per criterion 4/5/4/3; 4 two-criteria files SUB-368 to 371; 3 criterion-4 files); `--check-ops-gold` 32 ok, 0 fail.
- `smoke_readers.py` printed `smoke ok`, exit 0. No reader failed.
- Cache: fresh empty folder `underwriting_pipeline/cache/T-119-live` made just before the run. Before any call, the cache key of all 32 submissions (`llm_extract.key_for(sources.read_folder(...))`) was computed without a model call and checked against `insureflow-ai-team/underwriting_pipeline/cache/extractions` (67), `.../T-104-live/extractions` (20), `.../T-108-live/extractions` (21), `.../T-117-live/extractions` (20), `-insureflow-ai-1/underwriting_pipeline/cache/extractions` (164) and the fresh folder (0): **0 cached replies** for SUB-340-371. The run's `from_cache` is 0.
- Run: `LLM_CACHE_DIR=$PWD/underwriting_pipeline/cache/T-119-live LLM_PACE_SECONDS=55 HOLDOUT_IDS=340-371 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-340-371-holdout-v11 <python> underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v11 --write`. Run id `20261024T000318-70195`, start 00:03:18, end 00:31:44, exit 0. Model `qwen/qwen3.8-27b` on Groq (D-011). Scored once with `--write`; no re-score, no second run.
- Files: 32 (20 in scope, 12 out of scope by gold Scope line). Score files `SUB-340-371-holdout-v11.md/.json` are as the scorer wrote them. Mismatches: `SUB-340-371-holdout-v11-mismatches.md`. Results: `SUB-340-371-results.md`.
- After the run, stored answers were read back through the scorer's own functions from a temp copy of the cache (`HOLDOUT_RESCORE`-style, no model call, nothing written in the repo) to fill the mismatch table. Not a re-score; the score files were not touched.
- Nothing was written to `gold-set/`, `simulation/inbox/`, the default token log or the outboxes. `git status`: only the two score files (and later the three write-ups) are new; `underwriting_pipeline/cache/` is git-ignored.
- `underwriting_pipeline/app/workbench.html` sha256 before `4fcfb1b553bc1ca79bb2ee16ef7e48c11e9b322589eef7a44ab490d867f355fb`, after `4fcfb1b553bc1ca79bb2ee16ef7e48c11e9b322589eef7a44ab490d867f355fb`: unchanged.

## Console output, as printed

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
00:03 SUB-340 ok attempts 1 retries ['rate_limit_429']
00:04 SUB-341 ok attempts 1 retries []
00:05 SUB-342 ok attempts 1 retries []
00:06 SUB-343 ok attempts 1 retries []
00:07 SUB-344 ok attempts 1 retries []
00:07 SUB-345 ok attempts 1 retries []
00:08 SUB-346 ok attempts 1 retries []
00:09 SUB-347 ok attempts 1 retries []
00:10 SUB-348 ok attempts 1 retries []
00:11 SUB-349 ok attempts 1 retries []
00:12 SUB-350 ok attempts 1 retries []
00:13 SUB-351 ok attempts 1 retries []
00:14 SUB-352 ok attempts 1 retries []
00:15 SUB-353 ok attempts 1 retries []
00:16 SUB-354 ok attempts 1 retries []
00:17 SUB-355 ok attempts 1 retries []
00:18 SUB-356 ok attempts 1 retries []
00:18 SUB-357 ok attempts 1 retries []
00:19 SUB-358 ok attempts 1 retries []
00:20 SUB-359 ok attempts 1 retries []
00:21 SUB-360 ok attempts 1 retries []
00:22 SUB-361 ok attempts 1 retries []
00:23 SUB-362 ok attempts 1 retries []
00:24 SUB-363 ok attempts 1 retries []
00:25 SUB-364 ok attempts 1 retries []
00:26 SUB-365 ok attempts 1 retries []
00:27 SUB-366 ok attempts 1 retries []
00:28 SUB-367 ok attempts 1 retries []
00:29 SUB-368 ok attempts 1 retries []
00:29 SUB-369 ok attempts 1 retries []
00:30 SUB-370 ok attempts 1 retries []
00:31 SUB-371 ok attempts 1 retries []
/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration/deliverables/ai-engineer/evals/SUB-340-371-holdout-v11.md
named_insured {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 9, 'hit (needs review)': 0, 'miss': 11, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
tiv {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
construction {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 15, 'hit (needs review)': 0, 'miss': 3, 'not_credited': 0, 'call_failed': 0, 'flagged': 2}
status {'hit': 9, 'hit (needs review)': 0, 'miss': 11, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
route {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 1, "automated": 162, "silent_error_rate": 0.006, "automation_rate": 0.9}
failed attempts {'rate_limit_429': 1, 'timeout': 0, 'other': 0, 'reply_not_usable': 0} {'rate_limit_429': 'per minute: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_01kcpawq5vecv8na8y22z8xpx0` service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Used 434, Requested 588. Please try again in 1.319999999s. Need more tokens? Upgrade to Dev Tier today at htt'}
tokens {"run": "20261024T000318-70195", "skipped_lines": 0, "this_run": {"model_calls": 20, "from_cache": 0, "tokens": 35315, "tokens_per_call": 1766}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 20, "tokens": 35315}}}
exit 0
```
