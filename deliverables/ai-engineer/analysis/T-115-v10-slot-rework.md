# T-115 — scorer v10 (P-068) reworked: operations scored on slots, not wording

- Task: T-115. Proposal: P-068 (scorer v10, operations scored on facts not wording), reworked after @model-risk BLOCK. Date: 2026-10-20. Author: @ai-engineer-assistant (orchestrator session).
- Inputs: `underwriting_pipeline/ai/eval_holdout_v10.py` (reworked); slot vocabulary `deliverables/senior-underwriter/operations-gold-rule.md` ("Slot definition table (T-114 / D-117, 2026-10-20)"); validation `deliverables/senior-underwriter/T-114-slot-list-sub127-173.md`; lint `deliverables/senior-test-engineer/lint_holdout.py` (default scorer v10, `--self-check` PASS, new H1 repro block).
- Method (D-069): `HOLDOUT_RESCORE=1`, `HOLDOUT_GOLD=deliverables/senior-underwriter/gold-set-T-108-corrected`, `HOLDOUT_IDS=206-237`, `LLM_CACHE_DIR` = a temp copy of `underwriting_pipeline/cache/T-108-live`, `LLM_PACE_SECONDS=0`, `--write`. **0 model calls**, 0 call_failed. Nothing written to the real cache, the token log, `team/`, the inbox or the outboxes.
- This rework **supersedes T-113** for operations. The "operations 19/20" in T-113 was measured before the corrected T-108 items lines existed (that copy had no `Operations items:` line, so both v9 and v10 fell back to the v4 words rule). On the corrected gold (all 32 cards carry an items line) both scorers read the checklist; the numbers below are on the corrected gold.

## What changed since the blocked draft (H1/H2 closed)

The draft matched operations items as **substrings over a flattened word list** with a T-108-derived synonym list. @model-risk H1 showed that admitting a wrong answer as a hit in 10 of 28 adversarial cases. The rework is **slot-based**:

- Every gold item is parsed into **fixed slots** (the T-114 table): `alcohol` (none / beer_wine / full_bar), `cooking` (none / light / full), `fryer` (yes / yes\<N\> / no), `hood` (yes / no), `open_flame`, `seats` (N), `units` (N), `entertainment` (none / live), `hours` (set of clock times), `delivery`, `open_24h`, `onsite_processing`, `outdoor`, `security`, `hazmat`, `floor`.
- The **answer** is parsed the same way; each gold slot must match the answer slot value, slot by slot. A count is compared as an exact integer, so `40 seats and 48 parking spaces` no longer matches gold `48 seats`.
- A slot is matched **only within one clause**; any negation in that clause (before, after, or the clause's trailing word) flips or voids it (`beer and wine: no` → alcohol none; `4 fryers: no` → fryer no). A negation for one slot no longer spans a neighbouring fact (`Beer with no wine or liquor` is not gold `beer wine liquor`).
- A gold item that names **no slot** (a business type, a trade exclusion like `no roofing`) is still checked, by the v9 wording rule (the item's words, together and in order, inside one clause, negation honoured). This keeps the non-slot items scoring exactly as v9 did — no regression.
- **Negation is scoped to its own fact**: the answer and the gold items are split on comma as well as `;`, `.` and newline (a colon stays, so `beer and wine: no` still voids). A negation in one segment therefore cannot flip a neighbouring fact (`Type I hood, no delivery` states a hood; `Full bar, no patio` states a full bar).
- **A negated trigger of one class never masks another class** (table row 2 note): `no liquor license` in a beer & wine clause reads `beer_wine`, never `full_bar` or `none`.
- **Hood triggers are the table's forms only** (bare `suppression` removed): a building sprinkler suppression system is not a kitchen hood.
- **Fail-closed**: any exception in the reader is a **miss**, never a silent hit.
- Triggers are matched in the same token form as the clause ("24-hour" → "24 hour"), so hyphen/dot forms match. Numbers after a connector are read ("seating for 24", "capacity of 96").

**H2** (synonym list overfit to T-108; `operations-gold-rule.md` had no synonym list) is closed: the trigger vocabulary now cites the T-114 slot table written by @senior-underwriter from underwriting knowledge, validated on SUB-127–173 (47 files, 0 rule-required facts uncovered), not on T-108 answers.

## Evidence

- v10 **self-check**: `ok` (the H1 repros are named negative cases in it).
- Adversarial set (37 cases): **0 false positives, 0 false negatives**. Includes every @model-risk repro across all four passes (H1/H3/H4/H5/H6/H7/H8/H9/H10: interleaved counts, spanned negation, neighbouring facts, clause-final negation, cross-clause precedence, negated unit counts, sprinkler suppression, stated-value precedence, negated repeats) and true positives (Spanish "sin cocina", "no alcohol of any kind", Type I hood, fryer/open-flame/hood).
- Lint `--self-check`: **PASS**, including a 37-case H1 block (each repro a miss, each true positive a hit) and the 12 near-miss cases.
- Lint on the corrected T-108 gold: **PASS** (0 failures, 0 info, 32 files, run date 2026-10-20).

## Gates (corrected T-108 gold, v10 reworked)

| Gate | v9 on the same gold | v10 reworked | Verdict |
|---|---|---|---|
| Route accuracy | 18/20 | 18/20 | PASS (≥18/20) |
| Unsafe routes | 0 | 0 | PASS |
| False completes | 0 | 0 | PASS |
| Scope leaks | 0 | 0 | PASS |
| Field floor (9 fields ≥18/20) | fails: operations 10/20 | fails: operations 12/20 | B-433 still open (non-ops fields unchanged) |

Every non-operations field is **byte-identical** to v9 (0 diffs over 32 files): the rework touches operations only.

## Per-field: v9 → v10 reworked (corrected gold)

| Field | v9 | v10 |
|---|---|---|
| named_insured / premises / effective_date / sales / construction / year_built | 20/20 | 20/20 |
| operations | 10/20 | **12/20** (2 gains, 0 regressions) |
| tiv | 19/20 | 19/20 |
| loss_runs | 17 hit, 3 not_credited | 17 hit, 3 not_credited |
| conflict | 15/20 | 15/20 |
| status | 15/20 | 15/20 |
| route | 18/20 | 18/20 |

**Operations gains** (v9 miss → v10 hit): **SUB-207, SUB-220** — a correct fact ("Retail seating for 24", "limited seating for 18") that v9 missed on wording, now read as `seats` slots. **Operations regressions: none.**

## Every remaining operations miss (8 of 20), class

Class: **M** = measurement (the answer states the fact; the gold item names no slot and its words are spread out) · **G** = gold/card artefact (the card itself is ambiguous or the items line mixes a slot with free text). No **R** (real pipeline miss) remains in operations.

| File | Failing gold item(s) | Why |
|---|---|---|
| SUB-206 | `office building lessor` / `leases office suites` (no slot) | answer "…office building, 22 suites… Building owner/lessor only…" states the fact; the free-text words are not contiguous in one clause → wording miss (v9 missed it too) · **M** |
| SUB-208 | `wholesale distributor; craft supplies; …` (no slot) | business-type items, no slot; answer has them in different order · **M** |
| SUB-209 | `concrete flatwork contractor; driveways; patios; …` (no slot); gold also maps `patios`→`outdoor` | gold slot `outdoor: yes` (from "patios") matches the answer, but the free-text business items miss · **M/G** |
| SUB-211 | `closes 11 p.m.` etc. | answer "Closes at 11 p.m." — this card's hours/all-items combination still misses on a clause detail · **M** |
| SUB-215 | `cooking: light` (gold) | gold items say both `cold prep; assembly only` (→light) and `no cooking` (→none); gold holds the first clause (`light`), answer reads `none` · **G** (card ambiguity) |
| SUB-218 | `refrigerated cold storage warehouse; …` (no slot) | business-type items, no slot; answer states them · **M** |
| SUB-221 | `retail strip center; 100% vacant; …` (no slot) | the gold slots (`units 6`, `cooking none`) both match; the free-text business items miss · **M** |
| SUB-225 | `lounge; bar; …; no food service` (no slot) | the gold slots (alcohol/hours/entertainment/cooking) all match; the free-text items miss · **M** |

**Reading:** the 8 remaining operations misses are all the *non-slot* free-text items (business-type phrases and trade exclusions that are not in the T-114 slot table). The slot items now match. A future P-### could add these business-type phrases as their own slot (e.g. `business_type`) or relax the free-text rule; that is a scorer/prompt change and needs a proposal, so it is **not** done here.

## conflict / status non-hits (step 4): real miss vs artefact

Unchanged from T-113 (the rework does not touch these). Reporting each, no fixes:

### conflict — 5 misses

| File | Cause | Class |
|---|---|---|
| SUB-209 | the model **did** flag sales 1248000 vs 1600000; the email quote crosses a line break → citation rejected → D-086/P-038(c) folds it into the field reason, no conflict card | **D** artefact (approved fold) |
| SUB-211 | the model returned **no** conflict; gold expects the email's "new spot on Guadalupe" vs 1120 Commerce St | **R** (real miss) |
| SUB-214 | the conflict **is** in the report (0 vs 890000); scorer needle `0 tenant` vs blob `$0 (tenant)` | **M** (measurement) |
| SUB-216 | the conflict **is** in the report (24500 vs 18900); the needle `24500 vs` never appears in the JSON | **M** (measurement) |
| SUB-219 | the model **did** flag the premises conflict; the schedule side is reformatted with commas → same D-086 fold | **D** artefact (approved fold) |

### status — 5 misses

| File | Cause | Class |
|---|---|---|
| SUB-206, SUB-213, SUB-218 | all fields present, status `complete — review pending`, `report.complete` is False vs gold "complete" | **D** artefact (B-325: review pending is safe, not automated) |
| SUB-207, SUB-215 | no "liquor" cue in a food-service text → `extra = ["liquor sales"]` → complete forced False | **D** artefact (P-015 T2 ask) |

**Totals for the report: 1 real conflict miss (SUB-211); the other 9 conflict/status non-hits are an approved rule doing what it says, or a measurement artefact. No scorer/gold artefact needs a code fix.**

## Second pass (@model-risk re-check H3/H4/H5)

The first reworked draft returned BLOCK on three Highs; all three are now closed in code and added to the self-check and the lint H1 block:

- **H3 (trailing negation crossed a neighbouring fact)**: the answer is now split on commas too, so `Type I hood, no delivery` states a hood and `Full bar, no patio` states a full bar — neither is voided by the following `no`. Clause-final negation still voids (`Live band music - no.`, `beer and wine: no`). Repros added (10) — all correct.
- **H4 (alcohol precedence)**: a negated full-bar trigger no longer sets `none` or masks a stated beer/wine value; `Beer and wine only, no liquor license` reads `beer_wine` (table row 2 note); the colon form `Beer and wine: no liquor license` also reads `beer_wine`. Repros added (4) — all correct.
- **H5 (off-table `suppression` trigger)**: bare `suppression` removed from `HOOD_WORDS`; a building sprinkler is no longer a hood; `UL 300 suppression` / `wet chemical` still read a hood. Repros added (3) — all correct.

## Third pass (@model-risk re-check H6/H7/H8)

The second pass's comma split introduced three new Highs; all are now closed. The comma split was reverted — negation is scoped by the **clause-final negation** rule instead, which handles both directions:

- **H6 (comma split let a trailing negation stop voiding its own fact)**: the answer is split on `;`, `.` and newline only (not comma). A clause that **ends** in a negation voids every slot in it (`Live music, no`, `Beer and wine, no`, `48 seats, no`, `Live band music - no.`); a negation followed by other content does not (`Type I hood, no delivery` still states a hood, `beer and wine: no liquor license` still states beer and wine). Repros added — all correct.
- **H7 (absence stated first lost to a later positive across clauses)**: `_slots` now lets a **positive** value beat an "absent" one across clauses (`No hard liquor; beer and wine only` → `beer_wine`, matching v9). Repros added — all correct.
- **H8 (a negated unit count was read)**: the units loop (and the seats loop) now skip a count preceded/trailed by a negation (`Not 6 units, 8 units` → miss; `No oven on site` no longer reads a full kitchen). Repros added — all correct.

The T-108 dev re-score is unchanged (operations 12/20, same 8 non-slot misses); 0 regressions. The lint H1 block is now 37 cases (0 false positives, 0 false negatives).

## Fourth pass (@model-risk re-check H9/H10)

The third pass introduced two new Highs from the precedence/negation change; both are now closed:

- **H9 (a later contradicting / correcting value was ignored)**: `_slots` now lets a **stated** value override an earlier value across clauses (last stated wins); an absent value only fills a gap. `40 seats. 48 seats.` vs gold `48 seats` → hit; `48 seats. 60 seats.` vs gold `48 seats` → miss. Repros added to the lint H1 block.
- **H10 (a clause-final negation voided an earlier positive of the same fact)**: a trigger is voided only when it has **no positive run** — a negated repeat of the same trigger (`Type I hood, no hood`, `No hood, Type I hood`) no longer discards the earlier positive, while a standalone trailing negation with no such run still voids (`Live music, no`, `Beer and wine, no`, `Type I hood, no`). Repros added.

One H10 sub-case is **deliberately a miss**: `48 seats, 60 seats, no` (a bare trailing `no` after two stated counts) — a standalone trailing negation with no repeated trigger is ambiguous and is scored fail-safe (miss). Noted as a design choice, not a defect.

The T-108 dev re-score is unchanged (operations 12/20, same 8 non-slot misses); 0 regressions. The lint H1 block is now **37 cases** (0 false positives, 0 false negatives).

## @model-risk verdict

**APPROVE** (fourth pass, 2026-10-20). H9 and H10 closed; no High findings; H1 adversarial set 37 cases with 0 false positives / 0 false negatives; v10 self-check PASS; T-108 dev re-score read-only reproduced (operations 12/20, gains SUB-207/220, 0 regressions, all other fields byte-identical to v9); v9 unchanged. P-068 (scorer v10) may be used for hold-out evaluation. No hold-out has been scored with v10 yet.

Medium/Low from the second pass, disposition (no code change without a proposal):

- **Medium** — `business_type`, `buildings`, `stories` (table slots 1, 5, 6) are not implemented as slots; 6 of the 8 remaining ops misses are those free-text items. This is the scope gap D-117 left open ("facts not wording" for business types); a P-### would add the slot. **Open, reported.**
- **Medium** — value precedence: first-wins across clauses vs last-wins inside one clause. Not hit by any T-108 card; the SUB-232 shape ("no hard liquor") now reads `beer_wine` under H4's fix. **Open.**
- **Medium** — cooking precedence gold-side positional vs answer-side "no cooking" first. SUB-215's answer now splits on commas and reads the first clause (`light`) to match gold — **no longer a v10-only gap.**
- **Medium** — the lint near-miss replaces the whole operations value (confounded); the isolated H1 block supersedes it for the negation repros. **Open (test quality).**
- **Low** — hours compares only clock times (direction/days ignored); `bar service`, `beer wine`, `cocina`, unqualified `patios` off-table triggers; `no bar` required as free text; stale v8/v9 strings in the docstring/run examples. **Open, noted.**

## Frozen-line check

- `eval_holdout_v9.py` is unchanged (frozen baseline, committed `6f959a9`). v10 does not import or alter it.
- `eval_holdout_v10.py` hash (reworked, fourth pass, approved): `ffd1afdda55fd761f21deb2f6ede49b9294d7517bed6500ccd9520eba361302b` (1313 lines).
- `deliverables/senior-test-engineer/lint_holdout.py` hash: `d21b92cb3aabd6bb8ac2948fd40e55b5e4a7880a6808838c19190815080b936a`.
- `underwriting_pipeline/ai/llm_extract.py` hash (with the B-446 fix): `e72d092acce2aa484d9eca89a92002c1789a8dbc29c1c64e625fe8f03961c606`.
- No hold-out has been scored with v10; P-068 is approved by @model-risk (fourth pass, no High).

## B-446 (llm_extract text-field scan gate)

@model-risk **APPROVE** (High-only, 2026-10-20). The **code** was the wrong side, not the self-check: the text-field drop gate used `confidence` (the single lowest cited word) where P-056(b) requires the cited-words **average** (`floor`). Fixed in `accept_field`: `drop = (on_scan and floor < SCAN_FLOOR) or (not on_scan and confidence < MIN_CONFIDENCE)`; `confidence` still stores the lowest cited word for reporting; the review flag fires when the field is in the `[SCAN_FLOOR, MIN_CONFIDENCE)` band or one cited word is under `MIN_CONFIDENCE`. Numbers and dates keep the lowest digit group (not averaged). `llm_extract.py` no-args prints `llm gate ok`. A 20k-case differential fuzz vs HEAD showed 0 fields newly dropped, 0 newly kept-unflagged, 0 number/date changes. Inside approved P-056(b)/D-104, so no new P-###.

## For the AI Engineer

- Pending proposal: **P-068** (scorer v10, reworked) — @model-risk APPROVE, no High; **frozen**.
- v10 matches v9 exactly on every field except operations, where it gains 2 (SUB-207/220) and regresses 0; 0 H1 false positives, 0 false negatives on the adversarial set and the lint H1 block.
- Top operations artefact to decide on next: the non-slot free-text items (8 files) — either a `business_type` slot or a relaxed free-text rule (needs a proposal).
