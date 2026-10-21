# Per-LOB test plan

- Author: @senior-test-engineer (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Design only. No test, gold, inbox or scorer file is changed by this document. Synthetic data only.
- Basis: `deliverables/pm/lob-roadmap.md`, `deliverables/architecture/lob-engine-design.md`, `deliverables/lobs/*/spec.md`, `underwriting_pipeline/ai/eval_holdout_v11.py`, `tests/pipeline/`.
- A LOB is "done" only when every gate in section 6 passes for that LOB, not when the code merges.

## 1. Sets per LOB

| Set | Size | Purpose | Rule |
|---|---|---|---|
| Dev | 10–15 | Build the pack, find reader gaps | May be re-run freely; never quoted as a score |
| Hold-out in scope | 20 | The only score that counts | Gold written first, frozen, run once (D-020/D-022) |
| Hold-out out of scope | 10–12 | Leakage and recall | Same 4 criteria plus LOB-specific ones, if approved |
| Quick set | 15 | After each approved change | Drawn from dev; not a hold-out |

Wave 1 keeps the T-117 shape: **dev 12, hold-out 20 in + 12 out**, except `commercial_package`, whose dev set is the 10 files built in this task. Later waves use **dev 10, hold-out 20 in + 12 out** (D-120 item 8: 20/12 for all waves).

## 2. Mix by LOB

Legend for loss runs: **A/B/C** = the three published typed formats; **NKL** = no-known-loss letter; **none** = no run on file; **scan** = scanned run; **sheet** = loss-run table in csv/xlsx.

| LOB | Wave | Dev | Hold-out in/out | Loss-run mix (in-scope) | Lint focus | Pytest suites |
|---|---|---|---|---|---|---|
| business_owners_policy | 1 | 12 | 20 / 12 | 8 A, 3 B, 3 C, 2 NKL, 2 none, 2 scan | Baseline format; every existing rule | All existing 43 + baseline snapshot |
| commercial_property | 1 | 12 | 20 / 12 | 8 A, 2 B, 3 C, 2 NKL, 2 none, 3 scan | Property lines; BPP/sprinkler scored; schedule conflict | Property required/optional, BPP, sprinkler, scope criterion 2 |
| general_liability | 1 | 12 | 20 / 12 | 8 A, 3 B, 2 C, 2 NKL, 3 none, 2 scan | COPE fields `not in documents`; `requires_tiv: false` | GL route without TIV, R6 bypass, required set |
| commercial_package | 1 | 10 (dev set SUB-270–279: 6 in / 4 out) | 20 / 12 | 7 A, 3 B, 3 C, 2 NKL, 2 none, 3 scan | Both coverage sections; one TIV line | Package pack, either-section-out placeholder |
| umbrella | 2 | 12 | 20 / 12 | 6 A, 3 B, 3 C, 2 NKL, 3 none, 3 scan | New limit lines; U1–U5; TIV `not in documents` | New fields, U rules, criterion 5 deferred |
| inland_marine | 2 | 10 | 20 / 12 | 6 A, 3 B, 3 C, 2 NKL, 3 none, 3 sheet | Item-level schedule; no single TIV | Schedule items, limits per item |
| builders_risk | 2 | 10 | 20 / 12 | 5 A, 3 B, 3 C, 2 NKL, 3 none, 4 sheet | Project value and dates | Project fields, scope |
| commercial_auto | 2 | 10 | 20 / 12 | 5 A, 3 B, 3 C, 2 NKL, 4 none, 3 sheet | Vehicle rows; VIN/year | Vehicle schedule reader, limits |
| workers_comp | 2 | 12 | 20 / 12 | 5 A, 4 B, 3 C, 2 NKL, 4 none, 2 sheet | Payroll by class; state | WC fields, state rules, class codes |
| crime | 3 | 10 | 20 / 12 | 4 A, 3 B, 3 C, 2 NKL, 4 none, 4 sheet | Financial statements; limits | Crime limits, controls |
| surety_bonds | 3 | 10 | 20 / 12 | 3 A, 3 B, 3 C, 2 NKL, 5 none, 4 sheet | Penal sum; financial capacity | Bond fields, financial reader |
| personal_homeowners | 3 | 12 | 20 / 12 | 5 A, 3 B, 3 C, 2 NKL, 4 none, 3 scan | Dwelling/contents split; mortgagee | Consumer fields, state forms |
| personal_auto | 3 | 12 | 20 / 12 | 4 A, 3 B, 3 C, 2 NKL, 5 none, 3 sheet | Drivers/vehicles | Consumer fields, MVR placeholder |
| directors_and_officers | 4 | 10 | 20 / 12 | 3 A, 3 B, 3 C, 2 NKL, 6 none, 3 scan | Limits-rated; no COPE | Entity/financial fields |
| errors_and_omissions | 4 | 10 | 20 / 12 | 3 A, 3 B, 3 C, 2 NKL, 6 none, 3 scan | Professional class; claims-made | Professional class, limits |
| cyber_liability | 4 | 10 | 20 / 12 | 3 A, 3 B, 3 C, 2 NKL, 6 none, 3 scan | Controls and data volume | Controls fields |
| trade_credit | 4 | 10 | 20 / 12 | 2 A, 2 B, 2 C, 2 NKL, 7 none, 5 sheet | Buyer-level rows | Buyer schedule, concentration |
| key_person | 4 | 10 | 20 / 12 | 2 A, 2 B, 2 C, 2 NKL, 7 none, 5 sheet | Face amount; financials | Face amount, financial reader |
| legal_expense | 4 | 10 | 20 / 12 | 3 A, 2 B, 2 C, 2 NKL, 6 none, 5 sheet | Limits; matter profile | Programme terms |
| pollution_liability | 4 | 10 | 20 / 12 | 3 A, 3 B, 3 C, 2 NKL, 6 none, 3 scan | Site/contaminant fields | Site fields, hazmat |
| kidnap_ransom | 4 | 10 | 20 / 12 | 2 A, 2 B, 2 C, 2 NKL, 7 none, 5 sheet | Territory and limits | Territory fields |
| political_risk | 4 | 10 | 20 / 12 | 2 A, 2 B, 2 C, 2 NKL, 7 none, 5 sheet | Country exposure | Country fields, sanctions hook (compliance) |
| flood_commercial | 5 | 12 | 20 / 12 | 4 A, 3 B, 3 C, 2 NKL, 5 none, 3 scan | Flood zone/elevation | Zone fields, cat data |
| earthquake_commercial | 5 | 12 | 20 / 12 | 4 A, 3 B, 3 C, 2 NKL, 5 none, 3 scan | Seismic zone/construction | Seismic fields, PML hook |
| terrorism | 5 | 10 | 20 / 12 | 3 A, 2 B, 3 C, 2 NKL, 7 none, 3 sheet | Location/TIV aggregation | Aggregation fields |
| aviation | 5 | 10 | 20 / 12 | 2 A, 2 B, 2 C, 2 NKL, 8 none, 4 sheet | Aircraft/crew | Aircraft schedule |
| life | 5 | 15 | 20 / 12 | 2 A, 2 B, 2 C, 3 NKL, 10 none, 1 scan | Face amount; medical/financial lines | Life fields, fairness review hook |
| health | 5 | 15 | 20 / 12 | 2 A, 2 B, 2 C, 3 NKL, 10 none, 1 scan | Plan/member data | Health fields, fairness review hook |
| general | 5 | 10 | 20 / 12 | 3 A, 2 B, 2 C, 3 NKL, 8 none, 2 scan | Triage only; no route | Triage routing, refusal reasons |

Mix rules:

- Every in-scope set includes at least two NKL, two `none`, and two scans; every wave includes at least one Spanish document and one multi-location file in the **out-of-scope** set (to exercise criteria 2 and 3).
- Wave 1 must reuse T-117 files where the LOB matches (BOP, property, GL); the package dev set is new and dev-only. It must **not** rewrite T-117 gold or scores.
- Each new LOB builds its own inbox folder (`simulation/inbox/<lob>/SUB-###/`) or a manifest mapping; no re-use of another LOB's gold.

## 3. Lint rules

Common (all LOBs):

1. Gold line format: every required line present once, `- ` prefix, no unknown scored line.
2. Scope line: exactly one, criteria 1–4 readable; a number outside 1–4 stops the run.
3. Operations: every item maps to a declared `business_type` or slot; anything else "move to notes".
4. Loss runs: the valued-as-of line holds exactly one ISO date when gold expects a date; absent on review cards.
5. Route/status: route from the closed set; a hold is on the status line, never the route line.
6. Conflict: `none` or a real two-sided conflict; no one-sided conflict.
7. No published score or gold file is edited by a lint run.

Per-LOB additions (only where the spec says so):

| LOB group | Extra lint |
|---|---|
| property / BOP / package | BPP line only if `bpp_limit` is in the pack; one TIV line per location |
| GL | COPE lines must read `not in documents` when property is not quoted |
| umbrella | Five limit lines; `TIV/construction/year built` must be `not in documents` |
| personal | Dwelling and contents separate; mortgagee line present when stated |
| specialty | Limits and financial lines; no COPE lines |
| cat | Zone/elevation/return-period values from a stated source only |
| life/health | Face amount/plan data; no medical inference; fairness fields flagged |
| general | No operations items; triage reason required |

A LOB lint is part of that LOB's done gate and must be hashed with the LOB's gold manifest.

## 4. Pytest coverage before a LOB counts as done

Shared suites (already exist, must stay green):

- `tests/pipeline/test_intake.py`, `test_extraction_gates.py`, `test_scope.py`, `test_routing.py`, `test_send_gates.py`.
- `tests/pipeline/test_lob_config.py`: pack loads, fails closed, baseline equality.
- `tests/pipeline/test_lob_regression.py`: cached-run replay per LOB; no model calls.
- `tests/pipeline/test_lob_routing.py`: the LOB's full route truth table (one case per rule id that applies).
- `tests/pipeline/test_lob_gold.py`: lint on the LOB's gold folder; fails on a missing line.
- `tests/pipeline/test_lob_ui.py`: render snapshot includes the LOB label, required fields and refusal reasons.

Per-LOB minimum cases:

1. One complete file → expected status, route, and every field value.
2. One file per required field missing → incomplete with that field named.
3. One file per applicable route rule (R1, R2, R7, R8, R10–R14, R16, R17, plus LOB-specific U/P/… rules).
4. One file per scope criterion (1–4, plus approved LOB-specific criteria).
5. One file per loss-run shape in the mix (A/B/C, NKL, none, scan).
6. One file with a stated conflict → both sides stored, field null, conflict listed.
7. One `extraction_failed` file → no suggestion, no draft, counted apart.
8. One multi-location file → manual intake with the reason on the card.
9. One Spanish file → manual intake; criterion 3.
10. One pack-missing/unknown-LOB case → fail closed, no extraction.

Every test uses `tmp_path`; no write to `simulation/`, `deliverables/**`, `team/` or real logs (D-069). No test calls the model.

## 5. Evaluation gates per LOB

| Gate | Threshold | Source |
|---|---|---|
| Every scored field | ≥ 18/20 (≥ 9/10 on the quick set) | D-013, D-020 |
| False completes | 0 | D-021 |
| Unsafe routes | 0 | D-096 |
| Scope leakage | 0 of out-of-scope files | P-055/D-105 |
| Scope recall | 100% of out-of-scope criteria | P-055 |
| Route accuracy | ≥ 18/20 | D-096 |
| Silent error rate | reported, 0 for any field marked automated | D-084 |
| Failed calls | counted apart, never cached | D-021/D-022 |
| Gold manifest | hashed before the run, unchanged after | D-020/D-022 |
| Lint | PASS on every gold file | T-117 pattern |
| Frozen code/prompt/scorer | hashes recorded before the run | D-113/D-114 |

A LOB that misses a gate is **not done**; it goes back to the backlog with the failing files named.

## 6. Definition of done (per LOB)

1. Pack exists, validates, and has a fingerprint.
2. Spec is written and every "needs review" item is either resolved or explicitly deferred.
3. Gold exists first, lint PASS, manifest hashed.
4. Dev set run clean; no model call in tests.
5. Hold-out (20 in + 10/12 out) run once, scored once, every gate in section 5.
6. `python -m pytest tests/pipeline -q` green, including the LOB suites.
7. @model-risk check (High only) on the pack, gold and scorer; @compliance sign-off where the LOB touches regulated data.
8. @senior-underwriter UI check on the LOB card (D-065), High only.
9. Standup, deliverable paths and "What's new" line recorded.

## 7. Sequencing

Wave 1 test work can start only after the engine's baseline snapshot test exists. Then: BOP baseline → property → GL → package, one LOB per branch, each with its own pack, `gold-set-<lob>/` and lint. Wave 2 starts with umbrella, then the schedule lines. No LOB's tests may import another LOB's gold.

## 8. Needs review

- *Decided (D-120 item 8): 20/12 out-of-scope for all waves.*
- The package dev set (`SUB-270–279`) is new and dev-only; Wave 1 reuses T-117 files for BOP/property/GL and builds fresh hold-outs for package and umbrella.
- The exact pytest file names once the engine lands.
