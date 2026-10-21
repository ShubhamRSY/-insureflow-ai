# T-117 — @model-risk build check (pre-run)

- Reviewer: @model-risk (independent)
- Date: 2026-10-21
- Scope: T-117 acceptance criteria and the six checks the user asked for. High findings in detail; Medium and Low one line each.
- Method: I read the gold cards, the route table, the mix, the plan, the lint files, `carrier-match.md`, `operations-gold-rule.md`, `simulation/carrier-loss-run-formats.md`, the builder source and the built inbox files. I pulled every builder value out with an AST read of `build_SUB-238-269.py` and did not execute it. I compared those values field by field with the gold, recomputed the manifest, and ran the frozen lint and the scorer's read-only `--check-gold` and `--check-ops-gold`. I ran no pipeline, extraction, model call or scorer in score mode, and I edited no gold, scorer, lint or inbox file. I did not read the author's T-117 messages or the task Notes.
- Code under test: `ai-team` `8d605acce37f06f719b5a865a79d783bc3e9c800`, prompt `759b3e6bc9b2`, scorer v11. HEAD is now `28bba4b`, but the only commit after `8d605ac` that touches code-adjacent files is `b05a89d`. That commit adds the T-117 build, gold and docs, plus one rule line in `operations-gold-rule.md` (M6). No code, prompt, scorer or lint file changed.

## Verdict

**The build may NOT be called frozen and run yet.** Two High findings are gold errors that the frozen scorer would count as misses on a correct answer. A hold-out is scored once and never rewritten (D-020), so they have to be fixed before the run, not after.

- H1: two route-gold cards contradict the written R17 rule.
- H2: one operations-gold card carries a class that the documents never state.

Each is a gold-only fix. After the fixes, the route table, plan, summary, lint, manifest and freeze note need re-doing; the full list is under "Re-freeze" below. Everything else I checked passes. Not a production approval: this is a hold-out build, and the T-027 position is unchanged.

## High findings

### H1 — SUB-246 and SUB-248 gold route `carrier_a` contradicts R17 (the strict Carrier A word rule)
- Rule: `carrier-match.md` R17 (P-053, D-099; P-054 a, D-100) allows the direct Carrier A route only when every word of the operations text is one of three things: an R14 allow-list phrase, a listed negation, or a listed non-occupancy word. Any other word gives `senior_referral` with Carrier A suggested.
  - SUB-246 operations (`simulation/inbox/SUB-246/application.md:13`): "Lessor of office building, 14 suites, professional tenants". Unlisted words: **lessor, suites, professional, tenants** (only `suite` singular is neutral).
  - SUB-248 operations (`SUB-248/application.md:13`): "Lessor of professional office building, six suites". Unlisted words: **lessor, professional, six, suites**.
  - The frozen code reads the same lists (`underwriting_pipeline/app/workbench.py` `ALLOW_A`, `NEUTRAL`, `_unlisted`, lines 176-205).
- Gold says otherwise: `gold-set/SUB-246.md:26` and `gold-set/SUB-248.md:25` give `carrier_a`, and so do `T-117-routes.md` lines 15 and 17, with counts at line 29.
- The routes file's judgment call 2 (line 39) admits the words are unlisted and follows "the T-108 precedent" of SUB-206 and SUB-213. That precedent is already settled the other way:
  - The T-108 run gave both files `senior_referral` (`deliverables/ai-engineer/evals/SUB-206-237-holdout-v7-mismatches.md:27-28`).
  - The T-110 cause analysis classed them **D, "an approved rule doing exactly what it says, gold disagrees"** (`deliverables/ai-engineer/analysis/T-110-v9-remeasure.md:85-86`).
- The gold also contradicts itself: it applies R17 strictly to SUB-243 ("bicycles, parts, repair, service") and to SUB-257, but not to the lessor words.
- Effect: two predictable route misses on a correct answer. Route is capped at 18/20 before any real error, and the misses are written into a score that can never be rewritten.
- Resolution, gold only:
  - `SUB-246.md:26` becomes `senior_referral, suggested market carrier_a — words not on Carrier A allow-list (R17; AG:29-30)`. Line 27 is reworded to match.
  - `SUB-248.md:25` becomes the same route, keeping `— hold: loss run not a recognised carrier format`. Line 26 is reworded; the physical-therapist verify note stays.
  - `T-117-routes.md`: rows 15 and 17 change to `senior_referral` / `carrier_a` / `R17; AG:29-30`. Counts become carrier_a 0 and senior_referral 16 (suggested carrier_a 5). Judgment call 2 is removed.
  - `T-117-plan.json:4` routes become `"carrier_a": 0, ..., "senior_referral": 16`.
  - `T-117-gold-summary.md` lines 9 and 14 are updated to match.

### H2 — SUB-249 operations gold carries `business_type=retail`, which the documents never state
- Gold `gold-set/SUB-249.md:14` reads `business_type=restaurant; business_type=retail; ...`.
- The documents say "Deli sandwiches and grocery market (milk, snacks, soda)" in the application and "Deli plus a little grocery market" in the email. Neither "grocery" nor "market" is a `retail` synonym in `operations-gold-rule.md` §1, and §2 says "a business_type item for every class the documents state ... Never infer a second operation".
- Recomputed with the frozen v11 `answer_classes`:
  - the application's operations line reads `{restaurant}`;
  - **the card's own `- Operations:` line (line 13) also reads `{restaurant}`**;
  - against the gold set `{restaurant, retail}`, a faithful answer is a guaranteed miss.
- Resolution, gold only: line 14 becomes `business_type=restaurant; no alcohol; grill; hood`, and "grocery market (milk, chips, soda)" moves to the notes line. The route does not change (R10, carrier_b suggested). `T-117-gold-summary.md` line 15 should drop 249 from the two-operation list.

### Re-freeze after H1 and H2
1. Re-run the lint with the updated plan. It must exit 0.
2. Re-run `--check-gold` and `--check-ops-gold` for 238-269.
3. Recompute the manifest the same way.
4. Record the new sha256 in the mix freeze note and in NEXT-SESSION.md, replacing `9ab5960d…`.

The code SHA, prompt and scorer stay as they are, because no code change is involved.

## What I verified and it passes

- **Hashes.**
  - Scorer `eval_holdout_v11.py` sha256 is `7ddcfb50…fcbb`; lint `lint_holdout.py` is `01147a75…ea653`. Both match.
  - The gold manifest reproduces exactly. I ran `shasum -a 256` over `gold-set/SUB-238..269.md` plus `T-117-routes.md` (33 lines, in file order). The output is byte-identical to `T-117-gold-manifest.sha256`, and its sha256 is **`9ab5960db77f49e02b27518fb13eaff7a0ceb8d6e78c498c430bd2ba350a943d`**, matching the mix freeze note and NEXT-SESSION.md:32.
- **Lint.** `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-117-plan.json --run-date 2026-10-21` exits 0 with `PASS: 0 failure(s), 3 info, 32 files`. The 3 info lines are the declared undated runs 241, 242 and 254.
- **Scorer format checks (read-only).**
  - `HOLDOUT_IDS=238-269 … eval_holdout_v11.py --check-gold` exits 0 with `32 ok, 0 fail`. Totals: in 20, out 12; criteria 4/5/4/2; two-criteria 263, 268, 269; criterion 4 on 258 and 259.
  - `HOLDOUT_IDS=238-257 … --check-ops-gold` exits 0 with `20 ok, 0 fail`.
- **Check 1, gold vs builder source.** For all 20 in-scope cards, these fields equal the builder's `app(...)` values: named insured, premises, effective date, sales, TIV (Building TIV, the T-108 convention), construction and year built.
  - Year built is `not in documents` on SUB-238, where the builder omits `yb`.
  - Claims count, paid and open match every `lr_carrier_*` row. SUB-239's scan lines match too.
  - The schedule rows equal the application on 243, 246, 250, 251, 254, 255, 256 and 257.
  - Gold holds the three conflicts the builder planted: 249 sq ft 2,800/3,150, 252 suites 2/3, 257 sales 412k/540k.
- **Check 2, Scope lines.** Every one of the 32 cards has `- Scope:`, and all 32 parse.
- **Check 3, operations slots.** Every in-scope items line passes the v11 slot check. M6 phrases: none appear in any SUB-238..269 file or in the builder (grep). Apart from H2 and the measurement notes M1 and M2, business_type matches the documents.
- **Check 4, loss-run dates.**
  - Each of the 14 `Loss runs valued as of:` lines equals the builder's `valued` argument: 238, 240, 243, 245, 246, 247, 249, 250, 251, 252, 253, 255, 256, 257.
  - All are before 2026-10-21. The latest in scope is 2026-09-30 (249); the latest out of scope is 2026-09-22 (268).
  - The six in-scope cards without a line are correct under `simulation/carrier-loss-run-formats.md`:
    - 239: the header differs and there is no claims table, as the builder source shows;
    - 241 and 248: no-known-loss letters (P-040);
    - 242 and 254: no valued line;
    - 244: no loss run.
- **Check 5, routes vs `carrier-match.md`.** Apart from H1, every in-scope route is what the written rules give:
  - W1/R1: 238, 239 (a lounge beside oven evidence is never softened);
  - W2c: 242;
  - W2d on the Line of business: 251;
  - R10: 240, 241, 247, 249, 253;
  - R11: 244;
  - R12: 245, 256;
  - R16: 250;
  - R17: 243, 254, 257;
  - R8: 255.
  - SUB-252 is a documented judgment call; see M2.
  - No route is `hold`, and no out-of-scope card carries a route.
- **Gold-first integrity.** None of these contain a T-117 artefact: `deliverables/ai-engineer/`, `underwriting_pipeline/` (including every cache), `simulation/to-carrier/`, `to-producer/` and `pending-approval/`. I searched the ids SUB-238..269 and four insured names. No score exists.
- **D-069.** No real workbench page, log, token log or outbox was written by this build.

## Medium

- **M1 — measurement, record before the run.** The frozen v11 word reader will mark faithful operations answers as misses where the class word sits outside the operations text, or where a customer word reads as a class. The gold is rule-correct on each; this is not a gold error, but the run record should list these as measurement (class M) in advance.
  - SUB-253: the class word is only on the Line of business line ("Restaurant package"); the operations text reads `other_class`.
  - SUB-254: "to contractors" reads as `contractor`, an extra class.
  - SUB-239: "full bar" appears in the email only.
- **M2 — SUB-252 route.** The frozen code gives R2 `senior_referral` for a pub beside fryer evidence (`workbench.py:280,291`). Gold takes R1 `no_match` because an office also sits beside the pub. `carrier-match.md` does not settle a bar that is beside both food and a non-food operation. @head-of-underwriting should rule before the run, or the run record should pre-register it. Neither route is a carrier route, so neither is unsafe.
- **M3 — coverage.** Once H1 is fixed, no in-scope file routes to Carrier A directly. The set then measures unsafe direct routes on all 20 files, but has no true-positive direct route. Record this as a limitation of T-117; there is no need to rebuild.
- **M4 — `T-117-lint.md` is stale.** It says "Result: FAIL (3 failures…)" while `T-117-lint.txt` and my re-run say PASS. Add a dated "after gold fixes: PASS" line so the deliverable does not contradict the freeze.

## Low

- **L1** — `SUB-244.md:13`: the Operations line includes "yard and small office", which reads as `office` if it is copied. The items line is correct. Consider moving "small office" to the notes.
- **L2** — `SUB-252.md`: the application's "Liquor liability claim 2025, open review" against the run's reserve of $0 is listed as Missing, not as a Conflict. That is defensible, but the call should be stated.
- **L3** — `operations-gold-rule.md` gained the M6 line in the gold commit, after the v11 freeze. It affects no T-117 file. It is a rule-document change, so record it in DECISIONS with its owner if that has not been done.
- **L4** — The mix freeze note is appended in the same commit as the gold, so "mix written before gold" cannot be confirmed from git alone. This is the same as T-108 L4.

## Approval

Not a production approval. The freeze gate is H1 and H2 only. Once both are fixed and the re-freeze above is done, I have no other objection to freezing and running T-117 once (D-020, with the user's approval).
