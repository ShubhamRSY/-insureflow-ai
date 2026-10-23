# T-118 — @model-risk check of the P-070 fix on dev

- Reviewer: @model-risk (independent). Date: 2026-10-22.
- Scope: T-118 acceptance criterion "@model-risk checks the fix on dev with no High before it counts toward H1/H2 closure". High findings in detail; Medium and Low one line each.
- What I read: the uncommitted `git diff` of `underwriting_pipeline/ai/prepare.py`, `app/package.py`, `app/workbench.py` on `fix-t117`; `deliverables/ai-engineer/P-070-as-built.md`; the dev set `simulation/inbox-dev/document_conflicts/SUB-290–295` and its gold/manifest; D-122; my T-117 gate memo. I did not read the author's T-118 messages or the task Notes.
- What I ran (temp copy of the worktree, D-069; no model call, no hold-out file, nothing written in the worktree except this file and one DISCUSSION entry):
  - Self-checks: `prepare ok`, `workbench ok`, `package ok`; `pytest tests/pipeline` 43 passed. `llm_extract.py` is not in the diff, so the request-equality claim holds.
  - Old (`HEAD`) vs new rules on all 26 dev folders in `simulation/inbox-dev/`.
  - Adversarial probes, rule-level and end to end through `process_submission` with the model call stubbed to the application's labelled lines.
- Synthetic data. **Not a production approval.** An approved P-### is not a production approval; the T-027 veto stands.

## Verdict: BLOCK (does not count toward H1/H2 closure)

The conflict half (H2) works on the planted cases and fails safe: every new path holds a file, none completes one. The cooking half (H1) can turn a held file into a **false complete** when another document states cooking. That is the T-027 gate's hardest criterion (0 false completes), so the fix cannot count toward closure until it is closed.

## High finding

### H1 — `complete_cooking_line` asserts "no cooking" against another document that states cooking, clears the only flag, and the file reads complete
- Code: `prepare.py` `complete_cooking_line()` checks for cooking equipment only in the **cited** document (`texts[row["source"]]`), and only with `OPS_COOK_EQUIPMENT` = fryer | kitchen | grill | microwave | cook stove | cooking equipment | deep fry. Other documents in the folder are never read. Words such as griddle, wok, range, oven, smoker and broiler are not in the list, though `workbench.py` (line ~179) already lists them as stated cooking equipment.
- Reproduction (end to end, `process_submission`, stubbed model, published Carrier A no-claims line): application `Operations: Office of an insurance agency` + `Cooking operations: None`; email "the tenant added a flat-top griddle and a wok station for staff lunches last spring".
  - Before (HEAD): `complete — review pending`; operations flagged "operations may be missing: no cooking", confidence 0.74.
  - After (P-070): **`complete`, complete=True**, operations `Office of an insurance agency; no cooking` at confidence 0.95, no flag, no conflict.
- With "deep fryer" in the email, the P-015 extras still hold the file, but the operations value still says "no cooking" with no flag, so the card states something one of the documents contradicts.
- Why High: this is a document disagreement, the very thing P-070 exists to surface (T-117 H2), and on a hazard fact (cooking drives R10 senior referral). The fix removes the one signal that held the file and adds a confident value that is not in any model answer. The 0-false-complete gate is breached by design, not by chance.
- What resolves it:
  1. Before the line is appended, read **every** document in the folder for stated cooking. Reuse the existing vocabulary (the workbench equipment list / `HAZARD_TERMS`) rather than a third list.
  2. When any document states cooking, append nothing and keep the flag, or raise an open cooking conflict with both sides.
  3. Add a dev file (new number, dev only): `Cooking operations: None` in the application and a griddle or wok in the email. Assert **through `process_submission`** that the status is not `complete`.
- This is a code change in `prepare.py`. It goes through the user's approval (within P-070 or a new P-###, as the user decides).
- Owner: @ai-engineer-assistant.

## Medium (backlog, one line each)
- M1 Sales takes only the first figure per document: "Sales of $412,000 last year; this year sales are $600,000" against $412,000 is missed, and "last year revenue was $380,000 and this year sales are $412,000" raises a false conflict and empties sales.
- M2 Square feet compares schedule rows across buildings: dev SUB-277/287 now raise `square_feet` 8000 vs 3000 for two different locations. It is harmless there only because scope sends them to manual intake. A one-premises, two-building schedule would be held, with a wrong producer question.
- M3 Count topic is mis-filed by the optional word in `COUNT_RE`: "12 unit apartment building" is read as `apartment_count`=12 and "4 HVAC units" as `unit_count`. So real disagreements can be missed and unlike things compared.
- M4 The dev set's loss runs (`| None reported |`) are not the published Carrier A format, so every SUB-290–295 file holds on the loss run end to end. The self-check bypasses `process_submission`, which means "SUB-294 stays complete" and the holds are shown only at rule level. This is the same class as T-117 H3. Fix the loss runs and assert the end-to-end status.
- M5 Provenance: the as-built and the dev gold say they were produced in OpenCode, and D-053 says OpenCode is not used on this repo. The user should confirm the D-122 approval and accept this build in the Claude Code session before it counts.

## Low (one line each)
- L1 The appended "; no cooking" keeps the model's confidence (0.95), though it is rule-added text. Mark the row as rule-completed.
- L2 `Cooking operations: N/A` is turned into "no cooking", but N/A is not a statement of none.
- L3 The dev gold describes itself as "not independently reviewed".

## What passes
- The planted conflicts SUB-290/291/292 raise open conflicts with both sides and hold. SUB-294/295 raise none.
- Across the other 20 dev folders, the only new conflict is M2, and it falls on files that are out of scope anyway.
- The plain topic names reach the card, the resolve form, the send refusal and the producer request. No published score, scorer, gold or hold-out file is touched, and the request is byte-identical.
