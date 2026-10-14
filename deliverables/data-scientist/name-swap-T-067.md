# Name-swap counterfactual test (T-067)

- Author: @data-scientist. 2026-10-14. D-070 item 4, D-023 item 5. Synthetic. Not a production approval.
- No model call (`llm_extract._post` raised), cache read from a scratch copy, no real workbench, log, or outbox file written. No rule, prompt, scorer, or score file changed.
- Files tested: 7 of 60 development files (SUB-017 to SUB-076); skipped 53: 6 name only in a scan or PDF; cannot be swapped (027, 038, 053, 067, 071, 074); 45 no cached reply (017, 018, 019, 020, 021, 022, 023, 024, 025, 026, 028, 030, 031, 032, 033, 034, 035, 036, 037, 039, 040, 041, 043, 045, 046, 047, 048, 049, 052, 054, 055, 057, 058, 059, 060, 061, 062, 063, 064, 065, 066, 068, 069, 072, 075); 2 swap not taken (named insured still read from a scan) (042, 056).
- Swap names (8): Guenther Tacos y Mas; Blanco Street Kitchen; Fryer and Sons Bookkeeping; Open Flame Yoga; Hood Street Books; Garcia Holdings; Smith Holdings; Nguyen Holdings. Pairs run: 56.
- **Files whose score changed: 0. Files whose carrier match changed: 0. Files whose status changed: 0.** Pairs changed: 0 of 56.
- Compared per pair: points, reason codes, the three display lines (loss history, cooking, hood), scored versus Not scored, carrier route and its note, status.

## How it stays on cached results, and what it tests

- The cache key holds the file text, so swapping the name in the input files would miss the cache. Instead the folder is copied, the name is swapped in its md and csv text, and the cached model reply is rewritten with the same swap and saved under the key of the swapped text. The cached reply is the original model output; no new one exists.
- Tested: everything after the model. The gate (quote must be found in the text), the document rules, the cooking facts, the cue list for producer asks (T2 removes the name before cues are matched), completeness and status, the points, and the carrier match.
- Not tested: whether the model would read a different name, or a Spanish versus English name, differently. That needs a model call and a P-###; the cached replies cannot answer it. Names in scans or PDFs cannot be swapped here: a file whose name is only in a scan is skipped, and in a mixed file the items cited to a scan keep the old name.
- A name appears where the original `named_insured` string (and the same string without LLC, Inc, or Corp) occurs, case-sensitive. A differently spelled mention is left as it is.

## Changes

None. Every pair gave the same points, codes, display lines, carrier route, note and status.

## Limits of this result

- Only 7 files could be tested: the cache holds replies for 15 of the 60 development files (the same 15 as B-222), and 8 of those have a name in a scan or in a scan-cited item. Of the 7, 1 carry a number; the rest are incomplete, so their points are Not scored before and after. "No change" for them means the status, the Not scored reason, the cooking lines and the carrier route did not move.
- It is a pass for these files only, not evidence for the 60 or for the inbox. More files need more cached replies, which means model calls and a decision.
- The five trigger-word names did not change any file's producer ask (the T2 name removal held on the swapped text) or the cooking line. No test file carries a stated cooking fact, so a trigger-word name next to a real fryer line is covered by the prepare.py self-check, not here.

## Per file (before the swap)

| File | Status | Points | Codes | Route |
|---|---|---|---|---|
| SUB-029 | incomplete | Not scored | - | hold |
| SUB-044 | incomplete | Not scored | - | hold |
| SUB-050 | incomplete | Not scored | - | hold |
| SUB-051 | complete | 0 | - | carrier_a |
| SUB-070 | incomplete | Not scored | - | hold |
| SUB-073 | incomplete | Not scored | - | hold |
| SUB-076 | incomplete | Not scored | - | hold |
