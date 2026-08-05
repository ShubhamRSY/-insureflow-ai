# External public training datasets

Downloaded reference data used by `scripts/ingest_public_datasets.py`.

| Path | Source | Service |
|------|--------|---------|
| `insurance/insurance_claims.csv` | Public insurance claims (fraud-labeled) | Insurance |
| `lending/sba_7a_fy2020_sample.csv` | SBA FOIA 7(a) (~80k rows) | Lending |
| `lending/german_credit/` | UCI Statlog German Credit | Lending |
| `lending/credit_card_default.csv` | UCI Default of Credit Card Clients | Lending |
| `mortgage/fannie/Acquisition_*.txt` | Fannie Mae SF Loan Performance (acq) | Mortgage ★ |
| `mortgage/fannie/Performance_*.txt` | Fannie Mae SF Loan Performance (perf) | Mortgage ★ |
| `mortgage/freddie/historical_data_*.txt` | Freddie Mac SFLLD origination | Mortgage ★ |
| `mortgage/freddie/historical_data_time_*.txt` | Freddie Mac SFLLD performance | Mortgage ★ |
| `mortgage/hmda/*.csv` | HMDA LAR (denial proxy if no GSE) | Mortgage |
| `mortgage/Default.csv` | ISLR Default (credit-risk proxy) | Mortgage |
| `mortgage/CreditCard.csv` | AER CreditCard (credit-risk proxy) | Mortgage |

★ **Gold standard** — register and download from Fannie Mae / Freddie Mac (login required). Drop files under the paths above; ingest prefers Fannie → Freddie → HMDA → ISLR/AER proxies → UW-rule seed.

Layout fixtures for CI live in `examples/mortgage/gse_sample/`.

```bash
PYTHONPATH=src python scripts/ingest_public_datasets.py --train
```
