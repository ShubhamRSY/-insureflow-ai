# Plan: two-step stronger-model test on dev SUB-206 to SUB-237 (D-115)

Author: @ai-engineer-assistant, 2026-10-19. Plan only. Nothing run, 0 model calls, no code, prompt, gold, scorer or score file changed, no key read or printed. D-115 (2026-10-19, ACCEPTED by @user) makes SUB-206–237 development data; the published T-108 scores stay as published. D-011 (no paid API) is unchanged and parked.

## 1. Step 1 (free, needs no D-011 change): openai/gpt-oss-120b on Groq

- **Model/host:** `openai/gpt-oss-120b` on Groq's free tier, set only through the shell (`LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` from the shell, never read or printed; the repo `.env` key is not used). No code change, so no P-### to run it; the free tier is already allowed by D-012's amendment to D-011.
- **Known weakness (D-084, DECISIONS.md:939–948):** this model already lost to qwen on named_insured, premises and effective_date on SUB-087–106 and **hit its Groq daily token limit after 12 of 20 files**. It is in this plan because the user asked for the free step first, not because it is expected to be stronger.
- **Calls and pacing:** the official T-108 run made **21 model calls, 42,158 tokens** (26,692 prompt + 15,466 completion, 2,008 per call) over the 20 in-scope files plus SUB-233; the 11 other out-of-scope files stop before any call. Expect the same 21 calls; gpt-oss-120b may write longer replies, so allow up to ~63k tokens (1.5x). Pace at `LLM_PACE_SECONDS=55` (the 1,000-output-token/minute limit seen in T-108 itself, which took 8 rate-limit retries). Because D-084's limit was hit mid-run, **plan for a paced split across two daily-limit days** (e.g. 12 files day 1, the rest day 2): `regression_dev.py` sets `LLM_MAX_WAIT=1800` and an interrupted run resumes from its own cache, so the second day continues, it does not restart.

## 2. Step 2 (paid, only if Step 1 is unclear): Claude Sonnet-class — needs the user to lift D-011; NOT approved

- **Candidate:** a Claude Sonnet-class model on the Anthropic API (the same candidate class as the T-103 plan; exact model name confirmed by the user at run time). This is a larger model than qwen/qwen3.8-27b, which is the only variable the test changes.
- **This step is not approved.** It requires the user to lift D-011 for one run, with the model name, the host, and a cost cap in the decision (suggested cap: 2 USD). D-011 stands until the user decides otherwise (D-115 item 2), and the user decides only after seeing the root cause and this plan. If Step 1 gives a clear answer, Step 2 does not run at all.
- "Unclear" means: the Step 1 run fails partway (daily limit twice, failed calls) or lands within noise of the published marks with no visible read-behaviour change. A clean Step 1 that matches the published marks is a clear answer (model is not the lever), not an unclear one.

## 3. What a stronger model can and cannot fix (T-108 root-cause classes)

The 17 silent errors, per `T-108-root-cause.md`:

- **7 loss-run scorer-convention: not model-fixable.** v7 takes the first date in the gold "Loss runs" line, which is the policy-period start, not the valuation date. The pipeline's answer is already correct in all seven (e.g. SUB-206: pipeline 2026-08-15 = gold valuation date; scorer compared to 2023-06-01). No model changes a scorer rule. Backlog B-435; the frozen v7 score stays as published (D-020/D-025).
- **9 operations gold-convention wording: not model-fixable.** In all nine the facts are present ("Retail seating for 24" vs gold's "24 seats"); the checklist rule wants the gold's exact phrases in order. A stronger model rephrasing differently is still a miss by design. Backlog B-436. One sub-case (SUB-211, the answer truncates and repeats) is partly prompt/extraction and is the only operations mark a model could plausibly touch.
- **1 SUB-224 scan misread (OCR): the only model-class mark.** The scan's 2026-07-06 came back as 2026-08-05 with no review flag, although `REASON_LOW_SCAN` exists for exactly this. Even here the real lever is the pipeline's scan-flag gap (B-435), not model size; a stronger model *might* copy the day correctly where qwen did not.
- **Honest expectation: at most ~1 mark is model-removable** (SUB-224, plus a maybe on SUB-211). The operations (9/20) and loss_runs (5/20) field scores are **unlikely to move at all**, because 16 of the 17 silents are scorer/gold convention. The SUB-233 scope leak (P-055 gate FAIL) is a detector check gap (B-432) and is untouched by any model.
- **The one T-027 gate criterion it could realistically target: route accuracy, currently 18/20 against the gate floor of at least 18/20.** The two misses (SUB-206, SUB-213: gold carrier_a, used senior_referral, "readable class on no carrier list; not held") are the only T-027 marks with any headroom; unsafe routes is already 0 and a model cannot help there. The route is computed by the routing table from extracted values, so only the model-side inputs are in scope — the gain is marginal and may well be zero. The P-055 scope gate is a separate, non-model fix.

## 4. Cost

- **Measured so far: $0.** The official T-108 run (21 calls, 42,158 tokens) ran on the Groq free tier today.
- **Step 1 (free tier): $0 again.** Estimate 21 calls, ~42k tokens at the qwen basis, up to ~63k at 1.5x for a more verbose model. The currency is daily token limits and wall-clock (two paced days), not money.
- **Step 2 (paid, estimate only):** at the T-103 plan's Sonnet-class prices — about 3 USD per million input and 15 USD per million output, **from memory, unverified; confirm at https://www.anthropic.com/pricing before any run** — 27k input x 3/1e6 + 23k output (1.5x) x 15/1e6 = 0.081 + 0.345 = **about 0.43 USD for one run of all 21 calls**; on the measured qwen token split alone about 0.31 USD. One run only, no retries beyond the pipeline's own, suggested cap **2 USD**.

## 5. Exact commands, files, and the acceptance test

Shape (from the T-108 run record, `SUB-206-237-run-record.md:6`), adjusted to a fresh cache and a temp output, **without `--write`**:

```
export LLM_MODEL=openai/gpt-oss-120b   # LLM_BASE_URL and LLM_API_KEY stay the Groq values already in the shell; key never printed
LLM_CACHE_DIR=$(mktemp -d) LLM_PACE_SECONDS=55 HOLDOUT_IDS=206-237 \
HOLDOUT_OUT=$(mktemp -d)/T-108-gpt-oss-120b \
  .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v7
```

- Fresh empty `LLM_CACHE_DIR`: no qwen reply is reused (the cache key includes host and model) and nothing is written to `underwriting_pipeline/cache/`. An interrupted day-1 run keeps its own temp cache for day 2 — set the day-2 `LLM_CACHE_DIR` to the same folder.
- `HOLDOUT_OUT` is a temp folder; without `--write` the runner also refuses to write inside the repo (regression_dev.py:28–41) and the score files land in its own scratch dir. Copy the two score files into `deliverables/ai-engineer/evals/` afterwards under a new name (e.g. `model-test-dev-T-108-gpt-oss-120b.{md,json}`). **The published `SUB-206-237-holdout-v7.{md,json}` are never overwritten.**
- D-069 sandbox: no writes to `team/`, real logs, outboxes or the workbench; the token log goes with the temp cache. Check `git status` before and after: only the new score folder may appear. Smoke first (`.venv/bin/python smoke_readers.py`).
- Submissions: all 32 of SUB-206–237; the 12 out-of-scope files stop before a call except SUB-233 (detected in-scope, hence 21 calls).
- **Approval needed first:** nothing for Step 1 beyond the user's go — it is a dev run on a free host, like D-084. **Any prompt, OCR or extraction change the test might motivate needs a new proposal and the user's exact words `approve change P-###` first (D-017); no such change is proposed or approved here.** Step 2 additionally needs D-011 lifted for one run (model, host, cap) — not approved.
- **Acceptance test (does the model move anything?):** compare the rerun file-by-file against the published v7 marks on the 17 silent errors. The stronger model **is** the lever only if it removes model-class marks — realistically SUB-224 read back as 2026-07-06, maybe the SUB-211 truncation — **and** loses nothing anywhere else (every field at or above its published hit count, 0 failed calls, 0 false completes, 0 unsafe routes, silent-error rate at or below 0.094). Expected per the root cause: operations stays 9/20 and loss_runs stays 5/20; if that is what the rerun shows, **the model is not the lever** and the levers are B-435 (scorer first-date convention plus the scan-flag gap) and B-436 (gold checklist wording), which need proposals, not compute. Either result is reported as it lands; a dev result is never production evidence.

## 6. Plainly

Plan only. Nothing has been run; 0 model calls; no code, prompt, gold, scorer or score file changed; no key read or printed. D-011 is unchanged. Step 2 is not approved. This is not a production approval; @model-risk's T-027 veto stands. No send is authorized.
