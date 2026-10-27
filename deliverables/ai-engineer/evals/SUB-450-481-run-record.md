# T-120 run record (2026-10-27), official hold-out SUB-450 to SUB-481 (D-137)

- Worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration`, branch `pilot-integration`, HEAD `8c157e9` (clean before the run). Python: `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team/.venv/bin/python` (this worktree has no `.venv`; the main folder's `.venv` is gone).
- Frozen values verified just before the run (team/NEXT-SESSION.md, Freeze 2026-10-27):
  - `git diff fa604b9..HEAD -- underwriting_pipeline src` empty. Score file: last pipeline commit `c9c8e17` (= the P-076 code merged in `fa604b9`).
  - `PROMPT_VERSION` `759b3e6bc9b2`.
  - v11 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`; lint `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653`; counter `count_ops_gate.py` `f942010dffab720b4c60942614973a7d9c5404d28f4cb53a10bc8709b62a9aa1`: all match.
  - Gold manifest `534e65a55456f2a173e5ef3f85ecfa700c5693afa82e1007eac58e41bbcb3a73` (match); `shasum -c`: 33/33 OK.
- Pre-checks (HOLDOUT_IDS=450-481): v11 `--self-check` ok; `--check-gold` 32 ok, 0 fail (20 in, 12 out; 3/3/3/3 per criterion); `--check-ops-gold` 32 ok. `smoke_readers.py`: `smoke ok`, exit 0.
- Cache: fresh empty `underwriting_pipeline/cache/T-120-live`. Cache keys of all 32 files checked against every cache folder in the five worktrees (312 entries): **0 cached replies**. Run `from_cache` 0.
- Run: `LLM_CACHE_DIR=$PWD/underwriting_pipeline/cache/T-120-live LLM_PACE_SECONDS=55 HOLDOUT_IDS=450-481 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-450-481-holdout-v11 <python> underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v11 --write`. Run id `20261027T124020-83695`, 12:40:20–13:08:47, exit 0. `qwen/qwen3.8-27b` on Groq (D-011). Once; scored once.
- C2/C4: `count_ops_gate.py` on the score JSON and the run's saved reports. The scoring driver writes reports to a temp folder (D-069), so they were rebuilt from a temp copy of the run cache with the model call disabled (32/32 statuses identical to the scored run). Output `SUB-450-481-ops-gate.txt`: C2 PASS, C4 PASS.
- Nothing written to gold, `simulation/inbox/`, real logs or outboxes. `workbench.html` sha256 before/after `4fcfb1b553bc1ca79bb2ee16ef7e48c11e9b322589eef7a44ab490d867f355fb` (unchanged). `underwriting_pipeline/cache/` is git-ignored.
- Retries (RUN-RULES): 2 × 429 on SUB-450 (logged), 0 timeouts, 0 failed calls.

## Console output, as printed (org id masked)

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
12:40 SUB-450 ok attempts 1 retries ['rate_limit_429', 'rate_limit_429']
12:41 SUB-451 ok attempts 1 retries []
12:42 SUB-452 ok attempts 1 retries []
12:43 SUB-453 ok attempts 1 retries []
12:44 SUB-454 ok attempts 1 retries []
12:44 SUB-455 ok attempts 1 retries []
12:45 SUB-456 ok attempts 1 retries []
12:46 SUB-457 ok attempts 1 retries []
12:47 SUB-458 ok attempts 1 retries []
12:48 SUB-459 ok attempts 1 retries []
12:49 SUB-460 ok attempts 1 retries []
12:50 SUB-461 ok attempts 1 retries []
12:51 SUB-462 ok attempts 1 retries []
12:52 SUB-463 ok attempts 1 retries []
12:53 SUB-464 ok attempts 1 retries []
12:54 SUB-465 ok attempts 1 retries []
12:55 SUB-466 ok attempts 1 retries []
12:55 SUB-467 ok attempts 1 retries []
12:56 SUB-468 ok attempts 1 retries []
12:57 SUB-469 ok attempts 1 retries []
12:58 SUB-470 ok attempts 1 retries []
12:59 SUB-471 ok attempts 1 retries []
13:00 SUB-472 ok attempts 1 retries []
13:01 SUB-473 ok attempts 1 retries []
13:02 SUB-474 ok attempts 1 retries []
13:03 SUB-475 ok attempts 1 retries []
13:04 SUB-476 ok attempts 1 retries []
13:05 SUB-477 ok attempts 1 retries []
13:06 SUB-478 ok attempts 1 retries []
13:06 SUB-479 ok attempts 1 retries []
13:07 SUB-480 ok attempts 1 retries []
13:08 SUB-481 ok attempts 1 retries []
/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration/deliverables/ai-engineer/evals/SUB-450-481-holdout-v11.md
named_insured {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 18, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 2}
tiv {'hit': 19, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 1}
construction {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 11, 'hit (needs review)': 0, 'miss': 2, 'not_credited': 0, 'call_failed': 0, 'flagged': 7}
status {'hit': 11, 'hit (needs review)': 0, 'miss': 9, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
route {'hit': 18, 'hit (needs review)': 0, 'miss': 2, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 0, "automated": 155, "silent_error_rate": 0.0, "automation_rate": 0.861}
failed attempts {'rate_limit_429': 2, 'timeout': 0, 'other': 0, 'reply_not_usable': 0} {'rate_limit_429': 'per minute: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_<masked>` service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Used 416, Requested 588. Please try again in 240ms. Need more tokens? Upgrade to Dev Tier today at https://co'}
tokens {"run": "20261027T124020-83695", "skipped_lines": 0, "this_run": {"model_calls": 21, "from_cache": 0, "tokens": 37085, "tokens_per_call": 1766}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 21, "tokens": 37085}}}
exit 0
```
