# Proposal P-015 — The score fixes (T-017)

- Author: @data-scientist
- Date: 2026-10-11
- For: @user (the AI Engineer)
- Task: T-084. Line 5 of `team/DEMO-BLOCKERS.md`. Decisions: D-031 item 5, D-033 item 3.
- Status: PROPOSAL. Not approved. Not implemented.
- No code, prompt, scorer, cache file, or score file was changed to write this. No model call was made. The workbench queue was not run. No scorer was run.
- Synthetic data only. Not a production approval. Each veto on T-017 is lifted only by its holder.
- The weights stay placeholders. Nothing is refit. No approval, carrier route, or underwriter decision is used as a label, now or by this change.

Where a point is your choice, the options are lettered and none is picked.

## What you asked for

D-031 item 5, your words: "T-017: fix as a proposal — remove loss-history points and show "Loss history: not scored" (claim extraction goes to backlog); failed or incomplete files show "Not scored" with reason; decision rows save points, codes and points version; underwriter can mark a code wrong with a logged reason."

D-033 item 3, your words: "P-015: include @responsible-ai's cooking-rule finding; cooking points must come from actual hazards (fryer, open flame, hood/suppression), never from business name or cuisine words."

## What the code does today

- `underwriting_pipeline/models/points.py`, `score()`: six codes. LOSS_HISTORY (30) needs `liability_claim` or `property_claim_over_25k`. Nothing supplies either key.
- `underwriting_pipeline/app/workbench.py`, `facts()`, lines 55 to 66: the inputs to the score are built here, outside `models/`. Cooking is `any(word in ops for word in ("fryer", "restaurant", "taco", "kitchen"))` on the extracted `operations` value. It is a substring test, so "office, no kitchen" fires and "taqueria" does not.
- `load_queue()`, line 96: every file is scored, whatever its status. `render()`, line 195: `Score: {points} · {codes or 'none'} · not a price`. A failed file prints "Score: 0 · none".
- `record_decision()`, lines 131 to 140: the row holds submission, action, underwriter id, reason, date, `ai_version`, `bound`, `sent_to_carrier`. No points, no codes, no points version, no mark on a code.
- `points.py` self-check: `assert score({})["points"] == 0`. It asserts the blank-is-zero behaviour as correct.

## The change

### 1. Loss history

- The LOSS_HISTORY branch is removed from `score()` and its row is removed from the table in reason-codes.md. The range becomes 0 to 80 (it was 0 to 110).
- Every file, scored or not, shows the line "Loss history: not scored". reason-codes.md says why: no claim fact is extracted, and a loss-run date is not a claim count.
- Claim extraction is in the backlog (B-149), by your words. It is not in this proposal.

### 2. Failed or incomplete files

- One new function in `points.py` takes the saved report, not a hand-built dict. It returns either a score or "not scored" with a reason. It never returns a number for a file that is not scored.
- Not scored, with the reason shown on the page:
  - `extraction_failed`: "Not scored — extraction failed: <the error>".
  - `incomplete`: "Not scored — file incomplete: missing <fields>" or "open conflict on <field>".
  - `all_values_rejected` (D-024): "Not scored — every value was rejected". This status is decided but is not in the code yet (T-070). The rule is written so it holds once it is.
  - Any other status the function does not know: "Not scored — unknown status". Unknown never becomes a number.
- The self-check line `assert score({})["points"] == 0` is replaced by a check that fails if a failed, incomplete, or empty report returns a number.

### 3. The decision row

- When a decision is recorded, the row also saves `points` (or `null` with the not-scored reason), `reason_codes`, and `points_version`.
- The saved values are the ones on the page the underwriter saw. They are held by the server from the render, not recomputed at the click and not taken from the browser's form. How is @software-engineer's design.
- Old rows in `decisions.jsonl` are not rewritten. A row without the new keys reads as "not recorded".
- `points_version` is one id set in `points.py`. It changes whenever the table or a fact rule changes. See choice V.

### 4. Marking a code wrong

- Next to each code shown, the underwriter can mark it wrong. A reason is required. No reason, no mark, the same rule as edit and decline today.
- The log saves the code, the reason, the underwriter id, the date, and the points version.
- A mark does not change the carrier match, a send gate, or the file's status. It is counted to find bad rules. It is never a training label.
- reason-codes.md defines this as the override. The sentence "An underwriter can ignore the total" is removed.
- The id check on who may write to the log is B-138, on the demo path by D-038 item 3. It is not in this proposal.

### 5. Cooking

- COOKING (25, unchanged) fires only when a cooking hazard is stated: a fryer or an open flame (grill, charbroiler). The words "restaurant", "kitchen", "taco", and every cuisine or food word are removed from the rule. A class word alone gives no points.
- The term list lives in `points.py` and is printed in reason-codes.md, English and Spanish (freidora, parrilla, llama abierta, campana, supresión), so a Spanish file is not left unscored for its language.
- Whole words only. "childhood" is not "hood".
- Negation: a hazard word after "no", "not", "without", or "sin" in the same clause is "stated no". It gives no points.
- The named insured's own text is removed before matching, so "Open Flame Yoga LLC" or "Hood Street Books" cannot fire the rule.
- Three outcomes are shown, never a silent zero: "COOKING +25 — fryer stated: <the cited text>", "Cooking: stated none", or "Cooking: not scored — no cooking equipment stated in the file".
- How hood and suppression count is choice H. Your words name them; they do not say which direction.
- `facts()` moves from `workbench.py` into `points.py` so the rule sits in the documented model. The habitational, contracting, frame, and TIV lines move as they are, with no change.

## Where the cooking hazard facts come from

| Fact | Where it is today | Does extraction return it? |
|---|---|---|
| Fryer, open flame | In the source documents. SUB-002 `kitchen.md`: "Cooking equipment: two floor fryers". SUB-011 `reply.md`: the same line. SUB-020, 030, 040, 050 `email.md`: "They use fryers." | No. Extraction returns nine fields and none is cooking equipment. The word sometimes rides inside `operations` (SUB-002 and SUB-011 applications: "restaurant, tacos, fryer"; gold SUB-011: "restaurant with fryer"). |
| Hood and suppression | SUB-002 `kitchen.md`: "Hood and fire suppression: wet chemical system, inspected 2026-05-12". Emails: "Hood and suppression are in place." | No. |

- `prepare.py`, lines 568 to 577, already reads the raw text for the cue words "cooking equipment", "fryer", "hood", "suppression". It uses them only to decide what to ask the producer. It returns no fact and no citation.
- That check starts only when the text holds "restaurant", "fryer", "taco", or "kitchen". The text includes the insured's name. Read from the code, not run: "Blanco Street Kitchen LLC" or "Guenther Tacos y Mas" starts the ask, the file becomes incomplete, and under this proposal an incomplete file shows "Not scored". A taqueria or a panaderia whose text has none of those four words is not asked. So a name or a cuisine word can still decide whether a number is shown. That is choice T.
- In text files of the inbox (md, csv; PDFs and images not searched), a hazard word appears in six folders: SUB-002, 011, 020, 030, 040, 050.

When the facts are missing: no points, and the page says "Cooking: not scored — no cooking equipment stated in the file". Whether the file still shows a number is choice M.

## Files and owners

| File | Change | Owner |
|---|---|---|
| `underwriting_pipeline/models/points.py` | LOSS_HISTORY removed; `facts()` moved in; cooking rule; not-scored result; `POINTS_VERSION`; self-checks | @data-scientist |
| `deliverables/data-scientist/reason-codes.md` | Table without LOSS_HISTORY; "Loss history: not scored"; not-scored rules; cooking terms and negation; where each fact comes from; the override; points version; range 0 to 80 | @data-scientist |
| `deliverables/data-scientist/problem-framing.md` | One dated line: loss history is not a v1 driver until claim facts exist | @data-scientist |
| `underwriting_pipeline/app/workbench.py` | `facts()` removed, calls `points`; the three display lines; the mark-wrong control; `record_decision` saves the new keys; self-checks | @software-engineer |
| `deliverables/software-engineer/decisions.jsonl` | New keys on new rows only | @software-engineer |
| `underwriting_pipeline/ai/prepare.py` | Only under S3 or T2 | @ai-engineer-assistant |
| `underwriting_pipeline/ai/llm_extract.py` (prompt and field list) | Only under S2 | @ai-engineer-assistant |

Nothing under `src/insureflow` changes. No scorer changes. No published score is rewritten.

## What the reviewers say resolves it, finding by finding

The verdict on each line is the reviewer's to give. This is my reading.

@actuary, REVIEW, Re: T-017, 2026-10-11:

| Finding | Their words | P-015 |
|---|---|---|
| High-1 | "Resolve: return and show "loss history not assessed" until claim facts exist, and say so in reason-codes.md. Extracting claims needs a P-### and the user." | Fully, in your wording "Loss history: not scored" in place of "not assessed". |
| High-2 | "Resolve: return "not scored" (no number) for those files, with a self-check." | Fully. |
| High-3 | "Resolve: define the override in reason-codes.md (remove or add a code, with a reason) and log shown and overridden codes; the log is @software-engineer's (T-019)." | Partly under A1: a code can be removed (marked wrong), not added. Fully under A2. |

@model-risk, OBJECTION, Re: T-017, 2026-10-11:

| Finding | Their words | P-015 |
|---|---|---|
| High-1 | "Resolves when: the claim facts are supplied with a source span, or LOSS_HISTORY is removed from reason-codes.md and the page says "loss history: not scored"." | Fully, by the second branch. |
| High-2 | "Resolves when: a failed or incomplete file, or one missing a driver input, returns and displays "not scored" with the reason, and a check fails if it shows a number." | Failed or incomplete: fully. "one missing a driver input": fully under M2; partly under M1, where the driver says "not scored" and the file still shows a number. |
| High-3 | "Resolves when: each decision row stores points, reason codes, and a points version id, and the underwriter can mark a code wrong with a reason that is logged." | Fully. |

The production veto is not lifted by this. B-027 ("no Tier 2 evidence exists for the score") is not addressed.

@responsible-ai, OBJECTION, Re: T-017, 2026-10-11: "Resolves it: (1) a cited claims fact feeds LOSS_HISTORY, or the code is removed from the table; (2) incomplete or extraction_failed shows "not scored"; (3) cooking comes from a stated class or equipment fact, no cuisine words, negation handled, with a wording-pair test; (4) the log stores points, codes, and a per-code "wrong" mark with reason."

| Item | P-015 |
|---|---|
| (1) | Fully. The code is removed from the table. |
| (2) | Fully. |
| (3) | Points: fully. Equipment fact only, which is your stricter wording; no class word, no cuisine word, negation handled, wording-pair test listed below. What is shown: partly under T1, because a cuisine word or a name in `prepare.py` can still turn a number into "Not scored"; fully under T2. Under S1 the fact is a word inside the cited `operations` value, not a fact with its own citation. |
| (4) | Fully. |

The two T-021 reviews (decision log), 2026-10-11:

| Finding | Their words | P-015 |
|---|---|---|
| @data-scientist High-1 | "Resolve: read model, prompt version, and cache key from the saved extraction run, not the shell; rule version from code; store the shown values, match, points, and codes (D-031 item 5 asks for the last two)." | Partly. Points, codes, and points version only. Under E2 also model, prompt version, and cache key. The shown field values and the match are not stored under either. |
| @model-risk High-1 | "To close: stamp each row with the model and prompt version saved with the extraction shown, plus the git commit hash of the rules and points code (D-034), taken at render time, with a self-check that an environment change does not alter the stamp." | Not under E1. Partly under E2 with V3. `ai_version` itself is not changed by this proposal. |
| @data-scientist High-2 | "Resolve: an edit stores field, AI value, new value ... one function returns, per submission, decided, zero field edits, declined ..." | Not. Out of scope. B-141 and B-139. |

## The tests

Wording-pair test, in the `points.py` self-check. Each row is an `operations` text with every other field held the same. The check fails if a row gives anything else.

| Text | Today | After |
|---|---|---|
| taco | +25 | 0, cooking not scored |
| taqueria | 0 | 0, cooking not scored |
| pizzeria | 0 | 0, cooking not scored |
| barbecue | 0 | 0, cooking not scored |
| steakhouse | 0 | 0, cooking not scored |
| catering, commercial cooking | 0 | 0, cooking not scored |
| restaurant | +25 | 0, cooking not scored |
| restaurant supply wholesale | +25 | 0, cooking not scored |
| apartamentos | 0 | 0 (HABITATIONAL is not changed; B-064 stays in the backlog) |
| office, no kitchen | +25 | 0, cooking not scored |
| office, no fryer | +25 | 0, cooking stated none |
| restaurant with fryer | +25 | +25 COOKING |
| taqueria with fryer | +25 | +25 COOKING |
| pizzeria with fryer / steakhouse with fryer / office with fryer | +25 each | +25 COOKING, all three the same |
| restaurante con freidora | +25, from the letters "restaurant" | +25 COOKING |
| taqueria con freidora | 0 | +25 COOKING |
| childhood education office | 0 | 0, cooking not scored |

The rule under test: swap the class or cuisine word and the points do not move; add or remove a stated hazard and they do; a negated hazard gives none.

Name-swap test (T-067), on saved extractions, no model call. It already asserts that the score and the match do not change. After this build it also checks:

- Names with a trigger word are in the swap list (B-065): "Guenther Tacos y Mas", "Blanco Street Kitchen", "Fryer and Sons Bookkeeping", "Open Flame Yoga", "Hood Street Books".
- The name is swapped in the named insured and wherever the same text appears in `operations` and in the text the cooking rule reads.
- Four things must stay the same per file: points, codes, the cooking line, and scored versus "Not scored".
- Under T1 I expect the last one to fail for a name holding "taco" or "kitchen", for the reason given above. T-067 says to report and stop, not to fix.

Other self-checks: no report returns LOSS_HISTORY; a failed, incomplete, or empty report returns no number; a decision row holds the three new keys and they do not change when `LLM_MODEL` changes; a mark with no reason is refused; each of the five remaining codes can fire from a report (B-067).

## Expected effect on the files in the inbox

Computed with a scratch script from the gold files and the 13 saved replies. No model call, nothing written. The cooking facts are taken from the `operations` value only (S1). Status is the gold status, not the pipeline's; the pipeline's own "incomplete" also counts its cooking-equipment ask, which I did not run.

The inbox has 86 folders. 80 have gold (SUB-007 to SUB-086). SUB-001 to SUB-006 have no gold and no saved reply, so they are not computed.

| On gold values, 80 files | Today | After |
|---|---|---|
| Shows a number | 80 | 43 |
| Shows "Not scored" with the reason | 0 | 37 (35 incomplete, 2 conflict) |
| Shows 0 | 48 | 27 |
| Shows 10 | 7 | 5 |
| Shows 15 | 13 | 11 |
| Shows 25 | 11 | 0 |
| Shows 35 | 1 | 0 |
| Carries COOKING | 8 | 0 |
| Carries LOSS_HISTORY | 0 | 0 |

- 24 files that show "Score: 0 · none" today become "Not scored".
- Among the 43 complete files, three numbers change: SUB-064 (bakery restaurant), SUB-074 (tortilla restaurant), SUB-084 (taco restaurant) go from 25 to 0 with "Cooking: not scored". The other 40 keep their number.
- The eight files with COOKING today: five are incomplete (SUB-011, 020, 030, 040, 050) and become "Not scored"; three are the scans above. Only SUB-011's gold `operations` names a hazard ("restaurant with fryer").
- Five gold files have paid claims (SUB-059, 069, 076, 079, 086). They get no loss-history points today and none after. After, the page says so.
- 13 saved replies (raw model replies, before the gate): 12 match a gold file. SUB-084 ("taqueria restaurant") goes 25 to 0. Four are gold-incomplete and become "Not scored" (SUB-029, 082, 083, 086). Seven keep their number. One reply has no values.
- Under S2 or S3 the six folders that state equipment could carry COOKING. Five of them are gold-incomplete (SUB-011, 020, 030, 040, 050) and SUB-002 has no gold. So I expect COOKING on at most SUB-002 in today's inbox.
- Under M2 with S1, 79 of 80 gold files state no cooking fact either way, and the eightieth is incomplete: all 80 would show "Not scored".

Extraction scores do not move under S1 or S4 with T1: nothing under `underwriting_pipeline/ai/` is touched. No published score is recounted in any case.

## Trade-off

- The score says less. With LOSS_HISTORY gone and cooking tied to stated equipment, most files show 0, 10, or 15, and on today's inbox no scored file carries COOKING. A restaurant with no equipment stated ranks with an office, with a line saying cooking was not scored.
- Nearly half the files show no number. That is the point of the fix, and it is also less on the page.
- A file with paid claims and a clean file still rank the same. The page now says loss history was not scored instead of implying it was.
- Scores before and after are not comparable. The points version marks which is which.
- S2 gives the best facts and costs the most: a prompt change, a new cache key, and every file called again.

## Risk to the loss-run no-guess rule

- Lower, not higher. Once LOSS_HISTORY is gone, no code needs a claim fact, so nothing pulls toward guessing one.
- `loss_run_valued_through`, its gate, and "A no-known-loss letter is not a loss-run date" are not touched.
- "Loss history: not scored" must not read as "no losses". The line is shown on every file, including those with a loss run, and reason-codes.md keeps "A missing loss run adds no points and does not mean zero claims."
- Under S1, S3, or S4 the prompt does not change, so the loss-run field cannot move. Under S2 the prompt changes; the quick set of 15 would show a drop on loss runs, and D-022 item 4 says one extraction change at a time.

## What is NOT changed

- The weights: COOKING 25, FRAME_CONSTRUCTION 15, HABITATIONAL 15, CONTRACTING 15, TIV_OVER_1M 10. Placeholders, not refit.
- The habitational, contracting, frame, and TIV rules, with their known faults (B-021, B-026, B-061 to B-064).
- Claim extraction (B-149).
- The carrier match, `route()`, the send gates, `package.py`.
- `ai_version`, the "no corrections" count, and what an edit stores (B-139 to B-142), except under E2.
- Who may write to the decision log (B-138).
- Raw code names on the page (B-070), the scale note (B-023), the placeholder note on the page (B-018).
- Every scorer, every published score, the gold files.
- The score still cannot decline, bind, set a price, or pick a carrier.

## After approval

@pm makes the build tasks. My part (`points.py`, reason-codes.md) goes first, then @software-engineer's, then any `ai/` part by @ai-engineer-assistant in its place in the one-change-at-a-time order. Then @actuary, @model-risk, and @responsible-ai look at T-017 again, and T-067 runs.

## Your choices on P-015

| | Choice | Options |
|---|---|---|
| S | Where the cooking facts come from | **S1** the extracted `operations` value only; no `ai/` change; cooking will read "not scored" on most restaurants. **S2** two new cited fields from the model (cooking equipment, hood and suppression); prompt change, new cache key, all files called again. **S3** a rule in `prepare.py` that reads the labelled lines in the source text with a citation, as `sprinklers_yes` does; no prompt change, no new call. **S4** the underwriter enters them on the workbench, logged with their id. |
| H | Hood and suppression | **H1** shown as a stated fact beside the code, no points either way. **H2** a stated "no hood" or "no suppression" also fires COOKING. **H3** a stated hood or suppression system counts as evidence of cooking and fires COOKING by itself. |
| M | A complete file with no cooking fact stated | **M1** the number is shown with "Cooking: not scored". **M2** the whole file shows "Not scored" until cooking is stated yes or none. |
| T | The cue list in `prepare.py` that asks for cooking equipment | **T1** leave it; a name or the word "taco" can still make a file incomplete and so "Not scored". **T2** drop cuisine words from it and ignore the insured's name; an `ai/` change. |
| V | Points version | **V1** a hand-set id ("points-v2"). **V2** a hash of the table and term lists, computed in code as `PROMPT_VERSION` is. **V3** V2, plus the git commit hash once P-017 is built. |
| W | What a "wrong" mark does to the number | **W1** logged and shown beside the code; the number does not change. **W2** the page also shows the total without the marked code. |
| A | Adding a code the score missed | **A1** no; mark wrong only, as you wrote. **A2** yes, with a logged reason, as @actuary's line asks. |
| E | What else the row saves | **E1** points, codes, and points version only, as you wrote. **E2** also the model, prompt version, and cache key read from the saved extraction. |

P-015 is not implemented until the user replies "approve change P-015".
