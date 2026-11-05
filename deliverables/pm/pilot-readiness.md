# Pilot readiness — assist-only pilot (T-109d, D-116)

- Owner: @pm. Created 2026-10-19; updated 2026-10-21 and 2026-11-02; **updated 2026-11-05 by the orchestrator (D-168)**. No model call.
- Source of conditions: `deliverables/model-risk/T-027-assist-mode-pilot.md` (C1–C8, @model-risk). Open decisions: `deliverables/pm/pilot/decisions-for-user.md` (c1–c9).
- Not a production approval. The T-027 production veto is lifted, conditional (D-167, below); it was KEEP after T-120. Synthetic data only. "Built" means built and tested on `pilot-integration`. It does not mean independently approved.
- Note: these pilot conditions C1–C8 are different from the T-027 operations gate C1–C7 (D-134). That gate was met in T-120.

## Update 2026-11-05 (D-167, D-168)

- **@model-risk T-027 production veto: LIFTED, conditional (D-167)** after the T-128 hold-out passed every gate.
  - The lift holds only for the frozen build (1ddae83c, prompt 392b9ce3c1af, scope-v8, qwen/qwen3.8-27b on Groq) and Texas BOP P-055 criteria 1–4.
  - It also needs C6 monitoring on ≥ 60 reviewed files with stop rules, and B-530/B-531 closed before any send-enabled mode. Any change to the build needs a new @model-risk check.
- **Go-live: not yet** (@user, D-168).
- **@responsible-ai T-082 fairness veto: stands.** Its lift requirements are below.
- **The plan for the final build** is in `deliverables/pm/pilot-final-build-plan.md`: P-085/P-086, the provider switch, then one fresh 20+12 hold-out (T-133), run once.
- **Deferred to pilot data (D-168):** B-525, B-529, B-532.
- **The repo will be made private** by @user (D-168).

### What's left before a pilot

1. `approve change P-085` (B-531 label) and `approve change P-086` (B-530 citations). Then build them, and @model-risk checks them.
2. AI provider with a data agreement. The switch, then a @model-risk check.
3. Freeze, then T-133 (gold first, run once, every T-128 gate), then a @model-risk memo.
4. C6 monitoring plan (≥ 60 reviewed files, stop rules), written before the first pilot file.
5. The older items below (c7, c8, C7 freeze, C8 registration) where still open.
6. T-082. @responsible-ai lists 7 items; items 1–6 can be done now on synthetic data (no model call):
   1. EN↔ES class counterfactual test.
   2. Spanish bar words routed the same as English. This is a rule change and a loosening, so it is your decision.
   3. B-197 Spanish-variant review.
   4. Housing proxy-review document.
   5. Your decision on the housing route.
   6. Recommendation-mix test by housing class.
   - Items 1–6 lift the veto for demo/synthetic use only.
   - Item 7 (language outcome rates against AIR ≥ 0.8) and the protected-group impact in item 6 need real pilot data before a pilot.

### Questions for the manager

- Go / no-go and who signs it. Pilot size (files, underwriters) and dates. C6 needs ≥ 60 reviewed files.
- Which accuracy numbers the pilot shows (c1), the reporting run (c2), and the per-field threshold that pauses the pilot (c3).
- The housing route under T-082 (keep never-overridable no_match with a written reason, or an alternative).

### Questions for IT

- **AI provider** with a data agreement: endpoint and region, exact model id and version, how the key is issued, stored and rotated, and rate limits for pilot volume.
- **Hosting:** which server or cloud account and region, who can reach it, backups, and where logs are kept, for how long, and who can read them.
- **Sign-in provider:** the OIDC issuer/tenant, a client for the workbench, pilot user accounts, and how a sign-in maps to an underwriter id (c5, c9).
- A host for the clamd virus scanner (B-485).

### Questions for compliance

- Is the provider agreement acceptable for real applicant documents? It should cover no training on our data, zero or short retention, no abuse-log storage or a bounded one, in-region processing, subprocessors, deletion, and breach notice.
- Retention period for pilot logs and decisions.
- The legal standard for the T-082 housing proxy review (Fair Housing Act disparate impact) and who signs it.

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
