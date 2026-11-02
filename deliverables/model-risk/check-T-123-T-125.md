# @model-risk independent check: T-123, T-124, T-125 (2026-11-02)

Scope: the uncommitted diff on `pilot-integration`, reviewed against the acceptance criteria only. I read no author messages.
I made no model calls, did no hold-out runs and edited no code. Every run used a scratch copy of the worktree (D-069); the real worktree did not change because of my runs.
Python: insureflow-ai-team/.venv.

## Verdicts

| Task | Verdict | High findings |
|---|---|---|
| T-123 C2 counter v2 | **APPROVE WITH CHANGES**: freeze before gold (M1) | none |
| T-124 Quick-15 refresh | **APPROVE** | none |
| T-125 Pilot blocks files with no scanner | **APPROVE** | none |

None of these is a production approval. These verdicts also do not approve the T-121 gate result or any hold-out.

## Evidence (recomputed)

**T-123**
- v1 `count_ops_gate.py` sha256 = `f942010d…9aa1`. This matches the acceptance criteria. v1 is unchanged.
- v2 imports only stdlib (argparse, json, re, sys, pathlib). `--self-check` → SELF-CHECK PASS.
- The self-check covers each required shape:
  - no reason
  - reworded only
  - policy only
  - empty "may be missing:"
  - unknown text
  - address note
  - named items
  - generic plus named
  - all three cooking reasons (`REASON_COOKING`, `_COPIED`, `_CONFLICT`)
  - an open operations conflict
  - a resolved cooking conflict
  - a sales conflict
  - a hit is never silent
  - the generic text is reported
- C4 is unchanged: the thresholds are still 18 and 15, and the code matches v1 line for line.
- I checked where reason texts come from:
  - The operations-row reasons are built by code (`prepare.OPS_MISSING`, `REASON_COOKING*`, `llm_extract.REASON_*`). They are never free text from the model, so a model cannot write a reason that passes the check.
  - Conflict resolution values in the code are only `unresolved` and `resolved`. Anything not equal to `resolved` counts as open, which fails closed.
- v2 sha256 now: `a57010b0796e7f88ce283375b2a3e6cde338d79c99fd79eab64f49a3ad63085a`. It is **not yet recorded** in DECISIONS/TASKS. No T-121 gold exists yet.

**T-124**
- QUICK has 15 unique files, all in SUB-017–076.
- With PILOT_MODE and CLAMAV_HOST unset, I ran `scope.detect(read_folder(...))` on each file. All 15 are `in_scope=True` under scope-v4.
- `regression_dev.py --self-check` → ok.
- Mutant test: I swapped SUB-037 for SUB-029. The self-check failed with `quick-set files that never reach the model: ['SUB-029']`.
- The scope gate is the only route to manual intake (`prepare.process_submission` line 1355), so the self-check tests the same condition the pipeline uses.

**T-125**
- I ran the `sources.py` self-check → ok. `tests/pipeline/test_pilot.py` → 12 passed.
- Mutant test: I disabled the `_pilot_without_scanner()` guard. Both the sources self-check and `test_b485…` failed.
- The guard runs before the `.zip`/`.eml` unpack. The unpack (`app/intake.unpack_folder`) is only reached after the guard.
- Under the guard, only the raw bytes are read, to compute the manifest sha256. No file is parsed and nothing is unpacked.
- Fail-closed cases:
  - An unknown `PILOT_MODE` raises.
  - A blank `CLAMAV_HOST` counts as no scanner.
  - Dev mode (pilot off) is unchanged, as the self-check asserts.
- The screenshot shows:
  - the scanner reason first in the manual-intake list
  - every file listed under "Not read" with its reason
  - a "What's new" line in `WHATS_NEW` (2026-11-02, B-485, D-143)

## Findings

### High
None.

### Medium (backlog, one line each)
- **M1 (T-123, required before any T-121 gold):** record v2 sha256 `a57010b0…3085a` in DECISIONS/TASKS and commit it. Any edit to v2 after that voids the counter for T-121.
- **M2 (T-123):** a cooking reason or any "may be missing: X" counts as specific even when the scorer's miss is a different item (for example, a liquor miss with a cooking-copied reason). The counter cannot see which item gold missed. The T-121 memo must state this limit.
- **M3 (T-124):** the new quick set has no Excel, scan, Spanish or handwritten file. Reader/OCR regressions now show only in the tests and the full 60. Also, the T-124 quick scores are a new baseline and are not comparable with earlier quick-15 runs.
- **M4 (T-125, UI):** on the blocked card, the send refusal ("manual intake (application text layer not known; document language not clear)") and the "Scope check" line do not name the missing scanner. Those scope reasons are side effects of nothing being read. The refusal text should lead with the scanner reason (D-065 item 2).

### Low
- L1 (T-124): SUB-018/SUB-023 are commented "scanned PDF", but `scan.pdf` has a text layer (293/304 chars, 0 images) and is read as typed. Fix the comment.
- L2 (T-123): the report truncates "not counted" text to 60 characters. Unknown text is shown but can be cut off; print it in full for silent rows.
- L3 (T-123): the cooking shape matches by prefix only. Any future code reason that starts with "cooking" would count as specific. Pin it to the three known constants.
- L4 (T-125): `app/intake.py` CLI `scan_inbox` still unpacks zips in memory with no pilot or scanner check. It is not on the pipeline path, but guard it or document it as dev-only.
- L5 (T-125): the screenshot sandbox shows "manifest check: FAILED" (the test run has no manifest). This is cosmetic in the demo image.

## What resolves each item
- T-123 M1: record the hash and commit it before any T-121 gold. This is the only condition on the T-123 approval.
- There are no High findings, so no veto is in force. M2–M4 and L1–L5 go to the backlog.
