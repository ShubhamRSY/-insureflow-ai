# T-108 run record (2026-10-19), official hold-out SUB-206 to SUB-237 (D-113/D-114)

- Worktree `insureflow-ai-team`, branch `ai-team`, HEAD `5d51a9b`. Pipeline code = `457f1bf` (`git diff 457f1bf -- underwriting_pipeline` is empty, checked at this record; the scorer reports "last pipeline commit 457f1bf5784cd8a0c95af72724ca9341be3ba207"). Prompt `759b3e6bc9b2` (P-059); scorer v7 `underwriting_pipeline/ai/eval_holdout_v7.py` sha256 `efe532a0006e21e60082279e29c97613eb5decdfadf12bedcdeb24f0d0437ca7` (equals the `457f1bf` blob, checked at this record). Gold manifest sha256 `11933e96b8370f57321ce5c1e1c6c3c3105a4f0517d841fbbbb8821bca18633d` (32 gold cards + route table, file order 206..237 then routes), recomputed and matched just before the run.
- `.venv/bin/python`. `smoke_readers.py` printed `smoke ok` on commit `5d51a9b` before the run (typed PDF, image-only PDF, colour/greyscale/rotated scan, Excel, email-only and Spanish all read; tesseract 5.5.2, poppler 26.10.0).
- Cache: fresh empty folder `underwriting_pipeline/cache/T-108-live` created just before the run; confirmed empty and holding no SUB-206..237 entry, so no cached reply existed for any T-108 file (live run, `from_cache` = 0). The run's token log is `underwriting_pipeline/cache/T-108-live/token_log.jsonl` (29 rows: 21 call rows, 8 retry rows).
- Run: `LLM_CACHE_DIR=$PWD/underwriting_pipeline/cache/T-108-live LLM_PACE_SECONDS=55 HOLDOUT_IDS=206-237 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-206-237-holdout-v7 .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v7 --write`. Run id `20261019T140831-50315`. Model `qwen/qwen3.8-27b` on Groq free tier (D-011). Scored once.
- Files: 32 (20 in scope, 12 out of scope by gold Scope line). Scorer pre-checks passed before the run: `eval_holdout_v7 --self-check` ok, and `--check-gold` parsed all 32 Scope lines (20 in, 12 out; per criterion 4/5/4/2; 3 two-criteria; 2 criterion-4).
- Score files: `SUB-206-237-holdout-v7.md/.json` govern. Scored once with `--write`; no re-score, no second run. Nothing was written to `gold-set/` or `simulation/inbox/`.

## Console output, as printed

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
14:09 SUB-206 ok attempts 1 retries ['rate_limit_429', 'rate_limit_429', 'rate_limit_429', 'rate_limit_429']
14:09 SUB-207 ok attempts 1 retries ['rate_limit_429']
14:10 SUB-208 ok attempts 1 retries ['rate_limit_429']
14:11 SUB-209 ok attempts 1 retries []
14:12 SUB-210 ok attempts 1 retries []
14:13 SUB-211 ok attempts 1 retries []
14:14 SUB-212 ok attempts 1 retries []
14:15 SUB-213 ok attempts 1 retries ['rate_limit_429']
14:15 SUB-214 ok attempts 1 retries ['rate_limit_429']
14:16 SUB-215 ok attempts 1 retries []
14:17 SUB-216 ok attempts 1 retries []
14:18 SUB-217 ok attempts 1 retries []
14:19 SUB-218 ok attempts 1 retries []
14:20 SUB-219 ok attempts 1 retries []
14:21 SUB-220 ok attempts 1 retries []
14:22 SUB-221 ok attempts 1 retries []
14:23 SUB-222 ok attempts 1 retries []
14:24 SUB-223 ok attempts 1 retries []
14:25 SUB-224 ok attempts 1 retries []
14:26 SUB-225 ok attempts 1 retries []
14:26 SUB-226 ok attempts 1 retries []
14:27 SUB-227 ok attempts 1 retries []
14:28 SUB-228 ok attempts 1 retries []
14:29 SUB-229 ok attempts 1 retries []
14:30 SUB-230 ok attempts 1 retries []
14:31 SUB-231 ok attempts 1 retries []
14:32 SUB-232 ok attempts 1 retries []
14:33 SUB-233 ok attempts 1 retries []
14:34 SUB-234 ok attempts 1 retries []
14:35 SUB-235 ok attempts 1 retries []
14:36 SUB-236 ok attempts 1 retries []
14:36 SUB-237 ok attempts 1 retries []
deliverables/ai-engineer/evals/SUB-206-237-holdout-v7.md
named_insured {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 9, 'hit (needs review)': 0, 'miss': 11, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
tiv {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
construction {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 5, 'hit (needs review)': 0, 'miss': 9, 'not_credited': 6, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 10, 'hit (needs review)': 0, 'miss': 10, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
status {'hit': 15, 'hit (needs review)': 0, 'miss': 5, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
route {'hit': 18, 'hit (needs review)': 0, 'miss': 2, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 17, "automated": 142, "silent_error_rate": 0.094, "automation_rate": 0.789}
failed attempts {'rate_limit_429': 8, 'timeout': 0, 'other': 0, 'reply_not_usable': 0}
tokens {"run": "20261019T140831-50315", "skipped_lines": 0, "this_run": {"model_calls": 21, "from_cache": 0, "tokens": 42158, "tokens_per_call": 2008}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 21, "tokens": 42158}}}
```

## Gate report

### P-055 scope gate: FAIL
- Leakage (hard gate): **1** of 12 (must be 0). SUB-233: field shown, provisional route, automated draft, send enabled.
- Detection recall, overall: **11/12** (must be 100%); missed: SUB-233. Per criterion: 1 scanned application 4/4; 2 multiple locations 4/5; 3 non-English 4/4; 4 application not identified 2/2.
- Reason accuracy (reported): 11/11 manual-intake cards list every gold criterion.
- False manual intake: **0** of 20 in-scope files (ceiling 2).

### False completes and status
- False completes (plain "complete" on a gold-incomplete file): **0** (must be 0).
- Failed calls left out: 0. Status automation: 3 of 8 gold-complete files shown as plain "complete".

### T-027 route gate: PASS
- Unsafe routes (a carrier route where gold says senior_referral or no_match): **0** (must be 0).
- Route accuracy: **18/20** (gate: at least 18/20).
- The 2 misses (gold route / route used): SUB-206 carrier_a -> senior_referral; SUB-213 carrier_a -> senior_referral. Neither is a carrier route, so neither is unsafe.

| File | Gold | Used | How it missed |
|---|---|---|---|
| SUB-206 | carrier_a | senior_referral | readable class on no carrier list; not held |
| SUB-213 | carrier_a | senior_referral | same R8 note; not held |

### Per-field hits, in-scope files (20)
Floor 18/20 per field (D-013 item 3).

| Field | Hit | Miss | Not credited | Floor 18/20 |
|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | met |
| premises | 20 | 0 | 0 | met |
| effective_date | 20 | 0 | 0 | met |
| operations | 9 | 11 | 0 | not met |
| sales | 20 | 0 | 0 | met |
| tiv | 19 | 1 | 0 | met |
| construction | 20 | 0 | 0 | met |
| year_built | 20 | 0 | 0 | met |
| loss_runs (date only) | 5 | 9 | 6 | not met |

Other marks: conflict 10/10; status 15/5; route 18/2. Call failed: 0 in every row.

### Operations checklist (v5): 20 of 20 files by the checklist; 9 hit, 11 miss
Misses: SUB-206, 207, 208, 209, 211, 215, 218, 220, 221, 222, 225.

### Loss runs (v7 rule)
- hits 5, misses 9, not_credited 6 (over 20). No file accepted automatically without review counted as automated (automation rate 0.0 for the field).

### Silent error rate and automation rate (D-084)
- Silent error rate: **17 of 180 = 0.094**. All 17 are operations (9) and loss_runs (8) values shown, wrong and not flagged.
- Automation rate: **142 of 180 = 0.789**. By field: named_insured, effective_date, construction 1.0; premises, sales, tiv 0.95; year_built 0.9; operations 0.35; loss_runs 0.0.
- Files with a failed call, left out: 0.

### Retries (RUN-RULES.md)
- Total: **8**, all `rate_limit_429` (Groq output-tokens-per-minute limit 1000). Per file: SUB-206 4, SUB-207 1, SUB-208 1, SUB-213 1, SUB-214 1; every other file 0.
- All logged in the token log (8 retry rows) and in each file's `retries`. No unlogged retry. Every file reached `ok` on attempt 1 of `score_retry` (no whole-file rescore).
- **call_failed: 0.** Timeouts 0, other errors 0, reply_not_usable 0.

### Tokens and cost
- 21 call rows totalling **42,158 tokens** (26,692 prompt + 15,466 completion), 2,008 per call. The 12 out-of-scope files stopped before any model call.
- Free tier (what was paid): **$0** (Groq free tier, D-011).
- Same tokens at the repo's paid list prices (`deliverables/architecture/system-design.md` 8.3; these are Gemini prices, not qwen's; label per D-038 item 5): Gemini 2.5 Flash ($0.30 in, $2.50 out): 26,692 x 0.30 + 15,466 x 2.50 = **$0.0467**; Gemini 2.5 Pro ($1.25 in, $10.00 out): **$0.1880**.
- Cost per file over all 32: Flash $0.0015, Pro $0.0059. Cost per in-scope call: Flash $0.0022, Pro $0.0090.
