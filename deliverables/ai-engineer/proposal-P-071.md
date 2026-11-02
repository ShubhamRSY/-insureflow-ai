# P-071 — The stated cooking line is added only when no document in the folder states cooking

- Author: orchestrator (main session), 2026-10-22. **Not approved, not built.** Development data only. Not a production approval; the T-027 veto stands.
- Raised because @model-risk blocked T-118 (`deliverables/model-risk/T-118-check.md`, High H1): P-070's `complete_cooking_line` can turn a held file into a false complete. This proposal fixes that High finding and nothing else.

## Problem

`complete_cooking_line` (`underwriting_pipeline/ai/prepare.py`, added by P-070) appends "; no cooking" to the operations value when the cited document says `Cooking operations: None`. It checks for cooking equipment only:

1. in the **cited** document, never the other documents in the folder, and
2. with a short list (`OPS_COOK_EQUIPMENT`: fryer, kitchen, grill, microwave, cook stove, cooking equipment, deep fry), which misses griddle, wok, oven, smoker, broiler, burner and more.

Reproduction (from @model-risk, end to end through `process_submission`): application `Cooking operations: None`, email "the tenant added a flat-top griddle and a wok station". Before P-070: `complete — review pending`, operations flagged. After P-070: `complete`, operations "…; no cooking" at 0.95, no flag, no conflict. That is a false complete.

## Change (inside `underwriting_pipeline/ai/prepare.py`, plus one shared word list)

1. **Read every document.** Before the line is appended, `complete_cooking_line` checks the text of **every** document in the submission (`texts`, all documents) for stated cooking. If any document states cooking, nothing is appended. The value and the existing flag ("operations may be missing: no cooking") stay exactly as they were before P-070, so the underwriter sees the flag and decides.
2. **One equipment list, no third list.** The cooking-word check uses the words already in the code:
   - the workbench equipment list `EQUIP` (fryer, burner, flat-top, griddle, charbroiler, broiler, oven, smoker, comal, wok, freidora, horno, …). It moves from `app/workbench.py` to `prepare.py` as `COOK_EQUIP`, and `workbench.py` keeps `EQUIP = prepare.COOK_EQUIP`, so the list has one home and the routing rules see exactly the same words as today;
   - `HAZARD_TERMS` (already in `prepare.py`);
   - `OPS_COOK_EQUIPMENT` (P-070's own pattern).
   The check is deliberately cautious. A negated mention ("no fryer") also counts as stated cooking, so it **keeps the flag**: the worst case is the pre-P-070 behaviour (a flag for the underwriter), never a false complete.
3. **Option not taken:** opening a new cooking conflict. Keeping the flag is the smaller change and already holds the file for review; a cooking conflict topic would be new pipeline behaviour, so it would need its own P-###.

## Self-checks (development files only, no model call, no hold-out file)

- **New dev file SUB-296** in `simulation/inbox-dev/document_conflicts/`, built by `deliverables/producer/build_document_conflicts_dev.py`, with a dev note and a manifest line: the application says `Cooking operations: None`, and the email says the tenant added a flat-top griddle and a wok station. Its loss run uses the **published Carrier A format**, so the file does not hold on the loss run and the test only passes if the cooking rule works (see @model-risk M4).
- An end-to-end assertion **through `process_submission`** with the model call stubbed: SUB-296's status is not `complete`, the operations value does not contain "no cooking", and the operations flag is present.
- Rule-level checks in the `prepare.py` self-check block: equipment in another document blocks the append; the existing P-070 cases still behave (SUB-293: the value already says no cooking, so nothing is added twice).
- `prepare ok`, `workbench ok`, `package ok`; `pytest tests/pipeline` green; the frozen v11 self-check and the frozen lint green; pyright shows no new finding.
- Request equality: `llm_extract.py` is not touched, so `PROMPT_VERSION` and `cache_key` stay the same and **zero requests change**.

## Not included (stays in the backlog, as @model-risk listed it)

- M1–M5 and L1–L3 from `T-118-check.md` (sales first-figure, square feet across buildings, count noun, dev loss-run format for SUB-290–295, provenance, rule-added confidence, "N/A" wording). Each is a separate item.
- No frozen file is touched: no `eval_holdout_*.py` scorer, no hold-out gold, no `simulation/inbox/` hold-out file, no published score.

## Risk

- A document that only mentions equipment in passing ("no fryer on site", a "grill" in a business name) keeps the flag. That is the pre-P-070 behaviour and fails safe; the underwriter clears it on the card.
- Moving `EQUIP` to `prepare.py` is a pure move: the same tuple, re-exported under the same name in `workbench.py`. The workbench self-check (`workbench ok`) proves the routing rules are unchanged.

## D-065 (the workbench)

No new field, status or reason: the card shows the existing operations flag, exactly as before P-070. So there is no new screenshot and no "What's new" line, and the @senior-underwriter UI review is not needed again. If the build turns out to change anything the underwriter sees, those steps are done after all.

After the build, @model-risk re-checks T-118 (a fresh reviewer, task id, criteria and paths only).

To approve, the user types: `approve change P-071`.
