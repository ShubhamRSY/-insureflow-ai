# Hold-out score review — SUB-107 through SUB-126 (T-027)

- Reviewer: @model-risk, 2026-10-15. Decisions: D-013, D-084, D-087.
- **9 of 9 extracted fields scored; claims not read; loss runs = date only.**
- Synthetic. Not a production approval. No send is authorized. P-039 (D-087) is an approved proposal, not a production approval.

## 0. Run record (checked)

- Commit `178aa28`; `git diff 178aa28 -- underwriting_pipeline deliverables/senior-underwriter/gold-set simulation/inbox` is empty, score file `uncommitted: 0`. Gold committed with the submissions before any extraction.
- `.venv/bin/python` 3.14.6, pdfplumber 0.11.10, openpyxl 3.1.5, pytesseract 0.3.13, tesseract 5.5.2 (`SUB-107-126-run-env.txt`). Model qwen/qwen3.8-27b on Groq, paced 55 s.
- Run `20261015T111434-28912`: 20 model calls, 0 from cache, 0 call failed, 35,205 tokens. Frozen scorer `eval_holdout_107.py`, run once by the run owner; I did not re-run it or edit any score file.
- No key string in the score, env, log or my script (grep for key patterns: none).

## 1. Per field (frozen scorer output)

Rate = (hit + hit needing review) / (hit + miss); not-credited and flagged are neither (same convention as SUB-087–106). D-013 floor = 9/10.

| Field | Hit | Hit (NR) | Miss | Not cred. | Flagged | Rate | D-013 |
|---|---|---|---|---|---|---|---|
| named_insured | 19 | 1 | 0 | 0 | 0 | 20/20 = 100% | Meets |
| premises | 0 | 0 | 20 | 0 | 0 | 0/20 = 0% | Below (see M1) |
| effective_date | 18 | 0 | 1 | 1 | 0 | 18/19 = 95% | Meets |
| operations | 17 | 0 | 3 | 0 | 0 | 17/20 = 85% | Below |
| sales | 17 | 1 | 2 | 0 | 0 | 18/20 = 90% | Meets |
| tiv | 19 | 0 | 1 | 0 | 0 | 19/20 = 95% | Meets |
| construction | 20 | 0 | 0 | 0 | 0 | 20/20 = 100% | Meets |
| year_built | 17 | 0 | 3 | 0 | 0 | 17/20 = 85% | Below |
| loss_runs (date only) | 10 | 0 | 2 | 8 | 0 | 10/12 = 83% | Below; 2 dates taken from a no-known-loss letter (H1) |
| conflict (check) | 11 | 1 | 7 | 0 | 1 | 12/19 = 63% | — |

**5 of 9 extracted fields meet the D-013 floor; 4 do not (premises, operations, year built, loss runs).**

- Silent error rate 4/180 = **2.2%** (operations 114, 124; loss runs 112, 123). Automation rate 105/180 = **58.3%** (dev check on the same model, SUB-087–106: 1.7% / 77.2%).
- Status accuracy **16/20 = 80%**. All 4 misses are **false completes**: SUB-111, 112, 123, 125 (gold incomplete, system complete). 0 false incompletes. (SUB-087–106 had 0 false completes.)
- Carrier-route accuracy **12/20 = 60%**, 0 call failed. Method: `deliverables/model-risk/route_holdout_107.py` (copy of the 087 script, ids changed only), `env -u LLM_API_KEY`, network replaced by a raise, temp copy of the cache. 0 cache misses, 0 unread files (all scans, including the sideways and upside-down ones, were read). `git status`, token-log mtime, workbench.html, team files, deliverables `*.jsonl` and the three outboxes unchanged before vs after.

| Submission | Expected | Got | Note |
|---|---|---|---|
| 107, 120 | carrier_a | no_match | "readable class on no carrier list" for a bookkeeping office (M2) |
| 111 | hold | senior_referral | sales conflict not raised; file called complete |
| 112 | hold | senior_referral | Spanish letter read as loss run (H1) |
| 114 | no_match | hold | missing information |
| 116 | carrier_b | senior_referral | contractor AG:38 referral |
| 123 | hold | **carrier_a** | Spanish letter read as loss run (H1) |
| 125 | hold | **carrier_a** | effective-date conflict not raised (H2) |

Hits: 108, 109, 110, 113, 115, 117, 118, 119, 121, 122, 124, 126.

## 2. Comparison with D-013 and the veto condition

T-027 veto resolves when SUB-107–126 is scored once, gold first, in a checked .venv after smoke_readers passes, **with all 9 fields at 9/10 or better**. Process conditions: met. Score condition: **not met** (premises 0%, operations 85%, year built 85%, loss runs 83%). Even with the premises comma read generously (M1), premises is 16/20 = 80%. **The T-027 veto stands.**

Progress against the SUB-087–106 hold-out (gpt-oss-120b, 1 of 9 at floor): now 5 of 9, no failed call, no unread scan. Real improvement, not yet production quality.

## 3. High findings

**H1 — A Spanish no-known-loss letter is read as a carrier loss run.** Owner: @ai-engineer-assistant.
- Evidence: SUB-112 and SUB-123 `loss-runs.md` are "Carta de pérdidas" letters from the prior agent ("segun el solicitante", "Carta firmada por el agente anterior") with a "Valued through: 2026-09-30" line. The system stored `loss_run_valued_through = 2026-09-30`, unflagged (both are silent errors), marked both files complete, and routed SUB-123 to **carrier_a** and SUB-112 to senior_referral. Gold: incomplete, hold for carrier loss runs. All five English no-known-loss letters (108, 114, 115, 121, 126) were correctly not credited.
- Why High: D-013 "a loss-run date is never guessed" and D-014 (a no-known-loss letter is not a loss run). A clean-looking file without a carrier loss run reaches a carrier route.
- Resolve: the no-known-loss rule recognises Spanish letters (e.g. "carta", "sin reclamos", "agente anterior", "según el solicitante"), as an approved P-### change, with tests on 112/123 shapes; scored on the next hold-out, not by editing this one.

**H2 — Four false completes; two route to a carrier.** Owner: @ai-engineer-assistant (rules), @senior-underwriter (confirm expected behaviour).
- Evidence: SUB-111 (sales 2.1M vs 2.4M not raised as a conflict; sales flagged needs review, file still complete), SUB-125 (effective date 2027-08-01 vs 2027-09-01 not raised; date flagged needs review, file still complete, route carrier_a), SUB-112 and SUB-123 (H1). Every earlier hold-out failure was in the safe direction (held); this run has 4 in the unsafe direction.
- Resolve: (a) a field flagged needs-review on a required field keeps the file incomplete/held, or the team records that it does not and why; (b) a conflict-detection check on the 111/125 shapes. Both as approved P-### changes, scored on the next hold-out.

## 4. Medium / Low (backlog, one line each)

- **M1** (@senior-underwriter, @ai-engineer-assistant): premises 0/20 is mostly a format mismatch — source and extraction write "Austin TX 78757", gold writes "Austin, TX 78757", and the frozen `address()` compares exactly. Published score stands (D-020); for the next hold-out, fix the comparison (commas/"Ste"/"Suite") before any gold exists. Comma-insensitive recount: 16/20 (nulls 113, 115, 117; 119 picked one side of an address conflict).
- **M2** (@software-engineer, @head-of-underwriting): bookkeeping office (107, 120) routed no_match with a restaurant-evidence note; class lookup rule, not the model.
- **M3** (@ai-engineer-assistant): automation 58.3% vs 77.2% on the dev check; effective date (45%), TIV (50%), year built (50%) and loss runs (50%) are mostly flagged-correct values. Find out why before the next run.
- **M4** (@ai-engineer-assistant): operations silent errors on 114 ("Apartments") and 124 (multi-location BBQ) — short or partial operations stored unflagged.
- **L1**: run log records 1 rate-limit (OTPM, max_tokens 1095 > 1000) failed attempt while every file shows "attempts 1"; reconcile the counter.
- **L2**: SUB-107-126 score, env and log files are untracked; commit them unchanged at wrap-up.

## 5. Acceptance criteria (T-027)

| Criterion | Evidence | Met |
|---|---|---|
| PDFs pdfplumber, Excel openpyxl, scans OCR | env record; 0 unread in rebuild incl. sideways/upside-down scans | Yes |
| Structured JSON with citation and confidence | cached replies carry source, quote, confidence per field | Yes |
| Confidence < 0.75 dropped | `MIN_CONFIDENCE = 0.75` (P-025 scan band stored-and-flagged as decided earlier) | Yes, as decided |
| Key from environment, not in repo | grep: no key in outputs | Yes |
| Hold-out score from a successful call | 20/20 called, 0 failed | Yes |
| Veto condition: all 9 fields ≥ 9/10 | 5 of 9 | **No** |

## 6. Decision

**T-027: OBJECTION stands (production veto not lifted).** Resolves when: H1 and H2 are closed by approved changes with tests, the M1 address comparison is fixed before gold, and a new 20-file hold-out (gold first, checked .venv, smoke_readers first, scored once) has all 9 fields at 9/10 or better with 0 false completes.
