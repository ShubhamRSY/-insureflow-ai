# P-075 — Copy the application's own "Cooking operations: None" line into operations (cited, verbatim); any cooking mention in another document opens a conflict and holds the file

- Author: @ai-engineer-assistant, 2026-10-24. **Not approved, not built.** Draft for @user to read (D-131). Development data only. Not a production approval; the T-027 veto stands.
- Raised by @model-risk T-027 memo after T-119, High H1 (`deliverables/model-risk/T-027-memo-T-119.md`, backlog B-468). Scope is the user's own, D-131. Builds on P-074 (D-132): conflicts that cannot be verified stay open.
- Nothing was run. No model call. The only probes were on dev text and the frozen v11 scorer's function, read only (results below).

## Problem

On T-119, 9 of 14 files whose application says `Cooking operations: None` dropped the line from the operations answer (D-127: a miss under v11). The model keeps it on the other 5, so the behaviour is inconsistent. The prompt already says to read that line and keep "None" as no cooking, and to quote it as an extra part (`SYSTEM`, `small_commercial.json`). More prompt words are a weak lever. Earlier code attempts failed for one reason: they read silence as "no cooking" (T-118 H1, three BLOCKs: griddle/wok, then cook/stove/hot food, then the scorer's 45 probes). P-075 never reads silence. It copies a line that is there, and it only does so after a scan of every document finds no cooking word.

## Change (a rule after extraction; no prompt change)

**A. Copy the line, `prepare.py`, before `check_operations`.**
- Trigger: the application (a document named `application*`, typed text, not an OCR read) has a line `Cooking operations:` whose whole body is one of: `None`, `No`, `Nil`, `No cooking`, `No commercial cooking`, `No kitchen` (case-insensitive, optional full stop). `N/A`, blank, anything with equipment or extra words are not copied (T-118 L2; they keep today's P-059 flag).
- If the operations answer already carries it (P-059's `ops_line_missing` finds nothing missing), nothing is added.
- Otherwise append the line **as written**, `; Cooking operations: None`, to the operations value, and store the line as its own cited part (source, offsets, exact quote) on the row (as `also_quoted`; works when operations is cited from the email, as on SUB-346/355). The words "no cooking" are never written by the rule. The row is marked `rule_copied`, and the confidence is not raised (the withdrawn P-070 set 0.95).
- Only if step B finds nothing (below). If B opens a conflict, nothing is copied.

**B. Cooking mention anywhere else is an open conflict and a hold (through P-074's path).**
- Applies when the application's line is one of the none-shapes in A, or the operations answer says none/no cooking (this catches the SUB-349 shape, where the model itself wrote "None").
- Scan every document in the folder, including the other lines of the application itself (SUB-348's application says "Sprinklers: Yes, hood only"). Not read: the matched `Cooking operations:` line, and the insured's name (reuse `_without_name`, P-015 T2).
- A hit opens `cooking` as a conflict: side 1 = the application line, side 2 = the other document's sentence, each with source and exact quote. The conflict is appended like `apply_sales_conflicts`; nothing is cleared, the file is incomplete, not routed, not sent. The operations value stays as the model gave it with NEEDS REVIEW, reason "cooking: the documents disagree".
- Schedule CSV: the `cooking` column (header only is not read). Any value other than blank, no, none, n/a, 0, false is a hit. (Dev check: the 12 schedule files in SUB-270–287 all say "No", so they do not hold.)
- **Word list** (whole words, case-insensitive; widened with every word the earlier checks found missing, incl. @model-risk's P-073 table): cook*, fry/fried/frying/fryer*, deep fry*, freidora/fritura, grill*, griddle*, flat top/flat-top, plancha, parrilla, comal, wok, stove*/stove top, estufa, cooktop, hot plate, burner*, range/ranges, oven*, horno, broil*, salamander, smoker*, barbecue/bbq, rotisserie, tandoor, panini, sandwich press, toaster*, waffle*, pancake*, skillet/tilt skillet, steamer*/steam table, sous vide, heat lamp, warming cabinet/oven/drawer, hot food/dog/breakfast/lunch/meal/soup, hotdog, heat(s/ed/ing) up soup/food/meal/water, boil*, bake/baking/bakery, kitchen*, cocina/cocin*, galley, food prep*/food service/food truck, prepared on site/prepared food, meal*, cafe/café/cafeteria, restaurant*, diner, eatery, lunch, breakfast, dinner, snack*, soup*, microwave*, hood, Ansul, UL 300, grease. "range" is skipped inside "price range, age range, range of, within range, wide/full range".
- **Negations fail safe.** A negation never voids a cooking word: "no fryer", "fryer removed last year", "no beer we fry wings", "wings fried daily and beer none" all open the conflict (hold, one underwriter click). The only words not counted are the exact agreeing phrases, removed before the scan: "no cooking", "no commercial cooking", "no kitchen", "no food prep*", "do/does not cook", "cooking operations: none/no/nil". "no cooking, but we fry wings" still hits on "fry". Any other wording of an agreeing statement ("There is no kitchen or any cooking on site", SUB-293) also holds. That is a false hold by design, never a false complete.
- The scan also runs when the model carried the none line itself (5 of the 14 on T-119; SUB-349). This tightens today's behaviour.
- **Residual risk, stated plainly:** a cooking statement in a word that is not on the list is not seen. The list is a finite list, not a parser, and @model-risk has shown three times that no list is complete. This is why the recommended build keeps a review note on the copied line (Status effects below), so a missed word cannot turn a held file into a clean complete.

**C. The whole-document check flags a stated cooking line missing from the answer** (`check_operations`, `prepare.py` ~1081). Today it reads only the document that operations is cited from. P-075 also reads the application's `Cooking operations:` line when operations is cited from another document, and flags "operations may be missing: <line>" whenever the answer lacks it and A did not copy it (conflict, scan, or a line not in A's none-shapes). The existing P-059 flag stays for those. Never silent.

**Scorer check (probe, read only, frozen v11 `ops_items_hit`, gold "no cooking; 48 seats").** "Insurance agency office, 48 seats; Cooking operations: None" scores a hit (also "cooking operations: none" and "no cooking"). With the line omitted: a miss. "Cooking operations: None; fryer": a miss. So the verbatim copy reads correctly under v11 with no scorer change. `Cooking: none` would not score, so the rule never reshapes the label.

## Requests, PROMPT_VERSION, cache (item 6)

- **Recommended build: `SYSTEM` and `request_for` are not touched.** `PROMPT_VERSION` (759b3e6bc9b2) and every cache key stay the same. **Changed requests over the 143-folder set (SUB-127 to SUB-269): 0 of 143.** Stored replies stay valid; dev checks run on them or on stubs with no model call.
- Test: `tests/pipeline/test_request_equality.py` only compares LOB_ENGINE off with on, so it would also pass if SYSTEM changed. To prove "0", the build records the SHA-256 of each of the 143 request bodies from the current HEAD in a new fixture file (`tests/pipeline/fixtures/request_baseline.json`) before any edit, and adds a second test that the 143 equal it. Result expected: 143 identical, 0 changed.
- **Option, not recommended: also add a prompt sentence.** `SYSTEM` is the system message of every request, so **143 of 143 requests change**, `PROMPT_VERSION` changes (and `prompt.version` in `small_commercial.json`), and every cache key changes. Every stored reply (T-119-live, the dev sets, `regression_dev.py --quick`) becomes unreachable. Dev checks would need stubs, or new model calls, which I will not make without your word (15 for the quick set, one per dev file). The baseline fixture would be regenerated and the test would list 143 changes as expected. The model already drops the line with the sentence in place, so I expect little gain. Say if you want this variant.

## Status effects (item 7)

| Case | Before | After |
|---|---|---|
| Application none-line, no cooking word anywhere else, answer lacks the line | operations NEEDS REVIEW "operations may be missing: no cooking"; complete — review pending | line copied, cited; operations keeps NEEDS REVIEW "cooking line copied from the application (P-075); no other document states cooking"; **complete — review pending, unchanged** |
| Cooking word in another document, or schedule cooking Yes | complete — review pending (SUB-349/348 shape), no conflict | open `cooking` conflict, incomplete, held, no carrier match, no send |
| Model carried the line, another document states cooking | complete | open conflict, held |
| Line not a none-shape, scan read, `N/A` | flag | same flag |

- **Recommended: the copied line never makes a file read complete.** The review note stays, so the status is what it is today. The file reads complete only if the model itself carried the line and nothing else is flagged, as today.
- **Variant, your choice:** clear the note after a clean scan. Then a file with no other flag moves from "complete — review pending" to "complete". Argument that this is not a loosening: it ends as a file where the model carried the line (5 of 14 on T-119), which reads complete today, and the scan makes that case stricter. Counter-argument: this is the exact T-118 path. A cooking word that is not on the list would then hold nothing. I recommend the note stays until T-120 shows the list holds; clearing it is a later, separate P-###.
- Every other change is toward held or review. `ready_to_route`, the send gate, completeness, appetite and routing are not edited.

## Dev checks only (item 8; no model call, no hold-out file)

New dev files in `simulation/inbox-dev/document_conflicts/` (builder `deliverables/producer/build_document_conflicts_dev.py`, dev note, manifest; SUB-299 and up are unused), model replies stubbed from stored shapes read from a temp copy of the cache (D-069):
- **SUB-299** (SUB-348 shape): application none + "Sprinklers: Yes, hood only"; email "stove top ... flat grill ... hot food". Expected: `cooking` conflict, held.
- **SUB-300** (SUB-349 shape): application none, model carried "Cooking operations: None", schedule `cooking` = Yes, email "griddle". Expected: conflict with the schedule side, held.
- **SUB-301** (T-119 shape): clean "Cooking operations: None", nothing else, stub reply drops the line. Expected: line copied with offsets, review note, status unchanged, `ops_items_hit` hit under frozen v11 (probe only, no score file).
- **SUB-302** (negations): "no fryer", "fryer removed last year", "no beer we fry wings". Expected: conflict each (a rule-level table, one file).
- **SUB-303** (SUB-350 shape, "plumbing supplies"): model carried "no cooking". Expected: unchanged.
- Re-run on dev: SUB-293 (expected to change: agreeing "no kitchen or any cooking" now holds, a false hold), SUB-294/295 (line copied, status unchanged), SUB-296 (held, griddle/wok/flat-top), SUB-297/298 (P-074 sales cases, expected unchanged status), SUB-350 read only on a temp copy from its stored reply, nothing scored.
- Rule-level self-check: every word above, the P-073 table, the T-118 seven sentences and the negation list. The 45 P-073 sentences are not in `P-073-v12-check.md` (only the table); I ask for them (question 3).
- A dry run of the word list on stored dev text (no model call, no hold-out file): of 21 dev folders with a "Cooking operations: None" application line, 7 are clean (copy applies), 12 are schedule files all saying "No" (no hold), 2 hold (SUB-293 false hold, SUB-296 true). The build counts again on every dev folder before it is checked.
- `python underwriting_pipeline/ai/prepare.py` self-check, `llm_extract` self-check, `workbench ok`; `pytest tests/pipeline` green; `regression_dev.py --quick` (D-022), any field whose hit count drops reported; pyright no new finding; @model-risk check, High only, one look-again (D-129, D-131).
- **Frozen, not touched:** every `underwriting_pipeline/ai/eval_holdout_*.py` (v11 and earlier), all hold-out gold and `simulation/inbox/` hold-out files (SUB-340–371 and earlier sets), every published score file, `underwriting_pipeline/cache/T-119-live`, the parked `deliverables/backlog/P-073-v12/`, the frozen lint. No T-119 re-score (D-020).

## Expected score effect (not measured)

Not re-scored. On a fresh hold-out, the 7 T-119 omissions that were class-right (SUB-340–343, 346, 347, 359) would be carried when no cooking word is present, so I expect operations to rise by about 7 of 20 on that shape. SUB-344, 350, 352, 355 are v11 class-reading misses and are not helped, so the 18/20 floor may still not be reached on operations; that is the v-next scorer work (B-464), not this change.

## D-065 (the workbench)

- Conflicts list and resolve form: a `cooking` conflict shows both sides with source and quote ("Application says: Cooking operations: None. Email says: ... griddle ..."), topic name "cooking" added with the other plain topic names in `prepare.py`. Refusal text for a held file stays "OPEN: no send until the underwriter chooses or enters the value".
- Operations row: the copied line shows as its own cited part and the note "cooking line copied from the application (P-075)". The card's cooking line (it reads only the application today, T-118 M-a) also shows a cooking word found in another document, so the underwriter is no longer pointed the wrong way.
- "What's new" line (date, P-075, D-131); it states that the line is copied as written and "no cooking" is still never added by the system (D-124 stands for inferred adds). Playwright screenshot of the SUB-299 card on a temp copy: `deliverables/software-engineer/screenshots/P-075.png`. @senior-underwriter UI check, High only.

## Risks

- A cooking word not on the list is missed (the T-118 class). Mitigation: the recommended build keeps the review note; the list is checked by @senior-underwriter before the build.
- False holds on agreeing statements ("no kitchen or any cooking", SUB-293) and on benign words (restaurant, meal, range). Cost: one click. Counted on dev before the check.
- The application's own other lines can hold it ("hood only", "Restaurant package"). Intended: a real self-contradiction.
- A rule-copied line is not model text; the card says so.
- OCR: a scanned application is never copied from; it keeps today's flag.

## Questions for @user

1. Review note after a clean scan: keep it (recommended, never complete from this change) or clear it (variant above)?
2. Rule only (0 changed requests, recommended) or rule plus a prompt sentence (143 of 143 change, new cache keys, no stored replies)?
3. The 45 P-073 probe sentences are not stored in full; may I ask @model-risk for them, or write 45 covering the table words?

## Not included

- Any scorer change (v11 stays frozen; B-464 stays in the backlog); any prompt change (option above only if you ask); any gate, route, appetite or send rule.
- Copying a positive or partial cooking line ("Electric ranges only", "N/A"); those keep the P-059 flag.
- Conflicts between two documents that both state cooking (equipment lists), or where the application states cooking and another does not.
- Clearing the review note after a clean scan (a later P-###).
- A model-based cooking check; T-120 planning (a separate step after this).

To approve, the user types: `approve change P-075`.
