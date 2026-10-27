# T-118 — @model-risk re-check after P-071 (D-123)

- Reviewer: @model-risk (independent, fresh dispatch). Date: 2026-10-23.
- Scope: T-118 criterion "@model-risk checks the fix on dev with no High before it counts toward H1/H2 closure". High in detail; the rest one line each.
- Read: uncommitted `git diff` of `prepare.py`, `workbench.py`, `package.py` on `fix-t117`; `proposal-P-071.md`; `P-070-as-built.md` § P-071; SUB-296; D-122, D-123; my `T-118-check.md`. I did not read the author's T-118 messages or the task Notes.
- Ran (temp copy of the worktree, D-069; no model call, no hold-out file; nothing written in the worktree except this file and one DISCUSSION entry): `prepare ok`, `workbench ok`, `package ok`; `pytest tests/pipeline` 43 passed. `workbench.EQUIP` is byte-equal to HEAD's tuple. `llm_extract.py` is unchanged, so the request stays byte-identical. End-to-end probes through `process_submission`, with the model stubbed the same way as the SUB-296 self-check, on new (HEAD) and old (P-070 + P-071) code.
- Synthetic data. **Not a production approval.** An approved P-### is not a production approval, and the T-027 veto stands.

## Verdict: BLOCK. This does not count toward H1/H2 closure.

P-071 closes the exact case I reproduced (griddle + wok). It does not close the finding. The rule still reads a document's silence on cooking as a statement of "no cooking", and it decides that silence from a fixed equipment word list. Any cooking statement that uses words outside the list still turns a held file into a false complete.

## High finding

### H1 (still open, same class): another document that states cooking in words outside the list still gets "; no cooking" and a false complete
SUB-296 (application `Cooking operations: None`, published Carrier A no-claims run) with only the email sentence changed:

| Email sentence | HEAD (before P-070) | P-070 + P-071 |
|---|---|---|
| "flat-top griddle and a wok station" (SUB-296) | complete — review pending | complete — review pending ✔ |
| "We started cooking hot breakfast for clients every morning on a stove." | complete — review pending | **complete**, "…; no cooking", no flag |
| "The tenant now runs a small cafe serving hot food prepared on site." | complete — review pending | **complete**, "…; no cooking" |
| "They added a hot plate and a panini press in the break room." | complete — review pending | **complete**, "…; no cooking" |
| "Staff barbecue every Friday on the patio, plus a rotisserie." | complete — review pending | **complete**, "…; no cooking" |
| "We now fry chicken wings for walk-in customers." | complete — review pending | **complete**, "…; no cooking" |
| "A range and a commercial hood with Ansul system were installed." | complete — review pending | **complete**, "…; no cooking" |

Six of seven plain cooking statements are new false completes. The worst is the first: the word "cooking" itself, and "stove", do not count, because `states_cooking` matches only `OPS_COOK_EQUIPMENT` (which has "cook stove" and "cooking equipment" but not "cooking", "cook" or "stove"), `COOK_EQUIP` and `HAZARD_TERMS`. The self-check proves only the one sentence it was written for. A mutation check against the P-070 rule cannot show that the coverage is wide enough.

Why this is High: 0 false completes is the T-027 gate's hardest criterion. On every row above, the fix removes the only signal that held the file, and it writes a confident hazard fact ("no cooking", rule-added at 0.95) that another document contradicts.

What resolves it (code change in `prepare.py`, so it needs the user's `approve change P-###`):
1. Make the default "keep the flag". Append "; no cooking" only when no other document, and no other line of the cited document (mask the matched `Cooking operations:` line), contains any cooking or food stem: at least `cook`, `fry/fried/frying`, `stove`, `range`, `hood`, `hot plate`, `food`, `cafe`, `meal`, `lunch`, `breakfast`, `barbecue/bbq`, `rotisserie`, `panini`, `toaster`, plus the existing lists. Over-holding is safe; under-holding is not. Or drop the append altogether and leave the cooking slot to the v-next scorer.
2. Add a dev self-check through `process_submission` that runs the seven sentences above, plus at least three more paraphrases written by someone other than the author (for example @senior-underwriter), and asserts that none is `complete`.

## Medium / Low (one line each)
- M-a The SUB-296 card flag still says "operations may be missing: no cooking" while the email states a griddle and a wok, and the card's cooking-equipment check reads "not stated" (it reads only the application). The underwriter is pointed the wrong way. A wording/UI fix is needed (D-065).
- M-b The earlier M1–M5 and L1–L3 from `T-118-check.md` are unchanged (sales first figure, sq ft across buildings, count noun, SUB-290–295 loss-run format, provenance, rule-added confidence, "N/A").
- L-a The P-071 behaviour change on SUB-293 (the flag stays on "no kitchen or any cooking") is correct and fails safe.

## What passes
- The exact griddle/wok reproduction now holds end to end. The EQUIP move is a pure move. The request is byte-identical. The self-checks and `tests/pipeline` are green. No frozen file, hold-out file or published score is touched.
