# Proposal P-039 — Switch the default extraction model to qwen/qwen3.8-27b

- Author: orchestrator (main session), for @ai-engineer-assistant's queue
- Date: 2026-10-15
- For: @user (the AI Engineer)
- Decision: D-086 item 4: "If all pass, draft P-039 (switch the default extraction model to qwen/qwen3.8-27b) and stop for my approval. Do not switch on your own."
- Status: PROPOSAL. Not approved. Not implemented. Nothing has been switched.
- Synthetic data only. Not a production approval; @model-risk's T-027 veto stands until a hold-out on the chosen model passes.

## Why

D-086 pass criteria, set before the run, measured on SUB-087–106 (development data) after P-038, uncached and paced (`deliverables/ai-engineer/analysis/pass-check-D-086.md`):

| Criterion | Result | Needed | Pass |
|---|---|---|---|
| Sales on the 9 shared files | 9 of 9 | 8 of 9 | PASS |
| Silent error rate, 20 files | 1.7% | ≤ 2.5% | PASS |
| Automation rate, 20 files | 77.2% | ≥ 71% | PASS |

Supporting evidence:
- Fair comparison (D-085, before P-038), 9 shared files: qwen had 60 of 81 hits vs gpt-oss-120b's 59, and automation 71.6% vs 69.1%. Silent error rate was 2.5% for both.
- Stability (D-085): two uncached qwen runs changed 0 of 180 marks.
- Cost: about 1,600 tokens per file vs about 2,800 for gpt-oss-120b. gpt-oss-120b hit its Groq daily token limit after 12 of 20 files (D-084).
- After P-038, qwen on all 20 files, compared with D-085 run 2: sales 6 → 18, status 9 → 15, year built 14 → 15, other fields unchanged.

## The change

1. The default model is the `LLM_MODEL` line in your shell profile (`~/.zshrc`); the code has no default (P-023). You change it to `qwen/qwen3.8-27b`. The orchestrator does not edit your shell file.
2. The docstring example in `underwriting_pipeline/ai/confidence_vs_hit.py` that names `openai/gpt-oss-120b` is updated to the new model. The `llm_extract.py` self-check keeps its own fixed model name; it tests the guard, not the default.
3. Every batch run on qwen sets `DEV_PACE_SECONDS=55` (or the equivalent pacing), because qwen's Groq cap is 1,000 output tokens per minute (about one file every 45 s). A 20-file run takes about 18 minutes.
4. No prompt, gate, OCR or scorer change. The cache key already holds the model, so no gpt-oss-120b result is reused.

## Risks and what is not known

- These numbers are development data: the code was changed while the gold was visible. Only the next hold-out (SUB-107–126, gold first, scored once) can show production accuracy. T-027 stays until then.
- One "request too large" per-minute 429 appeared in the D-086 run; it was retried and succeeded. A bigger file could need a longer wait.
- P-038 was not measured on gpt-oss-120b, so part of the gap may be P-038 rather than the model.
- A network outage (DNS) during the D-086 run was retried without losing a file.

## Rollback

Set `LLM_MODEL=openai/gpt-oss-120b` again. Cached results are per model, so nothing needs cleaning up.

To approve, type: `approve change P-039`.
