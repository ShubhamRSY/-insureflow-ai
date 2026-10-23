# P-073 scorer v12 as built (D-126, H1 only)

Author: @senior-test-engineer, 2026-10-23. Dev only until @model-risk checks it and the code is frozen. 0 model calls (shell LLM_* unset). Nothing committed.

## sha256
| File | sha256 |
|---|---|
| `underwriting_pipeline/ai/eval_holdout_v12.py` | `3bef7f76d76547e677556ed53da7b82112cdf6d3e837876a4c65669f3f210563` |
| `deliverables/senior-test-engineer/lint_holdout_v12.py` (lint used; wraps the frozen lint) | `a5f68045653a9be28ae45854d81760d5bf2ccda77ccf9eceee02e05e99df65e8` |
| `deliverables/senior-test-engineer/lint_holdout.py` (frozen, unchanged) | `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` |
| `underwriting_pipeline/ai/eval_holdout_v11.py` (frozen, unchanged) | `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` |

`git status` shows v11, the frozen lint and every other `eval_holdout_*.py` unmodified; v12 and the lint wrapper are new files.

## What v12 does (item 20 in its header)
Only gold `no cooking` (cooking=none) is affected. Gold light or full is read exactly as in v11.

(a) The answer leaves cooking out. Credited as "none" only if the answer holds no cooking evidence: a non-negated cooking word in any clause (clauses split on `, ; .` and newline). Evidence list: cook*, stove, fry*/fried, kitchen, oven, grill, griddle, burner, bake*, roast, saute, barbecue/bbq, microwave, reheat*, pizza, smoker, simmer, range(s), hood, exhaust, wok, comal, plancha, parrilla, horno, freidora, fritura, flat-top, and phrases hot food/meal/plate/line/dog, open flame, food prep(aration), prepared food, food service, wood fired, steam table, heated food. Negated (a NEG word within 3 words before, or clause ends in no/none) is not evidence. A clause's own "no cooking" statement is removed before the clause is read. A clause with tenant/tenants/residential/residents is never evidence (rule file row 7: "no cooking operations (tenant electric ranges only)" -> none).
- Why the hiding case is closed: evidence in ANY clause is a miss, also when another clause says "no cooking" ("no cooking, we fry wings", "no cooking. hot plate"). v11 read the first as a hit only by luck of clause order; v12 misses both.
(b) "no cooking" in plain words (cooking=none): no food service, no foodservice, no food preparation, no food prep, no hot food, no hot meals, no on-site/onsite cooking, does not / doesn't / do not / don't / did not cook, without cooking, without (a) kitchen, cooking none (plus the v11 phrases no cooking, no kitchen, sin cocina, no hay cocina). The new phrases are tried only after the light and full words: "does not cook; microwave only" is light, "no food service; grill" is full, as v11 order requires.
Side effect (intended): a gold item "no food service" now maps to the cooking slot (rule file line 160) instead of failing the gold check as "fits no slot".

Treatment by case: cooking left out, no cooking word -> hit; "no kitchen"/"does not cook"/... -> hit; cooking present (full, light, any evidence word, also unlisted-word cooking like stove, hot plate, fry wings, barbecue) -> miss; cooking left out against gold light or full -> miss; "no cooking" against gold light or full -> miss; empty answer -> miss; other slot or class wrong -> miss.

## Exact diff v11 -> v12 (`diff eval_holdout_v11.py eval_holdout_v12.py`)
Besides item 20 and the cooking code, the only other edits are version labels ("scorer v11 stopped" -> v12, "(scorer v11)" -> v12, self-check name and print).
```diff
1c1,15
< """Scorer v11 (P-069, T-116, D-119; dev only until frozen). A copy of eval_holdout_v10.py (frozen, sha256 ffd1afdd...302b) plus one change in
---
> """Scorer v12 (P-073, D-126; dev only until frozen). A copy of eval_holdout_v11.py (frozen) plus one change in the OPERATIONS COOKING SLOT
> only (item 20 below). Every other field, slot, gate, the route and the score files are the v11 code path. Written from
> `deliverables/senior-underwriter/operations-gold-rule.md` (slot 7 `cooking`: "no cooking" -> none); no gold answer or score file was read to write it.
> 20. Cooking slot, gold `no cooking` (cooking=none) only. (a) An answer that leaves cooking out is read as "no cooking" ONLY when it holds no
>     cooking evidence at all: no clause with a non-negated cooking word (cook*, stove, fry*/fried, kitchen, oven, grill, range, hood, burner, bake*,
>     barbecue/bbq, microwave, reheat*, pizza, hot food/meal/plate/line/dog, food prep, food service, open flame, ...). Evidence in any clause (clauses split on
>     , ; . newline) is a miss, also when the same answer says "no cooking" in another clause, so a real "cooking present" answer is never hidden.
>     A clause that carries its own "no cooking" statement is read without that statement; a tenant/residential qualifier ("no cooking operations
>     (tenant electric ranges only)", rule file row 7) is not evidence. (b) "no cooking" is also read from plain words: no food service, no food
>     preparation, no hot food, no on-site cooking, does not cook, doesn't cook, without cooking/kitchen, cooking none. These count only when no
>     light or full cooking word is stated positively (microwave only, grill ... win, as in v11). Omission is never credited for gold light or
>     full: a missing cooking slot is a miss there, as in v11. A cooking-present answer against gold none is a miss, as in v11.
> Earlier history, v11 header follows.
> 
> Scorer v11 (P-069, T-116, D-119; dev only until frozen). A copy of eval_holdout_v10.py (frozen, sha256 ffd1afdd...302b) plus one change in
402a417,428
> # v12 (P-073): plain-words "no cooking", and the evidence that stops an omitted cooking slot from being read as "none".
> COOKING_NONE_PLAIN = ["no food service", "no foodservice", "no food preparation", "no food prep", "no hot food", "no hot meals", "no on site cooking",
>                       "no onsite cooking", "does not cook", "doesn't cook", "do not cook", "don't cook", "did not cook", "without cooking",
>                       "without kitchen", "cooking none"]
> COOK_PREFIX = ("cook", "cocin", "stove", "fry", "fried", "fries", "bake", "baking", "roast", "saute", "barbecue", "bbq", "kitchen", "oven", "grill",
>                "griddle", "burner", "microwave", "hotplate", "charbroil", "smoker", "simmer", "reheat", "pizza")
> COOK_WORDS = {"range", "ranges", "hood", "hoods", "exhaust", "wok", "woks", "comal", "plancha", "parrilla", "horno", "freidora", "freidoras", "fritura",
>               "flattop"}
> COOK_PHRASES = ["hot food", "hot foods", "hot meal", "hot meals", "hot plate", "hot plates", "hot line", "hot dog", "hot dogs", "hot entrees", "open flame",
>                 "food prep", "food preparation", "prepared food", "prepared foods", "food service", "foodservice", "wood fired", "flat top", "deep fat",
>                 "steam table", "heated food", "heat food", "heats food", "heating food"]
> TENANT_WORDS = {"tenant", "tenants", "residential", "residents"}
489a516,517
>     elif has(COOKING_NONE_PLAIN):  # v12 (b): only when no light or full word is stated positively
>         out["cooking"] = "none"
682a711,713
> 
> 
> _NONE_STATEMENTS = ["no cooking", "no kitchen", "sin cocina", "no hay cocina"] + COOKING_NONE_PLAIN
684a716,737
> def cooking_evidence(text: str) -> bool:
>     """v12 (a): True when some clause of the answer states a cooking word that is not negated. Clauses split on , ; . newline (not parentheses); a clause's own
>     "no cooking" statement is removed before it is read; a tenant/residential clause is never evidence. Negated = a negation word within the 3
>     words before, or a clause that ends in one ("stove: no")."""
>     for clause in re.split(r"[,;.\n]", _hours(text or "")):
>         toks = item_words(clause)
>         low = " " + " ".join(toks) + " "
>         for p in _NONE_STATEMENTS:
>             low = low.replace(" " + " ".join(item_words(p)) + " ", " ")
>         toks = low.split()
>         if not toks or TENANT_WORDS & set(toks):
>             continue
>         hits = [i for i, w in enumerate(toks) if w in COOK_WORDS or w.startswith(COOK_PREFIX)]
>         for ph in COOK_PHRASES:
>             pw = item_words(ph)
>             hits += [i for i in range(len(toks) - len(pw) + 1) if toks[i:i + len(pw)] == pw]
>         for i in hits:
>             if not (set(toks[max(0, i - 3):i]) & NEG_WORDS) and toks[-1] not in NEG_WORDS:
>                 return True
>     return False
> 
> 
701a755,757
>             elif slot == "cooking" and want == "none":  # v12 (a): omitted = none, but never over a stated cooking word
>                 if cooking_evidence(BT_TOKEN.sub(" ", (answer or "").lower())) or got.get("cooking", "none") != "none":
>                     return False
880c936
<         raise SystemExit(f"scorer v11 stopped: {sid}: {why}")
---
>         raise SystemExit(f"scorer v12 stopped: {sid}: {why}")
922c978
<         raise SystemExit(f"scorer v11 stopped: {sid}: {why}")
---
>         raise SystemExit(f"scorer v12 stopped: {sid}: {why}")
1046c1102
<         raise SystemExit("scorer v11 stopped, nothing scored or written. Gold line problems:\n  " + "\n  ".join(bad))
---
>         raise SystemExit("scorer v12 stopped, nothing scored or written. Gold line problems:\n  " + "\n  ".join(bad))
1064c1120
<         f"# Extraction score (scorer v11) — {IDS[0]} through {IDS[-1]}",
---
>         f"# Extraction score (scorer v12) — {IDS[0]} through {IDS[-1]}",
1125a1182,1195
> 
> 
> def _v12_self_check() -> None:
>     """P-073: the cooking slot. Gold none: omission, plain-words none hit; every cooking-present or hidden answer is a miss."""
>     g = "no cooking; 48 seats"
>     for ans in ("48 seats", "48 seats, no cooking", "48 seats; no kitchen", "48 seats; no food service", "48 seats; does not cook", "48 seats; doesn't cook",
>                 "48 seats; no cooking operations (tenant electric ranges only)", "48 seats; no stove", "48 seats; no hot food", "48 seats; cooking: none"):
>         assert ops_items_hit(ans, g), ("v12 hit", ans)
>     for ans in ("48 seats; we cook", "48 seats; stove", "48 seats; fry chicken wings", "48 seats; hot food", "48 seats; hot plate", "48 seats; barbecue",
>                 "48 seats; range and hood", "48 seats; full kitchen", "48 seats; microwave only", "48 seats, no cooking; we fry wings", "no cooking. hot plate. 48 seats",
>                 "40 seats", "", "48 seats; no cooking operations (range and hood)", "48 seats; no food service; grill"):
>         assert not ops_items_hit(ans, g), ("v12 miss", ans)
>     assert not ops_items_hit("48 seats", "light cooking; 48 seats") and not ops_items_hit("48 seats", "full kitchen; 48 seats"), "omission never credits light/full"
>     assert not ops_items_hit("48 seats; no kitchen", "full kitchen; 48 seats") and not ops_items_hit("48 seats; stove", "full kitchen; 48 seats")
1458c1528,1529
<         print("eval_holdout_v11 self-check ok")
---
>         _v12_self_check()
>         print("eval_holdout_v12 self-check ok")
```

## Case table (lint_holdout_v12.py, data in `CASES`; direct reader and end to end through score_report)
| Gold | Answer | Result |
|---|---|---|
| no cooking | cooking left out (class/seats only) | hit |
| no cooking | no cooking / no kitchen / no food service / does not cook / doesn't cook / no on-site cooking / without a kitchen / cooking: none / no hot food / Sin cocina | hit |
| no cooking | no stove (negated word) | hit |
| no cooking | no cooking operations (tenant electric ranges only) | hit (rule file row 7) |
| no cooking | we cook / stove / fry chicken wings / hot food / hot plate / barbecue / range and hood / full kitchen / microwave only / pizza oven / reheats meals / soups cooked daily / grill / bbq pit / deep fryer | miss |
| no cooking | no cooking, we fry wings; no cooking. hot plate. | miss (hidden cooking) |
| no cooking | no cooking operations (range and hood); no food service; grill | miss |
| no cooking | other slot wrong (40 seats), empty answer, wrong class | miss |
| full kitchen | cooking left out; no kitchen; stove only | miss (v11 and v12) |
| microwave only | cooking left out; no cooking | miss |
| full kitchen | full kitchen | hit |
On every real card with a bare `no cooking` item, 13 wrong replacements (we cook, stove, fry chicken wings, hot food, hot plate, barbecue, range and hood, full kitchen, cooks on site, pizza oven, microwave only, kitchen with fryers, grill and hood) are each a miss; 8 plain-words variants are each a hit; omission is a hit unless the rest of the answer states cooking.
Test the test (`--self-check`): a scorer blind to cooking words fails 24 findings; a scorer that hits everything fails 49; frozen v11 differs on 12 of 42 cases.

## Lint result: PASS (`P-073-v12-lint.txt`)
Command: `.venv/bin/python deliverables/senior-test-engineer/lint_holdout_v12.py PLAN.json --run-date 2026-10-21` (wraps the frozen lint with `--scorer eval_holdout_v12`; perfect answers score 100%, route and P-055 gates pass, every per-field wrong answer, near-miss and unsafe route is caught, plus the cooking stage).
| Set | Frozen lint with v12 | Cooking stage |
|---|---|---|
| T-117 gold SUB-238-269 | PASS 0 failures | PASS (8 real cards) |
| commercial_property dev SUB-280-289 | PASS | PASS (5 cards) |
| commercial_package dev SUB-270-279 | PASS | PASS (5 cards) |
| frozen lint own `--self-check` | SELF-CHECK PASS (36 ok, the one FAIL line is its expected-failure case) | n/a |
| `lint_holdout_v12.py --self-check` | 4 ok | n/a |
Why a wrapper, not an edit: the frozen lint cannot take extra cases as data. It does take the scorer by `--scorer`, which is used. One finding forced the wrapper to replace its generic wrong operations answer: "Unrelated widget assembly" is now a HIT on a card whose items are only `business_type=other_class; no cooking` (SUB-255), because other_class accepts any unlisted class and v12 credits the omitted cooking. The wrapper uses "Unrelated widget assembly; full commercial kitchen with fryers".
Not lintable, same with v11: gold sets 174-205 and 206-237 (`gold-set-T-108-corrected`) are pre-v11 format (items "fit no slot"); 125 failures with v11, 124 with v12 (one fewer, the gold item "no food service" now reads as a slot).

## Dev re-score SUB-127-296, v11 vs v12 (`p073_dev_rescore.py`, `P-073-v12-dev-rescore.json`; no published score file touched)
Method: saved replies only, from a temp copy of the extraction caches (main-repo cache, insureflow-ai-team caches, the worktree's saved-replies and data-engineer extractions; read-only copies). The cache key includes model and host, so qwen/qwen3.8-27b and api.groq.com were patched in-process while the shell stayed unset; no key exists and `_post` raises. Calls made: 0. Gold: migrated copies where the published folder is pre-v11 (127-173 `P-069-dev/gold-SUB-127-173`, 206-237 `P-069-dev/gold-T-108`), `gold-set` for 174-205 and 238-269, the dev gold folders for 270-296.
Coverage: 170 ids. 140 re-scored (76 in scope, 64 out of scope). **30 have no saved reply** (SUB-176/177/178/180/181, 200-205, 270-274, 276, 280-285, 290-296): no cache I can reach holds them under the current request, so they are excluded, not scored. The 127-173 gold has no Scope line, so those 47 ids (36 in scope) are compared on the operations slot only (v11 and v12 `ops_items_hit`); the other eleven fields cannot change under v12 and are 0-changed for the 40 full-card rows.
| Field | Rows | v11 hit | v12 hit | Changed |
|---|---|---|---|---|
| named_insured | 40 | 40 | 40 | 0 |
| premises | 40 | 40 | 40 | 0 |
| effective_date | 40 | 40 | 40 | 0 |
| **operations** | 76 | 48 | **52** | **4** |
| sales | 40 | 39 | 39 | 0 |
| tiv | 40 | 39 | 39 | 0 |
| construction | 40 | 40 | 40 | 0 |
| year_built | 40 | 40 | 40 | 0 |
| loss_runs | 40 | 33 | 33 | 0 |
| conflict | 40 | 32 | 32 | 0 |
| status | 40 | 26 | 26 | 0 |
| route | 40 | 37 | 37 | 0 |
Operations by set (v11 -> v12): 127-173 20/36 -> 20/36; 206-237 15/20 -> 15/20; 238-269 13/20 -> 17/20.
Cooking slot (28 in-scope cards with a gold cooking slot): gold none 16 cards, v11 10 hit -> v12 15 hit; gold full 12 cards, 12 hit -> 12 hit (unchanged, no wrong credit). Remaining none-miss: SUB-207 (answer says "cold prep and assembly only" and "No cooking": reads light, gold ambiguity of the SUB-215 kind, same in v11 and v12).
Files whose result changed (all miss -> hit on operations, all in the T-117 set, nothing else moved):
| File | Gold items | Answer | Reason |
|---|---|---|---|
| SUB-246 | business_type=office; no cooking | Lessor of office building, 14 suites, professional tenants, no tenant food service | cooking left out; "food service" is negated, so no evidence (a) |
| SUB-248 | business_type=office; no cooking | Lessor of professional office building, six suites | cooking left out, no cooking word (a) |
| SUB-250 | business_type=office; business_type=retail; no cooking | Tax preparation office (second floor); cell phone repair and retail accessories (ground floor) | cooking left out (a) |
| SUB-257 | business_type=retail; no cooking | Thrift retail, used clothing and household goods, donations in the back | cooking left out (a) |
SUB-254 (wholesale, cooking left out) now reads cooking correctly but stays a miss on the class set (answer also states "contractors"), not a cooking issue. No file moved hit -> miss.

## Self-checks and suites
- `eval_holdout_v12.py --self-check`: ok. `eval_holdout_v11.py --self-check`: ok (unchanged). Frozen lint `--self-check`: SELF-CHECK PASS. `lint_holdout_v12.py --self-check`: 4 ok.
- `pytest tests/pipeline -q -p no:cacheprovider`: 86 passed (19 warnings), 116 s.
- No file under real `team/` logs (other than my DISCUSSION/STANDUP entries), outboxes, workbench.html, `underwriting_pipeline/cache/` or a token log was written; the temp cache copy lives in the session scratchpad.

## Findings for @model-risk (High only in detail)
- H (design, by the D-126 spec, for the reviewer to weigh): omission credit makes a gold line `business_type=other_class; no cooking` satisfiable by any non-empty answer that names no listed class and no cooking word (SUB-255 pattern; in v11 the answer at least had to state the cooking fact). Real dev effect today: 0 files (SUB-255 hit in both versions because its answer says "no cooking"). Mitigation open: other_class gold cards should carry a second scored slot; needs @senior-underwriter, not a scorer change.
- Medium: comma-list negations ("No stove, oven or hot plate") are a conservative miss, since commas split clauses and the second clause has no negation. Medium: "No cooking, tenant ranges only" is hit only because of the tenant word; "no cooking (range and hood)" is a miss. Low: evidence words are conservative on look-alikes (bakery, cookie, range as in price range).
- Assumptions to confirm: the 30 files without a saved reply were not scored; replaying them needs a model call (not done).
