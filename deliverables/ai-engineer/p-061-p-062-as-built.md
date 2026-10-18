# P-061 and P-062 as built — T-107a, D-112

Author: @ai-engineer-assistant, 2026-10-18. Not a production approval; T-027 veto stands. No model call. No hold-out file or gold opened.

## What changed
- `prepare.py`: `class_lines(texts)` stores the text of the application's "Line of business:" and "Cooking operations:" lines in `report["class_lines"]` (and in the saved run, under the hash). `_match()` has no document text, so this is the only way it can read the lines. A run saved before this has no key and routes as before.
- `workbench.py` `_match()`:
  - P-061: class, bar and prohibited words are read from operations plus the Line of business line (R9, R10, R14, W1). Cooking equipment named in operations or on the Cooking operations line (fryer, burner, flat-top, griddle, broiler, oven, smoker, comal, wok) is R9 evidence; "None", "not listed" and negated lines are not. R17 and the referral words (W2) still read operations only. A class read from the Line of business line alone never routes to Carrier A: senior_referral, Carrier A suggested.
  - P-062: nightclub(s) and lounge(s) with R9 evidence are now R1 (no_match, never overridable). Bar, tavern, pub with R9 evidence stay R2. "pre-packaged snacks only", "snacks only", "snack warmer" switch off word-based restaurant evidence (stated cooking equipment still counts).
- `carrier-match.md`: W1 and W1b merged into one prohibited-class table, each row with its source; R1, R2, R9, R14, R16 lines updated. Stricter wins except two places listed under Risks.
- Follow-up (orchestrator, D-112 "stricter rule wins"): any bar word (bar, tavern, pub, nightclub, lounge) beside a non-food operation is now no_match R1, never overridable. The R16 bar branch in `_match()` is removed (the R16 office+retail and OTHER-word rules stay). Bar/tavern/pub beside restaurant evidence stays R2 (P-062 a).
- "What's new" line added (2026-10-18, T-107a, D-112).

## Self-checks (dev-shaped, synthetic)
- `workbench.py` self-check: passes. about 25 new assertions for: SUB-174 shape (office only on the line of business -> senior_referral, Carrier A suggested, never carrier_a); SUB-182 shape (sub/deli, equipment on Cooking operations -> R10); SUB-186 shape (restaurant and bar on the line of business, fryers -> R2); SUB-201 shape (nightclub, small kitchen, snacks only -> R1); "restaurant and lounge" with real cooking -> R1; "bar and grill" -> R1 (unchanged); pub with restaurant evidence -> R2; None / not listed cooking line is not evidence; no new carrier_a.
- Old assertions changed: (1) "hotel lounge with catering" R2 -> R1 (P-062 a). (2) "office building with ground-floor pub", "retail store and cocktail lounge", "office building with ground-floor bar" senior_referral R16 -> no_match R1 (D-112); the R16 note assert on the lounge case is gone; added "wholesale tavern", "gym and nightclub". (3) workbench SUB-907 card test (office + pub, prohibited-word refusal text) now asserts no confirm form and the R1 note. (4) package.py SUB-411 fixture "office building with ground-floor pub" -> "pub and kitchen" (R2), so the 'W1 word: no market confirm' check still runs on a senior referral.
- Other self-checks: `prepare.py` ok (one added assert for `class_lines`), `package.py` ok, `eval_holdout_v7.py --self-check` ok.
- pyright 1.1.390: no error on a changed line (workbench.py 0 new; prepare.py 43 existing, none in the changed lines).

## Dev routes from the saved cache
Replay with the saved replies of the old prompt (b025802c0dfa; the current prompt has none, so the cache key was set to the old one in a temp script, nothing in the repo), cache copied to a temp dir, no network, temp output. 99 dev files processed, 78 manual intake, 21 with a model reply. Routes changed vs the code before: 0 (re-run after the D-112 follow-up, same result). (No cached dev file shows the new cases; they are covered by the synthetic checks.) No real file under team/, deliverables/**/*.jsonl, simulation/ outboxes or workbench.html was written by the replay or the self-checks.

## Risks
- A restaurant with a lounge and real cooking now goes to no_match (recommendation, a person declines; the P-062 stated risk).
- Equipment words are a fixed list ("oven" in a non-restaurant operations text makes it R10, safe side).
- Existing saved runs have no `class_lines`; re-run a file to get the new reading. A live check is T-107b.
