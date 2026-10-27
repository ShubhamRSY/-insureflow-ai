# Model Risk check: T-116 / P-069 (scorer v11, business_type slot), D-119

- Reviewer: @model-risk. Date: 2026-10-21. Independent, High findings in detail, Medium/Low one line each.
- Read: `eval_holdout_v11.py` (diff vs v10), `lint_holdout.py` (git diff), `operations-gold-rule.md` (git diff), `P-069-dev/` (gold copies, lint and gold-check output), `T-116-v11-business-type.md`, `carrier-match.md`, `validation-standards.md`. Author messages not read.
- Not a production approval. Approved proposal P-069 is not a production approval; T-027 veto stands.

## Verdict: OBJECTION. Do not freeze v11 for the next hold-out yet

One High (H1). It is a gold-rule and dev-gold defect, not a scorer-code defect: once H1 is closed, v11 can be frozen **as it is now** (sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`), with no code change. T-117 gold writing must not start before the H1 rule line exists.

## What I recomputed (temp paths / read-only; 0 model calls)

| Check | Result |
|---|---|
| v10 sha256 | `ffd1afdd...302b`, unchanged |
| v11 sha256 / lint sha256 | `7ddcfb50...fcbb` / `01147a75...a654`, as stated in the analysis |
| `eval_holdout_v11.py --self-check` | ok |
| `lint_holdout.py --self-check` | SELF-CHECK PASS (blind scorer and no-class scorer both caught) |
| Lint, T-108 dev gold copy, v11 | PASS, 0 failures, 7 info, 32 files (reproduced) |
| `--check-ops-gold` SUB-127-173 copy / `--check-gold` T-108 copy | 47/47 ok / 32/32 ok (reproduced) |
| Operations, SUB-206-225, recomputed from the cached answers (T-108-live extractions) with each scorer's own `ops_items_hit` | v10 12/20, v11 13/20: matches the analysis, same per-file split |

A full pipeline re-score into a temp folder was blocked by this session's permission system; the operations recompute above was done instead from the cached replies directly. Non-operations marks were not re-run by me.

## High

**H1. Dev gold for SUB-211 and SUB-222 was edited to avoid the scorer's reading of "bar", against the rule and carrier-match; v11 then credits an answer that drops a W1 bar word.**
- Documents (SUB-211 application.md line 13): "Full-service restaurant ... Full bar (beer, wine, liquor)". SUB-222: "full liquor bar".
- `operations-gold-rule.md` section 2: "A card carries a business_type item for every class the documents state"; section 1 lists `bar` as a `bar_pub` synonym; near-miss 1 says "restaurant and bar" must miss gold `restaurant`. `carrier-match.md` R2: a bar word beside restaurant evidence is senior_referral "possible bar/liquor exposure", never a market confirm.
- The migrated cards hold `business_type=restaurant` (211) and `business_type=lounge_nightclub` (222) only, the alcohol item is rewritten "full liquor", and the note says why: "so the word bar does not read as bar_pub".
- Repro (v11 as written, SUB-211 gold): "Full-service restaurant, ... full liquor, ..." (bar dropped) = **hit**; "... full bar with liquor, ..." (the documents' fact) = **miss**. The scorer rewards omitting the word that drives the never-confirmable R2 referral and punishes the correct extraction. Both cached answers for 211 and 222 are correct and are scored miss.
- Why High: a frozen scorer plus gold written this way would credit a route-relevant omission on a scored-once hold-out, and the rule file has no line that settles "full bar" / "bar snacks" / "bar service" beside another class. The analysis records the opposite convention as a mapping rule, so the T-117 gold author has two conflicting sources.
- Remediation (no scorer change):
  1. @senior-underwriter adds one line to `operations-gold-rule.md`: a bar/tavern/pub word the documents state about the premises ("full bar", "full liquor bar", "bar service") is `business_type=bar_pub` beside the other class; the alcohol item is written without a class word ("full liquor").
  2. Correct the dev copies of SUB-211 (add `business_type=bar_pub`) and SUB-222 (add `business_type=bar_pub`) in `P-069-dev/`; re-run lint (must PASS) and the 0-call dev re-score; update the analysis numbers.
  3. Then freeze v11 at the sha above. Separately (not blocking T-116): SUB-211's expected route says R9/R10, but carrier-match R2 applies to bar beside restaurant; @senior-underwriter / @head-of-underwriting to confirm the route gold.

## Medium / Low (backlog, one line each)

- M1 Analysis says the 5 new v11 misses are "real class disagreements, not wording"; recompute shows all 7 v11 misses are correct extractions read with incidental class words ("small office" 208/216/219, "sells to retail shops" 208, "retail seating" 207, "therapy" tenants 213, "bar" 211/222). Correct the sentence; label the v11 operations score as a lower bound with this ceiling in the score file.
- M2 The lint's perfect answer is the gold items line, so it carries `business_type=` tokens and never exercises the word reader on a natural-language perfect answer; add one natural-language perfect answer per card class (the dev re-score is today the only such test).
- M3 An answer-side `business_type=<value>` token is trusted verbatim and masks the rest ("pawn shop business_type=office" hits `office`); accept the token only in lint mode or require it to agree with the read classes.
- M4 `other_class` gold matches any answer that names no listed class ("Machine shop" hits a laundromat card); acceptable under R8 routing, note it as a known weak check.
- M5 Slot table rows 2-19 are said to "stay", but the reader has no trigger for several listed phrasings (no processing, no hot work, buildings/stories, until midnight); gold writers are forced to move real slot facts to notes. List the readable phrasings per slot in the rule file.
- L1 Leading negation masks the class ("No-frills bar" reads as other_class); fail-closed for bar gold, low impact.
- L2 "Medical office" reads `lab_medical` + `office`; matches carrier-match W2b behaviour but gold must write both or the correct answer misses.

## Freeze statement

v11 may **not** be frozen for the next hold-out until H1 items 1 and 2 are done and the lint and dev re-score are re-run (0 calls, temp paths). No code change to v11 is required; if the scorer file changes at all, this check must be redone.

---

## Look-again, 2026-10-21 (@model-risk): APPROVE. H1 closed; no new High. v11 may be frozen for the next hold-out

Checked file hashes (unchanged since the first check, so no code-review redo needed):
- `eval_holdout_v11.py` sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`
- `lint_holdout.py` sha256 `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653`
- `eval_holdout_v10.py` sha256 `ffd1afdd...302b`, unchanged

H1 remediation, item by item:
1. Rule line: present, `operations-gold-rule.md` section 2 "Bar word about the premises (H1, T-116...)", worded as requested, including "never reword gold to dodge the word reader". Closed.
2. Dev gold: SUB-211 = `restaurant; bar_pub`, SUB-222 = `lounge_nightclub; bar_pub`, alcohol item "full liquor". Closed.
3. Re-runs, done by me (temp TMPDIR, 0 model calls, no deliverable written): v11 `--self-check` ok; lint `--self-check` PASS; `--check-ops-gold` SUB-127-173 copy 47/47; `--check-gold` T-108 copy 32/32; lint on T-108 dev gold copy (v11 default) PASS, 0 failures, 7 info, 32 files. Operations recomputed straight from the 21 cached T-108-live extractions with v11 `ops_items_hit`: **15/20**, same split as the analysis (misses 207, 208, 213, 216, 219). The H1 repro now goes the right way: on SUB-211 gold, "... full liquor ..." (bar dropped) = miss, "... full bar with liquor ..." = hit.
- The M1 wording in the analysis is corrected (misses described as passing class mentions). Medium/Low M2-M5, L1-L2 stay in the backlog.

New, Medium only (backlog): M6 the rule line does not say what to do with non-premises compounds ("salad bar", "sushi bar", "espresso bar", "bar snacks only"); the reader counts each as `bar_pub`, so a correct answer for a non-bar card misses. Fails closed (under-credits), not a false hit; add one rule line before T-117 gold is written.

SUB-211 route gold (R9/R10 vs R2): both give `senior_referral`, so the scored route value is unaffected; cite text left to @senior-underwriter / @head-of-underwriting, not blocking.

**Freeze statement:** v11 at sha256 `7ddcfb50...fcbb` and lint at `01147a75...a653` may be frozen for the next hold-out. Any byte change to either reopens this check. This is not a production approval; the T-027 veto stands.
