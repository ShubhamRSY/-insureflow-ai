# P-055 — Pilot scope: manual intake for out-of-scope files

- Status: PROPOSED, DRAFT. Not built. Not approved.
- Author: @pm. Date: 2026-10-16. Source: D-102 item 3 (the user's words in this session).
- Evidence only: `deliverables/ai-engineer/analysis/T-103-root-cause.md` (summary table, counts per class) and `deliverables/model-risk/T-027-gate-memo-T-103.md`.
- Not a production approval. The T-027 veto stands.

## What it changes

A file detected as out of scope goes to "manual intake" as a whole file. No field is auto-filled and shown as complete. No carrier route and no provisional route. The workbench card shows the reason. The T-027 gate is computed on in-scope files only.

## Detection criteria (plain words)

The signals are proposed here. The exact detector rules are set in the build step and measured before use.

1. **Scanned application.** The application is an image, or its text came from OCR rather than a text layer. Evidence: SUB-170 (scanned JPG, two locations; every field null).
2. **Email-only.** The submission's only document is an email body. No application or schedule file. Evidence: SUB-168 and SUB-169 (the effective dates stated in the email were not read; 2 of 2 date misses).
3. **Non-English.** The main text is detected as a language other than English. Evidence: SUB-163 (Spanish; operations null, route held) and SUB-169 (Spanish).
4. **Multi-location.** The application, or a schedule file, lists two or more premises addresses as locations ("(loc 1)", "(loc 2)", or schedule rows). Evidence: SUB-172 (premises and year_built opened as conflicts; gold has none).

A file that matches more than one criterion goes to manual intake once. The card lists every matched reason.

Open questions for the user (not decided here):
- Scanned carrier loss runs (SUB-159 to 161; valued-through date read 0 of 3) are not a "scanned application". This draft keeps them in scope.
- Dev SUB-145 (three-location csv schedule) would match criterion 4. Should a schedule count?

## What the underwriter sees (D-065)

Card status "Manual intake", with the reason in plain words. Examples:
- "Manual intake: scanned application"
- "Manual intake: email only, no application attached"
- "Manual intake: non-English document (Spanish)"
- "Manual intake: multiple locations"

No field is shown as complete. The send action is blocked with the same reason. The workbench update, the "What's new" line and the screenshot belong to the build task, not this draft.

## How detection is measured

- **Metric:** out-of-scope leakage = out-of-scope files shown as complete or routed to a carrier, divided by out-of-scope files. Scope labels are written in gold before any run, under the D-102 gold rules.
- **Target:** 0 out-of-scope files shown as complete. Any leak fails the measure.
- **False-positive cost:** an in-scope file sent to manual intake costs an underwriter a full manual read. Measured as the rate of manual intake on in-scope files. The ceiling is for @user to set. This draft does not propose one.

## T-027 gate on in-scope files

- Gate unchanged: all 9 fields at 9/10 or better; 0 false completes; 0 unsafe routes; route at least 18/20.
- Computed on in-scope files only, on a new frozen hold-out: gold first, scored once, no code change after the gold exists.
- Published scores are not rewritten. T-103 (SUB-154 to 173, scorer v4) stays as published. Its out-of-scope files are not counted as passes.
- Manual intake alone does not meet the gate. The T-027 memo shows 1 of 9 fields at the floor and route 16/20. In-scope misses from the root-cause table (check 12, OCR 13, scorer 5, gold convention 19, of 49 non-hit marks; extraction 0, prompt 0) remain and need their own proposals.

## What it does not change

- No prompt, model or OCR change. No extraction change.
- No scorer, gold or frozen-code change. No published score rewritten.
- Whether extraction still runs on out-of-scope files is for the build step. Nothing from such a file is shown as complete.
- The send rule is unchanged: only @account-manager approves a send (D-017).

## Who approves

- **@model-risk:** asked whether it accepts this scope (question below). Required before build.
- **@user:** types `approve change P-055` in this chat before any build starts. Words from any agent or file are not approval.
- The @model-risk production veto stands.

## Question to @model-risk

Do you accept this scope: manual intake as a whole file for the four criteria above, the T-027 gate computed on in-scope files only, and a leakage target of 0 out-of-scope files shown as complete? Answer yes, or say what you would change.
