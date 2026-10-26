# RAG Corpus: Health Insurance

Health & Employee Benefits Underwriting Guide · Version 3.0 · Effective 2026-01-01

## LOB metadata
- LOB slug: health
- Products: 30
- Categories: 8
- Standards: ACA (PHSA §2702/2704), NAIC model regs, CMS Medicare guidance, state DOI rate filing
- Underwriting authority: Major medical is guaranteed-issue. Supplemental lines carry medical/occupational authority to $100K benefit; above refers.

## How to use for RAG
- Index each `documents/<product>.md` as one or more chunks (split on the `##` sections).
- Bias retrieval to this LOB (or category) when the submission's line is known.
- The sections map to likely underwriter questions: eligibility, decline, documents, coverages, exclusions, limits, rating, authority.

## Categories

| id | name | summary |
|---|---|---|
| individual | Individual & Family Health Insurance | ACA Marketplace metal-tier plans and off-exchange major medical. |
| family_floater | Family Health Plans | A single policy covering the household under one aggregate family deductible. |
| critical_illness | Critical Illness Insurance | Standalone lump-sum critical illness and disease-specific (cancer / cardiac / diabetes-kidney) cover. |
| senior | Senior Citizen Health Plans | Medicare Supplement (Medigap Plans A/G/N) and Medicare Advantage. |
| group | Group / Corporate Health | ACA small-group (community-rated) and ERISA large-group (fully insured or self-funded). |
| top_up | Top-up / Super Top-up | Supplemental / gap coverage above a high-deductible base plan — per-incident or annual-aggregate deductible. |
| personal_accident | Personal Accident Insurance | Accidental Death & Dismemberment (AD&D) and accident indemnity — individual, family, group. |
| disability | Disability Insurance | Short-term and long-term disability income replacement. |

## Product catalog

| product_id | name | category | status | docs | coverages | forms |
|---|---|---|---|---|---|---|
| aca_marketplace_plan | ACA Marketplace Plan | individual | live | 7 | 4 | 0 |
| off_exchange_major_medical | Off-Exchange Major Medical | individual | live | 6 | 1 | 0 |
| short_term_limited_duration | Short-Term Limited Duration Insurance | individual | live | 7 | 1 | 0 |
| hdhp_hsa_qualified | HSA-Qualified HDHP | individual | live | 6 | 1 | 0 |
| catastrophic_plan | ACA Catastrophic Plan | individual | live | 6 | 1 | 0 |
| family_health_plan | Family Health Plan | family_floater | live | 7 | 1 | 0 |
| family_hdhp_hsa_qualified | Family HSA-Qualified HDHP | family_floater | live | 7 | 1 | 0 |
| family_extended_dependents | Family Plan — Extended Dependent Coverage | family_floater | live | 7 | 1 | 0 |
| critical_illness_standalone | Critical Illness (Standalone) | critical_illness | live | 7 | 1 | 0 |
| disease_specific_critical_illness | Disease-Specific Critical Illness | critical_illness | live | 6 | 3 | 0 |
| critical_illness_rider | Critical Illness Rider | critical_illness | live | 7 | 1 | 0 |
| critical_illness_multistage | Multi-Stage Critical Illness | critical_illness | live | 8 | 1 | 0 |
| medicare_supplement | Medicare Supplement (Medigap) | senior | live | 7 | 4 | 0 |
| medicare_advantage | Medicare Advantage (Part C) | senior | live | 6 | 1 | 0 |
| medigap_high_deductible_plan_g | Medigap High-Deductible Plan G | senior | live | 7 | 2 | 0 |
| medicare_advantage_snp | Medicare Advantage Special Needs Plan | senior | live | 7 | 1 | 0 |
| medicare_part_d | Medicare Part D (Prescription Drug Plan) | senior | live | 7 | 1 | 0 |
| small_group_health | Small Group Health Plan | group | live | 7 | 1 | 0 |
| large_group_health | Large Group Health Plan | group | live | 8 | 2 | 0 |
| association_health_plan | Association Health Plan | group | live | 7 | 1 | 0 |
| public_sector_group_health | Public Sector Group Health | group | live | 7 | 1 | 0 |
| level_funded_group_health | Level-Funded Group Health | group | live | 8 | 1 | 0 |
| supplemental_gap_coverage | Supplemental / Gap Health Coverage | top_up | live | 6 | 2 | 0 |
| hospital_indemnity | Hospital Indemnity | top_up | live | 6 | 1 | 0 |
| add_accident_indemnity | AD&D / Accident Indemnity | personal_accident | live | 6 | 3 | 0 |
| standalone_add | Standalone AD&D | personal_accident | live | 7 | 1 | 0 |
| short_term_disability | Short-Term Disability Income | disability | live | 7 | 1 | 0 |
| long_term_disability | Long-Term Disability Income | disability | live | 7 | 1 | 0 |
| disability_ptd | Permanent Total Disability | disability | live | 7 | 1 | 0 |
| disability_ppd | Permanent Partial Disability | disability | live | 6 | 13 | 0 |

## Product summaries

### aca_marketplace_plan — ACA Marketplace Plan
Individual/family major medical sold on the ACA exchange — Bronze, Silver, Gold, or Platinum metal tier. Guaranteed issue; premium-tax-credit eligible.
- Full guide entry: `documents/aca_marketplace_plan.md`

### off_exchange_major_medical — Off-Exchange Major Medical
ACA-compliant individual major medical sold directly by the carrier — not subsidy-eligible, but the same guaranteed-issue floor as a Marketplace plan.
- Full guide entry: `documents/off_exchange_major_medical.md`

### short_term_limited_duration — Short-Term Limited Duration Insurance
Not ACA-compliant — the one genuinely medically-underwritten individual health product in the US market. Banned or restricted in several states.
- Full guide entry: `documents/short_term_limited_duration.md`

### hdhp_hsa_qualified — HSA-Qualified HDHP
Guaranteed-issue ACA plan with a deductible at or above the IRS HSA-qualifying minimum, enabling tax-advantaged HSA contributions.
- Full guide entry: `documents/hdhp_hsa_qualified.md`

### catastrophic_plan — ACA Catastrophic Plan
Guaranteed-issue, high-deductible ACA plan restricted to applicants under 30 or with a documented hardship/affordability exemption.
- Full guide entry: `documents/catastrophic_plan.md`

### family_health_plan — Family Health Plan
A single policy covering the applicant and dependents under one aggregate family deductible — the standard structure for a US family major-medical plan.
- Full guide entry: `documents/family_health_plan.md`

### family_hdhp_hsa_qualified — Family HSA-Qualified HDHP
Family-tier HSA-qualified HDHP — aggregate family deductible at or above the IRS family HSA-qualifying minimum.
- Full guide entry: `documents/family_hdhp_hsa_qualified.md`

### family_extended_dependents — Family Plan — Extended Dependent Coverage
Family plan covering dependents to age 26 automatically, plus disabled adult dependents past 26 with certification on file.
- Full guide entry: `documents/family_extended_dependents.md`

### critical_illness_standalone — Critical Illness (Standalone)
Lump-sum indemnity payment on first diagnosis of a covered condition (cancer, heart attack, stroke, kidney failure). Supplemental — does not replace major medical.
- Full guide entry: `documents/critical_illness_standalone.md`

### disease_specific_critical_illness — Disease-Specific Critical Illness
Single-condition lump-sum cover — Cancer Care, Cardiac Care, or Diabetes/Kidney Care — narrower and cheaper than standalone CI.
- Full guide entry: `documents/disease_specific_critical_illness.md`

### critical_illness_rider — Critical Illness Rider
Attaches to an existing base policy rather than standing alone — no independent free-look period or policy fee; terminates if the base policy lapses.
- Full guide entry: `documents/critical_illness_rider.md`

### critical_illness_multistage — Multi-Stage Critical Illness
Pays a graduated percentage of the benefit at increasing severity stages instead of one lump sum on first diagnosis.
- Full guide entry: `documents/critical_illness_multistage.md`

### medicare_supplement — Medicare Supplement (Medigap)
Standardized Plans A, G, and N — pays Original Medicare's cost-sharing gaps. Guaranteed issue for 6 months after Part B starts; medically underwritten outside that window.
- Full guide entry: `documents/medicare_supplement.md`

### medicare_advantage — Medicare Advantage (Part C)
A Medicare-replacement plan administered by a private carrier under CMS capitation — always guaranteed issue during an eligible enrollment period.
- Full guide entry: `documents/medicare_advantage.md`

### medigap_high_deductible_plan_g — Medigap High-Deductible Plan G
CMS-standardized Medigap variant — much lower premium in exchange for a high annual deductible (~$2,870) before the plan starts paying.
- Full guide entry: `documents/medigap_high_deductible_plan_g.md`

### medicare_advantage_snp — Medicare Advantage Special Needs Plan
Restricted-enrollment Medicare Advantage plan for applicants with a qualifying chronic condition (C-SNP) or dual Medicare/Medicaid eligibility (D-SNP).
- Full guide entry: `documents/medicare_advantage_snp.md`

### medicare_part_d — Medicare Part D (Prescription Drug Plan)
Standalone prescription drug plan every Medigap disclosure points to — guaranteed issue, with a permanent late-enrollment penalty for any coverage gap.
- Full guide entry: `documents/medicare_part_d.md`

### small_group_health — Small Group Health Plan
ACA small-group market (1-50 FTE employees) — guaranteed issue, community-rated, no group-level experience rating.
- Full guide entry: `documents/small_group_health.md`

### large_group_health — Large Group Health Plan
51+ employee groups — real experience rating, and (if self-funded) ERISA preemption of most state-mandated-benefit laws.
- Full guide entry: `documents/large_group_health.md`

### association_health_plan — Association Health Plan
DOL-regulated ERISA multi-employer plan sponsored by a bona fide trade, professional, or industry association covering multiple small employers.
- Full guide entry: `documents/association_health_plan.md`

### public_sector_group_health — Public Sector Group Health
Municipal, county, or state-government employer group plan — often self-funded, with different ACA employer-mandate exemption treatment.
- Full guide entry: `documents/public_sector_group_health.md`

### level_funded_group_health — Level-Funded Group Health
Structurally self-funded, sized for small employers, with a stop-loss policy capping the employer's claims exposure.
- Full guide entry: `documents/level_funded_group_health.md`

### supplemental_gap_coverage — Supplemental / Gap Health Coverage
Sits above a high-deductible base plan and pays once its deductible is exhausted — Standard Gap (per-incident) or Super Gap (annual aggregate).
- Full guide entry: `documents/supplemental_gap_coverage.md`

### hospital_indemnity — Hospital Indemnity
Fixed dollar-per-day-of-hospitalization cash payout — pays regardless of the base plan's deductible or coinsurance and independent of actual billed charges.
- Full guide entry: `documents/hospital_indemnity.md`

### add_accident_indemnity — AD&D / Accident Indemnity
Accidental Death & Dismemberment and accident indemnity cover — pays only for accidental injury or death, not illness. Individual, family, or group.
- Full guide entry: `documents/add_accident_indemnity.md`

### standalone_add — Standalone AD&D
Pure death/dismemberment schedule only — no accident-medical-expense or weekly-indemnity benefit. Cheaper and narrower than the combined AD&D / Accident Indemnity product.
- Full guide entry: `documents/standalone_add.md`

### short_term_disability — Short-Term Disability Income
Weekly income-replacement benefit, short elimination period, benefit period typically capped at 2 years. Coordinates with mandatory state SDI in CA/NY/NJ/RI/HI.
- Full guide entry: `documents/short_term_disability.md`

### long_term_disability — Long-Term Disability Income
Monthly income-replacement benefit, longer elimination period, benefit period runs to a fixed term or to age 65.
- Full guide entry: `documents/long_term_disability.md`

### disability_ptd — Permanent Total Disability
Lump-sum-or-extended-benefit payout triggered by a permanent and total inability to work — not a periodic income-replacement benefit like STD/LTD.
- Full guide entry: `documents/disability_ptd.md`

### disability_ppd — Permanent Partial Disability
Scheduled-injury lump sum (loss of a limb, sight, or hearing) — no income proof required since the payout is fixed by the schedule, not earnings.
- Full guide entry: `documents/disability_ppd.md`
