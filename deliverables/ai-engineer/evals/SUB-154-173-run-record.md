# T-103 run record (2026-10-16)

- Worktree insureflow-ai-team, commit 2c6b2d9 (pipeline 3557e4a, gold 33e399a), .venv/bin/python (3.14.6), LLM_CACHE_DIR unset, no cache folder before the run.
- Smoke first: `.venv/bin/python underwriting_pipeline/ai/smoke_readers.py` → 8 of 8 types read, "smoke ok", exit 0, before the run.
- Run: `LLM_PACE_SECONDS=55 HOLDOUT_IDS=154-173 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-154-173-holdout-v4 .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v4 --write`, run id 20261016T151351-65695, exit 0, 15:13–15:31.

## Console output, as printed

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
15:14 SUB-154 ok attempts 1 retries ['rate_limit_429']
15:14 SUB-155 ok attempts 1 retries ['rate_limit_429']
15:15 SUB-156 ok attempts 1 retries []
15:16 SUB-157 ok attempts 1 retries []
15:17 SUB-158 ok attempts 1 retries []
15:18 SUB-159 ok attempts 1 retries []
15:19 SUB-160 ok attempts 1 retries []
15:20 SUB-161 ok attempts 1 retries []
15:21 SUB-162 ok attempts 1 retries []
15:22 SUB-163 ok attempts 1 retries []
15:23 SUB-164 ok attempts 1 retries []
15:24 SUB-165 ok attempts 1 retries []
15:25 SUB-166 ok attempts 1 retries ['rate_limit_429']
15:25 SUB-167 ok attempts 1 retries []
15:26 SUB-168 ok attempts 1 retries []
15:27 SUB-169 ok attempts 1 retries []
15:28 SUB-170 ok attempts 1 retries []
15:29 SUB-171 ok attempts 1 retries []
15:30 SUB-172 ok attempts 1 retries ['rate_limit_429']
15:31 SUB-173 ok attempts 1 retries []
/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team/deliverables/ai-engineer/evals/SUB-154-173-holdout-v4.md
named_insured {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 17, 'hit (needs review)': 0, 'miss': 3, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 7, 'hit (needs review)': 0, 'miss': 13, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 17, 'hit (needs review)': 0, 'miss': 3, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
tiv {'hit': 17, 'hit (needs review)': 0, 'miss': 3, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
construction {'hit': 17, 'hit (needs review)': 0, 'miss': 3, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 5, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 11, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 17, 'hit (needs review)': 0, 'miss': 3, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
status {'hit': 15, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 1, 'call_failed': 0, 'flagged': 0}
route {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 6, "automated": 129, "silent_error_rate": 0.033, "automation_rate": 0.717}
failed attempts {'rate_limit_429': 4, 'timeout': 0, 'other': 0, 'reply_not_usable': 0} {'rate_limit_429': 'per minute: {"error":{"message":"Request too large for model `qwen/qwen3.8-27b` in organization `org_01kcpawq5vecv8na8y22z8xpx0` service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Requested 1093. The request\'s expected output tokens exceed the enforced limit; reduce max_tokens (or the requ'}
tokens {"run": "20261016T151351-65695", "skipped_lines": 0, "this_run": {"model_calls": 20, "from_cache": 0, "tokens": 38396, "tokens_per_call": 1920}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 20, "tokens": 38396}}}
```
