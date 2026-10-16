# @model-risk check — D-094 / P-047 (operations), scorer v2, retry logging

Date: 2026-10-15. Reviewer: @model-risk (independent). Scope: D-094 items 3, 4, 5 as typed by @user. High findings in detail; Medium/Low one line each.
Not a production approval. The T-027 veto is not in scope and stands. SUB-127–146 is development data; nothing here is a hold-out score.

## Verdict: APPROVE WITH CHANGES (P-047 not accepted as done until H1 is closed)

Items 4 (scorer v2) and 5 (retry logging, RUN-RULES.md) meet their criteria. Item 3 (a) and (c) meet theirs for details on the cited line. Item 3 (b) does not meet "compares source text": it compares only the cited line.

## What I re-ran (no model calls, no writes outside this memo and my log lines)
- Self-checks, `.venv/bin/python <file> --self-check`: llm_extract, prepare, regression_dev, eval_holdout_v2, eval_holdout_127, workbench: all ok.
- `eval_holdout_127.py` last changed in 964c159 (D-089), before D-094: frozen, unchanged. `diff` v1 → v2 shows only the three stated changes (not-in-documents rule, per-row retries, pipeline-commit header).
- `workbench.match` on the saved reports: route 14/20, senior_referral 0 of gold 2, carrier_c 0 of gold 2, as reported. With status forced to complete, SUB-141 and SUB-146 → senior_referral and SUB-133 → carrier_c, as claimed. Operations 18/20, silent errors 0, false completes 0: match the score file.

## High

### H1 — the missing-item check and the bar/liquor referral see only the cited line, not the source (item 3 b, c)
`check_operations` runs `ops_missing` on `_ops_source(text, start, end)`: the cited line plus unlabeled continuation lines, stopping at the next "Label:" line. `workbench._ops` reads value + quote. A rule item stated on its own labeled line in the same document is never compared, and the answer keeps confidence 1.0. Reproduced:
- Source `Operations: Family restaurant, 80 seats.` / `Liquor: full bar, 35% of sales`, answer "Family restaurant, 80 seats", quote = the Operations line → `needs_review False, confidence 1.0, reason None`; `workbench.match` (complete) → **carrier_b**, no D-079 referral.
- SUB-141 application as filed: answer = the Operations line only (wood-fired oven, two fryers on the separate `Cooking operations:` line left out) → `confidence 1.0, needs_review False`. Cooking and frying/open flame are gold-rule items.
The dev files have this shape (separate `Cooking operations:` line in SUB-130/132/141/146, `Stories:` in all apps); the dev result is clean only because the model happened to quote across those lines. This is the T-027 H2 failure (details dropped at full confidence) moved from the operations line to the next line, and on alcohol it can route a liquor risk to a carrier without the referral.
**Remediation (closes H1):** `_ops_source` also reads, in the cited file, every labeled line whose label names a rule item (cooking, liquor/alcohol/beer/wine, seating/seats, units, hours, entertainment/music, delivery/catering, patio, security, hazardous); `check_operations` flags any missing item; `_ops` reads those same lines for carrier match and the D-079 referral (negation as now). Add both cases above as self-checks. Re-score SUB-127–146 from cache and report operations hits, silent errors, routes. This is a code change under P-047 (or a new P-### if @user prefers); I do not make it.

## Medium / Low (backlog, one line each)
- M1: wrong polarity is not caught: source "full liquor license", answer "no liquor license" → `ops_missing` returns [] (the answer word is present, negated). Negate-aware answer match.
- M2: the committed reports/ and SUB-127-146-dev-v2.{md,json} are the cache re-score (retries 0 everywhere); the 9 live 429 retries survive only in run.log. Keep the live-run score file and reports beside the cache re-score, or never overwrite them.
- M3: the committed score file says "uncommitted changes in prepare.py; not a score of that commit" (scored before 093a6f9 was committed). Re-score at a clean commit.
- M4: SUB-134 is plain "complete" and routes no_match (glass shop on no carrier list) vs gold carrier_c; overridable, so safe, but a route miss on a complete file. Appetite list check by @senior-underwriter.
- M5: SUB-139 forced complete routes senior_referral (habitational without sprinklers) vs gold no_match; confirm which gold is right before the next route count.
- L1: the multi-line quote (SUB-130/133/141) spans employees, sales, TIV and sprinkler lines; `_ops` now reads those words for routing. Bound the quote to operations lines when H1 is built.
- L2: v2 header still says "Scored by @model-risk with this file unchanged after the gold answers were written" — not true for a dev re-score; make it conditional.
- L3: gold rule lists cooking as required, but published SUB-130/132/141 gold leaves out the stated cooking line (allowed: rule is not applied backward). Note for the next hold-out gold.
- L4: NEGATED drops only one word after "no" ("no bar or liquor" keeps "liquor"): errs toward referral, safe; note only.

## LOOK-AGAIN on H1 — commit 086a0e0 (2026-10-15, @model-risk)

**Verdict: H1 OPEN.** The fix passes my two probes literally, but it reads only exact label spellings, not "every labeled line whose label names a rule item". The repo's own application forms use other spellings, so the H1 failure (rule item on its own line, answer keeps confidence 1.0, no review) is still reproducible on repo data. Not a production approval; P-047 stays not done.

What I re-ran (no model calls, no keys printed, no writes outside this memo and my log lines; `git status` clean for `underwriting_pipeline/` and `simulation/` after):
- Self-checks at 086a0e0, `.venv/bin/python <file> --self-check`: prepare, llm_extract, regression_dev, eval_holdout_v2, workbench: all ok.
- Probe 1 (`Operations: Family restaurant, 80 seats.` / `Liquor: full bar, 35% of sales`, answer = Operations line): needs_review True, confidence 0.74, "operations may be missing: liquor, bar"; `workbench.match` (complete) → senior_referral, bar/liquor note. **Fixed.**
- Probe 2 (SUB-141 application as filed, answer = Operations line): confidence 0.74, "operations may be missing: frying or open flame", context = the `Cooking operations:` line. **Fixed.**
- Re-score from cache: recomputed `workbench.match` on all 20 saved reports and `ops_lines` from the inbox text for each cited source: 0 mismatches with readout.json / reports; route 14/20, operations hits 18/20, as reported. The dev files only use `Cooking operations:`, so the dev re-score does not exercise the gap below.

### H1 (still open) — OPS_LABEL matches only fixed label spellings
`OPS_LABEL` accepts `liquor|alcohol|beer|wine|bar|seating|seats|units|number of units` only as the whole label, and `cooking…`/`hours…` only with word characters and spaces after them. A label that names a rule item in any other way is not read. Reproduced at 086a0e0 (answer = "Family restaurant", cited Operations line, rule line below; all → needs_review False, confidence 1.0, route carrier_b, no referral):
`Liquor sales: 35% of sales, full bar`, `Alcohol sales: …, full bar`, `Liquor license: full bar`, `Bar sales: 35%`, `Seating capacity: 120`, `Live entertainment: DJ Fri-Sat`, `Patio: …`, `Delivery: …`, `Security: two bouncers`, `Hazardous materials: propane tanks`.
On repo data: **SUB-122 application.pdf** (`Cooking / hood / suppression: Wood-fired oven, fryer x1…` and `Bar / liquor: Full bar, last call 1am`): answer = the Operations line → confidence 1.0, needs_review False, context None; with those two lines read, `ops_missing` returns `['liquor', 'hours']`. The `Bar / liquor:` and `Cooking / hood / suppression:` form appears in at least SUB-107, 110, 112 (`Bar / licor:`), 113, 114, 115, 121, 122, 125, 126; `Liquor sales:` in SUB-002 and SUB-011.
**Remediation (closes H1):** a labeled line counts when its label (text before the first colon, up to ~40 characters, `/` and `%` allowed) contains a rule-item word from `OPS_ITEMS`/`OPS_COUNTS` source patterns or the label words above, incl. `licor`; `ops_lines` uses that test; keep `_ops` reading `context`. Add self-checks for `Bar / liquor: Full bar, last call 1am`, `Cooking / hood / suppression: …fryer…`, `Liquor sales: 8 percent of sales`, `Seating capacity: 120`. Re-score SUB-127–146 from cache (must stay 0 silent errors) and run SUB-122's saved run as a probe only (published hold-out: no score rewrite, D-020). Code change under P-047; I do not make it.

### New High: none.

### Backlog (one line each)
- M6: rule lines in another file of the same submission are not read (SUB-011 `reply.md` "Liquor sales: 8 percent of sales" while operations cites `application.md`) → confidence 1.0, carrier_b. Read rule lines across the submission's files.
- M7: the D-079 referral fires only on bar words; "full liquor license" / "Liquor sales: 35%" with no bar word routes carrier_b (needs_review is the only guard). @senior-underwriter to confirm whether liquor words should refer.
- L5: `context` now carries "Cooking operations: None" lines into `_ops` for 11 of 20 dev files; no route change today (0 mismatches), but "none" is not in NEGATED. Note only.

## LOOK-AGAIN 2 on H1 — commit b73bd40 (2026-10-15, @model-risk)

**Verdict: H1 CLOSED.** The label test now reads any label (≤40 characters, `/ & ( ) . -` allowed) that contains a rule-item word, and every repro form from LOOK-AGAIN 1 except `Delivery:` and the bare `Seating capacity: 120` count (both non-routing; backlog) now drops the answer below the confidence line with the item named. Not a production approval; an approved P-047 is not a production approval, and the published hold-outs stay unscored by this change (D-020).

What I re-ran (no model calls, `LLM_API_KEY` unset, no keys printed; `git status` clean for `underwriting_pipeline/` and `simulation/` before and after; probes in my scratchpad only):
- Self-checks at b73bd40, `.venv/bin/python <file> --self-check`: prepare, llm_extract, regression_dev, eval_holdout_v2, workbench: all ok.
- Cache re-score: for all 20 saved reports I recomputed `ops_lines` from the inbox text of each cited source and `workbench.match`: 0 context mismatches, 0 route mismatches. Operations 18/20, route 14/20, silent errors 0 (no miss without review), as the readout says.
- SUB-122 probe (published hold-out, probe only, no score): `ops_lines(application.pdf)` returns both `Cooking / hood / suppression: Wood-fired oven, fryer x1…` and `Bar / liquor: Full bar, last call 1am`; answer = the Operations line → needs_review True, confidence 0.74, "operations may be missing: liquor, hours" (was 1.0, no review).
- LOOK-AGAIN 1 repro lines (answer "Family restaurant"): `Liquor sales:`, `Alcohol sales:`, `Liquor license:`, `Bar sales:`, `Live entertainment:`, `Patio:`, `Security:`, `Hazardous materials:`, `Bar / licor:` all → review at 0.74 with the item. `Bar / liquor: Full bar` in context → senior_referral on a complete report.
- Repo sweep: every labeled line in `simulation/inbox/*` (incl. PDFs via `sources.read_folder`) whose label holds a rule-item word and states one: only two Spanish `cocina` labels are not read (M8 below).

### New High: none.

### Backlog (one line each)
- M8: `cocina` (an OPS_ITEMS source word) is not in OPS_LABEL: SUB-090 `Equipo de cocina: Plancha de gas, freidora…` with answer "Restaurante de tacos…" stays 1.0, no review (gold route is hold; `cooking_facts` also returns not_stated for this Spanish label). Add `cocina` / Spanish cooking labels.
- M9: a label word alone states the item: `Bar / liquor: None` / `: No` → "operations may be missing: liquor, bar" and senior_referral (bar referral reads the label); `Security: none`, `Hazardous materials: None`, `Liquor sales: 0%` likewise flag. Conservative direction (more human review), repo case SUB-002 `Liquor sales: none`. Strip the label or treat none/no/N/A values as negated.
- L6: label class has no `%` or `#` (`Alcohol (% of sales): 35% full bar`, `Liquor license #: …` not read) and no fryer/grill/catering/music/delivery label words (`Deep fryers: 2`, `Catering:` not read). No repo file uses these forms today.
- L7: `Seating capacity: 120` is read but the count is not taken (OPS_COUNTS needs "120 seats" / "capacity of 120"); the new self-check uses "60 seats" so it does not test this. Seats do not route today.
