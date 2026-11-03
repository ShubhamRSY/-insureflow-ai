# Pilot readiness — assist-only pilot (T-109d, D-116)

- Owner: @pm. Created 2026-10-19; updated 2026-10-21; **updated 2026-11-02 to the state of `pilot-integration`**. No model call.
- Source of conditions: `deliverables/model-risk/T-027-assist-mode-pilot.md` (C1–C8, @model-risk). Open decisions: `deliverables/pm/pilot/decisions-for-user.md` (c1–c9).
- Not a production approval. The T-027 production veto stands (KEEP after T-120). Synthetic data only. "Built" means built and tested on `pilot-integration`. It does not mean independently approved.
- Note: these pilot conditions C1–C8 are different from the T-027 operations gate C1–C7 (D-134). That gate was met in T-120.

## Summary (2026-11-02)

- **Everything is on one branch.** `sso-b190` (B-190) and `pilot-conditions` (C1–C6, B-191 item 2) were merged into `pilot-integration` on 2026-10-21. That branch is now the branch of record (D-144).
- **Built, not independently checked:** C1, C2, C3, C4, C5 and the C6 mechanism; B-190 sign-in; B-191 item 2. The @model-risk check of C1–C6 and B-191 item 2 (c7) and the @senior-underwriter UI check (c8) have not been done.
- **Not met:** C7 (freeze not started) and C8 (no pilot task, no threshold).
- **New since 2026-10-21:**
  - T-122 (P-078): every file goes through type, lock, virus, macro and injection checks.
  - T-125 (B-485, D-143): in pilot mode, if no virus scanner is set up, no file is opened. Built 2026-11-02; @model-risk check pending.
  - P-076: operations is always acknowledged before send.
  - T-127 (P-077, D-145/D-146): a second location found by rules or by the model's count, or any doubt, sends the whole file to manual intake. T-126 (B-508): blocked cards name the missing scanner.
- **No pilot can start** until c7 and c8 are done, C8 is registered, and the user's company answers c5 and c9 (IT) and c1–c4 (manager).

## C1–C8 checklist

| # | Condition | State 2026-11-02 | What is left |
|---|---|---|---|
| C1 | Send path never enabled for pilot files | Built on `pilot-integration`. `PILOT_MODE=assist-only` refuses send, package and approve with a plain reason. | @model-risk code check (c7). |
| C2 | No draft leaves the tool | Built. `write_drafts` and producer-request approval refuse; the outbox stays empty (tests). | @model-risk code check (c7). |
| C3 | Route and status shown only as proposals; scope verdict always shown | Built. Pilot banner, scope verdict on every card, "Suggestion only — not a decision". | @senior-underwriter UI check, High only (c8). |
| C4 | Only signed-in pilot users see output | Built: B-190 merged on `pilot-integration` (OIDC sign-in, signed session, CSRF, audit row per view, decision and send). | @model-risk check; IdP and tenant from IT (c5); identity → underwriter id mapping (c9). |
| C5 | Everything logged; failed calls counted apart | Built. Correction and event logs under `flock`+`fsync`, mode 0600; the monitor shows edits per field. Views carry the signed-in user once B-190 runs with a real IdP. | c7 check; @model-risk reviews the export at pilot end. |
| C6 | Every value labelled a proposal, with measured warnings | Mechanism built. The warning still names T-108 (9/20, 5/20) and T-117 (13/20, 16/20). The newer T-120 hold-out is not shown. | @model-risk decides which numbers the warning shows (c1) and the reporting run (c2). |
| C7 | Frozen build: code SHA, prompt version, model recorded; no pipeline change during the pilot | Note written (`deliverables/pm/pilot/freeze-note.md`, prompt `392b9ce3c1af` after P-077, scope-v5). Freeze not started. | Record the SHA at pilot start; no change to `underwriting_pipeline/` during the pilot. |
| C8 | Time-boxed pilot registered; per-field correction threshold; stop rules | **Not met.** Stop rules are written (`deliverables/pm/pilot/underwriter-guide.md`, `incident-rollback.md`). No task, no threshold. | @pm registers the task (c4); @head-of-underwriting sets the threshold (c3); @user decides go/no-go. |

## Hard blockers

- **B-190 — sign-in and audit log (before any real data).** Built and merged into `pilot-integration` (`e9edeba` via `f608d2c`). Open: an independent check, the real IdP/tenant (IT, c5), and how a sign-in identity becomes an underwriter id in `underwriters.json` (c9).
- **B-191 — concurrent decision-log writes (before a pilot).** Items 1, 3 and 4: done, @model-risk APPROVE. Item 2 (a failed write is never silent; "Decision refused: disk full"): built and tested, merged into `pilot-integration`. Its independent re-check is part of c7.
- **B-485 — virus scanner required in pilot mode.** Built 2026-11-02 (T-125); @model-risk check pending. In the pilot, `CLAMAV_HOST` must point at a running clamd. Otherwise every file is blocked by design.

## Needs the user's company (outside the team)

- **IT:**
  - sign-in tenant and issuer, OIDC client, accounts for pilot users (c5);
  - how a sign-in becomes an underwriter id (c9);
  - where pilot logs are stored, how long, and who can read them (c5);
  - a host for clamd (B-485).
- **Manager:**
  - which accuracy numbers the pilot shows (c1);
  - which run the correction rate is reported against (c2);
  - the per-field threshold that pauses the pilot (c3);
  - file count, underwriters and dates (c4);
  - go/no-go.
- **Compliance:** model host and data handling for real applicant documents (c5).

## Next

1. @model-risk: c7 (C1–C6 and B-191 item 2 on `pilot-integration`) and the c1/c2 warning source.
2. @senior-underwriter: c8 UI check, High only.
3. @pm / @head-of-underwriting: register the pilot task with a threshold (C8).
4. The user takes c1–c5 and c9 to the manager and IT.
