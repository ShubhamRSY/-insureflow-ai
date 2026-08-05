# ML training datasets

Labeled CSVs here train **production** models. Synthetic bootstrap is off by default.

## Layout

```
ml_data/
  loss_prediction.csv
  fraud_detection.csv
  premium_optimizer.csv
  churn_prediction.csv
  mortgage_default_risk.csv
  lending_default_risk.csv
```

## Build from real sources

```bash
# Wisconsin municipal claims + audit outcomes + UW-rule seeds for mortgage/lending
PYTHONPATH=src python scripts/build_ml_training_data.py

# Public downloads (SBA, UCI, insurance claims) + GSE/HMDA if present under external_data/mortgage/
PYTHONPATH=src python scripts/ingest_public_datasets.py

# or via trainer
PYTHONPATH=src python scripts/train_ml.py --build-data
```

Mortgage priority: Fannie/Freddie loan performance → HMDA LAR → ISLR/AER proxies → UW-rule seed.
See `external_data/README.md` and `examples/mortgage/gse_sample/`.

## Train (real data only)

```bash
PYTHONPATH=src python scripts/train_ml.py
PYTHONPATH=src python scripts/train_ml.py --status
```

Demo-only synthetic fallback:

```bash
PYTHONPATH=src python scripts/train_ml.py --allow-synthetic
```

## Schema

See `docs/ML_TRAINING_DATA.md`. Columns match each model's feature list plus `target`.
