# LOB roadmap — 29 lines on one shared engine

- Author: @pm (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Inputs: `deliverables/pm/lob-expansion-plan.md` (T-101); `InsuranceLine` in `src/insureflow/rating/models.py` (29 members); `deliverables/head-of-underwriting/carrier-appetite.md`; `deliverables/head-of-underwriting/carrier-match.md`; `deliverables/senior-underwriter/required-fields.md`; the T-117 pipeline state.
- Design only. No pipeline code, prompt, scorer, lint, gold, inbox or frozen file is changed by this roadmap. Synthetic appetite and placeholder carriers only.
- Not a production approval. The T-027 veto stands. Every wave needs its own gold-first evaluation before it counts as built.

## 1. Wave logic

Waves are ordered by **reuse of today's small-commercial pipeline**: the same readers, the same nine fields, the same scope criteria, the same operations slots and the same carrier-rule shape. A line moves to a later wave for each of these it changes:

| Change | Cost |
|---|---|
| New required field or new document type on the same exposure base | +1 wave |
| New exposure base (vehicles, payroll/class codes, limits, face amount, return period) | +1 to +2 waves |
| New regulator (state WC, life & health, flood/terrorism) | +2 waves |
| Consumer workflow (personal lines) | +1 wave |

Effort is a rough engineer-day range for config + fields + rules + gold + tests + review; it excludes the shared engine work in `deliverables/architecture/lob-engine-design.md`.

## 2. The 29 lines by wave

### Wave 1 — reuse today's pipeline (5 lines)

| LOB | Typical documents | What is new vs today | Main risks | Rough effort |
|---|---|---|---|---|
| `business_owners_policy` | ACORD 125 + 140-shaped application, email, carrier loss runs, SOV | **Reference line.** Today's nine fields, operations slots, scope criteria and routes | Baseline only; keep behaviour identical when the engine becomes settings-driven | 1–2 (spec + regression only) |
| `commercial_property` | Application, property schedule/SOV, loss runs, email | Same fields; property-only required set (BPP line, occupancy); TIV is the primary exposure | Schedule vs application conflicts; blanket vs per-location TIV | 3–5 |
| `general_liability` | ACORD 125 + 126-shaped application, email, loss runs | Same fields; property COPE optional, sales/payroll required | Class/operations reading; payroll vs sales | 3–5 |
| `commercial_package` | Application + property schedule + GL section, loss runs | Same as BOP with two coverage sections; no new readers | Double-counting TIV; two coverage limits | 3–5 |
| `umbrella` | Application + underlying declarations (GL, auto, employers liability) | **New fields:** underlying limits and umbrella limit; no building COPE | Underlying schedule not machine-readable; attachment logic | 6–9 |

### Wave 2 — property-adjacent schedules (4 lines)

| LOB | Typical documents | What is new vs today | Main risks | Rough effort |
|---|---|---|---|---|
| `inland_marine` | Application, equipment/schedule form, loss runs | Scheduled items and limits per item; no single building TIV | Item-level schedules; floaters vs property | 6–10 |
| `builders_risk` | Application, project schedule, loss runs | Project value, construction period, site address | Completed-value vs reported-value; project end date | 6–10 |
| `commercial_auto` | Application + auto schedule (VIN/year/vehicle), MVR where present, loss runs | Vehicle schedule; garage location; driver counts | VIN/schedule noise; state auto rules | 8–12 |
| `workers_comp` | WC application, class-code/payroll schedule, loss runs | Payroll by class code, experience mod, state | State rating manuals; class-code errors | 12–18 |

### Wave 3 — limits, financial and personal (4 lines)

| LOB | Typical documents | What is new vs today | Main risks | Rough effort |
|---|---|---|---|---|
| `crime` | Application, financial statements, loss runs | Limits by crime coverage; employee count; controls | Financial-statement reading; social-engineering sublimits | 8–12 |
| `surety_bonds` | Bond request, financial statements, work-in-progress | Penal sum, bond type, financial capacity | Surety judgment; indemnity; not a standard ACORD pack | 10–15 |
| `personal_homeowners` | Homeowners application, inspection, loss runs | Consumer named insured, dwelling/contents split, mortgagee | Consumer forms and state rules; high volume | 10–15 |
| `personal_auto` | Personal auto application, vehicle schedule, MVR | Drivers, vehicles, territory | Consumer state rules; driver/vehicle matching | 10–15 |

### Wave 4 — specialty and professional (9 lines)

| LOB | Typical documents | What is new vs today | Main risks | Rough effort |
|---|---|---|---|---|
| `directors_and_officers` | Application, financials, board/ownership info | Limits-rated; no COPE; entity and financial profile | Securities exposure; prior-acts exclusions | 12–18 |
| `errors_and_omissions` | Application, revenue/headcount, loss runs | Professional services class; limits-rated | Class/territory; claims-made wording | 12–18 |
| `cyber_liability` | Application, controls questionnaire, revenue | Controls and data-volume fields; no property COPE | Rapidly changing wording; ransomware limits | 12–18 |
| `trade_credit` | Buyer/obligor schedule, financials, credit limits | Buyer-level exposure; credit limits | Counterparty data; concentration | 15–20 |
| `key_person` | Application, financials, key-person details | Face amount and financial underwriting | Small market; manual review | 12–18 |
| `legal_expense` | Application, matter/limit profile | Limits-rated, low data volume | Programme terms; panel counsel | 10–15 |
| `pollution_liability` | Application, site/operations description, loss runs | Site and contaminant fields | Environmental exposure; unknown sites | 15–25 |
| `kidnap_ransom` | Application, travel/territory profile | Territory and limit fields | Low volume; high-severity terms | 10–15 |
| `political_risk` | Application, country/obligor exposure | Country risk fields | Sanctions and country limits | 15–20 |

### Wave 5 — catastrophe, life & health, catch-all (7 lines)

| LOB | Typical documents | What is new vs today | Main risks | Rough effort |
|---|---|---|---|---|
| `flood_commercial` | Application, flood zone/elevation data, SOV | Flood zone, elevation, return period | Cat modelling; NFIP vs private | 18–25 |
| `earthquake_commercial` | Application, seismic data, SOV | Seismic zone, construction class, PML | Cat modelling; reinsurance terms | 18–25 |
| `terrorism` | Application, location/TIV schedule | Aggregation and stand-alone limits | Reinsurer-driven; aggregation | 15–20 |
| `aviation` | Aviation application, aircraft schedule, pilot records | Aircraft and crew data | Specialised manual; low volume | 18–25 |
| `life` | Life application, medical/financial questionnaire, MIB-style data | Face amount; mortality underwriting | Health data; state DOI; fairness review | 25–40 |
| `health` | Health application, plan/rating data | Plan and member data; ACA/parity rules | State and federal regulation; fairness review | 25–40 |
| `general` | Whatever the producer sends; no fixed pack | Catch-all; must route to a person | Cannot be auto-scoped or auto-routed | 3–5 (triage only) |

## 3. Cross-wave rules

- Every LOB is a **configuration pack** plus its own gold and hold-out; no per-LOB code forks (`deliverables/architecture/lob-engine-design.md`).
- Gold first, then a hold-out scored once, per LOB (D-020/D-022); no pooled scores.
- One shared workbench with a LOB label and per-LOB field set; no separate UIs per line.
- New document types go through the existing readers first; a new reader is a separate, reviewed change.
- Placeholder carriers A/B/C stay synthetic until @head-of-underwriting and @compliance approve real appetite.
- Wave 1 must keep today's small-commercial behaviour byte-identical; its regression proof is the entry gate for every later wave.

## 4. Sequence and gates

1. Wave 1 config extraction + baseline regression (shared engine step 1–4) — no new model calls.
2. Wave 1 two new lines (package, umbrella) with their own gold-first evaluation.
3. Wave 2 one line at a time, property schedules first, WC last with @compliance.
4. Wave 3 personal lines only after the consumer workflow and state-form questions are answered.
5. Wave 4/5 after specialist roles and actuarial sign-off; life/health needs @responsible-ai before any build.

## 5. Open questions for the user

- Confirm the Wave 1 membership (three pilot lines + package + umbrella) and whether `commercial_package` is a true duplicate of BOP for now.
- Confirm `general` is triage-only (no extraction, no route) rather than a real line.
- Confirm the effort ranges are the right unit for planning, or replace them with calendar weeks at the next planning round.
