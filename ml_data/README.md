# ML training datasets

Drop labeled CSVs here to train production models instead of synthetic bootstraps.

## Layout

```
ml_data/
  loss_prediction.csv
  fraud_detection.csv
  premium_optimizer.csv
  churn_prediction.csv
```

Or per-model folders: `ml_data/<model_type>/train.csv`.

## Schema

Columns should match `insureflow.ml.features.DEFAULT_FEATURE_NAMES` plus a `target` column:

- Numeric features (missing → 0)
- `target` — regression or binary label depending on model

Train:

```bash
PYTHONPATH=src python -c "from insureflow.ml.training import train_all_models; print(train_all_models(force=True))"
```

Refuse synthetic fallback:

```bash
PYTHONPATH=src python -c "from insureflow.ml.training import train_all_models; train_all_models(force=True, allow_synthetic=False)"
```
