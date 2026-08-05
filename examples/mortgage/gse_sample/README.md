# Mortgage GSE / HMDA sample files

Tiny **layout fixtures** for mapper unit tests — not production training data.

| Path | Role |
|------|------|
| `fannie/Acquisition_*.txt` | Fannie Mae acquisition (pipe-delimited) |
| `fannie/Performance_*.txt` | Fannie Mae monthly performance |
| `hmda/hmda_lar_sample.csv` | HMDA LAR denial/origination proxy |

Production files go under `external_data/mortgage/` (see that README). Then:

```bash
PYTHONPATH=src python scripts/ingest_public_datasets.py --train
```
