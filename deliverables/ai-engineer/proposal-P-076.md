# P-076 — Operations is never auto-accepted; always flagged and acknowledged before send (C1 of T-027 gate)

- Author: @ai-engineer-assistant, 2026-10-26. **Draft for @user to read. Not approved, not built.** Development data only. Not a production approval; the T-027 veto stands.
- Raised by @model-risk in `deliverables/model-risk/T-027-operations-gate-answer.md` (D-133) and accepted with conditions by the user (decision 1 = A). This proposal covers **C1 only**. C2–C7 are recorded separately (see below). Per D-017, any code change under `underwriting_pipeline/ai/` needs a numbered proposal and `approve change P-076`.

## Problem
Under the current rules, an operations value can read as "complete" (no needs_review) if the model carries it cleanly and nothing else flags it. The T-027 gate requires that operations is never auto-accepted: every operations value with content must be flagged and acknowledged before any send, in all modes. A policy flag alone is not sufficient without a specific reason in the silent-error count (C2), but C1 is the enforcement in code.

## Change (enforcement only; reuse pilot per-value confirm)
**Location:** `underwriting_pipeline/ai/prepare.py` (last step, after P-074 and P-075: after conflicts, `check_operations`, cooking rule, merge). Also ensure the workbench and send gate consume the same `needs_review` list (they already do via `package.needs_review_ids`).

- **A. Always flag operations when present.** For any `operations` row with a non-empty `value` (after rule-copied line and all processing), set `row["needs_review"] = True`. Do not remove existing specific reasons (P-059/P-075 "operations may be missing: …", cooking conflict reasons). Add a policy note only if no specific item-naming reason exists: `row["reason"] = row.get("reason") or "operations is always checked by the underwriter (T-027/C1)"` (or equivalent). The policy reason is separate from specific reasons for the purposes of C2.
- **B. No change to completeness semantics except status.** A file may still be "complete — review pending"; it is never plain "complete" solely because operations is auto-accepted. The send gate already refuses when unacknowledged needs-review values exist (`package.ack_problem` / `send_to_carrier`). The acknowledgment list must include `operations` whenever flagged (already the case). Reuse the existing pilot per-value confirm path (named_insured/operations are confirmed together as tested in `package.py`).
- **C. Workbench/card.** Show the policy note alongside any specific reason. Add one "What's new" line (date, P-076, D-###). Add a Playwright screenshot of an affected operations row on a temp copy per D-065. @senior-underwriter UI check (High only).
- **D. No change to routing/appetite/sends except the acknowledgment requirement.** `ready_to_route` may still allow a complete — review pending file to routing as today (C1 does not make routing safe by itself; routing safety remains per existing gates). The only new blocker is acknowledgment before send. No auto-decline, no auto-bind.

## Tests / self-checks
- `underwriting_pipeline/ai/prepare.py` self-check: every path that produces an operations value with content leaves it `needs_review=True` (model-carried, rule-copied, merged, scan path). A row with empty operations remains as-is.
- `underwriting_pipeline/app/package.py`: send refused if operations not acknowledged on current run hash (test analogous to SUB-321). Acknowledging operations allows send when other gates pass.
- `underwriting_pipeline/app/workbench.py`: render shows policy note; "What's new" added.
- `pytest tests/pipeline` green. No hold-out files changed.
- No request changes expected (rule in `prepare.py`, not prompt/SYSTEM). If any test shows request changes, stop and report.

## Pre-registered with @model-risk conditions (C2–C7) — recorded now
- **C2 (frozen before gold):** Silent error = scored miss on operations with **no specific** item-naming reason. The C1 policy reason never counts. Counted by a script frozen before T-120 gold; v11 unchanged.
- **C3:** 0 understated hazards (cooking, fryer, hood, pub, contractor class) whether flagged or not.
- **C4:** Operations present ≥ 18/20 and hits ≥ 15/20 under frozen v11 (set now).
- **C5:** All other gates unchanged.
- **C6:** T-120 includes ≥12 files with "Cooking operations: None"-type lines, ≥3 with cooking stated, ≥2 with planted cooking conflicts.
- **C7:** This decision (gate) recorded in DECISIONS.md before any T-120 gold exists. Done in this session per user instruction.

## Approval
To approve, the user types: `approve change P-076`
