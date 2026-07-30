# Real-world insurance scenario pack

These scenarios live in code at `src/insureflow/testing/realworld_scenarios.py`.
Each mimics a broker submission (ACORD XML + loss run + SOV + inspection) with
intentional risk signals covering production decision paths.

## Run

```bash
PYTHONPATH=src python scripts/pilot/run_realworld_scenarios.py
PYTHONPATH=src python -m pytest tests/test_realworld_scenarios.py -q
```

## Conditions covered

| ID | Condition | Expected gate |
|----|-----------|---------------|
| clean_retail_accept_path | Preferred retail, inland TX, clean losses | Appetite pass |
| coastal_fl_appetite_decline | Miami Beach FL CAT zip | Hard decline |
| excluded_naics_decline | Hotel NAICS 7211 | Hard decline |
| mega_tiv_decline | Single loc TIV > $25M | Hard decline |
| loss_ratio_hard_decline | ~92% LR | Hard decline |
| loss_ratio_uw_referral | ~72% LR | Appetite referral |
| missing_docs_refer | ACORD only | Validation REFER |
| manuscript_terms_refer | Non-standard endorsements | REFER / review |
| hawaii_appetite_decline | HI location | Hard decline |
| construction_naics_referral | NAICS 2362 | Appetite referral |
| government_entity_referral | Government named insured | Appetite referral |
| coastal_tx_appetite_decline | Galveston TX zip | Hard decline |
| below_min_tiv_referral | TIV < $50k | Appetite referral |
| cope_discrepancy_package | ACORD vs inspection conflicts | Human review |

These are **synthetic but realistic**. They do not replace LexisNexis/Guidewire live sandboxes — they prove the insurance module behaves correctly in all decision states before real vendor data is available.
