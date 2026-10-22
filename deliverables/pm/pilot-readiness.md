# Pilot readiness — assist-only pilot (T-109d, D-116)

- Owner: @pm. Date: 2026-10-19; updated 2026-10-21 (C1–C7 build on `pilot-conditions`, B-190 on `sso-b190`, B-191 item 2). No model call.
- 2026-10-21 update written in OpenCode, not independently reviewed; status means "built and tested on this branch", not "approved".
- Source of conditions: `deliverables/model-risk/T-027-assist-mode-pilot.md` (C1–C8, @model-risk).
- Evidence read: that memo; `deliverables/ai-engineer/p-063-p-064-as-built.md`; `team/BACKLOG.md` B-190/B-191; `team/TASKS.md` T-109a–d; `team/DECISIONS.md` D-117/D-118; `deliverables/model-risk/check-P-066-P-067-P-068.md`; a grep of `underwriting_pipeline/app` and `underwriting_pipeline/ai` for assist-only, pilot and correction-log terms (no hits).
- Not a production approval. The T-027 veto stands. Synthetic data only.

## Summary

- C1–C8 on 2026-10-21: **C1, C2, C3 and C5 built; C6 mechanism built; C4 built on `sso-b190` but not merged; C7 note written; C8 not met.** Independent review and the company decisions below are still open. This is not "4 met".
- Hard blockers: **B-190 before any real data** — built and pushed on `sso-b190` (`e9edeba`), review and merge still open. **B-191 before a pilot** — items 1, 3 and 4 done; item 2 (failed write is never silent) is now built and tested on `pilot-conditions`, independent re-check still open.
- The code now knows `PILOT_MODE=assist-only`; C1–C6 guards and logs are in `underwriting_pipeline/app/pilot.py`, `package.py`, `workbench.py` and `ai/prepare.py`. Detail: `deliverables/pm/pilot/README.md`.
- New since 2026-10-19: P-068 (scorer v10) is dev-only and blocked; no hold-out may use it. The C6 warning shows both T-108 (9/20, 5/20) and the unapproved T-117 numbers (13/20, 16/20, KEEP) until @model-risk decides (`deliverables/pm/pilot/c-open-questions.md` c1/c2).

## C1–C8 checklist

| # | Condition (short) | Status | Evidence | What closes it |
|---|---|---|---|---|
| C1 | Send path never enabled for pilot files; `send_to_carrier`/`build_package` refuse pilot ids | Built, not yet reviewed | `PILOT_MODE=assist-only` refuses send and package with "assist-only pilot: send disabled"; `approve` is refused and a per-value `confirm` never makes the file sendable; tests prove no approve row and no outbox file (`deliverables/pm/pilot/self-check-C1-C6.md`). | @model-risk code check; record the self-check at pilot start. |
| C2 | No draft leaves the tool for pilot files; `write_drafts` never runs on them | Built, not yet reviewed | `write_drafts` refuses, deletes a stale pending draft and writes no request; `prepare.approve` refuses producer requests; test proves the outbox stays empty. | @model-risk code check. |
| C3 | Route and status shown only as proposals; scope verdict always shown | Built; UI review open | Pilot banner on every page; `scope_html` verdict on every card; route reads "Suggestion only — not a decision"; test asserts both. | @senior-underwriter UI check (High only). |
| C4 | Only authenticated pilot users see output; no AI output copied to deliverables | Code on `sso-b190`; not in `pilot-conditions` | B-190 sign-in, signed session, per-render CSRF, per-view/decision/send audit, typed actor ignored; commit `e9edeba`, screenshots and tests on `sso-b190`. | Review and merge `sso-b190`; @model-risk check; then C4 is met. |
| C5 | Everything logged: display, underwriter corrections, `extraction_failed` counted apart | Built, except display identity | Correction rows (field, suggested, final, reason, actor, run hash) and event rows under `flock`+`fsync` 0600; monitor shows edits per field, overrides, refusals, time per file, failed files apart; GET writes one view row per file with run hash, prompt and model. Actor on this branch is `unauthenticated`. | Merge B-190 so views carry the signed-in user; @model-risk reviews the export at pilot end. |
| C6 | Every value labelled a proposal, with citation, confidence, and measured warnings | Mechanism built; numbers open | "AI proposal — verify against the source" on every card and value; citations/confidence unchanged; needs-review never pre-ticked; warning names T-108 9/20 and 5/20 and T-117 13/20 and 16/20 (KEEP). | @model-risk decides the warning source (c1/c2); @senior-underwriter UI check. |
| C7 | Frozen build: code SHA, prompt version and model recorded before the first real file; no change to `underwriting_pipeline/` during pilot | Note written; freeze not started | `deliverables/pm/pilot/freeze-note.md` with the fields to record, prompt `759b3e6bc9b2`, model and scorer hashes, and the `git diff --stat underwriting_pipeline/` check. | Fill the branch SHA at pilot start; no pipeline change during the pilot. |
| C8 | Time-boxed pilot registered in TASKS.md; correction threshold per field; stop rules | Not met | No pilot task in `team/TASKS.md`; no threshold. Stop rules are written in `deliverables/pm/pilot/underwriter-guide.md` and `incident-rollback.md`. | @pm registers the task; @head-of-underwriting sets the threshold; @user decides go/no-go. |

## B-190 — SSO and audit log (HARD BLOCKER before any real data)

- Status 2026-10-21: **built, pushed, not merged** on `sso-b190` (`e9edeba`). It is not on `ai-team` or `pilot-conditions`. Evidence: `deliverables/software-engineer/B-190-oidc-sign-in.md`, `screenshots/B-190-sign-in.png`, `B-190-signed-in-queue.png`; 19 auth/workbench tests; full suite 62 passed on that branch.
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
- Status 2026-10-21: **items 1, 3 and 4 done (P-066); item 2 built and tested on `pilot-conditions`.** Items 1, 3 and 4: commits `39b2a46` + `e9e5683`, cross-process `flock`, seq under the lock, eight-thread and two-process tests pass, @model-risk APPROVE (High only). Item 2: `_append` no longer swallows `flock`/`fsync`; a forced `fsync` failure returns "Decision refused: disk full" in `test_pilot.py`. Independent re-check of item 2 still open.
- Build plan:
  1. Replace the per-process `_LOG_LOCK` with a cross-process file lock, or an atomic append that takes the next seq under the lock. **Done** — `workbench.py` `_append` takes `fcntl.flock(LOCK_EX)` on `<log>.lock` and computes `seq = max(existing) + 1` under it.
  2. Make a failed write visible in the UI as a plain-language refusal, never silent. **Done on `pilot-conditions`** — `flock` and `fsync` failures raise; `act` returns a refusal naming the error; `test_pilot.py` forces `fsync` to fail. Re-check owed.
  3. Re-run the stubbed eight-thread test and a two-process test. **Done** — `pytest tests/test_concurrent_writes.py tests/test_concurrent_writes_mp.py` passes (2 passed); no duplicate seq, no lost row. Note: `tests/test_concurrent_writes_proc.py` is an empty stub (unknown origin, not committed) — the two-process coverage lives in `_mp.py`.
  4. Independent check of the log code. **Done (High only)** — @model-risk checked the P-066 restore and lock path: APPROVE, no High; M1 (no "What's new"/screenshot, now added `ba22ce1`) and L1–L4 to backlog, incl. "flock failure swallowed".
- Test that proves it: eight-thread test and two-process test both pass with no duplicate seq and no lost row (✅); a forced write failure shows the refusal reason in the workbench (✅ on `pilot-conditions`, `tests/pipeline/test_pilot.py`).

## Next

- @model-risk: independent check of `pilot-conditions` C1–C6 and B-191 item 2; decide the C6 warning source (T-108 or T-117 or both) and the approved reporting run (c1/c2).
- @senior-underwriter: C3/C6 UI check, High only.
- @compliance / IT / @user: data handling, IdP/tenant and go/no-go (c5).
- @pm / @head-of-underwriting: register the pilot task, set the per-field threshold (c3/c4).
- @software-engineer: review and merge `sso-b190`; then confirm the display log uses the signed-in user.
- No pilot runs until B-190 is merged and B-191 item 2 is re-checked. @user decides whether and when.
