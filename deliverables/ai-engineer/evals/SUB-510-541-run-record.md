# T-121 run record (2026-11-03), official hold-out SUB-510 to SUB-541 (D-154)

- Worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration`, branch `pilot-integration`, HEAD `b92a5b8` (clean before the run). Python: `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team/.venv/bin/python`.
- Frozen values verified just before the run (team/NEXT-SESSION.md, Freeze 2026-11-03): `git diff 8baa00a..HEAD -- underwriting_pipeline src` empty; PROMPT_VERSION `392b9ce3c1af` (3,257 bytes), scope-v5; sha256 llm_extract `90ed6772…`, scope `79f4f7f7…`, prepare `c7afd354…`, v11 `7ddcfb50…`, lint `01147a75…`, counter v2 `a57010b0…`: all match. Gold manifest `8ba4a9f3…a7f` match; `shasum -c` 33/33 OK.
- Pre-checks (HOLDOUT_IDS=510-541): v11 `--self-check` ok; `--check-gold` 32 ok (20 in, 12 out; 2/6/2/2); `--check-ops-gold` 32 ok; `smoke_readers.py` smoke ok, exit 0.
- Cache: fresh empty `underwriting_pipeline/cache/T-121-live`. Cache keys of all 32 files checked against 427 cache entries in every worktree and temp folder: 0 cached replies.
- Run: `LLM_CACHE_DIR=$PWD/underwriting_pipeline/cache/T-121-live LLM_PACE_SECONDS=55 HOLDOUT_IDS=510-541 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-510-541-holdout-v11 <python> underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v11 --write`. Run id `20261103T151602-99173`, 15:16–15:45, exit 0. Once; scored once.
- C2/C4: `count_ops_gate_v2.py --v11 SUB-510-541-holdout-v11.json --runs <reports>`; reports rebuilt from a temp copy of the run cache with the model call blocked (0 blocked attempts; 32/32 statuses as scored). Output `SUB-510-541-ops-gate-v2.txt` (exit 1: C2 FAIL, C4 FAIL).
- Nothing written to gold, `simulation/inbox/`, real logs or outboxes. `workbench.html` sha256 before/after `4fcfb1b5…f355fb` (unchanged). `underwriting_pipeline/cache/` is git-ignored.

## Console output, as printed (org id masked)

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
15:16 SUB-510 ok attempts 1 retries []
15:16 SUB-511 ok attempts 1 retries []
15:18 SUB-512 ok attempts 1 retries []
15:18 SUB-513 ok attempts 1 retries []
15:19 SUB-514 ok attempts 1 retries []
15:20 SUB-515 ok attempts 1 retries []
15:21 SUB-516 ok attempts 1 retries []
15:24 SUB-517 ok attempts 2 retries ['other']
15:24 SUB-518 ok attempts 1 retries ['rate_limit_429']
15:24 SUB-519 ok attempts 1 retries []
15:25 SUB-520 ok attempts 1 retries []
15:26 SUB-521 ok attempts 1 retries []
15:27 SUB-522 ok attempts 1 retries []
15:28 SUB-523 ok attempts 1 retries []
15:29 SUB-524 ok attempts 1 retries []
15:30 SUB-525 ok attempts 1 retries []
15:31 SUB-526 ok attempts 1 retries []
15:32 SUB-527 ok attempts 1 retries []
15:33 SUB-528 ok attempts 1 retries []
15:34 SUB-529 ok attempts 1 retries []
15:35 SUB-530 ok attempts 1 retries []
15:35 SUB-531 ok attempts 1 retries []
15:36 SUB-532 ok attempts 1 retries []
15:37 SUB-533 ok attempts 1 retries []
15:38 SUB-534 ok attempts 1 retries []
15:39 SUB-535 ok attempts 1 retries []
15:40 SUB-536 ok attempts 1 retries []
15:41 SUB-537 ok attempts 1 retries []
15:42 SUB-538 ok attempts 1 retries []
15:43 SUB-539 ok attempts 1 retries []
15:44 SUB-540 ok attempts 1 retries []
15:45 SUB-541 ok attempts 1 retries []
/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration/deliverables/ai-engineer/evals/SUB-510-541-holdout-v11.md
named_insured {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 14, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 2}
tiv {'hit': 15, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 1}
construction {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 16, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 4, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 8, 'hit (needs review)': 0, 'miss': 2, 'not_credited': 4, 'call_failed': 0, 'flagged': 6}
status {'hit': 9, 'hit (needs review)': 0, 'miss': 11, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
route {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 0, "automated": 124, "silent_error_rate": 0.0, "automation_rate": 0.689}
failed attempts {'rate_limit_429': 1, 'timeout': 0, 'other': 1, 'reply_not_usable': 0} {'other': 'HTTP 503 {"error":{"message":"qwen/qwen3.8-27b is currently over capacity. Please try again and back off exponentially. Visit https://groqstatus.com to see if there is an active incident.","type":"internal_server_error"}}\n', 'rate_limit_429': 'per minute: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_<masked>` service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Used 859, Requested 835. Please try again in 41.64s. Need more tokens? Upgrade to Dev Tier today at https://c'}
tokens {"run": "20261103T151602-99173", "skipped_lines": 0, "this_run": {"model_calls": 21, "from_cache": 0, "tokens": 40132, "tokens_per_call": 1911}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 21, "tokens": 40132}}}
exit 0
```
