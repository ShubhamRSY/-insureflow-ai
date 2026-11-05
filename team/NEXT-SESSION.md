# NEXT-SESSION — read this first (written 2026-11-05 at /wrap-up)

Branches: `pilot-integration` (worktree `insureflow-integration`) merged into `ai-team` (worktree `insureflow-ai-team`), both pushed. Wrap-up commit (ai-team): `4be9a972`. The GitHub repo is **PUBLIC**. Never touch the main folder `-insureflow-ai-1`. Python: `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team/.venv/bin/python`. Model: qwen/qwen3.8-27b on Groq from the shell's LLM_* variables, paced 55 s; never the repo `.env`.

## Where we stopped
- P-082 (scope-v7, D-161) and P-084 (scope-v8, D-165, stricter only) merged after @model-risk APPROVE. P-083 (D-164) was dropped and reverted; B-525 stays open.
- T-128 hold-out SUB-550–581 built (rewritten after build check H2), gold frozen (manifest `307e6fec…e0ff`), run once (`20261105T012147-15550`) and scored once: **every T-121 gate PASS** — leakage 0/12, recall 12/12, false manual intake 0/20, false completes 0, unsafe routes 0, route 19/20, fields ≥ 19/20, C2 0, C3 0, C4 19/19, planted-conflict recall 8/8 (D-166). Results: `deliverables/ai-engineer/evals/SUB-550-581-results.md`.
- @model-risk T-027 memo: **LIFT, conditional** (D-167, `deliverables/model-risk/T-027-memo-T-128.md`). Not a go-live decision.

## Frozen build (the D-167 lift holds only for this; any change needs a new @model-risk check)

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

## Approved and not built
- None. (P-084 is built; P-083 dropped.)

## Pending decisions for the user
1. **Repo visibility**: the GitHub repo is PUBLIC. Older published score files contain the Groq org id (an id, not a key); T-128 files were masked. Options: make the repo private (recommended), or accept as is. Rewriting published files is not allowed (D-020).
2. **Go-live / pilot**: @model-risk lifted its veto (conditional, D-167); go-live is your call and the @responsible-ai T-082 veto still stands.
3. **B-530 / B-531** (must close before any send-enabled mode, D-167): 562 cooking conflict cites wrong lines; "complete — review pending" shown with an open conflict. Each is a code change: a P-### for you.
4. **B-525** (single FM / State Highway / County Road / I-35 Frontage premises → false manual intake): revisit with pilot data (your D-165 words), or a new P-###.
5. **B-529** ("Copy" in an insured name makes a clean loss run read as negated): a loosening, own P-###.
6. **B-532**: a lint check for stray topic words in gold Conflict lines (new lint version; v11 and the frozen lint stay unchanged).

## Open vetoes and what resolves each
- @model-risk T-027 (production): LIFTED, conditional (D-167). Reinstated by any change to the frozen build, use outside Texas BOP criteria 1–4, missing C6 monitoring (≥ 60 reviewed files, stop rules), or a send-enabled mode before B-530 and B-531 are closed.
- @responsible-ai T-082 (fairness): stands; resolves per its own memo (not touched this session).

## First 3 tasks next session, in order
1. Your decisions 1–3 above (repo visibility, go-live, P-### for B-530/B-531).
2. If approved: fix B-530 and B-531, then @model-risk check (the frozen build changes, so the lift conditions require it).
3. C6 monitoring plan (≥ 60 reviewed files, stop rules) for the pilot, written before any pilot file is processed.
