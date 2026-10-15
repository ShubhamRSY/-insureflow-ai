# LOB expansion plan for the 29 InsuranceLine lines

Co-authored: @pm (skeleton, rollout rationale) + @head-of-underwriting (appetite, pack, roles)

## 1. Families

| Family | Lines (all 29 members of `InsuranceLine`) |
|---|---|
| Small commercial P&C | commercial_property, general_liability, workers_comp, business_owners_policy, commercial_package, umbrella, commercial_auto, inland_marine, builders_risk |
| Specialty / professional | directors_and_officers, trade_credit, errors_and_omissions, key_person, cyber_liability, crime, surety_bonds, aviation, pollution_liability, kidnap_ransom, political_risk, legal_expense |
| Catastrophe | flood_commercial, earthquake_commercial, terrorism |
| Personal | personal_homeowners, personal_auto, general |
| Life & health | life, health |

9 + 12 + 3 + 3 + 2 = 29; every line appears in exactly one family, none omitted. Assumptions: (a) `general` (undetermined/catch-all) sits with personal per `PERSONAL_LINES` — @pm to confirm; (b) terrorism is catastrophe (property-attacked, reinsurer-driven), not specialty; (c) inland marine, builders risk and crime are grouped by data shape (schedules/limits close to the property pipeline), not by their rating manuals.

## 2. LOB pack format

**The pipeline stays shared** — intake, extraction, completeness, workbench and sending are one codebase. Each LOB is a configuration pack plus its own evaluation; no per-LOB code forks.

Pack fields:
- Identity: lob id, family, states in appetite, effective/expiration handling.
- Exposure base: what scoring computes from (TIV, payroll, sales, limits, face amount) — drives field mapping.
- Required extraction fields and document types.
- Carrier appetite rules (carriers, sublimits, out-of-appetite triggers) and hazard/score rules (reason codes, weights, per-LOB referral thresholds).
- Gold set path, hold-out path, per-LOB score targets.

Document types — ACORD section forms where they exist; numbers I am not sure of are marked *to confirm with @producer*:

| LOB group | Forms |
|---|---|
| Property / BOP / package | ACORD 125 (commercial application), ACORD 140 (property schedule) |
| General liability | ACORD 126 (GL section) with 125 |
| Commercial auto | ACORD 127 (auto section) with 125 |
| Workers comp | WC section form (ACORD 133?) — to confirm with @producer |
| Inland marine / builders risk | schedule form (ACORD 137?) — to confirm with @producer |
| Personal home / auto | ACORD 128 / 129 personal sections — to confirm with @producer |
| Life & health | no ACORD section mapping I can confirm — to confirm with @producer |
| Specialty / cyber / cat | carrier-specific supplements, no standard ACORD section — to confirm with @producer |

Evaluation per LOB, mirroring D-020/D-022: gold written first, then a 20-submission hold-out scored once with no code change after the gold exists; the quick set of 15 runs after each approved change. Proposed per-LOB targets (**numbers to confirm with @actuary**): every scored field ≥ 9/10 on the hold-out (the D-013 floor), 0 false completes, failed model calls counted apart and never cached (D-021).

## 3. Specialist roles

One specialist per family, not per line. **No new subagent files are created now** — these are roles to propose later (names and scopes for @pm):

- Commercial P&C specialist — COPE, loss runs, the current pilot lines.
- Management liability & professional lines specialist — D&O, E&O, cyber, credit, key person; limits-rated, no COPE.
- Cat & excess specialist — flood, earthquake, terrorism; works with @actuary on return periods and reinsurance.
- Personal lines specialist — homeowners and auto; state forms and policy conditions, high volume, low per-file complexity.
- Life & health specialist — face amount, medical and financial underwriting, carrier manuals.

Shared roles needing extra expertise: **@compliance** — life & health (state DOI rules, ACA/parity) and state-by-state differences for workers comp and personal lines; **@actuary** — life & health reserving and mortality, cat return periods, confirmation of per-LOB score targets; **@responsible-ai** — fairness review before life & health goes live; **@senior-underwriter** — per-family workbench review (D-065).

## 4. Rollout order

Starts after the current pilot lines (BOP, property, general liability — Texas). Front-loads lines closest to the existing COPE/property pipeline.

1. **commercial_package** — same COPE data and documents as BOP; highest small-commercial volume; lowest risk.
2. **umbrella** — attaches to underlying GL/property already extracted; little new data; low risk.
3. **inland_marine, builders_risk** — property schedules, same extraction; moderate volume; low–medium risk.
4. **commercial_auto** — good Texas volume; exposure shifts from TIV to vehicles/garage; medium risk.
5. **workers_comp** — high agency volume but state-regulated rating and experience mods; medium–high regulatory risk, run alongside @compliance.
6. **crime, surety_bonds** — limits and financial-statement rated; lower volume; medium risk (penal-sum judgment).
7. **personal_homeowners, personal_auto** — high volume but consumer forms and rules, different workflow; medium risk.
8. **specialty / professional (12 lines)** — non-COPE, carrier-specific supplements; medium–high risk; one line at a time, E&O/D&O first, cyber last.
9. **flood_commercial, earthquake_commercial, terrorism** — actuarially deep, reinsurer-driven; last.

Assumptions: agency volume ranks commercial above personal — @pm to confirm; flood may move earlier if San Antonio flood volume justifies it — flag @actuary and @producer.

## 5. Never shared across lines

- Scores and score targets.
- Gold sets and hold-out sets (each gold-first, scored once, per LOB).
- Carrier appetite rules and carrier-to-line mapping.
- Hazard/score rules, reason codes, and per-LOB referral thresholds.
- Required document types and completeness rules.
- Extraction field mappings where semantics differ — sales vs payroll vs TIV vs face amount; named insured on personal vs commercial.
- Evaluation metrics (automation, false completes, failed calls) reported per LOB, never pooled.
