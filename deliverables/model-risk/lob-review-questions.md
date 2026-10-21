# LOB review questions — @model-risk

- Author: @model-risk (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- **No verdicts today.** This is the question list each LOB must answer before a build check or a hold-out can be reviewed. Synthetic data only.
- Standing: the T-027 production veto is unchanged; an assist-only pilot is outside it only while C1–C8 hold (`deliverables/model-risk/T-027-assist-mode-pilot.md`).

## 1. Questions that apply to every LOB

1. What is the **frozen run** (code SHA, prompt sha, pack fingerprint, model, host, temperature) and where is it recorded?
2. Which **scorer version** and **lint hash** are used, and were they frozen before the gold existed?
3. What are the **gold manifest hashes**, and was any gold or score file changed after the run? (D-020/D-022)
4. What are the **per-field floors** and the source of each (D-013, @actuary, @head-of-underwriting)?
5. What are the **scope criteria** for this LOB, and how is leakage measured (0 required)?
6. What is the **route safety** definition (which gold routes are unsafe for this LOB)?
7. How are **failed calls** counted and kept out of the rates, and is a failed call ever cached?
8. What is the **silent-error** measure and the automation rate, per field, never pooled?
9. Which fields are **weak** (below floor) and what warning text quotes their measured rate on the card?
10. What **human confirmation** is required before any value is used, and where is it logged?
11. What is the **rollback** if the pack changes baseline behaviour (the `LOB_ENGINE=off` path)?
12. What is the **prompt-change control** (P-###, exact user line) and who checks it?
13. What **cache key** components identify the pack, and can an old reply be replayed under a new pack?
14. What is the **model host/data path** (Groq free tier, D-011/D-012) and is any paid API used?

## 2. Per-LOB questions

| LOB | Questions |
|---|---|
| business_owners_policy | Does the baseline pack reproduce today's prompt sha and route truth table exactly? Which files prove it? |
| commercial_property | How is a property-only file held without TIV, and does the pack's required set change the completeness gate? Is BPP a scored field or a note? |
| general_liability | What replaces R6 (TIV hold) when `requires_tiv` is false? What is the source for any sales-based referral? |
| commercial_package | Does "either coverage section out of appetite → refer" have a written source? How is a missing section counted (incomplete vs leak)? |
| umbrella | Are the new limit fields scored, and what is the gold source? What are U1–U5 and who signs them? Is scope criterion 5 approved? |
| inland_marine | How are item-level schedules scored without a single TIV? What is the per-item floor? |
| builders_risk | How are project value and project dates validated against the completion period? |
| commercial_auto | How are vehicle rows matched (VIN/year) and what is the silent-error measure per vehicle field? |
| workers_comp | Which state manuals are in scope, and how is the class-code/payroll join validated? |
| crime | Are financial-statement values read by the model or by a rule? What is the floor for financial fields? |
| surety_bonds | What is the financial-capacity measure, and is it scored or only displayed? |
| personal_homeowners | What are the consumer-specific scope criteria, and how is dwelling/contents split validated? |
| personal_auto | How are drivers matched to vehicles, and what is the state-rule source? |
| directors_and_officers | What is the limits-rated target, and which financial fields are scored? |
| errors_and_omissions | How is claims-made wording validated, and what is the professional-class source? |
| cyber_liability | Which control answers are scored, and how is data volume validated? |
| trade_credit | How is buyer-level data scored without pooling counterparties? What is the concentration measure? |
| key_person | What is the face-amount source, and how is financial underwriting validated? |
| legal_expense | What is scored (limits/terms) and what is left to a human? |
| pollution_liability | How are site and contaminant fields validated, and what is the scope rule for unknown sites? |
| kidnap_ransom | What is scored (territory/limits) and what is the low-volume evidence base? |
| political_risk | Which country/sanctions checks are deterministic, and what is the model's role? |
| flood_commercial | What is the flood-zone/elevation source, and how is cat modelling kept out of field scoring? |
| earthquake_commercial | Same as flood, plus the seismic-zone source and PML boundary. |
| terrorism | How is aggregation measured, and what is the reinsurer-driven gate? |
| aviation | Which aircraft/crew fields are scored, and what is the low-volume evidence base? |
| life | How is medical data handled, and what is the fairness review before any build? |
| health | How are plan/member fields validated, and what is the ACA/parity review path? |
| general | Is this triage-only (no extraction, no route), and what is the refusal reason? |

## 3. Evidence expected at a build check

- Pack file and fingerprint; validator output.
- Gold manifest hashes; lint PASS output.
- Dev and hold-out run records with call counts, failures, retries and tokens.
- Per-field table (hits, misses, not credited, flagged) and the gate table.
- Route truth table and the unsafe-route proof.
- Scope leakage/recall evidence per criterion.
- A no-call regression proof that `small_commercial` is unchanged.

## 4. What this list is not

Not a verdict, not an approval and not a checklist that can be waived by the author. A LOB without answers to sections 1–2 does not get a build check.
