# P-015 prepare.py part, as built (S3, T2)

- Author: @ai-engineer-assistant. 2026-10-14. D-070 item 4, D-040 (S3 H1 M1 T2 V3 W1 A1 E2). Synthetic. Not a production approval.
- Changed: `underwriting_pipeline/ai/prepare.py` only. No prompt change (PROMPT_VERSION unchanged), no new model call, no scorer or score file touched. Extraction scores do not move.

## S3: cooking facts from the labelled lines, with a citation
- New `cooking_facts(texts)`, read like `sprinklers_yes`. Lines read: `Cooking equipment:` and `Hood and fire suppression:` (also `Hood and suppression:`, `Hood:`, `Suppression:`). First file with the line wins. Uses `extract_labeled`, so the citation is checked against the text.
- Saved in the run as `report["cooking"]` and in the saved payload as `"cooking"` (so it is under the saved hash). A run saved before this change has no `cooking` key: read it as `not_stated` for both facts.

### Exact keys for `models/points.py`
`run["cooking"]["equipment"]` and `run["cooking"]["hood_suppression"]`, each: `{"state", "terms", "source", "start", "end", "quote"}`.
- `equipment.state`: `"yes"` (a hazard term stated, not negated; `terms` lists them), `"none"` (line starts no / none / not / without / sin / ninguno / n/a), `"other"` (a line with no hazard term, e.g. "microwave"), `"not_stated"` (no such line anywhere).
- `hood_suppression.state`: `"stated"`, `"none"`, `"not_stated"`. H1: shown beside the code, no points either way.
- Hazard terms (whole words, English and Spanish): fryer(s), freidora(s), open flame, llama abierta, charbroiler, grill, parrilla. `campana` and `supresión` are not hazards (hood/suppression is its own fact).
- `source`, `start`, `end`, `quote`: the file and the character span of the stated text in that file; all null when `not_stated`.
- Not read: class words, cuisine words, the insured's name, the `operations` value, email prose ("They use fryers", "Fryers, full hood"). Only labelled lines. In today's inbox only SUB-002 and SUB-011 (reply.md) carry such lines. SUB-011 is gold-incomplete; SUB-002 has no gold.
- Hood and suppression text is not interpreted beyond "stated" or "none" (a line "Hood: not installed" reads as `none`).

## T2: the ask for cooking equipment
- "taco" removed from the starting cue list (now restaurant, fryer, kitchen: class and equipment words).
- The insured's name is removed from the text before cues are looked for: the extracted `named_insured` value plus any `Named insured:` line. Limit: for an email-only file where the model returned no name, the name is not removed (no labelled line to find).
- The ask cues are now matched at a word start, so "childhood" no longer satisfies "hood".
- Effect: "Guenther Tacos y Mas", "Blanco Street Kitchen", "Fryer and Sons Bookkeeping", "Open Flame Yoga", "Hood Street Books" no longer start an ask; a taqueria with no class or equipment word is not asked (same as a pizzeria today).

## Self-checks (in prepare.py's block, `.venv/bin/python underwriting_pipeline/ai/prepare.py`, LLM_* unset)
Fact states and citation spans (yes / none / negated Spanish / other / not_stated); names, class and cuisine words give no fact; the five names above and a cuisine word give an unchanged `extra` list on the same text; a class word still asks. All pass: "prepare ok". Also run and pass: ai/llm_extract.py, ai/sources.py, app/workbench.py, app/package.py.

## Not done (not mine)
`points.py` reads these keys (@data-scientist); workbench lines (@software-engineer). No UI change in this part, so no screenshot.
