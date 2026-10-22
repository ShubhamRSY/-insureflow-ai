# Decisions for the user — assist-only pilot

- Date: 2026-10-21. Author: @pm. Written in OpenCode, not independently reviewed.
- **Nothing here is decided.** Each item is a question, 2–3 options, a recommendation with a reason, and the parties outside the team who must agree. The decision owner is named; the answer is the user's, recorded in `team/DECISIONS.md` as a `D-###` after the user answers in chat.
- Scope: the eight open items `c1`–`c8` from `deliverables/pm/pilot/c-open-questions.md`, plus `c9`, a new item found during the three-way branch integration on 2026-10-21.
- Not a production approval. The T-027 veto stands. No pilot runs until B-190 is reviewed and merged and B-191 item 2 is re-checked.
- Sources: `deliverables/model-risk/T-027-assist-mode-pilot.md` (C1–C8, authoritative), `deliverables/model-risk/T-027-memo.md` (T-108, scorer v7), `deliverables/model-risk/T-027-memo-T-117.md` (T-117, scorer v11), `deliverables/pm/pilot-readiness.md`, `deliverables/pm/pilot/README.md`, `deliverables/pm/pilot/c-open-questions.md`, `deliverables/pm/pilot/freeze-note.md`, `deliverables/pm/pilot/data-handling.md`.

## Who is "outside the team"

| Party | What they own in these decisions |
|---|---|
| **IT** (agency IT / identity administrator) | The sign-in tenant and issuer, the OIDC client, account provisioning for pilot users, where the pilot logs are stored, how long they are kept, who can read them. |
| **Compliance** (the agency's compliance officer, not the @compliance team role) | Whether real applicant documents may be sent to a third-party model host (M1), which data-processing terms apply, what personal data the audit trail holds and for how long. A compliance block stops the pilot regardless of any other answer. |
| **Manager** (the non-technical business owner the pilot is run for; the audience of `deliverables/pm/demo-guide.md`) | Whether the pilot is worth the underwriters' time, how many real files it is worth exposing, which underwriters take part, and the go/no-go on the window. |

## Status of each item today

| # | Decision needed | Owner | Blocks | State on 2026-10-21 |
|---|---|---|---|---|
| c1 | Which accuracy numbers the pilot may show | @model-risk | C6 sign-off | Code shows T-108 **and** T-117 with statuses. Open. |
| c2 | Which frozen run the pilot's correction rate is reported against | @model-risk | C6, pilot report | Open. |
| c3 | Correction-rate threshold per field that pauses the pilot | @head-of-underwriting | C8 | No threshold exists. Open. |
| c4 | Pilot registered as a task: owner, file count, end date | @pm, with @user go/no-go | C8 | Not registered. Open. |
| c5 | Model host and data handling for real applicant documents; IdP/tenant; audit retention | @compliance; tenant with IT; go/no-go @user | C4, real data | Open. |
| c6 | Review and merge `sso-b190`; confirm C4/C5 display identity | @model-risk, @senior-test-engineer | C4, C5 display log | Merged on a throwaway branch only (`pilot-integration` `5a8063f`). Branch of record `pilot-conditions` still lacks it. Open. |
| c7 | Independent check of the C1–C6 code and B-191 item 2 | @model-risk | Pilot start (D-057) | Not done. Open. |
| c8 | UI check from the underwriter's point of view, High only | @senior-underwriter | C3, C6 | Not done. Open. |
| c9 | **New.** How a sign-in identity becomes an underwriter id | @software-engineer, with IT | Real sign-in, C4, C5 | Found during the three-way integration. Open. |

---

## c1 — Which accuracy numbers may the pilot show?

**Question.** The standing C6 warning tells an underwriter how accurate the operations and loss-run values are. T-027 C6 requires the warning to name "their measured T-108 accuracy (9/20 and 5/20) until a fresh frozen run says otherwise". T-117 is a fresh frozen run (13/20 and 16/20) but @model-risk recorded **KEEP, not approval**, and it carries three open High findings (H1 cooking line dropped, H2 0/3 planted conflicts caught, H3 Carrier C build format). May the pilot show T-108 only, T-117 only, or both with their statuses?

**Options.**

- **A. T-108 only** — "Last approved numbers: operations 9/20, loss runs 5/20 (T-108 frozen run, scorer v7)". Newer T-117 numbers are not shown.
- **B. T-117 only** — "Latest frozen run: operations 13/20, loss runs 16/20 (T-117, scorer v11, @model-risk KEEP — not a production approval)". T-108 numbers are not shown.
- **C. Both, each labelled with its run and its status** — what the code does today (`underwriting_pipeline/app/pilot.py:34` `ACCURACY`, `warning_text()` at `:164`).

**Recommendation: C.** Reason: neither run is approved for production, and T-117 is *better* on both fields, so showing it alone would read as "the numbers went up, use these", which is not what a KEEP means. Showing T-108 alone would hide the newer frozen run and would leave the underwriter warning in place after a run that measured better. Both on screen, each named with its run id and its status, keeps the underwriter looking at the weakest number while leaving the record honest. If the label is judged too long for the card, shorten the labels, not the set of numbers.

**Outside agreement required.** **Manager** — the warning is what an underwriter is told to check, and it goes on a card a manager may read in a demo. **Compliance** — only if the wording is changed to make a claim about accuracy of real applicant data. **IT** — none.

**If the answer is A or B**, that is an `app/` change to `pilot.py` and the workbench card: @software-engineer, with @model-risk's decision and @senior-underwriter's UI check, plus a new "What's new" line and a screenshot. No `approve change P-###` is required: no prompt, model, OCR or scorer changes. If the *numbers* themselves change, that is a new frozen run, not a wording change.

**Blocks:** C6 sign-off.

---

## c2 — Which frozen run is the pilot's correction rate reported against?

**Question.** The pilot's error measure is the underwriters' corrections (C5). For that number to be comparable, the report has to name the run it is compared to. P-068 / scorer v10 is dev-only and blocked; v11 (T-117) is frozen and scored once but is KEEP, not approved; v7 (T-108) is the last run whose numbers are published and quoted. Which run is the baseline?

**Options.**

- **A. v11 / T-117 as the baseline** — the newest frozen run; corrections are reported against 13/20 and 16/20, and the report notes the KEEP verdict and the three open Highs.
- **B. v7 / T-108 as the baseline** — the run the numbers on the card come from; corrections are reported against 9/20 and 5/20.
- **C. v7 as the baseline, v11 reported alongside as the newer frozen run** — one primary number, one comparison, both named with run id, scorer and status.

**Recommendation: C.** Reason: the pilot's correction rate is read next to the warning on the card, and the card quotes T-108. A correction rate measured against a baseline that is not on the card invites the reader to compare two things that were never on the same surface. v11 is still the more recent measurement and should not be hidden, but it is not a baseline: it is KEEP with three open Highs, and a High means the number itself may still move. P-068/v10 is excluded from all reporting; it is blocked for hold-out use.

**Outside agreement required.** **Manager** — the correction rate is the pilot's headline number and will be read as a performance measure of the tool. **Compliance** — none unless real applicant values appear in the report (they must not; the report counts corrections per field, not their values). **IT** — none.

**Blocks:** C6, and the pilot report.

---

## c3 — What correction-rate threshold per field pauses the pilot?

**Question.** C8 requires a written threshold per field, set before the pilot starts, and any field above it pauses the pilot. No threshold exists. T-108 measured operations at 9/20 and loss runs at 5/20, so on the weakest field most values are already known to be wrong; a threshold must be set against that baseline, not against an assumption that values are usually right.

**Options.**

- **A. One threshold for every field** — e.g. pause when more than 10% of the values confirmed on a field across the pilot were corrected.
- **B. Per-field thresholds scaled to the measured baseline** — e.g. loss runs 25%, operations 15%, every other field 5%. The numbers are placeholders; the owner sets the values.
- **C. Absolute counts only** — e.g. two wrong loss-run values on one file, or three across the pilot, stops the pilot regardless of any rate.

**Recommendation: B, with C as a hard floor.** Reason: a single global rate fires on the weakest field almost immediately (T-108 says roughly three of four loss-run values are wrong) and is therefore a stopwatch, not a measure; it says nothing about the fields that are usually right. Per-field thresholds let each field be judged against what is actually known about it. The absolute floor from C is still needed on top, because a rate over a small number of files can hide one badly wrong file, and one badly wrong value reaching a real customer is the harm the whole pilot is designed to contain.

**Outside agreement required.** **Manager** — a threshold is a business decision about how much review time the agency will spend, and it defines when work stops mid-week. **Compliance** — none, provided the threshold is set before the first real file and the pause rule is in writing. **IT** — none.

**Owner.** @head-of-underwriting sets the numbers. The recommendation above is @pm's; it does not set them.

**Blocks:** C8.

---

## c4 — Register the pilot as a task: owner, file count, end date

**Question.** C8 requires the pilot to exist as a `team/TASKS.md` task with an owner, a file count and an end date. What are they?

**Options.**

- **A. 20 files over 4 weeks** — enough files for a per-field rate to be meaningful (see c3).
- **B. 10 files over 2 weeks** — a shorter window, still enough for a rate on the weakest field to be read, with less of the agency's real book exposed.
- **C. 5 files over 1 week** — a minimal smoke pilot.

**Recommendation: B, and only if c5 is answered yes for real documents.** Reason: with 5 files a per-field correction rate is mostly noise and the pilot proves little; with 20 real files the agency has put a fifth of a month's real applicant data through a free-tier host before anyone has answered c5 — if c5 is unresolved, the only defensible file count is 0 real files, because the pilot can run on synthetic submissions and still produce the correction-rate and timing evidence C8 and C2 need.

**Outside agreement required.** **Manager** — the window, the file count and which underwriters take part are business commitments. **IT** — accounts and sessions for the pilot users must exist for the whole window, and the log store must be available for it. **Compliance** — the file count is the number of real applicant documents the host will see, so it must match whatever c5 permits.

**Blocks:** C8.

---

## c5 — Model host, data handling, IdP/tenant and audit retention for real applicant documents

**Question.** M1 is not assessed: real applicant documents would be sent to a third-party model host. The pilot's sign-in needs a real IdP and tenant. The pilot logs hold the same values the underwriter saw, and they are confidential records with a retention life. Which host, which IdP, and how long are the logs kept?

**Options.**

- **A. The approved free-tier host as it stands** (Groq via `LLM_BASE_URL`/`LLM_MODEL`, key from the shell only) with the agency IdP as tenant, and pilot logs kept 30 days then deleted on written instruction.
- **B. Synthetic-only pilot** — no real applicant document is opened in the tool at all; the pilot runs on synthetic submissions and produces correction-rate, timing and refusal evidence without exposing any real file. Real data comes later, after a separate clearance.
- **C. A paid or contracted host with data-processing terms** — removes the M1 question at the cost of the "no paid API" rule (D-011), which would need its own decision.

**Recommendation: B until compliance answers, then A.** Reason: B loses the one thing a real pilot adds — corrections on real documents — but keeps every other measurement and removes the M1 question from the critical path. A is the realistic end state, because the free-tier host is already the project's approved host and switching hosts for a pilot adds a second code path without adding evidence. C is not a live option while D-011 stands; it is listed so the trade-off is visible, not recommended.

Two facts that bear on the answer, both from the 2026-10-21 integration:

- The repo's `underwriting_pipeline/app/underwriters.json` lists `user`, `UW-001` and `UW-002` with **no `oidc_sub`, `email`, or `issuer`+`subject`**, so no real OIDC identity can be mapped to an underwriter today. A real pilot cannot sign anyone in until c9 is answered.
- The sign-in, audit and pilot logs are designed to be written under a temp sandbox for tests and to real 0600 files in operation; where the pilot logs live in production is an IT question that this repository does not answer.

**Outside agreement required.** **Compliance** — whether real applicant documents may go to a third-party host, under what terms, and what personal data the audit trail holds. **IT** — the IdP tenant, issuer and OIDC client, the account list, where logs are stored, and who can read them. **Manager** — the go/no-go on running the pilot on real files at all.

**Blocks:** C4 and any use of real data. A compliance block stops the pilot regardless of every other answer.

---

## c6 — Review and merge `sso-b190`, then confirm the C4/C5 display identity

**Question.** C4 requires that only authenticated pilot users see output, and C5 requires every display to be logged. The sign-in work (B-190) exists on `sso-b190` (`e9edeba`) and has been merged once, on the throwaway three-way branch `pilot-integration` (`f608d2c`, `5a8063f`) — that branch is not the branch of record and is not merged into `ai-team`. The branch of record for the pilot is `pilot-conditions` (`1c83343`), which still does not contain it. How is the review and merge done?

**Options.**

- **A. Review `sso-b190` on its own, then merge it into `pilot-conditions`** — the smallest change; the pilot branch gains the sign-in and the display log.
- **B. Review the merged three-way branch `pilot-integration` (`5a8063f`) as the pilot candidate** — the sign-in, the assist-only guards and the LOB engine are reviewed together, as they would actually run.
- **C. Do both**: @model-risk reviews the assist-only code on `pilot-conditions` (with B-191 item 2, see c7), @senior-test-engineer reviews the merged branch, and the pilot branch of record is then `pilot-conditions` + `sso-b190` merged.

**Recommendation: C.** Reason: the two reviews answer different questions and neither substitutes for the other. @model-risk's condition is about the C1–C6 guards and the correction log, which live on `pilot-conditions`; the review must be of the code that will be frozen, so it must be on the branch that will be frozen. @senior-test-engineer's condition is about the combination — sign-in, guards and logs working together — which is exactly what the three-way integration exercised and what no single-branch review can see. Merging `sso-b190` into `pilot-conditions` afterwards gives one branch to freeze, with the combination already tested.

For the record, the three-way integration found one combination-only break, which is c9, and one pre-existing gap that was left as found: a per-value confirmation is written to the decision log but not to the pilot correction log, so a confirmed-but-never-edited value does not appear in the per-field correction counts. It is not a C5 breach (a confirmation is not a correction) but it means the correction rate counts edits and resolutions only. @model-risk should say whether that is the measure C8 wants.

**Outside agreement required.** **IT** — the IdP tenant and the test accounts must exist for the reviewers to exercise a real sign-in and a real audit row. **Manager** — the list of underwriters who may sign in during the pilot. **Compliance** — the sign-in audit trail is personal data; retention and access must be agreed before real use.

**Blocks:** C4, and the C5 display-identity half.

---

## c7 — Independent check of the C1–C6 code and B-191 item 2

**Question.** @model-risk's memo makes an independent check of the C1–C6 code and of B-191 item 2 (a failed write is never silent) a precondition for the pilot. Where is it done?

**Options.**

- **A. On `pilot-conditions` only** — one review of the branch that will be frozen.
- **B. On `pilot-integration` only** — one review of the merged branch.
- **C. Split**: @model-risk reviews the assist-only code and B-191 item 2 on `pilot-conditions`; @senior-test-engineer reviews the merged branch and the combination, with a look-again after the merge.

**Recommendation: C.** Reason: the condition is about the frozen build, and the frozen build will be `pilot-conditions` + `sso-b190`; a review of a throwaway branch that nobody will freeze proves something about that branch and nothing about the pilot. Splitting the two keeps one reviewer on the conditions and the other on the combination, and the look-again after the merge is the only point at which the merged code is actually reviewed as a whole.

**Outside agreement required.** **IT** — only for the environment needed to exercise sign-in and the audit log (an IdP test tenant). **Compliance** — none. **Manager** — the result is reported to the manager before the go/no-go, not as a condition of this review.

**Blocks:** pilot start (D-057).

---

## c8 — UI check from the underwriter's point of view, High findings only

**Question.** C3 and C6 both require @senior-underwriter's UI check before the pilot starts, on the card as an underwriter will actually see it. On which build, with which data?

**Options.**

- **A. `pilot-conditions` with synthetic data** — the pilot card as built, without sign-in in front of it.
- **B. The merged branch with sign-in in front of it** — the whole underwriter journey: sign in, open a card, read the scope verdict and the warning, confirm values, and see the refusal if they try to send.
- **C. Both**, High findings only, with the merged branch as the deciding build.

**Recommendation: B.** Reason: the underwriter's journey in the pilot starts at the sign-in page and includes a send attempt that must be refused in plain words. Checking the card without the sign-in in front of it misses the two things most likely to be High for a user: what the first screen says about the pilot, and whether a refusal explains itself. Synthetic data throughout; no real applicant document appears in a screenshot (protocol data rule, C4).

**Outside agreement required.** **Manager** — the UI check is also the check that the pilot does not add unreasonable work per file, which is a business judgement. **IT** — a test tenant for the sign-in screen. **Compliance** — none, provided the screenshots stay synthetic.

**Blocks:** C3, C6.

---

## c9 — How a sign-in identity becomes an underwriter id

**Question.** *New item, found during the three-way integration on 2026-10-21.* `auth.map_identity` only recognises an identity that matches an entry in `underwriting_pipeline/app/underwriters.json` by `oidc_sub`, by `issuer`+`subject`, or by a verified `email`. That file currently lists only `user`, `UW-001` (senior) and `UW-002`, with no identity fields at all, so any real sign-in ends in "signed in as …, but that identity is not on the workbench underwriter list". How is the mapping supplied?

**Options.**

- **A. Add identity fields to `underwriters.json`** — one entry per pilot user with `oidc_sub` (and `issuer`). Simple, and the file already exists for exactly this purpose.
- **B. Match on verified `email`** only — the least configuration, but a shared or changed email silently changes who a session belongs to, and `email_verified` must be true or the match fails.
- **C. Keep `underwriters.json` synthetic and supply a separate identity file at deploy time** (e.g. `underwriters.local.json`, git-ignored, read by IT at start-up). The repository stays free of real identities; IT owns the mapping.

**Recommendation: C, with A as the fallback.** Reason: the repository's rule is that only synthetic identities live in tracked files, and a real OIDC subject is a real person's identifier. A separate file keeps that rule, keeps the merge in IT's hands, and lets the pilot's user list change without a code change or a branch. The cost is one more file and a start-up step, which the pilot does not mind. B is not recommended: email is the weakest of the three identifiers and this pilot's whole point is attributability.

Whichever is chosen, the pilot needs at least one **senior** underwriter on the list, because a senior-referral file cannot be confirmed by a non-senior.

**Outside agreement required.** **IT** — owns the identity file, the issuer and the subject values, and the account provisioning; must confirm which mapping the agency IdP can supply. **Compliance** — a subject or email on file is personal data; the file is access-controlled and its retention is part of c5. **Manager** — which staff are in the pilot, and that one of them is senior.

**Blocks:** real sign-in, and therefore C4 and the C5 display identity.

---

## How to answer

Reply in chat with one line per item, for example:

```
c1: C   c2: C   c3: B with C floor   c4: B, synthetic first   c5: B then A
c6: C   c7: C   c8: B   c9: C
```

With your answers, @pm records each as a `D-###` in `team/DECISIONS.md` with the owner's name, the options considered and the reason, and the items are closed in `deliverables/pm/pilot/c-open-questions.md`. Items that belong to @model-risk, @head-of-underwriting or @compliance are sent to them as a proposal with your answer attached; they are decided by their owner, not by this file.

Two things that do **not** change with these answers: the T-027 production veto stays as written, and no change to extraction, prompts, OCR, models or scorers is authorized by anything here — that still needs `approve change P-###` in chat (D-017).
