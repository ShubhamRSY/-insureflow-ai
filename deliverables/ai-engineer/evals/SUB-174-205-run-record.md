# T-104 run record (2026-10-17), official hold-out SUB-174 to SUB-205 (D-109)

- Worktree insureflow-ai-team, branch ai-team, HEAD 066d774. Pipeline code = 6e7cfa2 (`git diff 6e7cfa2 -- underwriting_pipeline` is empty, checked at this record). Scorer v6 `underwriting_pipeline/ai/eval_holdout_v6.py` sha256 4bf1cd63a632ad38834909f6822c92619a7b597fe5994a24be1a5914c9d54e5b (matches D-108/D-109, checked at this record). Gold and inbox files unchanged since 3678c0f (`git diff 3678c0f` on gold-set and inbox is empty).
- `.venv/bin/python`. `smoke_readers.py` printed "smoke ok" before the run (orchestrator).
- Cache: fresh empty folder `underwriting_pipeline/cache/T-104-live` created just before the run, so no cached reply existed for any T-104 file. The run's token log is `underwriting_pipeline/cache/T-104-live/token_log.jsonl` (25 rows: 20 calls, 5 retry rows). `from_cache` = 0.
- Run: `LLM_CACHE_DIR=$PWD/underwriting_pipeline/cache/T-104-live LLM_PACE_SECONDS=55 HOLDOUT_IDS=174-205 HOLDOUT_OUT=deliverables/ai-engineer/evals/SUB-174-205-holdout-v6 .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v6 --write`. Run id 20261017T200158-46947, start 20:01:58, end 20:31:32, exit 0. Model qwen/qwen3.8-27b on Groq free tier (D-011). Scored once.
- Files: 32 (20 in scope, 12 out of scope by gold Scope line). The 12 out-of-scope files were stopped by scope-v3 before any model call ("not sent"), so 20 model calls were made.
- Score files: `SUB-174-205-holdout-v6.md/.json` govern. Mismatches: `SUB-174-205-holdout-v6-mismatches.md`. Nothing was re-scored with `--write` and no model call was made to write this record (the as-is lines come from the run's saved replies, replayed from a temp copy of the cache with the model call blocked; 0 calls; `git status` shows no repo file written by the replay).

## Console output, as printed

```
provider https://api.groq.com/openai/v1 model qwen/qwen3.8-27b
20:02 SUB-174 ok attempts 1 retries []
20:02 SUB-175 ok attempts 1 retries []
20:03 SUB-176 ok attempts 1 retries []
20:04 SUB-177 ok attempts 1 retries ['rate_limit_429']
20:05 SUB-178 ok attempts 1 retries []
20:06 SUB-179 ok attempts 1 retries []
20:07 SUB-180 ok attempts 1 retries []
20:08 SUB-181 ok attempts 1 retries []
20:09 SUB-182 ok attempts 1 retries []
20:10 SUB-183 ok attempts 1 retries []
20:11 SUB-184 ok attempts 1 retries []
20:12 SUB-185 ok attempts 1 retries ['rate_limit_429', 'rate_limit_429', 'rate_limit_429']
20:13 SUB-186 ok attempts 1 retries []
20:13 SUB-187 ok attempts 1 retries []
20:14 SUB-188 ok attempts 1 retries []
20:16 SUB-189 ok attempts 1 retries []
20:17 SUB-190 ok attempts 1 retries []
20:18 SUB-191 ok attempts 1 retries []
20:19 SUB-192 ok attempts 1 retries []
20:20 SUB-193 ok attempts 1 retries []
20:21 SUB-194 ok attempts 1 retries []
20:22 SUB-195 ok attempts 1 retries []
20:23 SUB-196 ok attempts 1 retries []
20:24 SUB-197 ok attempts 1 retries []
20:25 SUB-198 ok attempts 1 retries []
20:26 SUB-199 ok attempts 1 retries []
20:26 SUB-200 ok attempts 1 retries ['rate_limit_429']
20:27 SUB-201 ok attempts 1 retries []
20:28 SUB-202 ok attempts 1 retries []
20:29 SUB-203 ok attempts 1 retries []
20:30 SUB-204 ok attempts 1 retries []
20:31 SUB-205 ok attempts 1 retries []
/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team/deliverables/ai-engineer/evals/SUB-174-205-holdout-v6.md
named_insured {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
premises {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
effective_date {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
operations {'hit': 12, 'hit (needs review)': 0, 'miss': 8, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
sales {'hit': 19, 'hit (needs review)': 0, 'miss': 1, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
tiv {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
construction {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
year_built {'hit': 20, 'hit (needs review)': 0, 'miss': 0, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
loss_runs {'hit': 9, 'hit (needs review)': 0, 'miss': 8, 'not_credited': 3, 'call_failed': 0, 'flagged': 0}
conflict {'hit': 15, 'hit (needs review)': 0, 'miss': 5, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
status {'hit': 11, 'hit (needs review)': 0, 'miss': 9, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
route {'hit': 16, 'hit (needs review)': 0, 'miss': 4, 'not_credited': 0, 'call_failed': 0, 'flagged': 0}
metrics {"scored": 180, "silent": 3, "automated": 147, "silent_error_rate": 0.017, "automation_rate": 0.817}
failed attempts {'rate_limit_429': 5, 'timeout': 0, 'other': 0, 'reply_not_usable': 0} {'rate_limit_429': 'per minute: {"error":{"message":"Request too large for model `qwen/qwen3.8-27b` in organization `org_01kcpawq5vecv8na8y22z8xpx0` service tier `on_demand` on output tokens per minute (OTPM): Limit 1000, Requested 1400. The request\'s expected output tokens exceed the enforced limit; reduce max_tokens (or the requ'}
tokens {"run": "20261017T200158-46947", "skipped_lines": 0, "this_run": {"model_calls": 20, "from_cache": 0, "tokens": 35455, "tokens_per_call": 1773}, "last_24_hours": {"qwen/qwen3.8-27b": {"calls": 20, "tokens": 35455}}}
```

## D-109 report

### Scope gate (P-055, apart from the T-027 gate): PASS
- Leakage: **0 of 12** out-of-scope files (must be 0).
- Detection recall, overall: **12/12**. Per criterion: 1 scanned application 4/4; 2 multiple locations 5/5; 3 non-English 4/4; 4 application not identified 2/2.
- Reason accuracy (reported): 12/12 manual-intake cards list every gold criterion.
- False manual intake (in-scope file sent to manual intake): **0 of 20** (ceiling 2).

### False completes and status
- False completes (plain "complete" on a gold-incomplete file): **0**. Failed calls left out: 0.
- Status automation: 0 of 9 gold-complete files shown as plain "complete" (all 9 are "complete — review pending" or incomplete). Status mark: 11 hit, 9 miss (all 9 misses are the 9 gold-complete files).

### T-027 route gate: FAIL
- Unsafe routes (a carrier route where gold says senior_referral or no_match): **0**. Must be 0: met.
- Route accuracy: **16/20** (gate: at least 18/20). Verdict FAIL on accuracy.
- The 4 misses (gold route / route used by the pipeline). None is a carrier route.

| File | Gold | Used | How it missed |
|---|---|---|---|
| SUB-174 | senior_referral (market carrier_a) | no_match | match note: "readable class on no carrier list (R8; KO 8)"; the file is not held |
| SUB-182 | senior_referral (market carrier_b) | no_match | same note as SUB-174; the file is not held |
| SUB-186 | senior_referral | no_match (provisional; file on hold: missing information) | same R8 note, shown as the provisional route of a held file |
| SUB-201 | no_match | senior_referral (provisional; file on hold: missing information) | provisional note "possible bar/liquor exposure — confirm liquor sales (R2; AG:46, AG:39)" |

### Per-field hits vs the 9/10 floor (in-scope files, 20)
Floor read as 18 of 20 hits per field (D-013 item 3). "Not credited" = a null that matches a missing gold line (not a hit).

| Field | Hit | Miss | Not credited | Floor 18/20 |
|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | met |
| premises | 20 | 0 | 0 | met |
| effective_date | 20 | 0 | 0 | met |
| operations | 12 | 8 | 0 | **not met** |
| sales | 19 | 1 | 0 | met |
| tiv | 20 | 0 | 0 | met |
| construction | 20 | 0 | 0 | met |
| year_built | 20 | 0 | 0 | met |
| loss_runs (date only) | 9 | 8 | 3 | **not met** (9 hits of 20; 9 of 17 if the 3 not-credited are left out) |

Other marks (not extracted fields): conflict 15 hit / 5 miss; status 11 / 9; route 16 / 4. Call failed: 0 in every row.

### Operations checklist (v5): 20 of 20 files scored by the checklist (ops_rule "checklist"); 12 hit, 8 miss
Missing items per file (items of the gold "Operations items" line not found in the pipeline value, by the scorer's own ops_items_hit):

| File | Items missing from the pipeline value |
|---|---|
| SUB-175 | 24 seats; convection oven; no liquor; hood and extinguishing system inspected 2026-08-12 |
| SUB-177 | gas-fired masa mill; no liquor |
| SUB-180 | no gas |
| SUB-182 | two convection ovens; no liquor; hood and extinguishing system inspected 2026-07-28 |
| SUB-186 | restaurant with bar; fire suppression service yearly; hood and extinguishing system inspected 2026-08-19 |
| SUB-201 | until 2 a.m.; snack warmer |
| SUB-203 | espresso bar; hood and extinguishing system inspected 2026-09-10 |
| SUB-204 | no cooking |

### Silent error rate and automation rate (D-084)
- Silent error rate: **3 of 180 = 0.017**. All 3 are operations values, wrong and not flagged: SUB-180, SUB-201, SUB-204 (operations: 3/20 = 0.15).
- Automation rate: **147 of 180 = 0.817**. By field: named_insured, premises, effective_date, tiv, construction 1.0; sales 0.95; year_built 0.95; operations 0.45 (9/20); loss_runs 0.0 (0/20).
- Files with a failed call, left out: 0.

### Loss runs: accepted automatically vs needs review (20 in-scope files)
Counted from the saved reports: field `loss_run_valued_through` value and needs_review, and the gold "Expected loss run" line.

- Carrier run **accepted automatically** (value kept, not flagged): **0 of 20**.
- **Needs review with a date kept**: 9 (scan 2; typed carrier run 7, flagged "valued-as-of date ... is not a real past date; check it").
- **No date, needs review** (null): 11.

| File | Pipeline value | Needs review | Why (pipeline reason) | Gold expected loss run | Mark |
|---|---|---|---|---|---|
| SUB-174 | 2027-01-15 | yes | read from a scan | loss run from scan: check it | hit |
| SUB-175 | 2027-03-01 | yes | read from a scan | loss run from scan: check it | hit |
| SUB-176 | none | yes | none given | missing — owner's no-known-loss letter | not credited |
| SUB-177 | none | yes | none given | needs review — not a recognised carrier loss run | miss |
| SUB-178 | none | yes | none given | same | miss |
| SUB-179 | 2026-11-17 | yes | not a real past date | 2026-11-17 accepted | hit |
| SUB-180 | none | yes | none given | missing — owner's letter | not credited |
| SUB-181 | none | yes | none given | needs review — not recognised | miss |
| SUB-182 | 2027-01-29 | yes | not a real past date | 2027-01-29 accepted | hit |
| SUB-183 | 2027-06-17 | yes | not a real past date | 2027-06-17 accepted | hit |
| SUB-184 | 2027-02-15 | yes | not a real past date | 2027-02-15 accepted | hit |
| SUB-185 | 2027-07-18 | yes | not a real past date | 2027-07-18 accepted | hit |
| SUB-186 | 2027-05-01 | yes | not a real past date | 2027-05-01 accepted | hit |
| SUB-187 | 2027-03-17 | yes | not a real past date | 2027-03-17 accepted | hit |
| SUB-200 | none | yes | none given | needs review — not recognised | miss |
| SUB-201 | none | yes | none given | needs review — not recognised | miss |
| SUB-202 | none | yes | none given | needs review — not recognised | miss |
| SUB-203 | none | yes | none given | needs review — not recognised | miss |
| SUB-204 | none | yes | none given | needs review — not recognised | miss |
| SUB-205 | none | yes | none given | missing — none provided | not credited |

The run date was 2026-10-17; the seven typed-run dates are 2026-11-17 to 2027-07-18, after it. That is why the "not a real past date" check fired on all seven.

### Retries (RUN-RULES.md)
- Total: **5**, all `rate_limit_429` (Groq output-tokens-per-minute limit 1000, request 1400). Per file: SUB-177 1, SUB-185 3, SUB-200 1; every other file 0.
- All logged: the token log has 5 retry rows (20:04:43 SUB-177; 20:12:03, 20:12:04, 20:12:06 SUB-185; 20:26:55 SUB-200), the score file rows carry the same `retries`, and the console shows them. Call attempts per file in the token log: 2, 4, 2 for those three files, 1 for the other 17. No unlogged retry.
- **call_failed: 0.** Timeouts 0, other errors 0, reply_not_usable 0. No file was rescored by `score_retry` (attempts 1 each).

### Tokens and cost
- 20 model calls, **35,455 tokens** (22,192 prompt + 13,263 completion), 1,773 per call (range 1,537 SUB-205 to 1,949 SUB-204). 12 out-of-scope files: 0 tokens. Per file over all 32: 1,108.

| File | Prompt | Completion | Total |
|---|---|---|---|
| SUB-174 | 1107 | 657 | 1764 |
| SUB-175 | 1148 | 683 | 1831 |
| SUB-176 | 996 | 641 | 1637 |
| SUB-177 | 1214 | 647 | 1861 |
| SUB-178 | 1109 | 626 | 1735 |
| SUB-179 | 1185 | 652 | 1837 |
| SUB-180 | 1003 | 644 | 1647 |
| SUB-181 | 1185 | 645 | 1830 |
| SUB-182 | 1132 | 669 | 1801 |
| SUB-183 | 1119 | 684 | 1803 |
| SUB-184 | 1079 | 646 | 1725 |
| SUB-185 | 1169 | 658 | 1827 |
| SUB-186 | 1166 | 677 | 1843 |
| SUB-187 | 1099 | 656 | 1755 |
| SUB-200 | 1088 | 657 | 1745 |
| SUB-201 | 1084 | 663 | 1747 |
| SUB-202 | 1111 | 614 | 1725 |
| SUB-203 | 1210 | 646 | 1856 |
| SUB-204 | 1083 | 866 | 1949 |
| SUB-205 | 905 | 632 | 1537 |

- **Cost, free tier (what was paid): $0** (Groq free tier, D-011).
- Same tokens at a paid list price already written in the repo (`deliverables/architecture/system-design.md` section 8.3, prices P1-P4, read 2026-10-13 from the saved page captures; label per D-038 item 5: "estimate from public list prices, Oct 2026; free tier is development only"). These are Gemini prices, not qwen's; qwen has no price in the repo, and none was looked up:
  - Gemini 2.5 Flash ($0.30 in, $2.50 out per 1,000,000 tokens): 22,192 x 0.30 + 13,263 x 2.50 = **$0.0398** for the 20 calls, $0.0020 per call called, $0.0012 per file over 32.
  - Gemini 2.5 Pro ($1.25 in, $10.00 out): **$0.1604**, $0.0080 per call called, $0.0050 per file over 32.
  - The 5 retried 429 attempts carry no prompt or completion tokens in the token log and are not counted.
