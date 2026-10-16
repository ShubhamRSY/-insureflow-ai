# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `65bf6b9` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** `.venv` there is a symlink to the main folder's venv. The main folder `-insureflow-ai-1` stays on `feat/gcp-infrastructure` with the user's uncommitted work: never touch it. Check `git branch --show-current` says `ai-team` before work.
- **Run every pipeline command with `.venv/bin/python`.** Score files are written only with `--write`; re-scores use `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`. Self-checks run with no argument.

## Where we stopped (D-102)

- **Nothing built, 0 model calls, no code change.**
- **T-103 root cause** (`deliverables/ai-engineer/analysis/T-103-root-cause.md`, saved replies only): 49 non-hit marks = OCR 13, check 12, scorer 5, gold convention 19, extraction 0, prompt 0. The model did not misread any document.
  - Operations 7/20: 11 misses are wording-only (v4 "every gold word"; T-103 gold averages 17 words vs 7.5 on dev); the P-047 check flagged 0 of 20 because it compares only the cited line against a closed list.
  - SUB-170: values dropped in `accept_field` (`llm_extract.py:417-507`) by the per-field OCR floor (0.50, lowest word of the quote); date "3/1/27" unread (4-digit years only).
  - SUB-159–161: OCR garbled the date line (page conf 0.56–0.73); 159/161 would stay incomplete anyway (extras rule fires on "restaurant"/"kitchenware").
  - SUB-172: per-location values cited from the application, not a schedule file, so they became false conflicts. SUB-163: a " ... " quote join fails the newline-only matcher. A trailing period flags an exact copy as reworded (SUB-158 status).
- **Gold rules for all future gold** (D-102 item 2, in `deliverables/senior-underwriter/operations-gold-rule.md`): empty field = `not in documents`; "hold" is a status, never a route.
- **P-055 pilot scope** drafted by @pm (`deliverables/pm/proposal-P-055.md`), not built. @model-risk: **ACCEPT WITH CONDITIONS** (`deliverables/model-risk/scope-P-055.md`): H1 the scope was drawn after seeing T-103, so T-103 is not gate evidence (even with the 5 out-of-scope files removed, operations 6/15 and loss runs 5/9 fail); the criteria, the open questions and an in-scope-to-manual ceiling must be fixed in writing before new gold. H2 detection measure: 100% detection per criterion, correct reason on the card, fail closed, leakage counts provisional route / suggested carrier / "complete — review pending" / enabled send, and the detector in the model inventory (Tier 2, versioned). Mix: 20 in-scope + 12 out-of-scope (D-020 says 20, so 32 needs the user's word or a separate detection set).
- **Stronger-model plan** (`deliverables/ai-engineer/analysis/T-103-stronger-model-plan.md`): Sonnet-class on the Anthropic API (paid, needs D-011 lifted; ~$0.013/file, $0.26 for 20, prices from memory, **unverified**) or free openai/gpt-oss-120b on Groq (weaker in D-084). The author expects it **unlikely to move the gate** (model class 0 marks); check fixes are the better lever. Needs a user decision only (dev comparison like D-084).
- Self-checks at wrap-up: llm_extract, prepare, intake, package, workbench, points all ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-055**: open questions: do scanned carrier loss runs (SUB-159–161) count as "scanned application"? Does a multi-location schedule count (dev SUB-145 would match)? Mixed-language rule. The ceiling on in-scope files sent to manual intake by mistake. Then `approve change P-055` or not, after @pm adds @model-risk H1/H2.
2. **Next hold-out size**: 20 in + 12 out (needs a D-020 exception) or 20 plus a separate detection set.
3. **Operations scoring** (B-396 M2): keep v4 "every gold word" (new scorer version) or make the gold shorter and closer to the documents' wording (11 of 13 misses are wording).
4. **Check fixes** to raise as P-### (from the root cause): 2-digit-year dates; OCR floor on the lowest word of the whole quote; " ... " quote join; trailing-period reword flag; per-location values outside a schedule file.
5. **Stronger-model dev test**: run it or not; paid (lift D-011 for one run, check prices) or free.
6. Still open from D-101: dev gold to R17 (B-392 M4); GCP branch and `5ceeef8` roles (B-388); SUB-161/167/173 ambiguities for @head-of-underwriting.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | Approved P-### fixes for H1 (field floor) and H2 (route), then a new frozen hold-out, gold first (D-102 gold rules; if P-055 scope applies, its conditions in scope-P-055.md), smoke first, .venv, paced, scorer v4 `--write`, run and scored once: all 9 fields at 9/10, 0 false completes, 0 unsafe, route ≥18/20. T-103's score stays as published. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the worktree and branch (`ai-team`); user decisions 1–3.
2. @pm revises P-055 with @model-risk H1/H2 and the user's answers; @ai-engineer-assistant writes the check-fix P-### (decision 4) from saved replies, no model call.
3. Decisions 5–6.

## For the AI Engineer

- Pending: P-055 (pilot scope, draft, @model-risk ACCEPT WITH CONDITIONS); check-fix P-### not yet written.
- Latest scores (T-103 hold-out SUB-154–173, v4, `3557e4a`): 0 unsafe, 0 false completes, route 16/20, operations 7/20, only named_insured at 9/10; T-027 KEEP.
- Top failure to fix next: operations scoring/gold wording (11 of 13 misses), then the OCR word floor that empties scanned-application fields (SUB-170).
