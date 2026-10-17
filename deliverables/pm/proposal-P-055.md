# P-055 — Pilot scope: manual intake for out-of-scope files

- Status: PROPOSED, revision 2 (D-103 item 1). Not built. Not approved. Waits for `approve change P-055` from @user in the Claude Code session.
- Author: @pm draft (D-102); revision 2 written by the orchestrator from the user's D-103 answers and @model-risk `scope-P-055.md` H1/H2 (budget rule 3). No new criteria were added.
- Not a production approval. The T-027 veto stands.

## Fixed in writing before any new gold (@model-risk H1)

These are fixed by @user (D-103) and do not change after the new gold is written. T-103 is not gate evidence and is not re-scored. Any re-read of it is a separate file labelled "post-hoc, not gate evidence".

### Out of scope (whole file to "manual intake")

1. **Scanned application.** The application is an image (JPG, PNG, TIFF), an image-only PDF, or a PDF whose application text came from OCR rather than a text layer. A scanned page anywhere in the application counts. Evidence it is needed: SUB-170.
2. **Multi-location schedule.** The file lists two or more premises as locations: a schedule file (csv, xlsx, or a file named "schedule") with two or more address rows, or an application location list ("(loc 1)", "(loc 2)", "Location 2:"). A mailing address or prior address is not a location. Evidence: SUB-172; dev SUB-140, 144, 145 also match.
3. **Substantial non-English content.** The application, or the main document when there is no application, is mostly in a language other than English. Evidence: SUB-163, SUB-169.

### In scope (reviewed as now)

- **Scanned carrier loss runs** with a typed application (SUB-159 to 161 kind). User's decision (D-103).
- **Email-only files.** Not in the user's D-103 list, so they stay in scope. (Draft 1 had them out.)
- A non-English email or business name beside an English application; a one-row schedule; a mailing or prior address on the application.

### Ceiling on in-scope files sent to manual intake by mistake

- At most **2 of 20** in-scope files. Reported every run. Above 2, the gate fails.
- A file sent to manual intake by mistake is left out of the in-scope gate denominator only if the ceiling is met.

## What it changes

A file the detector puts out of scope goes to "manual intake" as a whole file: no field is shown as complete, no status "complete" or "complete — review pending", no carrier route, no provisional route, no carrier suggested, and the send action is blocked with the same reason. The workbench card lists every matched reason:

- "Manual intake: scanned application"
- "Manual intake: multiple locations"
- "Manual intake: non-English documents (Spanish)"

`extraction_failed` keeps precedence (D-021) and is counted apart.

## The detector (@model-risk H2)

- A new Tier 2 component, entered in `deliverables/model-risk/model-inventory.md` with a version id before it is used. Deterministic rules only, no model call. Any change to its rules is a change under D-017 (`approve change P-###`) and is revalidated.
- **Fail closed:** a detector error, an unknown language, or an unknown text layer sends the file to manual intake, never to in scope.

## How it is measured (on every run, reported apart from the T-027 field scores)

| Measure | Definition | Target |
|---|---|---|
| Leakage (hard gate) | Out-of-scope files that show any field as complete, status complete or complete — review pending, any carrier or provisional route, any carrier suggested, or an enabled send ÷ out-of-scope files | 0. One leak fails the gate |
| Detection recall | Out-of-scope files sent to manual intake ÷ out-of-scope files, per criterion and overall | 100% per criterion and overall |
| Reason accuracy | Manual-intake cards whose listed reasons include every gold scope label | 100% (extra reasons allowed) |
| False manual intake | In-scope files sent to manual intake ÷ in-scope files | At most 2 of 20 |
| Fail closed | Detector error or unknown input | Always manual intake |

Scope labels are written in the gold of every file, before any run, under the D-102 gold rules.

## Next hold-out (D-020 exception granted by @user, D-103)

- 32 files in one frozen set: **20 in scope + 12 out of scope**. Gold first, scope label in every gold file, scored once, no code change after the gold exists. Scorer v5.
- 20 in scope, at least 6 boundary cases that must stay in scope: scanned or image-only carrier loss run with a typed application; email-only English file; English application with a Spanish email or Spanish business name; one-row schedule; application with a mailing or prior address that is not a location.
- 12 out of scope: 4 per criterion, of which at least 3 match two criteria; each criterion has a near-pass form (scanned application with a good OCR score; multi-location only in a schedule file; Spanish application with an English email).
- T-027 gate unchanged, on the 20 in-scope files: all 9 fields at 9/10 or better, 0 false completes, 0 unsafe routes, route at least 18/20. Plus the detection measures above.
- With 12 out-of-scope files, 0 leaks still leaves an upper bound near 22% (95%), so leakage is also watched on every file in shadow and in the pilot (@model-risk M2).

## What it does not change

No prompt, model, OCR or extraction change. No published score or gold rewritten. The send rule is unchanged: only @account-manager approves a send (D-017).

## Who approves

- @model-risk: checks this revision (High only) against its H1/H2.
- @user: types `approve change P-055` in this chat before any build.
