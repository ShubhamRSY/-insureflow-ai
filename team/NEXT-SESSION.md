# Next session

## Freeze for the T-128 hold-out (D-162), re-recorded 2026-11-05 after P-084 (D-165) — read this first

First recorded 2026-11-04 (code e1169ddc, scope-v7); re-recorded by the orchestrator on 2026-11-05 after T-132 (P-084) merged, before any T-128 file or gold exists (no SUB-550–581 in simulation/inbox or gold-set). P-083 (D-164) was dropped and never merged. Any byte change below reopens the freeze.

| Item | Value |
|---|---|
| Branch / worktree | `pilot-integration` / `insureflow-integration` (merged into `ai-team` 0358eec7; both pushed) |
| Code commit | `1ddae83c9b3755a6b9c4ffe383347f17251ebb01` (T-132 P-084 after @model-risk APPROVE, check-T-132.md) |
| `PROMPT_VERSION` | `392b9ce3c1af` (3,257 bytes) |
| `llm_extract.py` sha256 | `90ed677226c174b05c2f94f9293637a1604c18f70b63cb584cad761a8ce2eaa4` |
| Scope detector | **scope-v8** (P-084); `scope.py` sha256 `645ff5e1d3a5d21434f6afdbad7a7a7090867426b1d194733532bb64aea4b111` |
| `prepare.py` sha256 | `161914cbc56d6c9ed83219179c484b62b40dcc30703b7c560f0adb88edd00196` |
| `package.py` sha256 | `d9d0edb87817124eda88a900116ed4361ac5ab4c02fafd53ea865f9ae9e41f6f` |
| `sources.py` sha256 | `3ef093883c1d36d2f6949b137401c939618bde1e927b337800e283d2109d411b` |
| `workbench.py` sha256 | `5e0b2d88e89f91a870ab85ebafe6a6d4ac3076e8e2718bf2a96b35b4966fe9d1` |
| `smoke_readers.py` sha256 | `6e83bb523769c9110fc94cd471f9b4743fd663bccc279cecd3280a8e44409b09` |
| Scorer v11 sha256 | `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` |
| Lint sha256 | `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` |
| C2 counter v2 sha256 | `a57010b0796e7f88ce283375b2a3e6cde338d79c99fd79eab64f49a3ad63085a` (D-141) |
| Counter notes (M1 rule, D-158) sha256 | `3e99ce9e2ff0f791da755ed76c3bbee5fb739e669b5addb1490f90c19e5a2cd1` |
| T-128 gold manifest sha256 | `307e6fec738d6132eeca82a91472d1ca6dfaf052dd638fd2931063283db8e0ff` (`deliverables/senior-underwriter/T-128-gold-manifest.sha256`: 32 gold cards + T-128-routes.md; frozen 2026-11-05 after @model-risk look-again APPROVE, T-128-build-check-2.md; D-166) |

## 2026-11-03 (third part): T-129 merged — read this first
- P-079 (D-155), P-080 (D-156), P-081 (D-157) built as T-129; @model-risk REJECT (H1–H3) → fixed (D-159) → look-again APPROVE WITH CHANGES, no High. Merged into ai-team; pilot-integration pushed. Scope detector **scope-v6**; PROMPT_VERSION unchanged `392b9ce3c1af`.
- Dev re-check 12 files: SUB-510/513/527/529 shapes stay in scope; SUB-475, 533–537 shapes and a highway second address go to manual intake. scope-v5 → v6 over 365 folders: 0 loosened; SUB-533 and SUB-219 (D-160, known gold difference) stricter. Quick-17: 0 differences.
- Demo SUB-133: resolve → confirm → approve (operations acknowledged) → sent → quote, 0 live calls; guide Demo A restored.
- Next: T-128 hold-out (SUB-550–581) is planned only; before building, freeze code/prompt/scope-v6/scorer/lint/counter in this file. M1 rule (D-158) in count_ops_gate_v2-notes.md. Backlog B-523, B-524.
- Next free: P-082, T-130, D-161, B-525.

## 2026-11-03 (second part): T-121 run and memo — read this first
- T-121 run once (`20261103T151602-99173`), scored once with v11 and count_ops_gate_v2 (D-154). Met: 0 leaks, recall 12/12 (words-only 534–537 4/4), 0 false completes, 0 unsafe routes, conflicts 6/6, C3 0, silent error rate 0. Failed, all from SUB-510/513/527/529 (P-077 Part B "number of locations not clear"): false manual intake 4/20, near-misses kept 1/3, route 16/20, fields 16/20, C2 v2 4 counted, C4 present 16. Results `deliverables/ai-engineer/evals/SUB-510-541-results.md`.
- @model-risk T-027 memo: **KEEP** (`deliverables/model-risk/T-027-memo-T-121.md`). H1 B-518 (Part B; loosening, needs a P-### from @user), H2 B-519 (A3 misses SUB-533; stricter-only P-###). Lift needs both fixed, a check with no High, and a fresh 20+12 hold-out (>= 2 SUB-533-shaped, >= 2 highway addresses, a C2/C4 rule for manual-intake files set before gold).
- Demo (D-152): SUB-133 resolve step added; the file still ends at "the file is not complete" (B-522). Replay 0 live calls; screenshots retaken. Guide Demo A rewritten.
- Next free: P-079, T-128, D-155, B-523.

## Freeze 2026-11-03 for the T-121 hold-out (read this first)

Recorded by the orchestrator in the Claude Code session, 2026-11-03, before any T-121 file or gold exists. Any byte change below reopens the freeze.

| Item | Value |
|---|---|
| Branch / worktree | `pilot-integration` / `insureflow-integration` |
| Code commit | `8baa00a43abcc77ea76f511de99c8e3b6ab33ab7` (pipeline code identical to `f1a5cf6`, P-077 A+B; only the dev quick set changed) |
| `PROMPT_VERSION` | `392b9ce3c1af` (3,257 bytes) |
| `llm_extract.py` sha256 | `90ed677226c174b05c2f94f9293637a1604c18f70b63cb584cad761a8ce2eaa4` |
| Scope detector | scope-v5; `scope.py` sha256 `79f4f7f70c6b0eaba93b8ffe9348a3a1c773f4677656a80d02c37b9da9694c68` |
| `prepare.py` sha256 (Part B) | `c7afd3549e20a8d0b73e5b8b3874d6db7e503415e99d8e2e5576209a50e25d63` |
| Scorer v11 sha256 | `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` |
| Lint sha256 | `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` |
| C2 counter v2 sha256 | `a57010b0796e7f88ce283375b2a3e6cde338d79c99fd79eab64f49a3ad63085a` (D-141) |
| T-121 gold manifest sha256 | `8ba4a9f3779d7e34b8ec5a6d0b022ebb639310de08462ef681beda5c0d3fea7f` (gold frozen 2026-11-03; T-121 not run) |

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
- Quick-15 on `ai-team` code (finished 2026-10-31, real ClamAV): with vs without P-078 **0 differences** over 15 files; 0 failed calls; 0 model calls needed (5 from cache, 10 manual intake by scope-v4, same as pilot-integration). The Mac slept during the run; one earlier run was stopped after Docker stopped answering.
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
