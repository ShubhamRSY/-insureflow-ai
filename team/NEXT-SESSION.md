# Next session

Written 2026-10-30 by the orchestrator at wrap-up. Wrap-up commits: `ai-team` `0b9c019`, `pilot-integration` `74c4e85` (fast-forward of branch `p078-security`, worktree `insureflow-p078`). **Not pushed: GitHub reports the repo as PUBLIC** (`gh repo view`: visibility PUBLIC). Push only after @user decides (decision 1).

- Standing rules: budget rule 8 (demo blockers only), D-065, D-069, D-097 plugins, D-129 fast lane. One AI session on this repo. `frontend/` and `.claude/settings*.json` are the user's; never staged.
- **Branch of record: `pilot-integration`** (worktree `insureflow-integration`); it holds T-120 and all decisions up to D-138. `ai-team` is 66 commits behind on pipeline code.
- Python: `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team/.venv/bin/python` (the integration and p078 worktrees have no `.venv`).
- Numbering: next free P-079 (P-077 kept for the scope words-only fix, not yet written), T-123 (T-121 kept for the planned hold-out, not yet written), D-139, B-499.
- T-120 freeze and hashes: see this file at `pilot-integration` commit `d7adb55`; unchanged.

## Where we stopped

- **T-122 (P-078, D-138) security checks** built, reviewed (@senior-underwriter UI APPROVE, @senior-test-engineer APPROVE, each after one look-again) and committed on both branches. Renumbered from P-070/T-121/D-130; @user re-approved as P-078 on 2026-10-30.
- ClamAV: `docker-compose.yml` now uses `clamav/clamav-debian:stable`, which starts natively on arm64. Real clamd: EICAR blocked (plain and inside a zip); scanner down → every file blocked with "the antivirus scanner could not be reached". `CLAMAV_HOST` unset → no scan (`deliverables/pm/demo-guide.md` says to set it).
- Quick-15 on pilot-integration, with vs without P-078: **0 field or status changes**; the 5 files that reach the model hit the same cache keys. 10 of 15 go to manual intake before any model call (scope-v4, "application not identified"), so the quick set barely tests extraction there (B-498).
- Live paced quick-15 on `ai-team` code (with P-078, real ClamAV): **unfinished** at wrap-up: 7 of 15 done, all ok, 0 failed calls, 0 live model calls so far (cache or manual intake). The Mac kept sleeping; one earlier run was stopped after Docker stopped answering. The "without P-078" side was not run.
- Tests: tests/pipeline 93 passed on p078; self-checks 6/6 ok on both branches; pyright 39 → 39.
- P-077 (memo H1 words-only scope rule): no proposal text exists anywhere. C2 counter tightening (memo M2, B-491): not built; counter still frozen `f942010d`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |

## Pending decisions for the user

1. The repo is PUBLIC: make it private and push `ai-team` + `pilot-integration`, or keep both local.
2. P-077: have @ai-engineer-assistant draft the stricter-only words-only scope rule (memo T-120 H1), then `approve change P-077`.
3. B-491: approve a v-next C2 counter (the reason must name the item), frozen and hashed before any T-121 gold.
4. B-498: refresh the quick-15 set so it reaches the model on pilot-integration, or accept 5/15.
5. B-485: block files when `CLAMAV_HOST` is unset (stricter), or keep scanning optional for dev.
6. Merge `pilot-integration` back into `ai-team` (ai-team is 66 commits behind).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production), KEEP after T-120 | P-077 stricter-only scope rule approved and built; dev self-checks incl. near-pass negatives; @model-risk check with no High; fresh 20+12 hold-out (T-121) with ≥ 6 criterion-2 files (≥ 4 words-only), gold first, run and scored once, meeting every gate. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. User decisions 1–3 above; push once the repo is private.
2. @ai-engineer-assistant drafts P-077; @senior-test-engineer drafts the B-491 counter; both frozen before any T-121 gold.
3. Plan T-121 (hold-out) in TASKS.md per the memo's step 4; optionally finish the live quick-15 on ai-team with the Mac kept awake.

## For the AI Engineer

- Pending proposals: P-077 (not yet written). P-078 approved and built (T-122).
- Latest scores: T-120 hold-out (v11, scored once): every field ≥ 18/20, operations C1–C7 met, conflict recall 7/7, route 18/20, 0 false completes; failed: 1 leak and recall 11/12 (SUB-475). Quick-15 with P-078: 0 changes.
- Top failure to fix next: a second location stated only in words is not detected (SUB-475, P-077).
