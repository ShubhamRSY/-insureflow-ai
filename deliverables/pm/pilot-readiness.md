# Pilot readiness — assist-only pilot (T-109d, D-116)

- Owner: @pm. Date: 2026-10-19; updated 2026-10-20 (P-066/B-191). No build, no code change, no run by @pm.
- Source of conditions: `deliverables/model-risk/T-027-assist-mode-pilot.md` (C1–C8, @model-risk).
- Evidence read: that memo; `deliverables/ai-engineer/p-063-p-064-as-built.md`; `team/BACKLOG.md` B-190/B-191; `team/TASKS.md` T-109a–d; `team/DECISIONS.md` D-117/D-118; `deliverables/model-risk/check-P-066-P-067-P-068.md`; a grep of `underwriting_pipeline/app` and `underwriting_pipeline/ai` for assist-only, pilot and correction-log terms (no hits).
- Not a production approval. The T-027 veto stands. Synthetic data only.

## Summary

- C1–C8: 0 Met, 4 Partly met, 3 Not met, 0 Not started, 1 Not verified. (C5 moved Not met → Partly met; C8 still Not started but folded into C5/C7 wording, see rows.)
- Hard blockers: **B-190 before any real data** (Open) and **B-191 before a pilot** (now **Partly done** — see below). The B-191 cross-process lock and tests are built (P-066, commits `39b2a46`, `e9e5683`); the failed-write-is-never-silent requirement is not yet shown (@model-risk M/L).
- Nothing in the code knows "assist-only" or "pilot". No pilot submission guard exists in `package.py`, `prepare.py` or `workbench.py`.
- New since 2026-10-19: P-068 (scorer v10) was built as dev work and **blocked by @model-risk** (`check-P-066-P-067-P-068.md` re-check, 2026-10-20): wrong operations answers still score as hits, and the synonym list is overfit to T-108. v10 is dev-only; no hold-out may use it. This does not change C1–C8, but it means the pilot's value-warning text (C6) must be written against an approved scorer.

## C1–C8 checklist

| # | Condition (short) | Status | Evidence | What closes it |
|---|---|---|---|---|
| C1 | Send path never enabled for pilot files; `send_to_carrier`/`build_package` refuse pilot ids | Partly met | P-063 send-time scope re-check refuses out-of-scope files (`p-063-p-064-as-built.md`). No pilot-id refusal exists. | Pilot-id refusal with "assist-only pilot: send disabled" in `package.py`; self-check (@software-engineer). |
| C2 | No draft leaves the tool for pilot files; `write_drafts` never runs on them | Not met | `write_drafts` is live (T-027 memo H-A1). No pilot guard. | Refuse pilot ids in `prepare.write_drafts`; self-check that `pending-approval/` gets no pilot id (@software-engineer). |
| C3 | Route and status shown only as proposals; scope verdict always shown | Partly met | Scope reason shown only on a refused send or approve (P-063). Always-on verdict and "suggestion only" labels not found. | Always-on scope verdict and suggestion labels on pilot cards; @senior-underwriter UI check (@software-engineer, @senior-underwriter). |
| C4 | Only authenticated pilot users see output; no AI output copied to deliverables | Not met | B-190 Open (`team/BACKLOG.md` line 210). B-185 prototype limit. | B-190 (see below). |
| C5 | Everything logged: display, underwriter corrections, `extraction_failed` counted apart | Partly met | Decision log exists and every entry now takes its sequence number under a **cross-process file lock** (`fcntl.flock`, `workbench.py` `_append`, P-066); 8-thread and 2-process tests pass. B-191 Partly done. No correction log found in code. | Correction log (field, suggested, final, reason); show a failed log write as a plain-language refusal (the lock failure is still swallowed, @model-risk M/L); display log with run hash; `extraction_failed` counted apart (@software-engineer; metric by @model-risk). |
| C6 | Every value labelled a proposal, with citation, confidence, and T-108 warnings (ops 9/20, loss runs 5/20) | Not verified | Citation/confidence (P-016) not re-checked in this pass. Warning text not found by grep. The warning numbers depend on the scorer: v10 is blocked (2026-10-20), so the operations figure is still the v9 one. | Warning on operations and loss-run values against an **approved** scorer; @senior-underwriter UI check (High only). |
| C7 | Frozen build: code SHA, prompt version and model recorded before the first real file; no change to `underwriting_pipeline/` during pilot | Partly met | T-108 froze `457f1bf` and prompt `759b3e6bc9b2`. P-063/P-064 changed code after it; P-066/P-067 changed it again (2026-10-20). No pilot freeze note yet. | Freeze note with new SHA after C1–C6 land; `git diff` empty over the pilot (@senior-test-engineer records). |
| C8 | Time-boxed pilot registered in TASKS.md; correction threshold per field; stop rules | Not started | No pilot task in `team/TASKS.md`. No threshold set. | @pm registers task after B-190/B-191; @head-of-underwriting sets threshold. |

## B-190 — SSO and audit log (HARD BLOCKER before any real data)

- Risk: any caller can type an underwriter id; decisions and sends are unattributable (B-185, B-100 rise to High once the send gate reads the log).
- Build plan:
  1. Choose sign-in method (SSO or local login) with @compliance on data handling. Owner: @compliance (decision), @head-of-underwriting (scope).
  2. Add sign-in to the workbench; every decision, send and view needs a signed-in user. Owner: @software-engineer.
  3. Write an audit row (user, action, submission, time) for every view, decision and send. Owner: @software-engineer.
  4. Remove the typed actor field; B-185 and B-196 close with it. Owner: @software-engineer.
  5. Independent check of the sign-in and audit path. Owner: @model-risk (High only), @senior-test-engineer (run).
- Test that proves it: unauthenticated `/send`, `/decision` and `/approve-draft` are refused with a plain reason; a signed-in decision writes one audit row naming that user; a typed actor cannot be used.

## B-191 — concurrent decision-log writes (HARD BLOCKER before a pilot)

- Risk: two workbench processes can issue the same sequence number or lose a write (eight-thread stub test errors; B-184 per-process lock). Assist logging (C5) writes to this log.
- Status 2026-10-20 (**Partly done**, P-066, commits `39b2a46` + `e9e5683`): item 1 built, item 3 built and passing, item 4 checked with no High; item 2 not shown.
- Build plan:
  1. Replace the per-process `_LOG_LOCK` with a cross-process file lock, or an atomic append that takes the next seq under the lock. **Done** — `workbench.py` `_append` takes `fcntl.flock(LOCK_EX)` on `<log>.lock` and computes `seq = max(existing) + 1` under it.
  2. Make a failed write visible in the UI as a plain-language refusal, never silent. **Not shown** — the `flock` failure is still swallowed (`except Exception: pass`, `workbench.py:592`); a forced failure has no proven refusal reason. @model-risk M/L finding; owned by @software-engineer.
  3. Re-run the stubbed eight-thread test and a two-process test. **Done** — `pytest tests/test_concurrent_writes.py tests/test_concurrent_writes_mp.py` passes (2 passed); no duplicate seq, no lost row. Note: `tests/test_concurrent_writes_proc.py` is an empty stub (unknown origin, not committed) — the two-process coverage lives in `_mp.py`.
  4. Independent check of the log code. **Done (High only)** — @model-risk checked the P-066 restore and lock path: APPROVE, no High; M1 (no "What's new"/screenshot, now added `ba22ce1`) and L1–L4 to backlog, incl. "flock failure swallowed".
- Test that proves it: eight-thread test and two-process test both pass with no duplicate seq and no lost row (✅); a forced write failure shows the refusal reason in the workbench (❌ — item 2).

## Next

- @software-engineer: item 2 of B-191 (failed write → plain refusal + screenshot); B-190 (SSO + audit log); C1–C3 self-checks.
- @ai-engineer-assistant / @model-risk: fix P-068 (v10) to @model-risk's BLOCK list (spanned-match negation/look-again, counts as one token, synonym list into `operations-gold-rule.md`), re-request the check; C6 warning numbers await an approved scorer.
- @pm: register the pilot as a task once B-190 and B-191 both pass; no pilot runs before then.
- @user: decides whether and when the pilot runs (D-057, T-027 memo).
