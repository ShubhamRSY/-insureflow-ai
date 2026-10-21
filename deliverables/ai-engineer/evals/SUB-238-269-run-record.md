# T-117 run record (2026-10-21), official hold-out SUB-238 to SUB-269 (D-119)

- Worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team`, branch `ai-team`, HEAD `b0c78d5`. `.venv/bin/python` (3.14.6; the worktree `.venv` is a symlink to `-insureflow-ai-1/.venv`).
- Frozen code under test, verified just before the run:
  - code-under-test commit `8d605acce37f06f719b5a865a79d783bc3e9c800`; `git diff 8d605ac..HEAD -- underwriting_pipeline/` is empty (commits after it touch docs and gold only). The score file records "last pipeline commit 8d605acce37f06f719b5a865a79d783bc3e9c800".
  - prompt `PROMPT_VERSION` `759b3e6bc9b2`.
  - scorer `underwriting_pipeline/ai/eval_holdout_v11.py` sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`.
  - lint `deliverables/senior-test-engineer/lint_holdout.py` sha256 `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653`.
  - T-117 gold manifest sha256 `7e076534432f1276bfe6198643547498b613c4f2b7aceb2ed618314b5e39fd33` (`shasum -c` on all 33 lines: OK).
- Scorer pre-checks before the run: `eval_holdout_v11 --self-check` ok; `--check-gold` 32 ok, 0 fail (20 in scope, 12 out; per criterion 4/5/4/2; 3 two-criteria, 2 criterion-4); `--check-ops-gold` 32 ok.
- `smoke_readers.py` on `b0c78d5` printed `smoke ok`, exit 0 (typed PDF, image-only PDF, colour/greyscale/rotated scan, Excel, email-only and Spanish all read; tesseract 5.5.2, poppler 26.10.0). No reader failed.
- Cache: fresh empty folder `underwriting_pipeline/cache/T-117-live` made just before the run. Before any call, the cache key of all 32 submissions was computed without a model call and checked against `cache/extractions` (67), `cache/T-104-live/extractions` (20), `cache/T-108-live/extractions` (21) and the fresh folder: **0 cached replies** for SUB-238–269. The run's `from_cache` is 0.
- Run: `LLM_CACHE_DIR=$PWD/underwriting_pipeline/cache/T-117-live LLM_PACE_SECONDS=55 HOLDOUT_IDS=238-269 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-238-269-holdout-v11 .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v11 --write`. Run id `20261021T112723-44537`, start 11:27:23, end 11:58:43, exit 0. Model `qwen/qwen3.8-27b` on Groq free tier (D-011). Scored once with `--write`; no re-score and no second run.
- Files: 32 (20 in scope, 12 out of scope by gold Scope line). Score files: `SUB-238-269-holdout-v11.md/.json` govern; mismatches as-is in `SUB-238-269-holdout-v11-mismatches.md`.
- Nothing was written to `gold-set/`, `simulation/inbox/`, the default token log or the outboxes. `underwriting_pipeline/app/workbench.html` sha256 `4fcfb1b5…55fb` unchanged before/after.

## Console output, as printed

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
11:27 SUB-238 ok attempts 1 retries []
11:28 SUB-239 ok attempts 1 retries []
11:29 SUB-240 ok attempts 1 retries []
11:30 SUB-241 ok attempts 1 retries []
11:31 SUB-242 ok attempts 1 retries []
11:32 SUB-243 ok attempts 1 retries []
11:33 SUB-244 ok attempts 1 retries []
11:34 SUB-245 ok attempts 1 retries []
11:34 SUB-246 ok attempts 1 retries []
11:35 SUB-247 ok attempts 1 retries []
11:36 SUB-248 ok attempts 1 retries []
11:37 SUB-249 ok attempts 1 retries []
11:38 SUB-250 ok attempts 1 retries []
11:39 SUB-251 ok attempts 1 retries []
11:40 SUB-252 ok attempts 1 retries []
11:41 SUB-253 ok attempts 1 retries []
11:42 SUB-254 ok attempts 1 retries []
11:43 SUB-255 ok attempts 1 retries []
11:43 SUB-256 ok attempts 1 retries []
11:44 SUB-257 ok attempts 1 retries []
11:45 SUB-258 ok attempts 1 retries []
11:46 SUB-259 ok attempts 1 retries []
11:47 SUB-260 ok attempts 1 retries []
11:48 SUB-261 ok attempts 1 retries []
11:49 SUB-262 ok attempts 1 retries []
11:50 SUB-263 ok attempts 1 retries []
11:51 SUB-264 ok attempts 1 retries []
11:52 SUB-265 ok attempts 1 retries []
11:53 SUB-266 ok attempts 1 retries []
11:54 SUB-267 ok attempts 1 retries []
11:55 SUB-268 ok attempts 1 retries []
11:56 SUB-269 ok attempts 1 retries []
deliverables/ai-engineer/evals/SUB-238-269-holdout-v11.md
named_insured {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 13, 'hit (needs review)': 0, 'miss': 7, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
tiv {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
construction {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 16, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 4, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 17, 'hit (needs review)': 0, 'miss': 3, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
status {'hit': 11, 'hit (needs review)': 0, 'miss': 9, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
route {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 0, "automated": 153, "silent_error_rate": 0.0, "automation_rate": 0.85}
failed attempts {'rate_limit_429': 0, 'timeout': 0, 'other': 0, 'reply_not_usable': 0} {}
tokens {"run": "20261021T112723-44537", "skipped_lines": 0, "this_run": {"model_calls": 20, "from_cache": 0, "tokens": 36255, "tokens_per_call": 1813}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 20, "tokens": 36255}}}
```

## Gate report

### P-055 scope gate: PASS
- Leakage (hard gate): **0** of 12 (must be 0).
- Detection recall, overall: **12/12 = 100%** (must be 100%). Per criterion: 1 scanned application 4/4; 2 multiple locations 5/5; 3 non-English 4/4; 4 application not identified 2/2.
- Reason accuracy (reported): 12/12 manual-intake cards list every gold criterion.
- False manual intake: **0** of 20 in-scope files (ceiling 2).

### False completes and status
- False completes (plain "complete" on a gold-incomplete file): **0** (must be 0).
- Status automation: 1 of 10 gold-complete files shown as plain "complete". status marks: 11 hit, 9 miss (all 9 are "complete — review pending" or "incomplete" where gold says complete; the safe direction).
- Failed calls, left out of both: 0.

### T-027 route gate: PASS
- Unsafe routes (a carrier route where gold says senior_referral or no_match): **0** (must be 0).
- Route accuracy: **19/20** (gate: at least 18/20).
- The 1 miss: SUB-252 gold no_match -> senior_referral; not a carrier route, so not unsafe (B-448).

### Per-field hits, in-scope files (20), floor 18/20 (D-013 item 3)

| Field | Hit | Miss | Not credited | Floor 18/20 |
|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | met |
| premises | 20 | 0 | 0 | met |
| effective_date | 20 | 0 | 0 | met |
| operations | 13 | 7 | 0 | **not met** |
| sales | 20 | 0 | 0 | met |
| tiv | 20 | 0 | 0 | met |
| construction | 20 | 0 | 0 | met |
| year_built | 20 | 0 | 0 | met |
| loss_runs (date only) | 16 | 0 | 4 | **not met** (a not_credited null is not a correct answer) |

Other marks: conflict 17/3; status 11/9; route 19/1. Call failed: 0 in every row.

### Operations checklist (v11): 20 of 20 files by the checklist; 13 hit, 7 miss
Misses: SUB-239, 244, 246, 248, 250, 254, 257. All are stored free text where the gold wants a `business_type=` slot set. No silent errors (each is a review field).

### Loss runs (v11 rule)
- hits 16, misses 0, not_credited 4 (SUB-238, 245, 251, 252, all Carrier C loss runs with no readable valued-as-of date). 0 silent errors.
- Pre-registered B-447 expected 3 operations misses; the run has 7.

### Silent error rate and automation rate (D-084)
- Silent error rate: **0 of 180 = 0.0**.
- Automation rate: **153 of 180 = 0.85**. By field: named_insured, premises, effective_date, sales, tiv, construction 1.0; year_built 0.95; operations 0.3; loss_runs 0.4.
- Files with a failed call, left out: 0.

### Retries (RUN-RULES.md)
- Total: **0**. No failed attempt of any kind (`rate_limit_429` 0, timeout 0, other 0, reply_not_usable 0). Every file reached `ok` on attempt 1 of `score_retry`. No unlogged retry.
- **call_failed: 0.**

### Tokens and cost
- 20 call rows totalling **36,255 tokens** (23,090 prompt + 13,165 completion), 1,813 per call. The 12 out-of-scope files stopped before any model call.
- Free tier (what was paid): **$0** (Groq free tier, D-011).
- Same tokens at the repo's paid list prices (`deliverables/architecture/system-design.md` 8.3; these are Gemini prices, not qwen's; label per D-038 item 5): Gemini 2.5 Flash ($0.30 in, $2.50 out): 23,090 x 0.30 + 13,165 x 2.50 = **$0.0398**; Gemini 2.5 Pro ($1.25 in, $10.00 out): **$0.1605**.
- Cost per file over all 32: Flash $0.0012, Pro $0.0050. Cost per in-scope call: Flash $0.0020, Pro $0.0080.

## Pre-registered limitations (from NEXT-SESSION.md, recorded before the run)
- **B-447:** 3 operations misses pre-registered. Actual: 7 operations misses.
- **B-449:** no in-scope direct carrier_a route. Gold routes are carrier_a 0, senior_referral 16, no_match 4, so the route gate is exercised on the safe direction only.
- **B-448:** SUB-252 R1 no_match vs R2 senior_referral. The run gives senior_referral; scored as a route miss, not unsafe.
