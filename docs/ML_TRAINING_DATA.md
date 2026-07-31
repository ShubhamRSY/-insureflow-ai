# ML Training Data — Real-Data CSV Schema

Rytera's ML models train on **real labeled data** when it is present at
`ml_data/<model_type>.csv` (one CSV per model type). If a CSV is missing, the
training pipeline falls back to synthetic bootstrap data so the product keeps
working during pilots — but real models require real rows.

## How it works

- Every model type expects a CSV with its **feature columns in order** plus a
  `target` column (see schemas below).
- `load_training_csv` (`src/insureflow/ml/training.py`) zero-fills any missing
  feature column, so a **subset of columns is fine** — only the columns you
  include are used.
- `target` is a numeric label:
  - **classification models** (fraud, churn, mortgage default, lending default):
    `1` = event (fraud / churn / default), `0` = no event. `0.5` is treated as
    "refer" for loss/decision-derived targets.
  - **regression models** (loss prediction, premium optimizer): a positive
    amount (expected loss in $, optimal premium in $).

## Quick start

```bash
# 1. (optional) auto-build CSVs from persisted audit outcomes
PYTHONPATH=src python scripts/train_ml.py --export

# 2. see what's trained and which CSVs are detected
PYTHONPATH=src python scripts/train_ml.py --status

# 3. train everything — real CSV wins, synthetic only as fallback
PYTHONPATH=src python scripts/train_ml.py

# 4. or train one model from an explicit real CSV (fail on synthetic)
PYTHONPATH=src python scripts/train_ml.py --only loss_prediction --csv ml_data/loss_prediction.csv --no-synthetic

# same via the API
curl -X POST "https://ryterainc.com/ml/train/loss_prediction?allow_synthetic=true"
```

Drop a header row + rows into `ml_data/loss_prediction.csv` and it is picked up
automatically on the next `train_all_models()` call (or `POST /ml/train`).

## Schemas

### `loss_prediction.csv` — expected loss (regression)

```
revenue,employees,years_in_business,prior_claims_count,prior_claims_total,tiv,requested_premium,loss_ratio,credit_score,dti_ratio,ltv_ratio,property_age,construction_type,occupancy_type,protection_class,roof_type,year_built,square_footage,num_stories,sprinkler_system,alarm_system,prior_cancellations,month_of_binding,quarter,revenue_per_employee,claims_per_year,tiv_to_revenue,premium_to_tiv,risk_score_raw,target
10000000,120,15,3,150000,25000000,45000,0.65,720,0.35,0.8,25,0,0,1,1,1999,80000,3,1,1,1,6,3,83333.33,0.2,2.5,0.0018,0.2,65000
```

Only `tiv`, `loss_ratio`, `prior_claims_count`, `revenue`, `years_in_business`,
`credit_score`, `requested_premium` are typically populated — the rest can be
omitted (they default to `0`).

### `fraud_detection.csv` — fraud probability (classification)

Same 29 feature columns as `loss_prediction`. `target` = `1` fraud, `0` clean.

### `premium_optimizer.csv` — optimal premium (regression)

Same 29 feature columns. `target` = optimal premium in $.

### `churn_prediction.csv` — non-renewal risk (classification)

Same 29 feature columns. `target` = `1` churn, `0` renew.

### `mortgage_default_risk.csv` — mortgage default (classification)

```
credit_score,dti_ratio,ltv_ratio,loan_amount,annual_income,reserves,employment_years,self_employment_income,utilization_rate,derogatory_marks,property_age,bankruptcies,foreclosures,prior_cancellations,loan_to_income,reserves_to_loan,utilization_norm,income_stability,target
720,36,78,400000,120000,45000,8,0,35,1,15,0,0,0,3.33,0.1125,0.35,0.8,0
580,48,92,350000,70000,2500,2,40000,72,3,40,1,0,1,5.0,0.007,0.72,0.2,1
```

Engineered columns (`loan_to_income`, `reserves_to_loan`, `utilization_norm`,
`income_stability`) can be omitted — they default to `0` and the model still
trains on the raw columns.

### `lending_default_risk.csv` — lending default (classification)

```
loan_segment_business,credit_score,dti_ratio,annual_income,loan_amount,years_in_business,employment_years,dscr,current_ratio,leverage_ratio,profit_margin,debt_service,ebitda,total_assets,total_liabilities,bankruptcies,foreclosures,loan_to_income,target
1,0,0,2000000,500000,12,0,1.35,1.8,2.5,12.5,120000,420000,6000000,2500000,0,0,0.25,0
0,590,48,60000,25000,0,3,0,0,0,0,0,0,0,0,0,0,0.42,1
```

`loan_segment_business` = `1` business, `0` consumer. Business rows typically
leave credit fields at `0`; consumer rows leave DSCR/leverage fields at `0`.

## Where the real data comes from

1. **`scripts/train_ml.py --export`** scans `audit_logs/` (insurance
   `pipeline_summary.json`, lending `lending/*.json`, mortgage `mortgage*.jsonl`)
   and derives a `target` from each file's decision.
2. **Post-pilot feedback loop**: human-underwriter decisions/overrides on
   production submissions are the highest-quality labels — feed them into the
   matching CSV and retrain.
3. **Vendor data** (LexisNexis CLUE, Verisk A-PLUS) adds loss-history features
   to the insurance CSVs as pilot contracts come online.
