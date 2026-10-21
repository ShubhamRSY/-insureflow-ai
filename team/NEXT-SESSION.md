# Next session

Written 2026-10-20 by the orchestrator at wrap-up (session 4 of the day). Wrap-up commit: `c1ff2a4` on `ai-team`, pushed to `origin/ai-team` (private). Previous: `9f9532e`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** New hold-outs are scored with `eval_holdout_v9` (v7/v8 frozen). Scorer v10 exists but is **blocked** (below). Gold check: `HOLDOUT_IDS=<a-b> .venv/bin/python underwriting_pipeline/ai/eval_holdout_v9.py --check-gold`.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only via `/opt/homebrew/opt/python@3.14/bin/python3.14`; `deliverables/software-engineer/T-105-demo/snap.py` runs under it.


## Where we stopped (post-freeze, 2026-10-21)

- **P-068 frozen (commit `e03dfcc`)**: scorer v10 approved by @model-risk (fourth pass, no High). `underwriting_pipeline/ai/eval_holdout_v10.py` sha256 `ffd1afdda55fd761f21deb2f6ede49b9294d7517bed6500ccd9520eba361302b` (1313 lines). Slot-based operations matching from `operations-gold-rule.md` (T-114 table), clause-scoped negation, fail-closed; H9/H10 closed; 37-case H1 block 0 FP/0 FN; v10 ops 12/20 on T-108 (gains SUB-207/220, 0 regressions, non-ops byte-identical to v9).
- **B-446 resolved (same commit)**: `underwriting_pipeline/ai/llm_extract.py` sha256 `e72d092acce2aa484d9eca89a92002c1789a8dbc29c1c64e625fe8f03961c606` — text-field scan gate uses cited-words average per P-056(b); @model-risk APPROVE, 20k-case fuzz 0 unsafe changes, `llm gate ok`.
- **Lint updated**: `deliverables/senior-test-engineer/lint_holdout.py` sha256 `d21b92cb3aabd6bb8ac2948fd40e55b5e4a7880a6808838c19190815080b936a`, v10 default, 37-case H1 block.
- **Docs added**: `deliverables/ai-engineer/analysis/T-115-v10-slot-rework.md`, `deliverables/senior-underwriter/T-114-slot-list-sub127-173.md`, `deliverables/ai-engineer/evals/P-068-dev/` rescore evidence. Empty stub `tests/test_concurrent_writes_proc.py` deleted.
- **T-108 dev re-score (held)**: ops 12/20, route 18/20, 0 unsafe/false-completes/leaks/call_failed. No hold-out has been scored with v10 yet.

## Pending decisions for the user

1. **Next hold-out (20+12), gold-first with operations slots.** Build from a fresh set (next after SUB-206-237), write gold cards in T-108 corrected format with `- Operations items:` slots per `operations-gold-rule.md`/T-114, create plan JSON in `deliverables/senior-test-engineer/`, run `lint_holdout.py <plan>` and it must PASS before freeze; then run once with `eval_holdout_v10.py` and record scores. This is needed to advance the T-027 veto path.
2. **Non-slot operations items (8 of 20).** Either add a `business_type` slot or relax free-text rule via a proposal; reported in T-115.

## First task next session

1. Build next hold-out gold (20 in-scope + 12 out-of-scope), gold-first with operations slots, plan + lint PASS, then score with v10 once; update T-027 tracking. If lint fails, fix before scoring.
