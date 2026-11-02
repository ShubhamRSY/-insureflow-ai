# Open company decisions — assist-only pilot (c)

- Date: 2026-10-21. None of these is decided here. Decision rights are in `team/DECISIONS.md` and the protocol.
- Written in OpenCode, not independently reviewed.

| # | Question | Owner | Blocks |
|---|---|---|---|
| c1 | Which warning numbers may the pilot show? T-027 C6 names T-108 operations 9/20, loss runs 5/20 "until a fresh frozen run says otherwise". T-117 (v11) is frozen but you recorded KEEP, not approval. May the code show T-108 only, T-117 only after approval, or both with their statuses as it does now? | @model-risk | C6 sign-off |
| c2 | Which scorer and frozen run are approved for the pilot's correction-rate reporting? P-068/v10 is blocked; v11 is KEEP. | @model-risk | C6, pilot report |
| c3 | What correction-rate threshold per field pauses the pilot? | @head-of-underwriting | C8 |
| c4 | Register the pilot as a `team/TASKS.md` task with owner, file count and end date. | @pm, with @user's go/no-go | C8 |
| c5 | Is the model host and data handling acceptable for real applicant documents (M1)? Which IdP/tenant, and what audit retention? | @compliance; tenant with IT; go/no-go @user | C4, real data |
| c6 | Review and merge `sso-b190` (`e9edeba`), then confirm C4/C5 display identity on the pilot branch. | @model-risk, @senior-test-engineer | C4, C5 display log |
| c7 | Independent check of the C1–C6 code and B-191 item 2 on `pilot-conditions`. | @model-risk | Pilot start (D-057) |
| c8 | UI check from the underwriter's point of view, High findings only. | @senior-underwriter | C3, C6 |