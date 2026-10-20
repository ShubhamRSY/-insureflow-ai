# Next session

Written 2026-10-20 by the orchestrator at wrap-up (session 4 of the day). Wrap-up commit: `c1ff2a4` on `ai-team`, pushed to `origin/ai-team` (private). Previous: `9f9532e`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** New hold-outs are scored with `eval_holdout_v9` (v7/v8 frozen). Scorer v10 exists but is **blocked** (below). Gold check: `HOLDOUT_IDS=<a-b> .venv/bin/python underwriting_pipeline/ai/eval_holdout_v9.py --check-gold`.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only via `/opt/homebrew/opt/python@3.14/bin/python3.14`; `deliverables/software-engineer/T-105-demo/snap.py` runs under it.

## Where we stopped (D-117, D-118)

- **P-066 defect fixed** (commit `e9e5683`). Commit `39b2a46` had deleted `REFUSED_AS` while two uses stayed: every refusal raised `NameError` and the workbench self-check crashed. Restored the dict verbatim from `39b2a46^`; added a workbench self-check that exercises all 7 refusal routes. @model-risk re-checked: **APPROVE, no High**. D-065 item 5 closed with the "What's new" line + screenshots (`ba22ce1`).
- **P-067 defect fixed** (commit `ebd580b`) and its script-mode import (`bc268b8`). The "card reason for a rejected value" path was dead (`prepare.py:1057` skipped the row); fixed under P-067 with a self-check.
- **P-068 (scorer v10) is BLOCKED, dev-only, uncommitted.** The v10 + lint in the working tree differ from the `1da0066` check. @model-risk re-check (2026-10-20): **BLOCK**. H1 the rewritten `ops_items_hit` non-contiguous branch still admits wrong answers as hits (interleaved counts, spanned negation, neighbouring facts; 10/28 adversarial false positives). H2 the synonym list is overfit to T-108 and `operations-gold-rule.md` has no synonym list (both D-117 conditions). Fix list is in that check and in standup 2026-10-20 (4).
- **Uncommitted working-tree files held on purpose** (do not assume they are in git): `underwriting_pipeline/ai/eval_holdout_v10.py`, `deliverables/senior-test-engineer/lint_holdout.py`, `deliverables/ai-engineer/evals/P-068-dev/`, `tests/test_concurrent_writes_proc.py` (empty stub, unknown origin). The scorer v10 must not be used for any hold-out.
- **Committed this session:** frozen scorer v9 baseline (`6f959a9`, was untracked — model-risk P-068 M3); corrected T-108 gold copy, dev only (`69ad89b`); T-110 v9 re-measure + RUN-RULES (`1f4fbb3`); team records (`6d99ca8`, `c1ff2a4`).
- **B-191 concurrent decision-log writes: Partly done.** Cross-process `fcntl.flock` + 8-thread/2-process tests pass (`tests/test_concurrent_writes.py`, `_mp.py`); item 2 (failed write never silent) not shown — the lock failure is still swallowed (`workbench.py:592`); @model-risk M/L.
- **@pm `deliverables/pm/pilot-readiness.md` updated:** C1–C8 now 0 Met / 4 Partly / 3 Not met / 1 Not verified. B-190 (SSO) Open, B-191 Partly done.
- Demo replay re-checked this session: SUB-127/129/133/184 all render, 0 live calls (temp copy, D-069).

## Self-checks at wrap-up

- ok: `prepare.py`, `package.py`, `workbench.py`, `points.py`, `intake.py` (no args).
- **FAILED: `underwriting_pipeline/ai/llm_extract.py`** (no args). Pre-existing defect B-446: its self-check expects a 0.29-cited-word case to be kept, but `SCAN_FLOOR` is 0.50. Needs an approved proposal to fix; not fixed this session.

## Approved, not built

| Proposal | Task |
|---|---|
| P-067 (loss-run scan dates) | built (`ebd580b`); only its card-reason half is verified working |
| P-068 (scorer v10) | built as dev; **blocked by @model-risk**; re-work then re-check |
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-068 re-work.** Approve fixing v10 to @model-risk's block list (spanned-match negation/look-again, counts as one token, synonym list into `operations-gold-rule.md`), or abandon v10 and keep v9. Any change to the scorer needs the exact words `approve change P-###` in-session (D-017).
2. **B-446.** `llm_extract.py` self-check fails at HEAD. Fix needs an approved proposal.
3. **B-191 item 2** and **B-190** (SSO/audit): @software-engineer builds before any pilot (D-057).
4. Still open: B-440 (locations only in the email body), P-056 (a) month-first dates, B-402, B-398/B-404, B-416/B-417, B-429.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | KEEP. B-432 fixed on dev (checked). Still needs B-433 fixed on dev with a check, an approved scorer re-frozen (v9), and a fresh 20+12 hold-out, gold first with the lint PASS, run once and scored once, meeting every gate: 0 leaks, 100% recall, all fields ≥ 18/20, 0 false completes, 0 unsafe. v10 is blocked; do not freeze it. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. User decisions: the P-068 re-work (or abandon), B-446, and the T-027 path.
2. If the user says go: fix v10 to the block list and re-request the @model-risk check; only on its APPROVE, freeze code + v9/v10 and hashed.
3. @software-engineer: B-190 and B-191 item 2 (failed write → plain refusal + D-065 screenshot); keep the demo from `deliverables/pm/demo-guide.md` (`run-demo.sh`, 0 live calls) unchanged.

## For the AI Engineer

- Pending proposals: P-067 (built); **P-068 open and BLOCKED** — needs your decision to re-work or abandon.
- Latest scores (dev, T-108, scorer v10, on the blocked scorer): operations 19/20, loss_runs 17/20, tiv 19/20, conflict 15/20, status 15/20, route 18/20; 0 unsafe, 0 false completes, 0 leaks, 0 call_failed. v9 baseline: `SUB-206-237-holdout-v9-cache-rescore`.
- Top failure to fix next: scorer v10's non-contiguous operations match (P-068 H1), plus B-433 real misses (loss_runs SUB-209/211/225 OCR). Neither can lift the T-027 veto while v10 is blocked.
