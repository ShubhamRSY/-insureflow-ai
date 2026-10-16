# Plan: test one stronger model on dev SUB-127 to SUB-146 (D-102 item 4)

Author: @ai-engineer-assistant, 2026-10-16. Plan only. Nothing run, 0 model calls, no code, key not read or printed. SUB-154 to SUB-173 is never used.

## 1. Which model and host
- **Recommended (paid, needs a user decision under D-011): a Claude Sonnet-class model on the Anthropic API.** Why: the current model (qwen/qwen3.8-27b on Groq) is a 27B model. A larger model is the only variable this test changes. D-084 already showed that the free Groq alternatives are not stronger: gpt-oss-120b scored worse than qwen on named_insured, premises and effective_date and stopped at its daily token limit after 12 of 20 files; gpt-oss-20b had 4 failed files. The model name and prices must be confirmed by the user at run time (my price figures below are from memory, not checked).
- **Free option: openai/gpt-oss-120b on Groq (free tier, allowed by the amendment to D-011 at DECISIONS.md:136).** Weakness: D-084 already ran it on SUB-087 to 106 (worse, and rate-limited). Re-running on SUB-127 to 146 would need two or more days of daily limits or a paced split. Expect little new information. I would not choose it unless no paid call is allowed.
- Neither is a production choice. Host and model go in the shell as LLM_BASE_URL, LLM_MODEL and LLM_API_KEY (the repo `.env` key is not used). The prompt is not changed.
- Note: provider_guard and the cache key include the host and model, so the saved dev replies of qwen are not reused.

## 2. What it can and cannot fix (root-cause classes of T-103: OCR 13, check 12, scorer 5, gold convention 19, model 0)
- **Gold convention 19 and scorer 5 (24 of 49): no effect.** They are the wording of the gold and the v4 word rule. A better model does not make "Residential apartments" match "Apartment building".
- **Model 0: nothing to fix.** The root-cause replay found no mark where the model read the document wrongly.
- **OCR 13: little.** The model already read the garbled SUB-170 page correctly. The losses are in the pipeline's OCR word-confidence floor, which a stronger model does not change. A model might copy "2026-09-30" from "2026~09.35" but the gate would still reject it or it would be a guess, which the prompt forbids.
- **Check 12: little to some.** The gaps are in the gates: 2-digit-year dates, "..." in quotes, the reword flag on a trailing period, the extras rule, location handling. A stronger model might follow "copy the quote exactly" and "write the date as YYYY-MM-DD" more often (two things that explain SUB-163 and SUB-168), but the prompt does not ask for an ISO date and the parser still fails on a 2-digit year.
- **Honest expectation:** a stronger model is unlikely to move the 9/10 field gate. At best it moves a few check-class marks and the silent-error rate. The cheaper, surer levers are the check fixes and the gold rules already set by D-102.
- On the dev set the current operations score is 19/20 and the others are already at the level shown in section 5. The headroom is mostly premises (17), year_built (16), construction (17), tiv (17) and route (16): those are mostly location and scan cases, i.e. check and OCR classes.

## 3. Cost per file
- Basis: T-103 run record: 38,396 tokens for 20 calls, 1,920 tokens per file (one cached dev sample: 1,272 prompt and 786 completion). A stronger model may write longer replies; allow 1.5x, about 2,900 tokens per file.
- Claude Sonnet-class, price from memory and unverified, to be confirmed at https://www.anthropic.com/pricing before the run: about 3 USD per million input tokens and 15 USD per million output tokens. With 1,300 input and 600 output tokens: 1,300 x 3 / 1e6 + 600 x 15 / 1e6 = 0.0039 + 0.009 = about 0.013 USD per file; at 1.5x about 0.02 USD. **20 files: about 0.26 USD, upper bound about 0.40 USD.** One run only, no retries beyond the pipeline's own (RUN-RULES), so a cap of 1 USD.
- Free option: 0 USD, but the Groq output-token limit (1,000 output tokens per minute seen in T-103) means a pace of about 55 s per file and a daily limit; allow 20 to 40 minutes, or a second day.

## 4. Run rules
1. Temp copy: `LLM_CACHE_DIR` set to a fresh temp folder, empty (no copy of the qwen cache). Nothing is written to `underwriting_pipeline/cache/`.
2. Paced: `LLM_PACE_SECONDS=55` on Groq; paid host: a pace the host allows (for example 2 s).
3. Scorer: the existing frozen v4 via `underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v4` with `HOLDOUT_IDS=127-146`, **without `--write`**, and `HOLDOUT_OUT` pointing to a new folder `deliverables/ai-engineer/evals/model-test-dev-<model>/`. Without `--write` the run is read-only and the files go to a temp folder; I would copy the two score files there afterwards by hand. The run refuses to start if the score file exists.
4. D-069: no write to `team/`, `deliverables/**/*.jsonl` (the token log goes to the temp cache), `simulation/` outboxes, the real workbench page or any published score file. Check `git status` before and after: only the new output folder may appear.
5. Smoke first (`smoke_readers.py`), `.venv/bin/python` (not system python), one run, scored once, results reported as they are.
6. Only dev SUB-127 to 146. If a file is outside that range, the run stops.
7. Gold stays as it is (dev gold predates P-053 and P-054, so SUB-127, 128, 129 and 135 route marks stay stale for both models; compare like with like).

## 5. Success measure (against the current dev scores)
Baseline: `deliverables/ai-engineer/evals/P-054-dev/SUB-127-146-dev-v4-cache-rescore.json` (qwen, commit b007002): named_insured 20, effective_date 18, operations 19, sales 18, construction 17, year_built 16, premises 17, tiv 17, loss_runs 8 of 8 credited, conflict 16 of 19, status 18, route 16 of 20, 0 unsafe, 0 false completes.
- The test passes (worth a further step) only if: at least +3 hits in total over those columns **and** no field loses a hit **and** 0 false completes, 0 unsafe routes, 0 failed calls, and the silent-error rate is not higher than the baseline. Cost per file is reported next to the score.
- If the gain is smaller than that, the result is "no case for the model change", and the next work is the check fixes.
- A dev gain is not evidence for production. A hold-out would still be needed (20 new files, gold first, scored once).

## 6. Approval needed
- **Running the comparison needs a user decision, not a P-###.** It changes no code, prompt or production model, and it is dev-only, as D-084 was. Because the recommended host is paid, the decision must say that D-011 is lifted for this one run, with the cap (1 USD) and the model name. With the free option no decision beyond "go" is needed.
- **A P-### is needed only if the model were to change for the pipeline** (a different LLM_MODEL as the default, a prompt or provider guard change). That is a separate proposal after the result, and @model-risk can still block production. Nothing in this plan is a production approval.
