# T-128 run record (2026-11-05), official hold-out SUB-550 to SUB-581 (D-163, D-166)

- Worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration`, branch `pilot-integration`, HEAD `fffdcca5` (clean before the run). Python: `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team/.venv/bin/python`.
- Frozen values verified just before the run (team/NEXT-SESSION.md, freeze re-recorded 2026-11-05): `git diff 1ddae83c..HEAD -- underwriting_pipeline src` empty; PROMPT_VERSION `392b9ce3c1af`, scope-v8; sha256 of llm_extract, scope, prepare, package, sources, workbench.py, smoke_readers, v11, lint, counter v2, counter notes and the T-128 gold manifest: 12/12 match. `shasum -c` of the manifest 33/33 OK.
- Pre-checks (HOLDOUT_IDS=550-581): v11 `--self-check` ok; `--check-gold` 32 ok (20 in, 12 out; 2/6/2/2); `--check-ops-gold` 32 ok; `smoke_readers.py` smoke ok, exit 0.
- Cache: fresh empty `underwriting_pipeline/cache/T-128-live` (created for this run; no cached reply could be used).
- Run: `LLM_CACHE_DIR=$PWD/underwriting_pipeline/cache/T-128-live LLM_PACE_SECONDS=55 HOLDOUT_IDS=550-581 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-550-581-holdout-v11 <python> underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v11 --write`. Run id `20261105T012147-15550`, exit 0. Once; scored once.
- C2/C4: `count_ops_gate_v2.py --v11 SUB-550-581-holdout-v11.json --runs <reports>`; reports rebuilt from a temp copy of the run cache with the model call blocked (0 blocked attempts; 20/20 in-scope statuses equal to the scored ones). Output `SUB-550-581-ops-gate-v2.txt` (exit 0: C2 PASS, C4 PASS). M1 rule: no in-scope file went to manual intake, so nothing is set aside.
- Diagnostic only (not a score, nothing written): the SUB-561 year-built mark was traced in memory with v11 `score_report` on the rebuilt report; cause in results note 1.
- Nothing written to gold, `simulation/inbox/`, real logs or outboxes. `workbench.html` sha256 before/after `4fcfb1b5…` (unchanged). `underwriting_pipeline/cache/` is git-ignored.

## Console output, as printed (org id masked)

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
01:22 SUB-550 ok attempts 1 retries ['rate_limit_429']
01:22 SUB-551 ok attempts 1 retries []
01:23 SUB-552 ok attempts 1 retries []
01:24 SUB-553 ok attempts 1 retries []
01:25 SUB-554 ok attempts 1 retries []
01:26 SUB-555 ok attempts 1 retries []
01:27 SUB-556 ok attempts 1 retries []
01:28 SUB-557 ok attempts 1 retries []
08:42 SUB-558 ok attempts 1 retries ['timeout']
08:42 SUB-559 ok attempts 1 retries ['rate_limit_429']
08:43 SUB-560 ok attempts 1 retries []
08:44 SUB-561 ok attempts 1 retries []
08:45 SUB-562 ok attempts 1 retries []
08:46 SUB-563 ok attempts 1 retries []
08:47 SUB-564 ok attempts 1 retries []
08:48 SUB-565 ok attempts 1 retries []
08:49 SUB-566 ok attempts 1 retries []
08:50 SUB-567 ok attempts 1 retries []
08:51 SUB-568 ok attempts 1 retries []
08:51 SUB-569 ok attempts 1 retries []
08:52 SUB-570 ok attempts 1 retries []
08:53 SUB-571 ok attempts 1 retries []
08:54 SUB-572 ok attempts 1 retries []
08:55 SUB-573 ok attempts 1 retries []
08:56 SUB-574 ok attempts 1 retries []
08:57 SUB-575 ok attempts 1 retries []
08:58 SUB-576 ok attempts 1 retries []
08:59 SUB-577 ok attempts 1 retries []
09:00 SUB-578 ok attempts 1 retries []
09:01 SUB-579 ok attempts 1 retries []
09:01 SUB-580 ok attempts 1 retries []
09:02 SUB-581 ok attempts 1 retries []
/Users/disastershubz/INSURANCE FLOW AI/insureflow-integration/deliverables/ai-engineer/evals/SUB-550-581-holdout-v11.md
named_insured {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 17, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 3}
tiv {'hit': 19, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 1}
construction {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 10, 'hit (needs review)': 0, 'miss': 2, 'not_credited': 0, 'call_failed': 0, 'flagged': 8}
status {'hit': 10, 'hit (needs review)': 0, 'miss': 10, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
route {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 1, "automated": 155, "silent_error_rate": 0.006, "automation_rate": 0.861}
failed attempts {'rate_limit_429': 2, 'timeout': 1, 'other': 0, 'reply_not_usable': 0} {'rate_limit_429': 'per minute: {"error":{"message":"Rate limit reached for model `qwen/qwen3.8-27b` in organization `org_***` service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Used 794, Requested 311. Please try again in 6.3s. Need more tokens? Upgrade to Dev Tier today at https://con', 'timeout': 'The read operation timed out'}
tokens {"run": "20261105T012147-15550", "skipped_lines": 0, "this_run": {"model_calls": 20, "from_cache": 0, "tokens": 38449, "tokens_per_call": 1922}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 20, "tokens": 38449}}}
```
